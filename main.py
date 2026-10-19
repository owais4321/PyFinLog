# main.py

from logic_core import (
    ForAll,
    Exists,
    check,
    satisfiable,
    valid,
    equivalent,
    entails,
)
from tools import var, def_pred, print_trace
from examples import demonstrate_model_checks

def propositional_demo():
    print("\nPROPOSITIONAL REASONING\n")

    p = var("p")
    q = var("q")

    # Find a satisfying assignment.
    result = satisfiable(p & q)
    print("Satisfiability of p AND q:", result.status)
    print("Model:", result.assignment)

    # Check a contradiction.
    result = satisfiable(p & ~p)
    print("\nSatisfiability of p AND NOT p:", result.status)

    # Check a tautology.
    result = valid(p | ~p)
    print("Validity of p OR NOT p:", result.status)

    # Find a countermodel.
    result = valid(p >> q)
    print("\nValidity of p IMPLIES q:", result.status)
    print("Countermodel:", result.assignment)

    # Check De Morgan's law.
    result = equivalent(
        ~(p & q),
        (~p) | (~q),
    )
    print("\nDe Morgan equivalence:", result.status)

    # Check modus ponens.
    result = entails(
        [p, p >> q],
        q,
    )
    print("Entailment of q from p and p IMPLIES q:", result.status)


def quantified_demo():
    print("\nQUANTIFIED CHECKING\n")

    x = var("x")
    Even = def_pred("Even", lambda n: n % 2 == 0)

    universal = ForAll(x, Even(x), [2, 3, 4])
    result = check(universal)

    print("All numbers are even:", result.status)
    print("Counterexample:", result.trace.decisive_binding)

    existential = Exists(x, Even(x), [1, 3, 6])
    result = check(existential)

    print("\nSome number is even:", result.status)
    print("Witness:", result.trace.decisive_binding)


def access_control_demo():
    print("\nACCESS-CONTROL CHECKING\n")

    users = ["alice", "bob"]
    resources = ["public", "payroll"]

    u = var("u")
    r = var("r")

    # Intended permissions:
    # Everyone may access public.
    # Only Alice may access payroll.
    Allowed = def_pred(
        "Allowed",
        lambda user, resource: (
            resource == "public" or user == "alice"
        ),
    )

    # Faulty implementation grants every request.
    FaultyGrant = def_pred(
        "FaultyGrant",
        lambda user, resource: True,
    )

    safety_property = ForAll(
        u,
        ForAll(
            r,
            FaultyGrant(u, r) >> Allowed(u, r),
            resources,
        ),
        users,
    )

    result = check(safety_property)

    print("Faulty policy:", result.status)
    print_trace(result.trace)

    # These two nested universal quantifiers identify
    # the unauthorized user-resource pair.
    if result.status == "violated":
        outer = result.trace
        inner = outer.children[0]

        print(
            "\nUnauthorized grant:",
            outer.decisive_binding | inner.decisive_binding,
        )

    # Corrected implementation.
    CorrectGrant = def_pred(
        "CorrectGrant",
        lambda user, resource: (
            resource == "public" or user == "alice"
        ),
    )

    corrected_safety = ForAll(
        u,
        ForAll(
            r,
            CorrectGrant(u, r) >> Allowed(u, r),
            resources,
        ),
        users,
    )

    result = check(corrected_safety)
    print("\nCorrected policy safety:", result.status)

    # Safety alone also permits denying every request.
    # Check that allowed requests are actually granted.
    availability_property = ForAll(
        u,
        ForAll(
            r,
            Allowed(u, r) >> CorrectGrant(u, r),
            resources,
        ),
        users,
    )

    result = check(availability_property)
    print("Corrected policy availability:", result.status)


def main():
    propositional_demo()
    quantified_demo()
    access_control_demo()
    demonstrate_model_checks()


if __name__ == "__main__":
    main()