"""Reproducible ELE evaluation. Run: python evaluation.py --runs 3
Optional shared propositional baseline: python evaluation.py --runs 3 --z3
Outputs: evaluation_results/{correctness.json,benchmarks.csv,environment.json,summary.md,unit_tests.txt}
No runtime dependencies unless --z3 is selected (requires z3-solver).
"""
import argparse
import csv
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import asdict
from itertools import product
from pathlib import Path

from logic_core import Constant, Variable, Not, And, Or, Implies, Iff, ForAll, Exists
from logic_core.checking import explain, check, valid, satisfiable, LimitExceeded
from logic_core.model_checking import (
    Transition, TransitionSystem, check_invariant, check_deadlocks, replay_counterexample,
)
from tools import var, def_pred

SEED = 4321
ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def generate_formula(rng, depth):
    if depth == 0 or rng.random() < .25:
        return rng.choice(('a', 'b', 'c'))
    op = rng.choice(('not', 'and', 'or', 'implies', 'iff'))
    args = 1 if op == 'not' else 2
    return (op, *(generate_formula(rng, depth - 1) for _ in range(args)))


def reference_formula(tree, context):
    if isinstance(tree, str):
        return context[tree]
    op = tree[0]
    a = reference_formula(tree[1], context)
    if op == 'not':
        return not a
    b = reference_formula(tree[2], context)
    if op == 'and': return a and b
    if op == 'or': return a or b
    if op == 'implies': return (not a) or b
    if op == 'iff': return a == b
    raise ValueError(op)


def compile_formula(tree):
    if isinstance(tree, str): return Variable(tree)
    constructors = {'not': Not, 'and': And, 'or': Or, 'implies': Implies, 'iff': Iff}
    return constructors[tree[0]](*(compile_formula(t) for t in tree[1:]))


def compile_z3(tree, z3):
    if isinstance(tree, str): return z3.Bool(tree)
    children = [compile_z3(t, z3) for t in tree[1:]]
    op = tree[0]
    if op == 'not': return z3.Not(children[0])
    if op == 'and': return z3.And(*children)
    if op == 'or': return z3.Or(*children)
    if op == 'implies': return z3.Implies(*children)
    return children[0] == children[1]


def formula_validation(z3=None):
    rng = random.Random(SEED)
    evaluations = searches = baseline_checks = 0
    unique = set()
    for _ in range(1000):
        tree = generate_formula(rng, 4)
        unique.add(repr(tree))
        expression = compile_formula(tree)
        answers = []
        for values in product((False, True), repeat=3):
            context = dict(zip(('a', 'b', 'c'), values))
            expected = reference_formula(tree, context)
            require(expression.evaluate(context) == expected, 'evaluation mismatch')
            require(explain(expression, context).value == expected, 'trace mismatch')
            evaluations += 1
            answers.append(expected)
        sat, validity = satisfiable(expression), valid(expression)
        require((sat.status == 'sat') == any(answers), 'SAT mismatch')
        require((validity.status == 'valid') == all(answers), 'validity mismatch')
        if sat.assignment is not None:
            require(expression.evaluate(sat.assignment) is True, 'invalid model')
        if validity.assignment is not None:
            require(expression.evaluate(validity.assignment) is False, 'invalid countermodel')
        searches += 2
        if z3 is not None:
            symbolic = compile_z3(tree, z3)
            for term, expected in ((symbolic, any(answers)), (z3.Not(symbolic), not all(answers))):
                solver = z3.Solver()
                solver.add(term)
                verdict = solver.check()
                require(verdict != z3.unknown, 'Z3 returned unknown')
                require((verdict == z3.sat) == expected, 'Z3 disagreement')
                baseline_checks += 1
    return dict(generated=1000, unique= len(unique), assignment_cases=evaluations,
                search_checks=searches, z3_checks=baseline_checks, mismatches=0)


def reference_distances(graph):
    """Independent repeated edge relaxation, not the ELE BFS implementation."""
    distance = {0: 0}
    changed = True
    while changed:
        changed = False
        for source in list(distance):
            for target in graph[source]:
                candidate = distance[source] + 1
                if target not in distance or candidate < distance[target]:
                    distance[target] = candidate
                    changed = True
    return distance


