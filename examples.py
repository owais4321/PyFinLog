# examples.py
"""
Technical demonstrations for Easy Logic Engine.

Run:
    python examples.py

Execute one demonstration:
    python examples.py access
    python examples.py witnesses
    python examples.py entailment
    python examples.py protocol

Assumptions:
- Predicate callbacks are pure and terminating.
- Transition-system states are hashable.
- Transition functions describe the complete successor relation.
"""

import argparse
from collections import deque
from dataclasses import dataclass
from typing import Callable

from logic_core import (
    Constant,
    ForAll,
    Exists,
    LimitExceeded,
    check,
    satisfiable,
    valid,
    equivalent,
    entails,
)
from tools import var, def_pred, print_trace

# Additional imports for examples.py

from logic_core import (
    Transition,
    TransitionSystem,
    check_invariant,
    check_deadlocks,
    replay_counterexample,
)


def demonstrate_access_control():
    """Check authorization, availability, and separation of duties."""
    users = ["alice", "bob", "carol"]
    resources = ["public", "payroll", "audit"]

    roles = {
        "alice": {"employee", "payroll_admin"},
        "bob": {"employee"},
        "carol": {"employee", "auditor"},
    }

    u, r = var("u"), var("r")

    def allowed(user, resource):
        if resource == "public":
            return True
        if resource == "payroll":
            return "payroll_admin" in roles[user]
        if resource == "audit":
            return "auditor" in roles[user]
        return False

    Allowed = def_pred("Allowed", allowed)

    # Bug: every employee receives payroll access.
    FaultyGrant = def_pred(
        "FaultyGrant",
        lambda user, resource: (
            resource == "public"
            or (
                resource == "payroll"
                and "employee" in roles[user]
            )
            or (
                resource == "audit"
                and "auditor" in roles[user]
            )
        ),
    )

    safety = ForAll(
        u,
        ForAll(
            r,
            FaultyGrant(u, r) >> Allowed(u, r),
            resources,
        ),
        users,
    )

    result = check(safety)
    assert result.status == "violated"
    assert result.trace.decisive_binding == {"u": "bob"}
    assert result.trace.children[0].decisive_binding == {
        "r": "payroll"
    }

    print("\nFaulty authorization policy:", result.status)
    print_trace(result.trace, max_depth=2)

    CorrectGrant = def_pred("CorrectGrant", allowed)

    # Biconditional checks both:
    # no unauthorized grants and no missing authorized grants.
    exact_permissions = ForAll(
        u,
        ForAll(
            r,
            CorrectGrant(u, r).iff(Allowed(u, r)),
            resources,
        ),
        users,
    )

    assert check(exact_permissions).status == "holds"
    print("Corrected permissions: holds")

    # A deny-all policy passes safety but fails availability.
    DenyAll = def_pred(
        "DenyAll",
        lambda user, resource: False,
    )

    deny_all_safety = ForAll(
        u,
        ForAll(
            r,
            DenyAll(u, r) >> Allowed(u, r),
            resources,
        ),
        users,
    )

    deny_all_availability = ForAll(
        u,
        ForAll(
            r,
            Allowed(u, r) >> DenyAll(u, r),
            resources,
        ),
        users,
    )

    assert check(deny_all_safety).status == "holds"
    assert check(deny_all_availability).status == "violated"

    print("Deny-all safety: holds")
    print("Deny-all availability: violated")

    PayrollAdmin = def_pred(
        "PayrollAdmin",
        lambda user: "payroll_admin" in roles[user],
    )
    Auditor = def_pred(
        "Auditor",
        lambda user: "auditor" in roles[user],
    )

    separation_of_duties = ForAll(
        u,
        ~(PayrollAdmin(u) & Auditor(u)),
        users,
    )

    assert check(separation_of_duties).status == "holds"
    print("Separation of duties: holds")


