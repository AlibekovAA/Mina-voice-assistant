import asyncio
from collections.abc import Mapping
import time

import edge_tts
import miniaudio
import numpy as np
from numpy.typing import NDArray

from assistant.audio.models import AudioData, AudioFormat
from assistant.config import TtsConfig
from assistant.constants import TTS_DEFAULT_TIMEOUT_SECONDS
from assistant.logger import Logger
from assistant.tts.exceptions import TtsError, TtsNotReadyError

try:
    import aiohttp

    _NETWORK_ERRORS: tuple[type[BaseException], ...] = (aiohttp.ClientError,)
except ImportError:
    _NETWORK_ERRORS = ()

_TTS_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    OSError,
    MemoryError,
    TimeoutError,
    miniaudio.DecodeError,
    miniaudio.MiniaudioError,
    *_NETWORK_ERRORS,
)
_LOG = Logger.get(__name__)


class EdgeTts:
    def __init__(self, config: TtsConfig) -> None:
        self._config = config
        self._ready = False
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_ready(self) -> bool:
        return self._ready

    def initialize(self) -> None:
        if self._ready:
            return

        if not self._config.voice.strip():
            raise TtsError("TTS voice must not be empty")

        self._loop = asyncio.new_event_loop()
        self._ready = True
        _LOG.info(
            "TTS ready (engine=edge-tts, voice=%s, sample_rate=%d)",
            self._config.voice,
            self._config.sample_rate,
        )

    def shutdown(self) -> None:
        self._ready = False
        loop = self._loop
        self._loop = None
        if loop is not None and not loop.is_closed():
            loop.close()

    def synthesize(self, text: str) -> AudioData:
        if not self._ready or self._loop is None:
            raise TtsNotReadyError("Text-to-speech is not initialized")

        cleaned = " ".join(text.split())
        if not cleaned:
            raise TtsError("Cannot synthesize empty text")

        started = time.monotonic()
        try:
            mp3 = self._loop.run_until_complete(
                asyncio.wait_for(self._fetch_mp3(cleaned), timeout=TTS_DEFAULT_TIMEOUT_SECONDS)
            )
            samples = self._decode_mp3(mp3)
        except TimeoutError as error:
            raise TtsError(f"TTS timed out after {TTS_DEFAULT_TIMEOUT_SECONDS:.0f}s ({len(cleaned)} chars)") from error
        except _TTS_ERRORS as error:
            raise TtsError(f"Failed to synthesize speech: {error}") from error

        if samples.size == 0:
            raise TtsError("Synthesized audio is empty")

        _LOG.debug(
            "Synthesized %d chars in %.2fs",
            len(cleaned),
            time.monotonic() - started,
        )

        return AudioData(
            samples=samples,
            format=AudioFormat(sample_rate=self._config.sample_rate, channels=1),
        )

    async def _fetch_mp3(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(
            text,
            voice=self._config.voice,
            rate=self._config.rate,
        )
        chunks: list[bytes] = []

        async for item in communicate.stream():
            payload = _as_mapping(item)
            if payload.get("type") != "audio":
                continue

            data = payload.get("data")
            if isinstance(data, (bytes, bytearray)):
                chunks.append(bytes(data))

        if not chunks:
            raise TtsError("edge-tts returned no audio")

        return b"".join(chunks)

    def _decode_mp3(self, data: bytes) -> NDArray[np.float32]:
        decoded = miniaudio.decode(
            data,
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=self._config.sample_rate,
        )
        return np.frombuffer(decoded.samples, dtype=np.float32).copy()


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TtsError(f"Unexpected edge-tts payload type: {type(value)!r}")

    return value
