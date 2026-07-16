import logging
import os
import sys
from typing import Final, TextIO
import warnings

from assistant.constants import NOISY_LOGGERS

_LEVEL_LABELS: Final[dict[int, str]] = {
    logging.DEBUG: "DBG",
    logging.INFO: "INF",
    logging.WARNING: "WRN",
    logging.ERROR: "ERR",
    logging.CRITICAL: "CRT",
}


class _Formatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(datefmt="%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        short_name = record.name.removeprefix("assistant.").removeprefix("assistant")
        if not short_name:
            short_name = "app"

        label = _LEVEL_LABELS.get(record.levelno, record.levelname[:3].upper())
        message = record.getMessage()
        timestamp = self.formatTime(record, self.datefmt)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        suffix = f"\n{record.exc_text}" if record.exc_text else ""

        return f"{timestamp}  {label}  {short_name}  {message}{suffix}"


class Logger:
    _configured: bool = False

    @classmethod
    def configure(cls, level: int = logging.INFO, *, stream: TextIO | None = None) -> None:
        if cls._configured:
            return

        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("HF_HUB_VERBOSITY", "error")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

        warnings.filterwarnings("ignore", message=r".*unauthenticated requests to the HF Hub.*")
        warnings.filterwarnings("ignore", category=UserWarning, module=r"huggingface_hub(\..*)?")

        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(_Formatter())

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(level)

        for name in NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.ERROR)

        cls._configured = True

    @staticmethod
    def get(name: str) -> logging.Logger:
        return logging.getLogger(name)
