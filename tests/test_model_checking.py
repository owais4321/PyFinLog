# tests/test_model_checking.py

import unittest

from logic_core import (
    Constant,
    Transition,
    TransitionSystem,
    check,
    check_invariant,
    check_deadlocks,
    replay_counterexample,
)
from tools import var, def_pred
from examples import protocol_model, lock_model


class ModelCheckingTests(unittest.TestCase):

    def test_shortest_named_counterexample(self):
        state = var("state")
        Safe = def_pred(
            "Safe",
            lambda current: not current[2] or current[1],
        )

        model = protocol_model(faulty=True)
        result = check_invariant(model, Safe(state))

        self.assertEqual(result.status, "violated")
        self.assertEqual(
            result.actions,
            ["request", "grant"],
        )
        self.assertEqual(
            result.states,
            [
                (False, False, False),
                (True, False, False),
                (True, False, True),
            ],
        )
        self.assertTrue(replay_counterexample(model, result))

        self.assertEqual(
            check(
                Safe(state),
                {"state": result.states[-1]},
            ).status,
            "violated",
        )

    def test_corrected_protocol_is_exhausted(self):
        state = var("state")
        Safe = def_pred(
            "Safe",
            lambda current: not current[2] or current[1],
        )

        result = check_invariant(
            protocol_model(faulty=False),
            Safe(state),
        )

        self.assertEqual(result.status, "holds")
        self.assertTrue(result.complete)
        self.assertEqual(result.checked, 4)

    def test_initial_violation_has_zero_actions(self):
        result = check_invariant(
            TransitionSystem(
                (0,),
                lambda state: [],
            ),
            Constant(False),
        )

        self.assertEqual(result.status, "violated")
        self.assertEqual(result.states, [0])
        self.assertEqual(result.actions, [])

    def test_deadlock_and_corrected_lock_order(self):
        finished = lambda state: (
            state[0] == 3 and state[1] == 3
        )

        faulty = lock_model(reverse_second=True)
        result = check_deadlocks(
            faulty,
            allowed_terminal=finished,
        )

        self.assertEqual(result.status, "deadlock")
        self.assertEqual(
            result.actions,
            ["p0:acquire:A", "p1:acquire:B"],
        )
        self.assertTrue(replay_counterexample(faulty, result))
        self.assertEqual(
            list(faulty.successors(result.states[-1])),
            [],
        )

        corrected = check_deadlocks(
            lock_model(reverse_second=False),
            allowed_terminal=finished,
        )

        self.assertEqual(
            corrected.status,
            "deadlock_free",
        )
        self.assertTrue(corrected.complete)
        self.assertEqual(corrected.checked, 12)

    def test_terminal_state_and_self_loop(self):
        terminal = TransitionSystem(
            ("done",),
            lambda state: [],
        )

        self.assertEqual(
            check_deadlocks(terminal).status,
            "deadlock",
        )
        self.assertEqual(
            check_deadlocks(
                terminal,
                allowed_terminal=lambda state: state == "done",
            ).status,
            "deadlock_free",
        )

        looping = TransitionSystem(
            (0,),
            lambda state: [Transition("loop", 0)],
        )

        # Structural deadlock freedom does not imply progress.
        self.assertEqual(
            check_deadlocks(looping).status,
            "deadlock_free",
        )

    def test_state_budget_returns_unknown(self):
        infinite = TransitionSystem(
            (0,),
            lambda state: [Transition("next", state + 1)],
        )

        result = check_invariant(
            infinite,
            Constant(True),
            max_states=3,
        )

        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.complete)

    def test_transition_budget_returns_unknown(self):
        looping = TransitionSystem(
            (0,),
            lambda state: [
                Transition("first", 0),
                Transition("second", 0),
            ],
        )

        result = check_invariant(
            looping,
            Constant(True),
            max_transitions=1,
        )

        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.transitions, 1)

    def test_multiple_initial_states(self):
        model = TransitionSystem(
            (0, 10),
            lambda state: [],
        )

        Safe = def_pred("Safe", lambda state: state < 10)
        result = check_invariant(
            model,
            Safe(var("state")),
        )

        self.assertEqual(result.status, "violated")
        self.assertEqual(result.states, [10])
        self.assertEqual(result.actions, [])

    def test_none_is_a_valid_state(self):
        model = TransitionSystem(
            (None,),
            lambda state: (
                [Transition("advance", 1)]
                if state is None
                else []
            ),
        )

        Safe = def_pred("Safe", lambda state: state is None)

        result = check_invariant(
            model,
            Safe(var("state")),
        )

        self.assertEqual(result.states, [None, 1])
        self.assertTrue(replay_counterexample(model, result))


if __name__ == "__main__":
    unittest.main(verbosity=2)