# logic_core/quantifiers.py

from typing import Callable

from .base_expressions import (
    LogicalExpression,
    Variable,
    LogicError,
    require_bool,
)


class Predicate(LogicalExpression):
    """An interpreted predicate backed by a Python function."""

    def __init__(self, name: str, logic_func: Callable, *args):
        if not isinstance(name, str) or not name.strip():
            raise LogicError(
                "Predicate name must be a non-empty string."
            )

        if not callable(logic_func):
            raise LogicError(
                "Predicate logic function must be callable."
            )

        self.name = name.strip()
        self.logic = logic_func
        self.args = args

    def __call__(self, *args):
        """Create an application of this predicate."""
        return Predicate(self.name, self.logic, *args)

    def evaluate(self, context):
        resolved_args = []

        for index, arg in enumerate(self.args):
            try:
                if isinstance(arg, LogicalExpression):
                    value = arg.evaluate(context)
                else:
                    value = arg

                resolved_args.append(value)

            except Exception as error:
                raise LogicError(
                    f"Could not resolve argument {index} "
                    f"of predicate '{self.name}': {error}"
                ) from error

        try:
            result = self.logic(*resolved_args)

        except Exception as error:
            raise LogicError(
                f"Predicate '{self.name}' failed with "
                f"arguments {resolved_args!r}: {error}"
            ) from error

        return require_bool(result)

    def __str__(self):
        arguments = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({arguments})"


class Quantifier(LogicalExpression):
    """Base class for quantification over a supplied finite list."""

    def __init__(self, variable, formula, domain):
        if not isinstance(variable, Variable):
            raise LogicError(
                "Quantifier variable must be a Variable."
            )

        if not isinstance(formula, LogicalExpression):
            raise LogicError(
                "Quantifier formula must be a LogicalExpression."
            )

        if not isinstance(domain, list):
            raise LogicError(
                "Quantifier domain must be a finite list."
            )

        self.variable = variable
        self.formula = formula

        # Copy the list so later changes to the supplied list
        # do not change this quantifier's domain.
        self.domain = list(domain)

    def _evaluate_at(self, context, value):
        """Evaluate the body under a local variable binding."""
        local_context = dict(context)
        local_context[self.variable.symbol] = value

        try:
            result = self.formula.evaluate(local_context)
            return require_bool(result)

        except Exception as error:
            raise LogicError(
                f"Evaluation failed for "
                f"{self.variable.symbol}={value!r} "
                f"in {type(self).__name__}: {error}"
            ) from error


class ForAll(Quantifier):
    """Universal quantifier: every domain element satisfies the body."""

    def evaluate(self, context):
        for value in self.domain:
            if not self._evaluate_at(context, value):
                return False

        # Universal quantification over an empty domain is true.
        return True

    def __str__(self):
        return (
            f"∀{self.variable} ∈ {self.domain!r} "
            f"[{self.formula}]"
        )


class Exists(Quantifier):
    """Existential quantifier: some domain element satisfies the body."""

    def evaluate(self, context):
        for value in self.domain:
            if self._evaluate_at(context, value):
                return True

        # Existential quantification over an empty domain is false.
        return False

    def __str__(self):
        return (
            f"∃{self.variable} ∈ {self.domain!r} "
            f"[{self.formula}]"
        )