def graph_validation():
    rng = random.Random(SEED + 1)
    violations = deadlocks = 0
    for _ in range(200):
        graph = {s: [t for t in range(8) if rng.random() < .15] for s in range(8)}
        bad = {s for s in range(8) if rng.random() < .2}
        model = TransitionSystem((0,), lambda s, g=graph: [Transition(f'edge:{s}:{t}', t) for t in g[s]])
        invariant = def_pred('Safe', lambda s, b=bad: s not in b)(var('state'))
        distance = reference_distances(graph)
        failures = set(distance) & bad
        result = check_invariant(model, invariant)
        require(result.status == ('violated' if failures else 'holds'), 'graph invariant mismatch')
        if failures:
            require(len(result.actions) == min(distance[s] for s in failures), 'non-shortest invariant path')
            require(replay_counterexample(model, result), 'invariant replay failure')
            require(result.states[-1] in bad, 'endpoint is not a violation')
            violations += 1
        else:
            require(result.complete and result.checked == len(distance), 'incomplete positive verdict')
        sinks = {s for s in distance if not graph[s]}
        result = check_deadlocks(model)
        require(result.status == ('deadlock' if sinks else 'deadlock_free'), 'deadlock mismatch')
        if sinks:
            require(len(result.actions) == min(distance[s] for s in sinks), 'non-shortest deadlock path')
            require(replay_counterexample(model, result), 'deadlock replay failure')
            require(not graph[result.states[-1]], 'endpoint is not a sink')
            deadlocks += 1
        else:
            require(result.complete and result.checked == len(distance), 'incomplete deadlock verdict')
    return dict(graphs=200, status_checks=400, replayed_invariant_paths=violations,
                replayed_deadlock_paths=deadlocks, mismatches=0)


def quantified_validation():
    x, y = var('x'), var('y')
    less = def_pred('Less', lambda a, b: a < b)
    domains = [[], [0], [0, 1], [1, 2], [0, 1, 2]]
    count = 0
    for dx in domains:
        for dy in domains:
            result = check(ForAll(x, Exists(y, less(x, y), dy), dx))
            expected = all(any(a < b for b in dy) for a in dx)
            require((result.status == 'holds') == expected, 'quantified mismatch')
            if expected:
                for child in result.trace.children:
                    a = child.bindings['x']
                    b = child.decisive_binding['y']
                    require(a < b and b in dy, 'invalid dependent witness')
            else:
                a = result.trace.decisive_binding['x']
                require(a in dx and not any(a < b for b in dy), 'invalid outer counterexample')
            reverse = check(Exists(y, ForAll(x, less(x, y), dx), dy))
            expected_reverse = any(all(a < b for a in dx) for b in dy)
            require((reverse.status == 'holds') == expected_reverse, 'reversed quantifier mismatch')
            count += 2
    return dict(domain_pairs=25, checks=count, mismatches=0)


def boundary_validation():
    chain = TransitionSystem((0,), lambda s: [Transition('next', s + 1)])
    require(check_invariant(chain, Constant(True), max_states=3).status == 'unknown', 'state budget unsound')
    loop = TransitionSystem((0,), lambda s: [Transition('a', 0), Transition('b', 0)])
    require(check_invariant(loop, Constant(True), max_transitions=1).status == 'unknown', 'transition budget unsound')
    formula = ForAll(var('x'), Constant(True), [1, 2])
    require(check_invariant(loop, formula, max_steps=1).status == 'unknown', 'formula budget unsound')
    terminal = TransitionSystem((0,), lambda s: [])
    require(check_deadlocks(terminal).status == 'deadlock', 'sink not detected')
    require(check_deadlocks(terminal, allowed_terminal=lambda s: True).status == 'deadlock_free', 'terminal exemption failed')
    require(check_deadlocks(loop).status == 'deadlock_free', 'self-loop classified as deadlock')
    require(check_invariant(terminal, Constant(False)).actions == [], 'initial violation path invalid')
    return dict(checks=7, mismatches=0)


def authorization_model(n, faulty):
    """Each user may be authorized/granted. Bug permits grant before authorization."""
    def successors(state):
        authorized, granted = state
        for user in range(n):
            bit = 1 << user
            if not authorized & bit:
                yield Transition(f'authorize:{user}', (authorized | bit, granted))
            if not granted & bit and (faulty or authorized & bit):
                yield Transition(f'grant:{user}', (authorized, granted | bit))
    user = var('user')
    state = var('state')
    authorized = def_pred('Authorized', lambda s, u: bool(s[0] & (1 << u)))
    granted = def_pred('Granted', lambda s, u: bool(s[1] & (1 << u)))
    invariant = ForAll(user, granted(state, user) >> authorized(state, user), list(range(n)))
    return TransitionSystem(((0, 0),), successors, 'authorization'), invariant


