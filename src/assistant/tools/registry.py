from collections.abc import Mapping, Sequence
from typing import Self

from gigachat.models import Function

from assistant.tools.calculator import CalculatorTool
from assistant.tools.currency import CurrencyTool
from assistant.tools.datetime_tool import DateTimeTool
from assistant.tools.desktop import DesktopTool
from assistant.tools.protocol import Tool
from assistant.tools.shutdown import ShutdownTool
from assistant.tools.weather import WeatherTool


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._specifications = [tool.specification for tool in self._tools.values()]

    @classmethod
    def default(cls, *, default_city: str, default_timezone: str) -> Self:
        return cls(
            [
                CalculatorTool(),
                DateTimeTool(default_timezone=default_timezone),
                WeatherTool(default_city=default_city),
                CurrencyTool(),
                DesktopTool(),
                ShutdownTool(),
            ]
        )

    @property
    def specifications(self) -> list[Function]:
        return self._specifications

    def execute(self, name: str, arguments: Mapping[str, object]) -> dict[str, object]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Неизвестная функция: {name}"}
        return tool.execute(arguments)