def demonstrate_dependent_witnesses():
    """Show that witness scope changes a property's meaning."""
    jobs = ["job_a", "job_b"]
    workers = ["worker_1", "worker_2"]

    capabilities = {
        ("job_a", "worker_1"),
        ("job_b", "worker_2"),
    }

    j, w = var("j"), var("w")

    CanExecute = def_pred(
        "CanExecute",
        lambda job, worker: (job, worker) in capabilities,
    )

    # Each job has some suitable worker.
    per_job_worker = ForAll(
        j,
        Exists(w, CanExecute(j, w), workers),
        jobs,
    )

    result = check(per_job_worker)
    assert result.status == "holds"

    witnesses = [
        (
            child.bindings["j"],
            child.decisive_binding["w"],
        )
        for child in result.trace.children
    ]

    assert witnesses == [
        ("job_a", "worker_1"),
        ("job_b", "worker_2"),
    ]

    print("\nPer-job witnesses:", witnesses)

    # Stronger property: one worker can execute every job.
    universal_worker = Exists(
        w,
        ForAll(j, CanExecute(j, w), jobs),
        workers,
    )

    assert check(universal_worker).status == "violated"
    print("One worker for every job: violated")

    # An additional unsupported job causes coverage failure.
    incomplete_coverage = ForAll(
        j,
        Exists(w, CanExecute(j, w), workers),
        jobs + ["job_c"],
    )

    result = check(incomplete_coverage)
    assert result.status == "violated"
    assert result.trace.decisive_binding == {"j": "job_c"}

    print("Unsupported job:", result.trace.decisive_binding)


def demonstrate_entailment_and_consistency():
    """Check requirements and detect inconsistent premises."""
    request = var("request")
    authorized = var("authorized")
    granted = var("granted")

    requirements = [
        granted >> authorized,
        (request & authorized) >> granted,
    ]

    premise = Constant(True)
    for requirement in requirements:
        premise = premise & requirement

    consistency = satisfiable(premise)
    assert consistency.status == "sat"

    print("\nRequirements consistency:", consistency.status)
    print("Example model:", consistency.assignment)

    safety = entails(
        requirements,
        granted >> authorized,
    )
    assert safety.status == "valid"

    # Requests alone do not imply permission.
    unconditional_service = entails(
        requirements,
        request >> granted,
    )

    assert unconditional_service.status == "invalid"

    countermodel = unconditional_service.assignment

    assert premise.evaluate(countermodel) is True
    assert (request >> granted).evaluate(countermodel) is False

    print("Unconditional service:", unconditional_service.status)
    print("Countermodel:", countermodel)

    contradictory_requirements = [
        granted,
        ~granted,
    ]

    contradiction = granted & ~granted
    assert satisfiable(contradiction).status == "unsat"

    # Classical entailment is valid here because no model
    # satisfies the premises. It is not a useful safety proof.
    vacuous = entails(
        contradictory_requirements,
        authorized,
    )
    assert vacuous.status == "valid"

    print("Contradictory requirements: unsat")
    print("Entailment from contradiction: valid, but vacuous")

    # Independent logical identity demonstration.
    assert equivalent(
        ~(request & authorized),
        (~request) | (~authorized),
    ).status == "valid"


@dataclass
class ReachabilityResult:
    status: str
    discovered: int
    checked: int
    counterexample: list | None = None


def check_reachable_invariant(
    initial_states,
    successors: Callable,
    invariant,
    *,
    max_states=10_000,
):
    """
    Explore reachable states breadth-first and check an ELE invariant.

    Returns:
    - violated: a reachable state fails the invariant, with a path.
    - holds: the reachable state space has been exhausted.

    Raises LimitExceeded if exploration would exceed max_states.
    A bounded, unfinished exploration never returns holds.

    The invariant uses a variable named 'state'.
    """
    if type(max_states) is not int or max_states < 1:
        raise ValueError("max_states must be a positive integer.")

    initial_states = list(initial_states)
    if not initial_states:
        raise ValueError("At least one initial state is required.")

    queue = deque()
    parents = {}

    def discover(state, parent):
        if state in parents:
            return

        if len(parents) >= max_states:
            raise LimitExceeded(
                "Reachable-state budget exceeded; "
                "exploration is incomplete."
            )

        parents[state] = parent
        queue.append(state)

    for state in initial_states:
        discover(state, None)

    checked = 0

    while queue:
        state = queue.popleft()
        checked += 1

        result = check(invariant, {"state": state})

        if result.status == "violated":
            path = []
            current = state

            # Every discovered state points toward an initial root.
            while True:
                path.append(current)
                parent = parents[current]
                if parent is None:
                    break
                current = parent

            path.reverse()

            return ReachabilityResult(
                status="violated",
                discovered=len(parents),
                checked=checked,
                counterexample=path,
            )

        for successor in successors(state):
            discover(successor, state)

    return ReachabilityResult(
        status="holds",
        discovered=len(parents),
        checked=checked,
    )


