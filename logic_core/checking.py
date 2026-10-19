# logic_core/checking.py

from dataclasses import dataclass, field
from itertools import product
from typing import Any

from .base_expressions import (
    Variable,
    Constant,
    LogicError,
    require_bool,
)
from .connectives import Not, And, Or, Implies, Iff
from .quantifiers import Predicate, ForAll, Exists


class LimitExceeded(LogicError):
    """A check exceeded its budget before reaching a conclusion."""


@dataclass
class Trace:
    """Scoped evidence from evaluating an expression."""

    expression: str
    value: bool
    bindings: dict[str, Any] = field(default_factory=dict)
    children: list["Trace"] = field(default_factory=list)
    decisive_binding: dict[str, Any] | None = None


@dataclass
class CheckResult:
    """Result of a concrete check or propositional search."""

    status: str
    assignment: dict[str, Any] | None = None
    checked: int = 0
    trace: Trace | None = None

    def __bool__(self):
        raise TypeError(
            "Inspect CheckResult.status explicitly."
        )


def explain(expression, context=None, *, max_steps=100_000):
    """
    Evaluate a formula and return a scoped trace.

    A false universal retains its first counterexample.
    A true existential retains its first witness.
    Other quantified outcomes retain all visited children.

    The budget counts expression-node visits. It cannot
    interrupt computations inside Python predicate callbacks.
    """
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer.")

    remaining = max_steps

    def visit(node, current_context):
        nonlocal remaining

        if remaining <= 0:
            raise LimitExceeded(
                "Explanation node budget exceeded."
            )

        remaining -= 1

        # Quantified expressions
        if isinstance(node, (ForAll, Exists)):
            universal = isinstance(node, ForAll)
            children = []

            for value in node.domain:
                local_context = dict(current_context)
                local_context[node.variable.symbol] = value

                child = visit(node.formula, local_context)

                # Universal failure or existential success:
                # this child decides the result.
                if child.value != universal:
                    return Trace(
                        expression=str(node),
                        value=not universal,
                        bindings=dict(current_context),
                        children=[child],
                        decisive_binding={
                            node.variable.symbol: value
                        },
                    )

                children.append(child)

            # All universal instances hold, or no existential
            # instance holds. Also handles empty domains.
            return Trace(
                expression=str(node),
                value=universal,
                bindings=dict(current_context),
                children=children,
            )

        # Negation
        if isinstance(node, Not):
            child = visit(node.operand, current_context)

            return Trace(
                expression=str(node),
                value=not child.value,
                bindings=dict(current_context),
                children=[child],
            )

        # Binary connectives
        if isinstance(node, (And, Or, Implies, Iff)):
            if isinstance(node, Implies):
                left_node = node.ant
                right_node = node.cons
            else:
                left_node = node.left
                right_node = node.right

            left = visit(left_node, current_context)
            right = visit(right_node, current_context)

            if isinstance(node, And):
                value = left.value and right.value
            elif isinstance(node, Or):
                value = left.value or right.value
            elif isinstance(node, Implies):
                value = (not left.value) or right.value
            else:
                value = left.value == right.value

            return Trace(
                expression=str(node),
                value=value,
                bindings=dict(current_context),
                children=[left, right],
            )

        # Atomic expressions
        if isinstance(node, (Variable, Constant, Predicate)):
            value = require_bool(
                node.evaluate(current_context)
            )

            return Trace(
                expression=str(node),
                value=value,
                bindings=dict(current_context),
            )

        raise LogicError(
            f"Unsupported expression type: "
            f"{type(node).__name__}"
        )

    initial_context = {} if context is None else dict(context)
    return visit(expression, initial_context)


def check(expression, context=None, *, max_steps=100_000):
    """Check a formula under one supplied interpretation."""
    initial_context = {} if context is None else dict(context)

    trace = explain(
        expression,
        initial_context,
        max_steps=max_steps,
    )

    return CheckResult(
        status="holds" if trace.value else "violated",
        assignment=initial_context,
        checked=1,
        trace=trace,
    )


def _symbols(expression):
    """Collect symbols and reject non-propositional syntax."""
    if isinstance(expression, Variable):
        return {expression.symbol}

    if isinstance(expression, Constant):
        require_bool(expression.value)
        return set()

    if isinstance(expression, Not):
        return _symbols(expression.operand)

    if isinstance(expression, (And, Or, Implies, Iff)):
        if isinstance(expression, Implies):
            left = expression.ant
            right = expression.cons
        else:
            left = expression.left
            right = expression.right

        return _symbols(left) | _symbols(right)

    raise LogicError(
        "Propositional search accepts only Boolean constants, "
        "variables, and connectives. Predicates and quantifiers "
        "are not supported by this search."
    )


def _search(
    expression,
    target,
    found_status,
    exhausted_status,
    max_assignments,
):
    """Search Boolean assignments in a deterministic order."""
    if (
        type(max_assignments) is not int
        or max_assignments < 1
    ):
        raise ValueError(
            "max_assignments must be a positive integer."
        )

    symbols = sorted(_symbols(expression))
    checked = 0

    for values in product(
        (False, True),
        repeat=len(symbols),
    ):
        if checked >= max_assignments:
            raise LimitExceeded(
                "Assignment budget exceeded. "
                "The search has no conclusive result."
            )

        assignment = dict(zip(symbols, values))
        checked += 1

        value = require_bool(
            expression.evaluate(assignment)
        )

        if value == target:
            return CheckResult(
                status=found_status,
                assignment=assignment,
                checked=checked,
            )

    return CheckResult(
        status=exhausted_status,
        assignment=None,
        checked=checked,
    )


def satisfiable(expression, *, max_assignments=65_536):
    """Return 'sat' with a model, or 'unsat' after exhaustion."""
    return _search(
        expression,
        target=True,
        found_status="sat",
        exhausted_status="unsat",
        max_assignments=max_assignments,
    )


def valid(expression, *, max_assignments=65_536):
    """Return 'invalid' with a countermodel, or 'valid'."""
    return _search(
        expression,
        target=False,
        found_status="invalid",
        exhausted_status="valid",
        max_assignments=max_assignments,
    )


def equivalent(left, right, *, max_assignments=65_536):
    """Check whether two propositional formulas are equivalent."""
    return valid(
        Iff(left, right),
        max_assignments=max_assignments,
    )


def entails(axioms, conjecture, *, max_assignments=65_536):
    """
    Check classical propositional entailment.

    Inconsistent premises entail every conjecture.
    Check premise satisfiability separately when needed.
    """
    premise = Constant(True)

    for axiom in axioms:
        premise = And(premise, axiom)

    return valid(
        Implies(premise, conjecture),
        max_assignments=max_assignments,
    )