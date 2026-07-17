import ast
from collections.abc import Callable, Mapping
import math
import operator
from typing import ClassVar, Final

from gigachat.models import Function

from assistant.constants.tools import (
    CALCULATOR_MAX_ABS_EXPONENT,
    CALCULATOR_MAX_ABS_RESULT,
    CALCULATOR_MAX_EXPRESSION_LENGTH,
)
from assistant.tools.specs import make_function, string_param

type Number = float | int
type BinaryOp = Callable[[Number, Number], Number]
type UnaryOp = Callable[[Number], Number]


def _add(left: Number, right: Number) -> Number:
    return left + right


def _sub(left: Number, right: Number) -> Number:
    return left - right


def _mul(left: Number, right: Number) -> Number:
    return left * right


def _truediv(left: Number, right: Number) -> Number:
    return left / right


def _floordiv(left: Number, right: Number) -> Number:
    return left // right


def _mod(left: Number, right: Number) -> Number:
    return left % right


def _pos(value: Number) -> Number:
    return +value


def _neg(value: Number) -> Number:
    return -value


_BINARY_OPS: Final[dict[type[ast.operator], BinaryOp]] = {
    ast.Add: _add,
    ast.Sub: _sub,
    ast.Mult: _mul,
    ast.Div: _truediv,
    ast.FloorDiv: _floordiv,
    ast.Mod: _mod,
}

_UNARY_OPS: Final[dict[type[ast.unaryop], UnaryOp]] = {
    ast.UAdd: _pos,
    ast.USub: _neg,
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
        if len(expression) > CALCULATOR_MAX_EXPRESSION_LENGTH:
            return {"expression": expression, "error": "Слишком длинное выражение"}

        try:
            result = _safe_eval(expression)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError, MemoryError) as error:
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
            return _checked(value)
        case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARY_OPS:
            return _checked(_UNARY_OPS[type(op)](_eval_node(operand)))
        case ast.BinOp(left=left, op=ast.Pow(), right=right):
            return _safe_pow(_eval_node(left), _eval_node(right))
        case ast.BinOp(left=left, op=op, right=right) if type(op) in _BINARY_OPS:
            return _checked(_BINARY_OPS[type(op)](_eval_node(left), _eval_node(right)))
        case ast.Expr(value=value):
            return _eval_node(value)
        case _:
            raise ValueError("Разрешены только числа и арифметические операции")


def _safe_pow(base: Number, exponent: Number) -> Number:
    if isinstance(exponent, float) and not exponent.is_integer():
        raise ValueError("Показатель степени должен быть целым числом")

    exp_int = int(exponent)
    if abs(exp_int) > CALCULATOR_MAX_ABS_EXPONENT:
        raise ValueError(f"Показатель степени не должен превышать {CALCULATOR_MAX_ABS_EXPONENT}")

    try:
        result = operator.pow(base, exp_int)
    except ValueError as error:
        raise ValueError("Некорректное возведение в степень") from error

    return _checked(result)


def _checked(value: Number) -> Number:
    if isinstance(value, bool):
        raise ValueError("Разрешены только числа и арифметические операции")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise OverflowError("Результат выходит за допустимый диапазон")
        if abs(value) > CALCULATOR_MAX_ABS_RESULT:
            raise OverflowError("Результат выходит за допустимый диапазон")
        return value
    if abs(value) > CALCULATOR_MAX_ABS_RESULT:
        raise OverflowError("Результат выходит за допустимый диапазон")
    return value
