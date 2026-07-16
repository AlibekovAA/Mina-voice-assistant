import ast
from collections.abc import Callable, Mapping
import operator
from typing import ClassVar, Final, cast

from gigachat.models import Function

from assistant.tools.specs import make_function, string_param

type Number = float | int
type BinaryOp = Callable[[Number, Number], Number]
type UnaryOp = Callable[[Number], Number]

_BINARY_OPS: Final[dict[type[ast.operator], BinaryOp]] = {
    ast.Add: cast(BinaryOp, operator.add),
    ast.Sub: cast(BinaryOp, operator.sub),
    ast.Mult: cast(BinaryOp, operator.mul),
    ast.Div: cast(BinaryOp, operator.truediv),
    ast.FloorDiv: cast(BinaryOp, operator.floordiv),
    ast.Mod: cast(BinaryOp, operator.mod),
    ast.Pow: cast(BinaryOp, operator.pow),
}

_UNARY_OPS: Final[dict[type[ast.unaryop], UnaryOp]] = {
    ast.UAdd: cast(UnaryOp, operator.pos),
    ast.USub: cast(UnaryOp, operator.neg),
}


class CalculatorTool:
    name: ClassVar[str] = "calculate"

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description="Вычисляет математическое выражение с числами и операциями + - * / // % ** и скобками.",
            properties={
                "expression": string_param("Математическое выражение, например 150/2 или (10+5)*3"),
            },
            required=["expression"],
            examples=[
                ("Сколько будет 150 разделить на 2", {"expression": "150/2"}),
                ("Посчитай 25 плюс 17", {"expression": "25+17"}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "result": {"type": "number", "description": "Результат вычисления"},
                    "expression": {"type": "string", "description": "Исходное выражение"},
                    "error": {"type": "string", "description": "Описание ошибки, если вычисление не удалось"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        expression = str(arguments.get("expression", "")).strip()
        if not expression:
            return {"error": "Пустое выражение"}

        try:
            result = _safe_eval(expression)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
            return {"expression": expression, "error": str(error)}

        if isinstance(result, float) and result.is_integer():
            result = int(result)

        return {"expression": expression, "result": result}


def _safe_eval(expression: str) -> Number:
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> Number:
    match node:
        case ast.Constant(value=value) if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARY_OPS:
            return _UNARY_OPS[type(op)](_eval_node(operand))
        case ast.BinOp(left=left, op=op, right=right) if type(op) in _BINARY_OPS:
            return _BINARY_OPS[type(op)](_eval_node(left), _eval_node(right))
        case ast.Expr(value=value):
            return _eval_node(value)
        case _:
            raise ValueError("Разрешены только числа и арифметические операции")
