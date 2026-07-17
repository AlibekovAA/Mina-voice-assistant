from collections.abc import Callable
import queue
import threading

import numpy as np
from numpy.typing import NDArray
import sounddevice as sd

from assistant.audio.models import AudioData
from assistant.constants.audio import AUDIO_LEVEL_CALLBACK_STRIDE
from assistant.core.exceptions import AudioPlaybackError
from assistant.logger import Logger

_LOG = Logger.get(__name__)

LevelCallback = Callable[[float], None]
type PcmChunk = NDArray[np.float32]
type PcmQueue = queue.SimpleQueue[PcmChunk | None]


class AudioPlayer:
    def __init__(self) -> None:
        self._stream: sd.OutputStream | None = None
        self._buffer: NDArray[np.float32] | None = None
        self._pcm_queue: PcmQueue | None = None
        self._pending: NDArray[np.float32] | None = None
        self._stream_ended = False
        self._offset = 0
        self._done = threading.Event()
        self._on_level: LevelCallback | None = None
        self._level_tick = 0

    def play(
        self,
        audio: AudioData,
        *,
        device: int | None = None,
        on_level: LevelCallback | None = None,
    ) -> None:
        audio.format.validate()

        if audio.samples.size == 0:
            raise AudioPlaybackError("Cannot play empty audio")

        self.stop()

        samples = self._prepare_output(audio)
        self._buffer = samples
        self._pcm_queue = None
        self._pending = None
        self._stream_ended = True
        self._offset = 0
        self._on_level = on_level
        self._level_tick = 0
        self._done.clear()

        try:
            self._stream = sd.OutputStream(
                samplerate=audio.format.sample_rate,
                channels=audio.format.channels,
                device=device,
                dtype="float32",
                callback=self._on_audio,
                finished_callback=self._done.set,
            )
            self._stream.start()
        except sd.PortAudioError as error:
            self._reset_state()
            raise AudioPlaybackError(
                "Failed to play audio "
                f"(device={device}, sample_rate={audio.format.sample_rate}, "
                f"channels={audio.format.channels}, frames={samples.shape[0]}): {error}"
            ) from error

        self._wait()

    def play_stream(
        self,
        pcm_queue: PcmQueue,
        *,
        sample_rate: int,
        channels: int = 1,
        device: int | None = None,
        on_level: LevelCallback | None = None,
    ) -> None:
        if sample_rate <= 0:
            raise AudioPlaybackError(f"Invalid sample_rate: {sample_rate}")
        if channels < 1:
            raise AudioPlaybackError(f"Invalid channels: {channels}")

        self.stop()

        self._buffer = None
        self._pcm_queue = pcm_queue
        self._pending = np.zeros((0, channels), dtype=np.float32)
        self._stream_ended = False
        self._offset = 0
        self._on_level = on_level
        self._level_tick = 0
        self._done.clear()

        try:
            self._stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=channels,
                device=device,
                dtype="float32",
                callback=self._on_audio,
                finished_callback=self._done.set,
            )
            self._stream.start()
        except sd.PortAudioError as error:
            self._reset_state()
            raise AudioPlaybackError(
                "Failed to start streamed playback "
                f"(device={device}, sample_rate={sample_rate}, channels={channels}): {error}"
            ) from error

        self._wait()

    def stop(self) -> None:
        stream = self._stream
        self._reset_state()

        if stream is None:
            return

        try:
            if stream.active:
                stream.abort()
            stream.close()
        except sd.PortAudioError as error:
            raise AudioPlaybackError(f"Failed to stop playback: {error}") from error

    def _wait(self) -> None:
        self._done.wait()

        stream = self._stream
        self._stream = None
        self._buffer = None
        self._pcm_queue = None
        self._pending = None
        self._offset = 0
        self._on_level = None
        self._level_tick = 0

        if stream is None:
            return

        try:
            if stream.active:
                stream.stop()
            stream.close()
        except sd.PortAudioError as error:
            raise AudioPlaybackError(f"Failed while waiting for playback: {error}") from error

    def _on_audio(
        self,
        outdata: NDArray[np.float32],
        frames: int,
        _time: object,
        status: object,
    ) -> None:
        if status:
            _LOG.warning("Output stream status: %s", status)

        if self._pcm_queue is not None:
            self._fill_stream_outdata(outdata, frames)
            return

        if self._buffer is None:
            outdata.fill(0)
            raise sd.CallbackStop

        remaining = self._buffer.shape[0] - self._offset
        if remaining <= 0:
            outdata.fill(0)
            raise sd.CallbackStop

        chunk_size = min(frames, remaining)
        outdata[:chunk_size] = self._buffer[self._offset : self._offset + chunk_size]
        self._emit_level(outdata, chunk_size)

        if chunk_size < frames:
            outdata[chunk_size:].fill(0)
            self._offset += chunk_size
            raise sd.CallbackStop

        self._offset += chunk_size

    def _fill_stream_outdata(self, outdata: NDArray[np.float32], frames: int) -> None:
        written = 0
        while written < frames:
            pending = self._pending
            if pending is None:
                outdata[written:].fill(0)
                raise sd.CallbackStop

            if pending.shape[0] == 0:
                if not self._pull_stream_chunk():
                    outdata[written:].fill(0)
                    if self._stream_ended:
                        raise sd.CallbackStop
                    return
                continue

            take = min(frames - written, pending.shape[0])
            outdata[written : written + take] = pending[:take]
            self._emit_level(outdata[written : written + take], take)
            self._pending = pending[take:]
            written += take

    def _pull_stream_chunk(self) -> bool:
        pcm_queue = self._pcm_queue
        if pcm_queue is None:
            self._stream_ended = True
            return False

        try:
            chunk = pcm_queue.get_nowait()
        except queue.Empty:
            return False

        if chunk is None:
            self._stream_ended = True
            return False

        prepared = self._prepare_pcm_chunk(chunk)
        if prepared.size == 0:
            return True

        pending = self._pending
        if pending is None or pending.shape[0] == 0:
            self._pending = prepared
        else:
            self._pending = np.concatenate((pending, prepared), axis=0)
        return True

    def _emit_level(self, chunk: NDArray[np.float32], chunk_size: int) -> None:
        if self._on_level is None or chunk_size <= 0:
            return

        self._level_tick += 1
        if self._level_tick % AUDIO_LEVEL_CALLBACK_STRIDE != 0:
            return

        level_chunk = chunk[:chunk_size]
        if level_chunk.ndim == 2:
            level_chunk = level_chunk[:, 0]
        level = float(np.linalg.norm(level_chunk) / np.sqrt(level_chunk.size))
        self._on_level(level)

    def _prepare_output(self, audio: AudioData) -> NDArray[np.float32]:
        return self._prepare_pcm_chunk(np.asarray(audio.samples, dtype=np.float32), channels=audio.format.channels)

    def _prepare_pcm_chunk(
        self,
        samples: NDArray[np.float32],
        *,
        channels: int | None = None,
    ) -> NDArray[np.float32]:
        data = np.asarray(samples, dtype=np.float32)
        channel_count = channels
        if channel_count is None:
            pending = self._pending
            channel_count = 1 if pending is None or pending.ndim < 2 else pending.shape[1]

        if data.ndim == 1:
            if channel_count != 1:
                raise AudioPlaybackError(f"Mono buffer cannot be played with channels={channel_count}")
            return np.ascontiguousarray(data.reshape(-1, 1))

        if data.ndim == 2:
            if data.shape[1] != channel_count:
                raise AudioPlaybackError(
                    f"Audio channel mismatch: buffer has {data.shape[1]}, format has {channel_count}"
                )
            return np.ascontiguousarray(data)

        raise AudioPlaybackError(f"Unsupported audio shape for playback: {data.shape}")

    def _reset_state(self) -> None:
        self._stream = None
        self._buffer = None
        self._pcm_queue = None
        self._pending = None
        self._stream_ended = False
        self._offset = 0
        self._on_level = None
        self._level_tick = 0
        self._done.set()
