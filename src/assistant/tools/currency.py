from collections.abc import Mapping
from typing import ClassVar

from gigachat.models import Function

from assistant.constants import CURRENCY_CODE_ALIASES, EXCHANGE_RATE_API_URL, SUPPORTED_CURRENCIES
from assistant.tools.http import HttpError, get_json
from assistant.tools.specs import make_function, string_param


class CurrencyTool:
    name: ClassVar[str] = "get_currency_rate"

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description="Возвращает курс одной валюты к другой.",
            properties={
                "base": string_param("Исходная валюта: USD, EUR, GBP, CNY или название на русском"),
                "quote": string_param("Валюта котировки, по умолчанию RUB"),
            },
            required=["base"],
            examples=[
                ("Курс доллара", {"base": "USD", "quote": "RUB"}),
                ("Сколько стоит евро", {"base": "EUR", "quote": "RUB"}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "base": {"type": "string"},
                    "quote": {"type": "string"},
                    "rate": {"type": "number"},
                    "error": {"type": "string"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        base = _normalize_currency(str(arguments.get("base", "")))
        quote = _normalize_currency(str(arguments.get("quote") or "RUB"))
        if base is None:
            return {"error": "Неизвестная исходная валюта"}
        if quote is None:
            return {"error": "Неизвестная валюта котировки"}
        if base == quote:
            return {"base": base, "quote": quote, "rate": 1.0}

        try:
            data = get_json(f"{EXCHANGE_RATE_API_URL}/{base}")
        except HttpError as error:
            return {"error": str(error)}

        if data.get("result") != "success":
            return {"error": f"Курс {base}/{quote} недоступен"}

        rates = data.get("rates")
        if not isinstance(rates, dict) or quote not in rates:
            return {"error": f"Курс {base}/{quote} недоступен"}

        return {"base": base, "quote": quote, "rate": rates[quote]}


def _normalize_currency(value: str) -> str | None:
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    upper = cleaned.upper()
    if upper in SUPPORTED_CURRENCIES:
        return upper
    return CURRENCY_CODE_ALIASES.get(cleaned)
