from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from gigachat.models import Function

from assistant.constants.app import MONTHS_RU, WEEKDAYS_RU
from assistant.tools.specs import make_function, string_param


class DateTimeTool:
    name: ClassVar[str] = "get_datetime"

    def __init__(self, *, default_timezone: str) -> None:
        self._default_timezone = default_timezone

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description="Возвращает текущие дату и время.",
            properties={
                "timezone": string_param("Часовой пояс IANA, например Europe/Moscow"),
            },
            examples=[
                ("Который час", {}),
                ("Какое сегодня число", {}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "datetime": {"type": "string", "description": "Дата и время"},
                    "timezone": {"type": "string", "description": "Часовой пояс"},
                    "error": {"type": "string", "description": "Описание ошибки"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        timezone_name = str(arguments.get("timezone") or self._default_timezone).strip()
        try:
            zone = ZoneInfo(timezone_name)
        except (KeyError, ValueError):
            return {"error": f"Неизвестный часовой пояс: {timezone_name}"}

        now = datetime.now(zone)
        weekday = WEEKDAYS_RU[now.weekday()]
        month = MONTHS_RU[now.month]
        text = f"{weekday}, {now.day} {month} {now.year} года, {now.hour:02d}:{now.minute:02d}"
        return {"datetime": text, "timezone": timezone_name}