# State: (pending_request, authorized, granted)
INITIAL_PROTOCOL_STATE = (False, False, False)


def protocol_successors(state, *, faulty=False):
    """A small authorization protocol transition model."""
    pending, authorized, granted = state
    successors = []

    # A new request arrives.
    if not pending:
        successors.append((True, False, False))

    # Authorization is completed.
    if pending and not authorized:
        successors.append((True, True, granted))

    # Buggy implementation can grant before authorization.
    if pending and not granted and (authorized or faulty):
        successors.append((True, authorized, True))

    # End the current request and clear its state.
    if pending:
        successors.append(INITIAL_PROTOCOL_STATE)

    return successors


def demonstrate_protocol_verification():
    """Detect a reachable protocol bug and check its correction."""
    state = var("state")

    SafeGrant = def_pred(
        "SafeGrant",
        lambda current: (
            not current[2] or current[1]
        ),
    )

    invariant = SafeGrant(state)

    faulty = check_reachable_invariant(
        [INITIAL_PROTOCOL_STATE],
        lambda current: protocol_successors(
            current,
            faulty=True,
        ),
        invariant,
    )

    assert faulty.status == "violated"
    assert faulty.counterexample == [
        (False, False, False),
        (True, False, False),
        (True, False, True),
    ]

    print("\nFaulty protocol:", faulty.status)
    print("Shortest counterexample path:", faulty.counterexample)

    corrected = check_reachable_invariant(
        [INITIAL_PROTOCOL_STATE],
        lambda current: protocol_successors(
            current,
            faulty=False,
        ),
        invariant,
    )

    assert corrected.status == "holds"
    assert corrected.discovered == 4
    assert corrected.checked == 4

    print("Corrected protocol:", corrected.status)
    print("Reachable states checked:", corrected.checked)


def protocol_model(faulty=False):
    """
    State: (pending_request, authorized, granted).

    Faulty mode permits granting before authorization.
    """

    def successors(state):
        pending, authorized, granted = state

        if not pending:
            yield Transition(
                "request",
                (True, False, False),
            )

        if pending and not authorized:
            yield Transition(
                "authorize",
                (True, True, granted),
            )

        if pending and not granted and (authorized or faulty):
            yield Transition(
                "grant",
                (True, authorized, True),
            )

        if pending:
            yield Transition(
                "reset",
                (False, False, False),
            )

    return TransitionSystem(
        initial_states=((False, False, False),),
        successors=successors,
        name="authorization_protocol",
    )


def lock_model(reverse_second=True):
    """
    Two processes acquire two locks.

    State:
        (phase_p0, phase_p1, owner_A, owner_B)

    Phases:
        0: before first acquisition
        1: holding first lock
        2: holding both locks
        3: finished

    Owners:
        -1: free
         0: process 0
         1: process 1

    Faulty configuration:
        P0 acquires A then B.
        P1 acquires B then A.

    Corrected configuration:
        Both processes acquire A then B.
    """

    def successors(state):
        phases = list(state[:2])
        owners = list(state[2:])

        for process in (0, 1):
            first = (
                1
                if process == 1 and reverse_second
                else 0
            )
            second = 1 - first
            stage = phases[process]

            new_phases = phases.copy()
            new_owners = owners.copy()

            if stage in (0, 1):
                lock = first if stage == 0 else second

                if owners[lock] != -1:
                    continue

                new_owners[lock] = process
                new_phases[process] += 1

                action = (
                    f"p{process}:acquire:"
                    f"{'AB'[lock]}"
                )

            elif stage == 2:
                for lock in (0, 1):
                    if new_owners[lock] == process:
                        new_owners[lock] = -1

                new_phases[process] = 3
                action = f"p{process}:release"

            else:
                continue

            yield Transition(
                action,
                tuple(new_phases + new_owners),
            )

    return TransitionSystem(
        initial_states=((0, 0, -1, -1),),
        successors=successors,
        name="two_lock_protocol",
    )


