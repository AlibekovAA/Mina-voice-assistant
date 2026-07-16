from collections.abc import Callable
from typing import Protocol

from assistant.audio.models import AudioData, AudioFormat

LevelCallback = Callable[[float], None]


class AudioCapture(Protocol):
    @property
    def is_active(self) -> bool: ...

    def start(
        self,
        audio_format: AudioFormat,
        *,
        device: int | None = None,
        blocksize: int = 1024,
    ) -> None: ...

    def read(self, *, timeout: float | None = 0.1) -> AudioData | None: ...

    def stop(self) -> None: ...


class AudioPlayback(Protocol):
    @property
    def is_active(self) -> bool: ...

    def play(
        self,
        audio: AudioData,
        *,
        device: int | None = None,
        on_level: LevelCallback | None = None,
    ) -> None: ...

    def stop(self) -> None: ...
