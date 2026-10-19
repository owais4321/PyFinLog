# tests/test_checking.py

import unittest
from itertools import product

from logic_core import (
    Constant,
    LogicError,
    LimitExceeded,
    ForAll,
    Exists,
    check,
    explain,
    satisfiable,
    valid,
    equivalent,
    entails,
)
from tools import var, def_pred, truth_table


class TestChecking(unittest.TestCase):

    def test_connective_truth_tables(self):
        p, q = var("p"), var("q")

        for a, b in product((False, True), repeat=2):
            context = {"p": a, "q": b}

            cases = [
                (~p, not a),
                (p & q, a and b),
                (p | q, a or b),
                (p >> q, (not a) or b),
                (p.iff(q), a == b),
            ]

            for expression, expected in cases:
                with self.subTest(
                    expression=str(expression),
                    context=context,
                ):
                    self.assertIs(
                        expression.evaluate(context),
                        expected,
                    )
                    self.assertIs(
                        explain(expression, context).value,
                        expected,
                    )

    def test_satisfiability_and_returned_model(self):
        p, q = var("p"), var("q")

        expression = p & q
        result = satisfiable(expression)

        self.assertEqual(result.status, "sat")
        self.assertEqual(
            result.assignment,
            {"p": True, "q": True},
        )
        self.assertIs(
            expression.evaluate(result.assignment),
            True,
        )

        self.assertEqual(
            satisfiable(p & ~p).status,
            "unsat",
        )

    def test_validity_and_returned_countermodel(self):
        p, q = var("p"), var("q")

        self.assertEqual(
            valid(p | ~p).status,
            "valid",
        )

        expression = p >> q
        result = valid(expression)

        self.assertEqual(result.status, "invalid")
        self.assertIs(
            expression.evaluate(result.assignment),
            False,
        )

    def test_equivalence(self):
        p, q = var("p"), var("q")

        self.assertEqual(
            equivalent(
                ~(p & q),
                (~p) | (~q),
            ).status,
            "valid",
        )

        self.assertEqual(
            equivalent(p, q).status,
            "invalid",
        )

    def test_entailment(self):
        p, q = var("p"), var("q")

        self.assertEqual(
            entails([p, p >> q], q).status,
            "valid",
        )

        self.assertEqual(
            entails([], p).status,
            "invalid",
        )

        # Classical logic: inconsistent premises entail
        # every conjecture.
        self.assertEqual(
            entails([p, ~p], q).status,
            "valid",
        )

    def test_quantified_counterexample_and_witness(self):
        x = var("x")
        Even = def_pred("Even", lambda n: n % 2 == 0)

        result = check(
            ForAll(x, Even(x), [2, 3, 4])
        )

        self.assertEqual(result.status, "violated")
        self.assertEqual(
            result.trace.decisive_binding,
            {"x": 3},
        )
        self.assertIs(
            result.trace.children[0].value,
            False,
        )

        result = check(
            Exists(x, Even(x), [1, 3, 6])
        )

        self.assertEqual(result.status, "holds")
        self.assertEqual(
            result.trace.decisive_binding,
            {"x": 6},
        )
        self.assertIs(
            result.trace.children[0].value,
            True,
        )

    def test_nested_witness_dependencies(self):
        x, y = var("x"), var("y")

        Less = def_pred(
            "Less",
            lambda a, b: a < b,
        )

        expression = ForAll(
            x,
            Exists(y, Less(x, y), [1, 2]),
            [0, 1],
        )

        result = check(expression)

        self.assertEqual(result.status, "holds")

        # Each outer assignment has its own witness.
        witnesses = [
            child.decisive_binding
            for child in result.trace.children
        ]

        self.assertEqual(
            witnesses,
            [{"y": 1}, {"y": 2}],
        )

        outer_bindings = [
            child.bindings["x"]
            for child in result.trace.children
        ]

        self.assertEqual(outer_bindings, [0, 1])

    def test_nested_failure_without_existential_witness(self):
        x, y = var("x"), var("y")

        Less = def_pred(
            "Less",
            lambda a, b: a < b,
        )

        expression = ForAll(
            x,
            Exists(y, Less(x, y), [1, 2]),
            [0, 1, 2],
        )

        result = check(expression)

        self.assertEqual(result.status, "violated")
        self.assertEqual(
            result.trace.decisive_binding,
            {"x": 2},
        )

        failed_existential = result.trace.children[0]

        self.assertIsNone(
            failed_existential.decisive_binding
        )
        self.assertEqual(
            len(failed_existential.children),
            2,
        )
        self.assertTrue(
            all(
                child.value is False
                for child in failed_existential.children
            )
        )

    def test_variable_shadowing_preserves_context(self):
        outer_x = var("x")
        inner_x = var("x")

        Positive = def_pred(
            "Positive",
            lambda n: n > 0,
        )

        expression = ForAll(
            outer_x,
            Exists(
                inner_x,
                Positive(inner_x),
                [1],
            ),
            [0],
        )

        context = {"x": 99}

        self.assertIs(expression.evaluate(context), True)
        self.assertIs(explain(expression, context).value, True)
        self.assertEqual(context, {"x": 99})

    def test_empty_domains(self):
        x = var("x")

        universal = ForAll(x, Constant(False), [])
        existential = Exists(x, Constant(True), [])

        self.assertIs(universal.evaluate({}), True)
        self.assertIs(existential.evaluate({}), False)

        self.assertEqual(check(universal).status, "holds")
        self.assertEqual(check(existential).status, "violated")

    def test_domain_is_copied(self):
        x = var("x")
        domain = [2, 4]
        Even = def_pred("Even", lambda n: n % 2 == 0)

        expression = ForAll(x, Even(x), domain)
        domain.append(3)

        self.assertEqual(expression.domain, [2, 4])
        self.assertIs(expression.evaluate({}), True)

    def test_numeric_literal_predicate_arguments(self):
        Even = def_pred("Even", lambda n: n % 2 == 0)

        self.assertIs(Even(Constant(4)).evaluate({}), True)
        self.assertIs(Even(Constant(3)).evaluate({}), False)

        # Numeric literals are not Boolean formulas.
        with self.assertRaises(LogicError):
            check(Constant(4))

    def test_non_boolean_results_are_rejected(self):
        x = var("x")

        with self.assertRaises(LogicError):
            (~x).evaluate({"x": 1})

        Bad = def_pred("Bad", lambda n: "yes")

        with self.assertRaises(LogicError):
            Bad(1).evaluate({})

        with self.assertRaises(LogicError):
            ForAll(x, Bad(x), [1]).evaluate({})

        with self.assertRaises(LogicError):
            check(Exists(x, Bad(x), [1]))

    def test_symbolic_truth_conversion_is_rejected(self):
        p, q = var("p"), var("q")

        with self.assertRaises(TypeError):
            bool(p)

        with self.assertRaises(TypeError):
            bool(p == q)

        with self.assertRaises(TypeError):
            bool(check(Constant(True)))

    def test_propositional_search_rejects_quantified_syntax(self):
        x = var("x")
        Even = def_pred("Even", lambda n: n % 2 == 0)

        with self.assertRaises(LogicError):
            satisfiable(Even(x))

        with self.assertRaises(LogicError):
            valid(ForAll(x, Even(x), [2, 4]))

    def test_resource_limits(self):
        p = var("p")

        # A tautology needs both assignments checked
        # before validity can be concluded.
        with self.assertRaises(LimitExceeded):
            valid(p | ~p, max_assignments=1)

        # A conclusive countermodel within the budget
        # is still a valid result.
        self.assertEqual(
            valid(p, max_assignments=1).status,
            "invalid",
        )

        x = var("x")

        with self.assertRaises(LimitExceeded):
            explain(
                ForAll(x, Constant(True), [1, 2]),
                max_steps=2,
            )

    def test_invalid_budgets(self):
        p = var("p")

        for budget in (0, -1, True, 1.5):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    valid(p, max_assignments=budget)

                with self.assertRaises(ValueError):
                    explain(p, {"p": True}, max_steps=budget)

    def test_truth_table_rows(self):
        p, q = var("p"), var("q")

        rows = list(truth_table(p >> q, [p, q]))

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [row["result"] for row in rows],
            [True, True, False, True],
        )

        for row in rows:
            self.assertIs(
                (p >> q).evaluate(row["assignment"]),
                row["result"],
            )

    def test_truth_table_validation(self):
        p = var("p")

        with self.assertRaises(LogicError):
            list(truth_table(p, [p, p]))

        with self.assertRaises(LimitExceeded):
            list(
                truth_table(p | ~p, [p], max_rows=1)
            )

    def test_access_control_policy(self):
        u, r = var("u"), var("r")
        users = ["alice", "bob"]
        resources = ["public", "payroll"]

        Allowed = def_pred(
            "Allowed",
            lambda user, resource: (
                resource == "public" or user == "alice"
            ),
        )

        FaultyGrant = def_pred(
            "FaultyGrant",
            lambda user, resource: True,
        )

        faulty_property = ForAll(
            u,
            ForAll(
                r,
                FaultyGrant(u, r) >> Allowed(u, r),
                resources,
            ),
            users,
        )

        result = check(faulty_property)

        self.assertEqual(result.status, "violated")
        self.assertEqual(
            result.trace.decisive_binding,
            {"u": "bob"},
        )
        self.assertEqual(
            result.trace.children[0].decisive_binding,
            {"r": "payroll"},
        )

        CorrectGrant = def_pred(
            "CorrectGrant",
            lambda user, resource: (
                resource == "public" or user == "alice"
            ),
        )

        corrected_property = ForAll(
            u,
            ForAll(
                r,
                CorrectGrant(u, r).iff(Allowed(u, r)),
                resources,
            ),
            users,
        )

        self.assertEqual(
            check(corrected_property).status,
            "holds",
        )


if __name__ == "__main__":
    unittest.main()