def lock_model(n, faulty):
    """Ring of lock pairs; correction orders each pair by lock identifier."""
    def successors(state):
        phases, owners = state
        for process in range(n):
            pair = (process, (process + 1) % n)
            first, second = pair if faulty else tuple(sorted(pair))
            stage = phases[process]
            new_phases, new_owners = list(phases), list(owners)
            if stage in (0, 1):
                lock = first if stage == 0 else second
                if owners[lock] != -1: continue
                new_owners[lock] = process
                new_phases[process] += 1
                action = f'acquire:{process}:{lock}'
            elif stage == 2:
                for lock in pair: new_owners[lock] = -1
                new_phases[process] = 3
                action = f'release:{process}'
            else: continue
            yield Transition(action, (tuple(new_phases), tuple(new_owners)))
    return TransitionSystem((((0,) * n, (-1,) * n),), successors, 'lock_ring')


def buffer_model(capacity, faulty):
    """Finite workload: produced/consumed counters bound the execution length."""
    total = capacity + 2
    def successors(state):
        count, produced, consumed = state
        if produced < total and (faulty or count < capacity):
            yield Transition('produce', (count + 1, produced + 1, consumed))
        if count > 0:
            yield Transition('consume', (count - 1, produced, consumed + 1))
    invariant = def_pred('BufferInvariant', lambda s: 0 <= s[0] <= capacity and s[0] == s[1] - s[2])(var('state'))
    return TransitionSystem(((0, 0, 0),), successors, 'bounded_buffer'), invariant


def measure(function, runs):
    """Time without tracemalloc; measure traced allocation peak in a separate run."""
    durations, verdicts = [], []
    for _ in range(runs):
        start = time.perf_counter()
        result = function()
        durations.append(time.perf_counter() - start)
        verdicts.append(result.status)
    require(len(set(verdicts)) == 1, 'nondeterministic verdict')
    tracemalloc.start()
    try:
        memory_result = function()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    require(memory_result.status == result.status, 'memory-run verdict mismatch')
    return result, dict(runs=runs, time_median_s=statistics.median(durations),
                       time_min_s=min(durations), time_max_s=max(durations),
                       peak_traced_python_bytes=peak)


