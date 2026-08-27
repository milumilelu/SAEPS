# Post-hoc whitening stabilizer sensitivity, protocol v1

This analysis is post hoc and nonbinding. It uses only existing two-parameter matrices. No PINN was retrained and no new PDE experiment was performed.

## Provenance and scope

- Source evidence commit: `db55ef9d1db5d2080f7ceee68ba1d094f4cce49c`
- Source execution-record commit: `ad81f587e6193d59e9cf7d06d271f847ba6819d2`
- Source report SHA256: `73a5ffb112e7a9c630d9ae9e5579ce5ca718e5d7a46c53210dac5d7c810628c8`
- Frozen metric implementation SHA256: `6f7147448f1af758395c0229804b1ded26ee70e8774c5347749f9861156467f1`
- Planned records: 10
- Original binding-valid records: 8
- Original invalid records retained outside the sensitivity cohort: seeds 219 and 221
- Nominal reproduction: 8/8 passed exactly

`historical_evidence_modified = false`; `training_performed = false`; `new_pde_experiment = false`.

## Paired directions

| Relative stabilizer | SAEPS better | Raw better | Numerical ties | Numerical failures | Same direction as nominal |
|---:|---:|---:|---:|---:|---:|
| 1e-8 | 8/8 | 0/8 | 0/8 | 0/8 | 8/8 |
| 1e-10 (nominal) | 8/8 | 0/8 | 0/8 | 0/8 | 8/8 |
| 1e-12 | 8/8 | 0/8 | 0/8 | 0/8 | 8/8 |

No additional sign test or confirmatory statistic was computed. The original two-parameter status remains `INCONCLUSIVE` because only 8/10 planned checkpoints were binding-valid, below the preregistered 9/10 gate.

## Metric variation relative to nominal

| Relative stabilizer | E_raw median change | E_raw maximum change | E_SAEPS median change | E_SAEPS maximum change |
|---:|---:|---:|---:|---:|
| 1e-8 | 6.86446e-9 | 1.32730e-8 | 3.12101e-9 | 1.99655e-8 |
| 1e-10 | 0 | 0 | 0 | 0 |
| 1e-12 | 6.86445e-11 | 1.32730e-10 | 3.12101e-11 | 1.99655e-10 |

The direction of all eight valid paired comparisons is preserved across relative whitening stabilizers `1e-8`, `1e-10`, and `1e-12`. This is an observed sensitivity result, not a mathematical invariance claim.

## Paper-facing explanation

> The raw Gauss--Newton matrix is used only to define a common, target-independent coordinate scaling for the paired matrix errors. It is available at every checkpoint and is positive semidefinite before the small diagonal stabilization. The same whitening transformation is therefore applied to the raw and SAEPS errors without using the exact reference or the competing method to define the coordinate scale.

The data support adding: “The observed paired direction is unchanged when the relative stabilization factor is varied from `1e-12` to `1e-8`.”

## Limitations

The analysis covers only the eight historically binding-valid two-parameter confirmation checkpoints and three pre-frozen stabilizer factors. It does not reclassify invalid records, establish ordering invariance for other matrices or stabilizers, or increase the original evidence level. The raw matrix defines a common coordinate scale but does not theoretically guarantee preservation of paired ordering.

Machine-readable aggregate, flat table, and all eight derived per-record results are stored alongside this report. Matrix-analysis runtime was approximately 0.101 seconds.
