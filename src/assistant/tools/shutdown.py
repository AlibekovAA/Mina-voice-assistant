from collections.abc import Mapping
from typing import ClassVar

from gigachat.models import Function

from assistant.tools.specs import make_function


class ShutdownTool:
    name: ClassVar[str] = "shutdown_assistant"

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description=(
                "Выключает голосового помощника и завершает работу программы. "
                "Вызывай, когда пользователь просит выключиться, остановиться или завершить работу."
            ),
            properties={},
            examples=[
                ("Выключи себя", {}),
                ("Мина, остановись", {}),
                ("Заверши работу", {}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "shutdown": {"type": "boolean", "description": "Признак остановки"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        del arguments
        return {"shutdown": True}
