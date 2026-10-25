import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import queue
import threading
import time

from aiohttp import ClientError
import edge_tts
from edge_tts.exceptions import EdgeTTSException
import miniaudio
import numpy as np

from assistant.audio.player import PcmQueue
from assistant.config import TtsConfig
from assistant.constants.tts import TTS_DEFAULT_TIMEOUT_SECONDS
from assistant.core.exceptions import TtsError
from assistant.logger import Logger

_LOG = Logger.get(__name__)
_TTS_ERRORS = (ClientError, EdgeTTSException, OSError, RuntimeError, ValueError, TypeError)


@dataclass(slots=True)
class StreamSpeakTiming:
    first_pcm_ms: float = 0.0
    tts_ms: float = 0.0


@dataclass(slots=True)
class _DecodeState:
    error: Exception | None = None


class _Mp3Stream:
    def __init__(self) -> None:
        self.ffi_handle: object = None
        self.error_in_readcallback: Exception | None = None
        self._chunks: queue.Queue[bytes | None] = queue.Queue()
        self._buffer = bytearray()
        self._finished = False

    def feed(self, chunk: bytes) -> None:
        self._chunks.put(chunk)

    def finish(self) -> None:
        self._chunks.put(None)

    def read(self, num_bytes: int) -> bytes:
        while not self._buffer and not self._finished:
            chunk = self._chunks.get()
            if chunk is None:
                self._finished = True
                break
            self._buffer.extend(chunk)

        result = bytes(self._buffer[:num_bytes])
        del self._buffer[:num_bytes]
        return result

    def seek(self, _offset: int, _origin: object) -> bool:
        return False


class EdgeTts:
    def __init__(self, config: TtsConfig) -> None:
        self._config = config
        self._ready = False

    @property
    def sample_rate(self) -> int:
        return self._config.sample_rate

    def initialize(self) -> None:
        if self._ready:
            return

        if not self._config.voice.strip():
            raise TtsError("TTS voice must not be empty")

        self._ready = True
        _LOG.info(
            "TTS ready (engine=edge-tts, voice=%s, sample_rate=%d)",
            self._config.voice,
            self._config.sample_rate,
        )

    def shutdown(self) -> None:
        self._ready = False

    def speak_stream(self, text: str, pcm_queue: PcmQueue) -> StreamSpeakTiming:
        if not self._ready:
            raise TtsError("Text-to-speech is not initialized")

        cleaned = " ".join(text.split())
        if not cleaned:
            raise TtsError("Cannot synthesize empty text")

        timing = StreamSpeakTiming()
        started = time.perf_counter()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._stream_pcm(cleaned, pcm_queue, timing, started))
        except TtsError:
            raise
        except TimeoutError as error:
            raise TtsError(f"TTS timed out after {TTS_DEFAULT_TIMEOUT_SECONDS:.0f}s ({len(cleaned)} chars)") from error
        except (miniaudio.DecodeError, miniaudio.MiniaudioError) as error:
            raise TtsError(f"Failed to decode TTS audio: {error}") from error
        except _TTS_ERRORS as error:
            raise TtsError(f"Failed to synthesize speech: {error}") from error
        finally:
            loop.close()

        timing.tts_ms = (time.perf_counter() - started) * 1000.0
        if timing.first_pcm_ms <= 0.0:
            raise TtsError("edge-tts returned no audio")

        return timing

    async def _stream_pcm(
        self,
        text: str,
        pcm_queue: PcmQueue,
        timing: StreamSpeakTiming,
        started: float,
    ) -> None:
        communicate = edge_tts.Communicate(
            text,
            voice=self._config.voice,
            rate=self._config.rate,
        )
        source = _Mp3Stream()
        decode_state = _DecodeState()
        decoder_thread: threading.Thread | None = None

        stream = communicate.stream().__aiter__()
        try:
            while True:
                try:
                    item = await asyncio.wait_for(anext(stream), timeout=TTS_DEFAULT_TIMEOUT_SECONDS)
                except StopAsyncIteration:
                    break

                payload = _as_mapping(item)
                if payload.get("type") != "audio":
                    continue

                data = payload.get("data")
                if not isinstance(data, (bytes, bytearray)):
                    continue
                if decoder_thread is None:
                    decoder_thread = threading.Thread(
                        target=self._decode_stream,
                        args=(source, pcm_queue, timing, started, decode_state),
                        name="tts-decode",
                        daemon=True,
                    )
                    decoder_thread.start()
                source.feed(bytes(data))
        finally:
            if decoder_thread is not None:
                source.finish()
                decoder_thread.join()

        if decode_state.error is not None and not isinstance(
            decode_state.error,
            (miniaudio.DecodeError, miniaudio.MiniaudioError),
        ):
            raise decode_state.error

    def _decode_stream(
        self,
        source: _Mp3Stream,
        pcm_queue: PcmQueue,
        timing: StreamSpeakTiming,
        started: float,
        state: _DecodeState,
    ) -> None:
        try:
            chunks = miniaudio.stream_any(
                source,
                source_format=miniaudio.FileFormat.MP3,
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=1,
                sample_rate=self._config.sample_rate,
            )
            for samples in chunks:
                chunk = np.asarray(samples, dtype=np.float32)
                if chunk.size == 0:
                    continue
                pcm_queue.put(np.ascontiguousarray(chunk))
                if timing.first_pcm_ms <= 0.0:
                    timing.first_pcm_ms = (time.perf_counter() - started) * 1000.0
        except (
            miniaudio.DecodeError,
            miniaudio.MiniaudioError,
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
        ) as error:
            state.error = error


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TtsError(f"Unexpected edge-tts payload type: {type(value)!r}")

    return value
