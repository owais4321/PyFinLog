# ELE evaluation

Correctness checks passed. Unit-test output is recorded separately.

Generated formulas: 1000; assignment cases: 8000; propositional search checks: 2000.
Generated graphs: 200; invariant/deadlock status checks: 400.
Quantified checks: 50; boundary checks: 7.
| Tool | Family | Size | Faulty | Status | Checked | Median seconds | Python traced peak bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ELE | authorization | 1 | False | holds | 3 | 0.000092 | 7433 |
| ELE | authorization | 1 | True | violated | 3 | 0.000093 | 7497 |
| ELE | authorization | 2 | False | holds | 9 | 0.000398 | 12612 |
| ELE | authorization | 2 | True | violated | 3 | 0.000133 | 9884 |
| ELE | authorization | 4 | False | holds | 81 | 0.006283 | 41115 |
| ELE | authorization | 4 | True | violated | 3 | 0.000206 | 15314 |
| ELE | authorization | 6 | False | holds | 729 | 0.082451 | 135280 |
| ELE | authorization | 6 | True | violated | 3 | 0.000293 | 20960 |
| ELE | authorization | 8 | False | holds | 6561 | 2.326316 | 1336403 |
| ELE | authorization | 8 | True | violated | 3 | 0.001635 | 26262 |
| ELE | lock_ring | 2 | False | deadlock_free | 12 | 0.000290 | 3060 |
| ELE | lock_ring | 2 | True | deadlock | 5 | 0.000153 | 2686 |
| ELE | lock_ring | 3 | False | deadlock_free | 42 | 0.001312 | 5690 |
| ELE | lock_ring | 3 | True | deadlock | 14 | 0.000496 | 3636 |
| ELE | lock_ring | 4 | False | deadlock_free | 150 | 0.003123 | 14804 |
| ELE | lock_ring | 4 | True | deadlock | 40 | 0.000580 | 7914 |
| ELE | lock_ring | 5 | False | deadlock_free | 534 | 0.010175 | 49030 |
| ELE | lock_ring | 5 | True | deadlock | 121 | 0.002259 | 24960 |
| ELE | lock_ring | 6 | False | deadlock_free | 1902 | 0.043219 | 436016 |
| ELE | lock_ring | 6 | True | deadlock | 379 | 0.008256 | 53554 |
| ELE | lock_ring | 7 | False | deadlock_free | 6774 | 0.204070 | 2409010 |
| ELE | lock_ring | 7 | True | deadlock | 1202 | 0.036064 | 452736 |
| ELE | bounded_buffer | 1 | False | holds | 7 | 0.000081 | 5406 |
| ELE | bounded_buffer | 1 | True | violated | 3 | 0.000064 | 4126 |
| ELE | bounded_buffer | 2 | False | holds | 12 | 0.000223 | 7046 |
| ELE | bounded_buffer | 2 | True | violated | 5 | 0.000064 | 4862 |
| ELE | bounded_buffer | 4 | False | holds | 25 | 0.000346 | 11118 |
| ELE | bounded_buffer | 4 | True | violated | 10 | 0.000165 | 6502 |
| ELE | bounded_buffer | 8 | False | holds | 63 | 0.001148 | 23078 |
| ELE | bounded_buffer | 8 | True | violated | 26 | 0.000405 | 11399 |
| ELE | bounded_buffer | 16 | False | holds | 187 | 0.003116 | 52998 |
| ELE | bounded_buffer | 16 | True | violated | 82 | 0.001495 | 30670 |
| ELE | bounded_buffer | 32 | False | holds | 627 | 0.011121 | 85605 |
| ELE | bounded_buffer | 32 | True | violated | 290 | 0.005027 | 57027 |
| ELE | propositional_validity | 4 | False | valid | 16 | 0.000137 | 864 |
| ELE | propositional_validity | 8 | False | valid | 256 | 0.004093 | 1160 |
| ELE | propositional_validity | 12 | False | valid | 4096 | 0.118490 | 1672 |
| ELE | propositional_validity | 16 | False | valid | 65536 | 2.304513 | 1672 |

## Interpretation limits

- Synthetic models and generated inputs do not establish industrial utility or usability.
- Positive model-checking verdicts require exhaustion; unknown results are inconclusive.
- Generated formulas can repeat; the unique count is reported in correctness.json.
- Counterexample JSON is an evidence record, not a standalone certified proof.
- Python traced memory excludes Z3 native allocations; it cannot support cross-tool total-memory claims.
- 10 repetitions support descriptive min/median/max values, not statistical significance.
- Formula/model construction is excluded from query timing; callbacks remain inside exploration timing.
