# V4.8 Paired Robustness Report

## Outcome

Engineering execution is `PASSED`; the scientific gate is
`DESCRIPTIVE_ONLY`. All 60 planned runs have terminal records and verified
manifest hashes. There are 52 binding-valid runs, seven
`CHECKPOINT_INVALID` runs, one `SOLVER_FAILURE`, and no unhandled numerical
failure.

## Noise × sparsity

The nine cells contain 45/45 planned records and 43 binding-valid chains.
Seven cells are 5/5 valid. `noise=0.01, fraction=0.5` is 4/5 because seed130
is center-invalid; `noise=0.01, fraction=1.0` is 4/5 because seed132 fails the
frozen curvature-solver gate. No failed run was replaced.

Across valid records, median retained fractions range from 0.0104 to 0.0378.
The lower observation fractions generally retain a smaller fraction of raw
curvature in this design. This is descriptive and is not a causal or universal
noise law.

The three exact-Hessian anchor cells provide 15 planned comparisons: 14 are
binding-valid and all 14 are strict SAEPS wins. Among valid anchors, median
`E_SAEPS` is 0.0879, median `E_raw` is 38.1318, and median paired `D` is
38.0163. These values support robustness of the scalar comparative effect at
the anchors, but do not create a new confirmation test.

## Architecture

- narrow width8: 5/5 binding-valid, median eta 0.0668;
- nominal width16: 4/5 binding-valid, median eta 0.0458; seed138 is
  center-invalid;
- wide width32: 0/5 binding-valid; all five fail the frozen state-center gate.

The wide-network SAEPS curvature hypothesis was therefore not tested. The
result is a strong architecture-dependent center-availability limitation, not
evidence that SAEPS curvature itself fails once a valid wide center exists.
No optimizer, center threshold, seed, or width may be changed in response.

## Integrity and source

The machine-readable source is `docs/evidence/v4_8_robustness.json`, generated
only from hashed records under `outputs/runs/v4_8_robustness/`. The config hash
is `7e0840d61703c6044e83d7f13a5260f7624d9248593cd56708c1ee53d4cc4ac8`.