def print_exploration(result):
    print("Status:", result.status)
    print("Complete exploration:", result.complete)
    print("Discovered states:", result.discovered)
    print("Checked states:", result.checked)
    print("Examined transitions:", result.transitions)
    print("Reason:", result.reason)

    if result.states:
        print("Initial:", result.states[0])

        for action, target in zip(
            result.actions,
            result.states[1:],
        ):
            print(f"  {action} -> {target}")

    if result.trace is not None:
        print("Failing-state formula trace:")
        print_trace(result.trace, max_depth=2)


def demonstrate_model_checks():
    print("\nNAMED-TRANSITION INVARIANT CHECKING\n")

    state = var("state")
    SafeGrant = def_pred(
        "SafeGrant",
        lambda current: (
            not current[2] or current[1]
        ),
    )
    invariant = SafeGrant(state)

    faulty_model = protocol_model(faulty=True)
    faulty = check_invariant(faulty_model, invariant)

    assert faulty.status == "violated"
    assert faulty.actions == ["request", "grant"]
    assert replay_counterexample(faulty_model, faulty)

    assert check(
        invariant,
        {"state": faulty.states[-1]},
    ).status == "violated"

    print("Faulty authorization protocol:")
    print_exploration(faulty)

    corrected = check_invariant(
        protocol_model(faulty=False),
        invariant,
    )

    assert corrected.status == "holds"
    assert corrected.complete
    assert corrected.checked == 4

    print("\nCorrected authorization protocol:")
    print_exploration(corrected)

    print("\nTWO-LOCK DEADLOCK DETECTION\n")

    def finished(current):
        return current[0] == 3 and current[1] == 3

    faulty_locks = lock_model(reverse_second=True)

    deadlock = check_deadlocks(
        faulty_locks,
        allowed_terminal=finished,
    )

    assert deadlock.status == "deadlock"
    assert deadlock.actions == [
        "p0:acquire:A",
        "p1:acquire:B",
    ]
    assert replay_counterexample(faulty_locks, deadlock)
    assert list(
        faulty_locks.successors(deadlock.states[-1])
    ) == []

    print("Opposite lock acquisition order:")
    print_exploration(deadlock)

    corrected_locks = check_deadlocks(
        lock_model(reverse_second=False),
        allowed_terminal=finished,
    )

    assert corrected_locks.status == "deadlock_free"
    assert corrected_locks.complete
    assert corrected_locks.checked == 12

    print("\nConsistent lock acquisition order:")
    print_exploration(corrected_locks)

    # Demonstrate incomplete exploration explicitly.
    limited = check_invariant(
        protocol_model(faulty=False),
        invariant,
        max_states=2,
    )

    assert limited.status == "unknown"
    assert not limited.complete

    print("\nInsufficient exploration budget:")
    print_exploration(limited)


DEMONSTRATIONS = {
    "access": demonstrate_access_control,
    "witnesses": demonstrate_dependent_witnesses,
    "entailment": demonstrate_entailment_and_consistency,
    "protocol": demonstrate_model_checks,
}


def main():
    parser = argparse.ArgumentParser(
        description="Run ELE technical demonstrations."
    )

    parser.add_argument(
        "demo",
        nargs="?",
        default="all",
        choices=["all", *DEMONSTRATIONS],
    )

    args = parser.parse_args()

    if args.demo == "all":
        for demonstration in DEMONSTRATIONS.values():
            demonstration()
    else:
        DEMONSTRATIONS[args.demo]()


if __name__ == "__main__":
    main()