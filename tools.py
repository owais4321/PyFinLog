# tools.py

from itertools import product
from typing import Callable

from logic_core import (
    LogicalExpression,
    Variable,
    Predicate,
    Trace,
    LogicError,
    LimitExceeded,
)
from logic_core.base_expressions import require_bool


def var(symbol: str) -> Variable:
    """Create a logical variable."""
    return Variable(symbol)


def def_pred(name: str, func: Callable) -> Predicate:
    """Define a predicate backed by a Boolean-valued function."""
    return Predicate(name, func)


def truth_table(
    expression: LogicalExpression,
    variables: list[Variable],
    *,
    max_rows: int = 65_536,
):
    """
    Yield truth-table rows as dictionaries.

    Each row contains an 'assignment' dictionary and a
    Boolean 'result'. Variables must cover every free
    propositional variable in the expression.
    """
    if not isinstance(expression, LogicalExpression):
        raise LogicError(
            "Expression must be a LogicalExpression."
        )

    if type(max_rows) is not int or max_rows < 1:
        raise ValueError(
            "max_rows must be a positive integer."
        )

    variables = list(variables)

    if not all(isinstance(v, Variable) for v in variables):
        raise LogicError(
            "Truth-table variables must be Variable objects."
        )

    symbols = [v.symbol for v in variables]

    if len(symbols) != len(set(symbols)):
        raise LogicError(
            "Truth-table variable symbols must be unique."
        )

    required_rows = 2 ** len(symbols)

    if required_rows > max_rows:
        raise LimitExceeded(
            f"Truth table requires {required_rows} rows, "
            f"but max_rows is {max_rows}."
        )

    for values in product(
        (False, True),
        repeat=len(symbols),
    ):
        assignment = dict(zip(symbols, values))

        result = require_bool(
            expression.evaluate(assignment)
        )

        yield {
            "assignment": assignment,
            "result": result,
        }


def print_truth_table(
    expression: LogicalExpression,
    variables: list[Variable],
    *,
    max_rows: int = 65_536,
):
    """Print a truth table using the supplied variable order."""
    variables = list(variables)

    rows = truth_table(
        expression,
        variables,
        max_rows=max_rows,
    )

    # Retrieve the first row to validate inputs before printing.
    first_row = next(rows)

    symbols = [v.symbol for v in variables]
    headers = symbols + ["Result"]

    print(f"Truth table for: {expression}")
    print("\t".join(headers))

    def print_row(row):
        values = [
            str(row["assignment"][symbol])
            for symbol in symbols
        ]
        values.append(str(row["result"]))
        print("\t".join(values))

    print_row(first_row)

    for row in rows:
        print_row(row)


def print_trace(trace: Trace, *, max_depth: int = 10):
    """
    Print an evaluation trace with nested bindings.

    max_depth limits displayed depth; it does not alter
    the stored trace or the checking result.
    """
    if not isinstance(trace, Trace):
        raise TypeError("trace must be a Trace object.")

    if type(max_depth) is not int or max_depth < 0:
        raise ValueError(
            "max_depth must be a non-negative integer."
        )

    def display(node, depth):
        indent = "  " * depth

        print(
            f"{indent}{node.expression} "
            f"=> {node.value}"
        )

        if node.bindings:
            print(
                f"{indent}  Bindings: "
                f"{node.bindings!r}"
            )

        if node.decisive_binding is not None:
            print(
                f"{indent}  Decisive binding: "
                f"{node.decisive_binding!r}"
            )

        if depth >= max_depth:
            if node.children:
                print(
                    f"{indent}  "
                    "[Further trace depth omitted]"
                )
            return

        for child in node.children:
            display(child, depth + 1)

    display(trace, 0)