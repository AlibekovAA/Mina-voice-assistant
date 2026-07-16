from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

HTTP_DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0
HTTP_USER_AGENT: Final[str] = "MinaAssistant"

EXCHANGE_RATE_API_URL: Final[str] = "https://open.er-api.com/v6/latest"

CURRENCY_CODE_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "usd": "USD",
        "доллар": "USD",
        "доллара": "USD",
        "долларов": "USD",
        "баксов": "USD",
        "eur": "EUR",
        "евро": "EUR",
        "rub": "RUB",
        "рубль": "RUB",
        "рубля": "RUB",
        "рублей": "RUB",
        "gbp": "GBP",
        "фунт": "GBP",
        "фунта": "GBP",
        "фунтов": "GBP",
        "cny": "CNY",
        "юань": "CNY",
        "юаня": "CNY",
        "юаней": "CNY",
    }
)
SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset({"USD", "EUR", "RUB", "GBP", "CNY"})

__all__ = (
    "CURRENCY_CODE_ALIASES",
    "EXCHANGE_RATE_API_URL",
    "HTTP_DEFAULT_TIMEOUT_SECONDS",
    "HTTP_USER_AGENT",
    "SUPPORTED_CURRENCIES",
)
