# logic_core/connectives.py

from .base_expressions import (
    LogicalExpression,
    _ensure_expr,
    require_bool,
)


class Not(LogicalExpression):
    """Logical negation: ¬P."""

    def __init__(self, operand):
        self.operand = _ensure_expr(operand)

    def evaluate(self, context):
        value = require_bool(self.operand.evaluate(context))
        return not value

    def __str__(self):
        return f"¬({self.operand})"


class And(LogicalExpression):
    """Logical conjunction: P ∧ Q."""

    def __init__(self, left, right):
        self.left = _ensure_expr(left)
        self.right = _ensure_expr(right)

    def evaluate(self, context):
        left_value = require_bool(self.left.evaluate(context))
        right_value = require_bool(self.right.evaluate(context))
        return left_value and right_value

    def __str__(self):
        return f"({self.left} ∧ {self.right})"


class Or(LogicalExpression):
    """Logical disjunction: P ∨ Q."""

    def __init__(self, left, right):
        self.left = _ensure_expr(left)
        self.right = _ensure_expr(right)

    def evaluate(self, context):
        left_value = require_bool(self.left.evaluate(context))
        right_value = require_bool(self.right.evaluate(context))
        return left_value or right_value

    def __str__(self):
        return f"({self.left} ∨ {self.right})"


class Implies(LogicalExpression):
    """Logical implication: P ⇒ Q."""

    def __init__(self, antecedent, consequent):
        self.ant = _ensure_expr(antecedent)
        self.cons = _ensure_expr(consequent)

    def evaluate(self, context):
        antecedent = require_bool(self.ant.evaluate(context))
        consequent = require_bool(self.cons.evaluate(context))
        return (not antecedent) or consequent

    def __str__(self):
        return f"({self.ant} ⇒ {self.cons})"


class Iff(LogicalExpression):
    """Logical biconditional: P ⇔ Q."""

    def __init__(self, left, right):
        self.left = _ensure_expr(left)
        self.right = _ensure_expr(right)

    def evaluate(self, context):
        left_value = require_bool(self.left.evaluate(context))
        right_value = require_bool(self.right.evaluate(context))
        return left_value == right_value

    def __str__(self):
        return f"({self.left} ⇔ {self.right})"


# Attach symbolic operators to all logical expressions.
LogicalExpression.__invert__ = lambda self: Not(self)

LogicalExpression.__and__ = (
    lambda self, other: And(self, other)
)
LogicalExpression.__rand__ = (
    lambda self, other: And(other, self)
)

LogicalExpression.__or__ = (
    lambda self, other: Or(self, other)
)
LogicalExpression.__ror__ = (
    lambda self, other: Or(other, self)
)

LogicalExpression.__rshift__ = (
    lambda self, other: Implies(self, other)
)
LogicalExpression.__rrshift__ = (
    lambda self, other: Implies(other, self)
)

# Legacy syntax: P == Q constructs a biconditional.
LogicalExpression.__eq__ = (
    lambda self, other: Iff(self, other)
)