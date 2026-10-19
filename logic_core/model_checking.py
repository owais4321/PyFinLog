# logic_core/model_checking.py

"""
Explicit-state invariant checking and deadlock detection.

Assumptions:
- States are immutable, hashable values with Boolean equality.
- Callbacks are pure, deterministic, and terminating.
- Successor callbacks enumerate the complete transition relation.

Budgets cannot interrupt a blocking Python callback.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .base_expressions import (
    LogicalExpression,
    LogicError,
    require_bool,
)
from .checking import Trace, LimitExceeded, check


@dataclass(frozen=True)
class Transition:
    action: str
    target: Any

    def __post_init__(self):
        if (
            not isinstance(self.action, str)
            or not self.action.strip()
        ):
            raise LogicError(
                "Transition action must be a non-empty string."
            )


@dataclass(frozen=True)
class TransitionSystem:
    initial_states: tuple
    successors: Callable[[Any], Iterable[Transition]]
    name: str = "model"

    def __post_init__(self):
        object.__setattr__(
            self,
            "initial_states",
            tuple(self.initial_states),
        )

        if not self.initial_states:
            raise LogicError(
                "At least one initial state is required."
            )

        if not callable(self.successors):
            raise LogicError("successors must be callable.")

        for state in self.initial_states:
            _validate_state(state)


@dataclass
class ExplorationResult:
    status: str
    complete: bool
    discovered: int
    checked: int
    transitions: int
    reason: str
    states: list = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    trace: Trace | None = None

    def __bool__(self):
        raise TypeError(
            "Inspect ExplorationResult.status explicitly."
        )


def _validate_state(state):
    if isinstance(state, LogicalExpression):
        raise LogicError(
            "Symbolic expressions cannot serve as states."
        )

    try:
        hash(state)
    except TypeError as error:
        raise LogicError(
            "States must be immutable and hashable."
        ) from error


def _positive(name, value):
    if type(value) is not int or value < 1:
        raise ValueError(
            f"{name} must be a positive integer."
        )


def _explore(
    model,
    invariant,
    allowed_terminal,
    max_states,
    max_transitions,
    max_steps,
):
    if not isinstance(model, TransitionSystem):
        raise TypeError(
            "model must be a TransitionSystem."
        )

    _positive("max_states", max_states)
    _positive("max_transitions", max_transitions)
    _positive("max_steps", max_steps)

    parents = {}
    queue = deque()
    checked = 0
    transitions = 0

    # Unique sentinel: None can be a legitimate model state.
    root = object()

    def result(
        status,
        reason,
        *,
        complete=False,
        endpoint=root,
        trace=None,
    ):
        states = []
        actions = []

        if endpoint is not root:
            current = endpoint

            while True:
                states.append(current)
                predecessor, action = parents[current]

                if predecessor is root:
                    break

                actions.append(action)
                current = predecessor

            states.reverse()
            actions.reverse()

        return ExplorationResult(
            status=status,
            complete=complete,
            discovered=len(parents),
            checked=checked,
            transitions=transitions,
            reason=reason,
            states=states,
            actions=actions,
            trace=trace,
        )

    for state in model.initial_states:
        if state in parents:
            continue

        if len(parents) >= max_states:
            return result(
                "unknown",
                "Initial-state budget exceeded.",
            )

        parents[state] = (root, None)
        queue.append(state)

    while queue:
        state = queue.popleft()
        checked += 1

        # Invariant checking at each reachable state.
        if invariant is not None:
            try:
                verdict = check(
                    invariant,
                    {"state": state},
                    max_steps=max_steps,
                )
            except LimitExceeded:
                return result(
                    "unknown",
                    "Per-state formula budget exceeded.",
                )

            if verdict.status == "violated":
                return result(
                    "violated",
                    "Reachable invariant violation.",
                    endpoint=state,
                    trace=verdict.trace,
                )

        has_successor = False

        for transition in model.successors(state):
            if not isinstance(transition, Transition):
                raise LogicError(
                    "successors must yield Transition objects."
                )

            _validate_state(transition.target)

            if transitions >= max_transitions:
                return result(
                    "unknown",
                    "Transition budget exceeded.",
                )

            transitions += 1
            has_successor = True
            target = transition.target

            if target not in parents:
                if len(parents) >= max_states:
                    return result(
                        "unknown",
                        "State budget exceeded.",
                    )

                parents[target] = (
                    state,
                    transition.action,
                )
                queue.append(target)

        # Structural deadlock: no outgoing transitions,
        # unless the state is an allowed termination state.
        if invariant is None and not has_successor:
            permitted = False

            if allowed_terminal is not None:
                permitted = require_bool(
                    allowed_terminal(state)
                )

            if not permitted:
                return result(
                    "deadlock",
                    "Reachable nonterminal sink.",
                    endpoint=state,
                )

    status = (
        "holds"
        if invariant is not None
        else "deadlock_free"
    )

    return result(
        status,
        "Reachable state space exhausted.",
        complete=True,
    )


def check_invariant(
    model,
    invariant,
    *,
    max_states=10_000,
    max_transitions=100_000,
    max_steps=100_000,
):
    """
    Check an ELE formula using the reserved variable 'state'.

    holds:
        The reachable state space was exhausted.

    violated:
        A reachable violation was found. The returned path
        is shortest in transition count from any initial state.

    unknown:
        Exploration was interrupted by a checking budget.
    """
    if not isinstance(invariant, LogicalExpression):
        raise TypeError(
            "invariant must be a LogicalExpression."
        )

    return _explore(
        model,
        invariant,
        None,
        max_states,
        max_transitions,
        max_steps,
    )


def check_deadlocks(
    model,
    *,
    allowed_terminal=None,
    max_states=10_000,
    max_transitions=100_000,
):
    """
    Find a reachable sink not designated as valid termination.

    A self-loop counts as a successor. This check does not
    detect livelock, starvation, or fairness violations.
    """
    if (
        allowed_terminal is not None
        and not callable(allowed_terminal)
    ):
        raise TypeError(
            "allowed_terminal must be callable."
        )

    return _explore(
        model,
        None,
        allowed_terminal,
        max_states,
        max_transitions,
        1,
    )


def replay_counterexample(
    model,
    result,
    *,
    max_successors=100_000,
):
    """
    Validate the initial state and every labelled path edge.

    Replay establishes path reachability. Recheck the final
    property separately to confirm the reported violation.
    """
    _positive("max_successors", max_successors)

    if (
        result.status not in ("violated", "deadlock")
        or not result.states
    ):
        raise LogicError(
            "Result does not contain a counterexample."
        )

    if len(result.actions) != len(result.states) - 1:
        raise LogicError(
            "Malformed counterexample path."
        )

    if result.states[0] not in model.initial_states:
        return False

    for source, action, target in zip(
        result.states,
        result.actions,
        result.states[1:],
    ):
        matched = False
        count = 0

        for transition in model.successors(source):
            if count >= max_successors:
                raise LimitExceeded(
                    "Replay successor budget exceeded."
                )

            count += 1

            if not isinstance(transition, Transition):
                raise LogicError(
                    "successors must yield Transition objects."
                )

            if (
                transition.action == action
                and transition.target == target
            ):
                matched = True
                break

        if not matched:
            return False

    return True