def benchmark(runs, z3=None):
    rows, witnesses = [], []
    cases = []
    for n in (1, 2, 4, 6, 8):
        for faulty in (False, True):
            model, invariant = authorization_model(n, faulty)
            cases.append(('authorization', n, faulty, model, invariant, None))
    for n in (2, 3, 4, 5, 6, 7):
        for faulty in (False, True):
            model = lock_model(n, faulty)
            cases.append(('lock_ring', n, faulty, model, None, lambda s: all(p == 3 for p in s[0])))
    for n in (1, 2, 4, 8, 16, 32):
        for faulty in (False, True):
            model, invariant = buffer_model(n, faulty)
            cases.append(('bounded_buffer', n, faulty, model, invariant, None))
    for family, size, faulty, model, invariant, terminal in cases:
        function = (lambda m=model, i=invariant: check_invariant(m, i, max_states=100000, max_transitions=1000000)) if invariant is not None else (lambda m=model, t=terminal: check_deadlocks(m, allowed_terminal=t, max_states=100000, max_transitions=1000000))
        result, timing = measure(function, runs)
        expected = ('violated' if faulty else 'holds') if invariant is not None else ('deadlock' if faulty else 'deadlock_free')
        require(result.status in (expected, 'unknown'), 'benchmark verdict mismatch')
        if result.states:
            require(replay_counterexample(model, result), 'benchmark replay failure')
            shortest = 1 if family == 'authorization' else size if family == 'lock_ring' else size + 1
            require(len(result.actions) == shortest, 'benchmark non-shortest witness')
            if invariant is not None:
                require(check(invariant, {'state': result.states[-1]}).status == 'violated', 'benchmark endpoint mismatch')
            else:
                require(not list(model.successors(result.states[-1])) and not terminal(result.states[-1]), 'benchmark sink mismatch')
            witnesses.append(dict(family=family, size=size, faulty=faulty, result=asdict(result)))
        if not faulty and result.status != 'unknown':
            if family == 'authorization':
                require(result.checked == 3 ** size, 'authorization reachable-count mismatch')
            elif family == 'bounded_buffer':
                expected_states = sum(min(size, p) + 1 for p in range(size + 3))
                require(result.checked == expected_states, 'buffer reachable-count mismatch')
        rows.append(dict(tool='ELE', family=family, size=size, faulty=faulty, status=result.status,
                         complete=result.complete, discovered=result.discovered, checked=result.checked,
                         transitions=result.transitions, path_length=len(result.actions) if result.states else '', **timing))
    # Worst-case validity: all assignments must be examined.
    for n in (4, 8, 12, 16):
        tree = ('or', 'v0', ('not', 'v0'))
        for i in range(1, n):
            name = f'v{i}'
            tree = ('and', tree, ('or', name, ('not', name)))
        expression = compile_formula(tree)
        result, timing = measure(lambda e=expression: valid(e), runs)
        require(result.status == 'valid' and result.checked == 2 ** n, 'tautology benchmark mismatch')
        rows.append(dict(tool='ELE', family='propositional_validity', size=n, faulty=False,
                         status=result.status, complete=True, checked=result.checked, **timing))
        if z3 is not None:
            symbolic = compile_z3(tree, z3)
            def solve(term=symbolic):
                solver = z3.Solver()
                solver.add(z3.Not(term))
                verdict = solver.check()
                # Keep the SMT solver's native verdict; unsat means validity.
                class Verdict:
                    status = str(verdict)
                return Verdict()
            result, timing = measure(solve, runs)
            require(result.status == 'unsat', 'Z3 benchmark mismatch')
            rows.append(dict(tool='Z3', family='propositional_validity', size=n, faulty=False,
                             status='valid', complete=True, **timing))
    return rows, witnesses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--z3', action='store_true')
    parser.add_argument('--output', default='evaluation_results')
    args = parser.parse_args()
    if args.runs < 1: parser.error('--runs must be positive')
    z3 = None
    if args.z3:
        try: import z3
        except ImportError: parser.error('--z3 requires: python -m pip install z3-solver')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v'], cwd=ROOT,
                           text=True, capture_output=True)
    (output / 'unit_tests.txt').write_text(tests.stdout + tests.stderr)
    require(tests.returncode == 0, 'Unit tests failed; see unit_tests.txt')
    correctness = dict(seed=SEED, formulas=formula_validation(z3), graphs=graph_validation(),
                       quantified=quantified_validation(), boundaries=boundary_validation())
    rows, witnesses = benchmark(args.runs, z3)
    sources = sorted((ROOT / 'logic_core').glob('*.py')) + [ROOT / 'tools.py', Path(__file__).resolve()]
    environment = dict(python=sys.version, platform=platform.platform(), machine=platform.machine(),
                       timer='perf_counter', repetitions=args.runs, z3_version=z3.get_version_string() if z3 else None,
                       source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                       memory_metric='tracemalloc peak during a separate run; excludes native allocations and is not RSS',
                       timing_scope='query/exploration including solver creation, excluding formula/model construction; no tracemalloc during timing')
    for name, data in [('correctness.json', correctness), ('environment.json', environment), ('counterexamples.json', witnesses)]:
        (output / name).write_text(json.dumps(data, indent=2) + '\n')
    fields = ['tool','family','size','faulty','status','complete','discovered','checked','transitions','path_length',
              'runs','time_median_s','time_min_s','time_max_s','peak_traced_python_bytes']
    with (output / 'benchmarks.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# ELE evaluation', '', 'Correctness checks passed. Unit-test output is recorded separately.', '',
             f'Generated formulas: 1000; assignment cases: 8000; propositional search checks: 2000.',
             'Generated graphs: 200; invariant/deadlock status checks: 400.',
             'Quantified checks: 50; boundary checks: 7.',
             '| Tool | Family | Size | Faulty | Status | Checked | Median seconds | Python traced peak bytes |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f'| {row["tool"]} | {row["family"]} | {row["size"]} | {row["faulty"]} | {row["status"]} | {row.get("checked", "")} | {row["time_median_s"]:.6f} | {row["peak_traced_python_bytes"]} |')
    lines += ['', '## Interpretation limits', '',
              '- Synthetic models and generated inputs do not establish industrial utility or usability.',
              '- Positive model-checking verdicts require exhaustion; unknown results are inconclusive.',
              '- Generated formulas can repeat; the unique count is reported in correctness.json.',
              '- Counterexample JSON is an evidence record, not a standalone certified proof.',
              '- Python traced memory excludes Z3 native allocations; it cannot support cross-tool total-memory claims.',
              f'- {args.runs} repetitions support descriptive min/median/max values, not statistical significance.',
              '- Formula/model construction is excluded from query timing; callbacks remain inside exploration timing.']
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(correctness, indent=2))
    print(f'Saved {len(rows)} benchmark rows and {len(witnesses)} counterexample records to {output}')


if __name__ == '__main__':
    main()
