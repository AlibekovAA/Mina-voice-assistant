from typing import Final

NOISY_LOGGERS: Final[tuple[str, ...]] = (
    "httpx",
    "httpcore",
    "huggingface_hub",
    "urllib3",
    "filelock",
    "faster_whisper",
    "ctranslate2",
    "aiohttp",
    "asyncio",
    "edge_tts",
)

__all__ = ("NOISY_LOGGERS",)
