# logic_core/base_expressions.py

from typing import Any, Dict


class LogicError(ValueError):
    """Raised for invalid logical expressions or evaluation results."""


def require_bool(value: Any) -> bool:
    """Accept only actual Boolean values, without implicit truthiness."""
    if type(value) is not bool:
        raise LogicError(
            f"Expected bool, received "
            f"{type(value).__name__}: {value!r}"
        )
    return value


class LogicalExpression:
    """Base class for logical expressions."""

    def evaluate(self, context: Dict[str, Any]) -> Any:
        raise NotImplementedError(
            "Subclasses must implement evaluate()."
        )

    def __bool__(self):
        raise TypeError(
            "Symbolic expressions have no Python truth value. "
            "Use evaluate() or check()."
        )

    def iff(self, other):
        """Construct a logical biconditional."""
        from .connectives import Iff

        return Iff(self, other)

    def __str__(self):
        return "Expr"

    def __repr__(self):
        return str(self)


class Constant(LogicalExpression):
    """
    Represent a Boolean constant or literal predicate argument.

    Constant(4) may be passed to a predicate, but it cannot be
    used as a Boolean formula.
    """

    def __init__(self, value: Any):
        self.value = value

    def evaluate(self, context: Dict[str, Any]) -> Any:
        return self.value

    def __str__(self):
        if self.value is True:
            return "T"
        if self.value is False:
            return "F"
        return repr(self.value)


class Variable(LogicalExpression):
    """Represent a symbol whose value comes from a context."""

    def __init__(self, symbol: str):
        if not isinstance(symbol, str) or not symbol.strip():
            raise LogicError(
                "Variable symbol must be a non-empty string."
            )

        self.symbol = symbol.strip()

    def evaluate(self, context: Dict[str, Any]) -> Any:
        if self.symbol not in context:
            raise LogicError(
                f"Variable '{self.symbol}' is missing "
                "from the evaluation context."
            )

        return context[self.symbol]

    def __str__(self):
        return self.symbol


def _ensure_expr(item: Any) -> LogicalExpression:
    """Convert a Boolean operand into a logical expression."""
    if isinstance(item, LogicalExpression):
        return item

    return Constant(require_bool(item))