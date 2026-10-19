# ELE evaluation

Correctness checks passed. Unit-test output is recorded separately.

Generated formulas: 1000; assignment cases: 8000; propositional search checks: 2000.
Generated graphs: 200; invariant/deadlock status checks: 400.
Quantified checks: 50; boundary checks: 7.
Z3 reference checks: 0.

| Tool | Family | Size | Faulty | Status | Checked | Median seconds | Python traced peak bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ELE | authorization | 1 | False | holds | 3 | 0.000085 | 7433 |
| ELE | authorization | 1 | True | violated | 3 | 0.000087 | 7497 |
| ELE | authorization | 2 | False | holds | 9 | 0.000409 | 12612 |
| ELE | authorization | 2 | True | violated | 3 | 0.000126 | 9884 |
| ELE | authorization | 4 | False | holds | 81 | 0.005914 | 41115 |
| ELE | authorization | 4 | True | violated | 3 | 0.000182 | 15314 |
| ELE | authorization | 6 | False | holds | 729 | 0.073289 | 135280 |
| ELE | authorization | 6 | True | violated | 3 | 0.000259 | 20960 |
| ELE | authorization | 8 | False | holds | 6561 | 1.756335 | 1336403 |
| ELE | authorization | 8 | True | violated | 3 | 0.000569 | 26262 |
| ELE | lock_ring | 2 | False | deadlock_free | 12 | 0.000097 | 3060 |
| ELE | lock_ring | 2 | True | deadlock | 5 | 0.000055 | 2686 |
| ELE | lock_ring | 3 | False | deadlock_free | 42 | 0.000446 | 5690 |
| ELE | lock_ring | 3 | True | deadlock | 14 | 0.000165 | 3636 |
| ELE | lock_ring | 4 | False | deadlock_free | 150 | 0.002040 | 14804 |
| ELE | lock_ring | 4 | True | deadlock | 40 | 0.000584 | 7914 |
| ELE | lock_ring | 5 | False | deadlock_free | 534 | 0.008496 | 49030 |
| ELE | lock_ring | 5 | True | deadlock | 121 | 0.002454 | 24960 |
| ELE | lock_ring | 6 | False | deadlock_free | 1902 | 0.046616 | 436016 |
| ELE | lock_ring | 6 | True | deadlock | 379 | 0.008324 | 53554 |
| ELE | lock_ring | 7 | False | deadlock_free | 6774 | 0.184989 | 2409010 |
| ELE | lock_ring | 7 | True | deadlock | 1202 | 0.032480 | 452736 |
| ELE | bounded_buffer | 1 | False | holds | 7 | 0.000103 | 5406 |
| ELE | bounded_buffer | 1 | True | violated | 3 | 0.000051 | 4126 |
| ELE | bounded_buffer | 2 | False | holds | 12 | 0.000180 | 7046 |
| ELE | bounded_buffer | 2 | True | violated | 5 | 0.000081 | 4862 |
| ELE | bounded_buffer | 4 | False | holds | 25 | 0.000400 | 11118 |
| ELE | bounded_buffer | 4 | True | violated | 10 | 0.000161 | 6502 |
| ELE | bounded_buffer | 8 | False | holds | 63 | 0.000964 | 23078 |
| ELE | bounded_buffer | 8 | True | violated | 26 | 0.000402 | 11399 |
| ELE | bounded_buffer | 16 | False | holds | 187 | 0.003146 | 52998 |
| ELE | bounded_buffer | 16 | True | violated | 82 | 0.001306 | 30670 |
| ELE | bounded_buffer | 32 | False | holds | 627 | 0.010746 | 85605 |
| ELE | bounded_buffer | 32 | True | violated | 290 | 0.005219 | 57027 |
| ELE | propositional_validity | 4 | False | valid | 16 | 0.000132 | 864 |
| ELE | propositional_validity | 8 | False | valid | 256 | 0.003695 | 1160 |
| ELE | propositional_validity | 12 | False | valid | 4096 | 0.090457 | 1672 |
| ELE | propositional_validity | 16 | False | valid | 65536 | 2.111800 | 1672 |

## Interpretation limits

- Synthetic models and generated inputs do not establish industrial utility or usability.
- Positive model-checking verdicts require exhaustion; unknown results are inconclusive.
- Generated formulas can repeat; the unique count is reported in correctness.json.
- Counterexample JSON is an evidence record, not a standalone certified proof.
- Python traced memory excludes Z3 native allocations; it cannot support cross-tool total-memory claims.
- The Z3 baseline covers propositional validity only, not transition-system verification.
- 10 repetitions support descriptive min/median/max values, not statistical significance.
- Formula/model construction is excluded from query timing; callbacks remain inside exploration timing.
