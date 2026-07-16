from typing import Final

TTS_DEFAULT_VOICE: Final[str] = "ru-RU-SvetlanaNeural"
TTS_DEFAULT_RATE: Final[str] = "+0%"
TTS_DEFAULT_SAMPLE_RATE: Final[int] = 24_000
TTS_DEFAULT_TIMEOUT_SECONDS: Final[float] = 6.0

__all__ = (
    "TTS_DEFAULT_RATE",
    "TTS_DEFAULT_SAMPLE_RATE",
    "TTS_DEFAULT_TIMEOUT_SECONDS",
    "TTS_DEFAULT_VOICE",
)
