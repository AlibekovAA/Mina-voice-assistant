from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

APP_NAME: Final[str] = "Мина"
PACKAGE_NAME: Final[str] = "assistant"
FALLBACK_VERSION: Final[str] = "0.0.0"

BROWSER_DEFAULT_URL: Final[str] = "https://yandex.ru"
LINUX_NOTE_PATH: Final[Path] = Path("/tmp/mina-note.txt")

APP_NAME_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "calculator": "calculator",
        "calc": "calculator",
        "калькулятор": "calculator",
        "notepad": "notepad",
        "блокнот": "notepad",
        "browser": "browser",
        "браузер": "browser",
    }
)

WEEKDAYS_RU: Final[tuple[str, ...]] = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
MONTHS_RU: Final[Mapping[int, str]] = MappingProxyType(
    {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
)

__all__ = (
    "APP_NAME",
    "APP_NAME_ALIASES",
    "BROWSER_DEFAULT_URL",
    "FALLBACK_VERSION",
    "LINUX_NOTE_PATH",
    "MONTHS_RU",
    "PACKAGE_NAME",
    "WEEKDAYS_RU",
)
