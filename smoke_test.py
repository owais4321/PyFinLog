# smoke_test.py

import unittest

from logic_core import (
    Constant,
    ForAll,
    Exists,
    LogicError,
    LimitExceeded,
    check,
    satisfiable,
    valid,
    entails,
)
from tools import var, def_pred, truth_table

from examples import (
    check_reachable_invariant,
    protocol_successors,
    INITIAL_PROTOCOL_STATE,
)


class SmokeTests(unittest.TestCase):

    def test_propositional_results_and_evidence(self):
        p, q = var("p"), var("q")

        model = satisfiable(p & q)
        self.assertEqual(model.status, "sat")
        self.assertIs((p & q).evaluate(model.assignment), True)

        self.assertEqual(
            satisfiable(p & ~p).status,
            "unsat",
        )
        self.assertEqual(
            valid(p | ~p).status,
            "valid",
        )
        self.assertEqual(
            entails([p, p >> q], q).status,
            "valid",
        )

        countermodel = valid(p >> q)
        self.assertEqual(countermodel.status, "invalid")
        self.assertIs(
            (p >> q).evaluate(countermodel.assignment),
            False,
        )

    def test_quantifier_evidence(self):
        x = var("x")
        Even = def_pred("Even", lambda value: value % 2 == 0)

        failure = check(ForAll(x, Even(x), [2, 3]))
        success = check(Exists(x, Even(x), [1, 4]))

        self.assertEqual(failure.status, "violated")
        self.assertEqual(
            failure.trace.decisive_binding,
            {"x": 3},
        )

        self.assertEqual(success.status, "holds")
        self.assertEqual(
            success.trace.decisive_binding,
            {"x": 4},
        )

    def test_empty_domains(self):
        x = var("x")

        self.assertEqual(
            check(ForAll(x, Constant(False), [])).status,
            "holds",
        )
        self.assertEqual(
            check(Exists(x, Constant(True), [])).status,
            "violated",
        )

    def test_truth_table(self):
        p, q = var("p"), var("q")
        rows = list(truth_table(p >> q, [p, q]))

        self.assertEqual(
            [row["result"] for row in rows],
            [True, True, False, True],
        )

    def test_fail_closed_behavior(self):
        p = var("p")

        with self.assertRaises(TypeError):
            bool(p)

        with self.assertRaises(LogicError):
            check(Constant(1))

        Bad = def_pred("Bad", lambda: "true")

        with self.assertRaises(LogicError):
            check(Bad())

        with self.assertRaises(LogicError):
            satisfiable(Bad())

        with self.assertRaises(LimitExceeded):
            valid(p | ~p, max_assignments=1)

    def test_protocol_counterexample_is_executable(self):
        state = var("state")
        Safe = def_pred(
            "Safe",
            lambda current: not current[2] or current[1],
        )

        result = check_reachable_invariant(
            [INITIAL_PROTOCOL_STATE],
            lambda current: protocol_successors(
                current,
                faulty=True,
            ),
            Safe(state),
        )

        self.assertEqual(result.status, "violated")
        path = result.counterexample

        self.assertEqual(path[0], INITIAL_PROTOCOL_STATE)

        # Every reported edge must be a real transition.
        for source, target in zip(path, path[1:]):
            self.assertIn(
                target,
                protocol_successors(source, faulty=True),
            )

        # The final state must actually violate the invariant.
        self.assertEqual(
            check(Safe(state), {"state": path[-1]}).status,
            "violated",
        )

    def test_corrected_protocol_exhaustion(self):
        state = var("state")
        Safe = def_pred(
            "Safe",
            lambda current: not current[2] or current[1],
        )

        result = check_reachable_invariant(
            [INITIAL_PROTOCOL_STATE],
            protocol_successors,
            Safe(state),
        )

        self.assertEqual(result.status, "holds")
        self.assertEqual(result.checked, 4)
        self.assertIsNone(result.counterexample)

    def test_incomplete_exploration_never_reports_holds(self):
        with self.assertRaises(LimitExceeded):
            check_reachable_invariant(
                [0],
                lambda current: [current + 1],
                Constant(True),
                max_states=3,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)