from collections.abc import Mapping
from typing import ClassVar, Protocol

from gigachat.models import Function


class Tool(Protocol):
    name: ClassVar[str]

    @property
    def specification(self) -> Function: ...

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]: ...
