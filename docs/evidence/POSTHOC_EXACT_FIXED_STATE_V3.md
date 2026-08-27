# SAEPS post-hoc exact fixed-state curvature decomposition v3

**Classification:** `POSTHOC_NONBINDING_MECHANISM_ANALYSIS`

> This analysis is post hoc and nonbinding. It does not alter any preregistered confirmation result.

## Purpose and scope

The original scalar confirmation pipelines computed the full exact objective
Hessian internally but did not persist `H_ll` / `exact_parameter_block` in the
frozen Burgers or Allen--Cahn records. V3 therefore reconstructed each planned
center once with the byte-matched historical CPU/float64 pipeline and captured
the complete exact and Gauss--Newton blocks after center construction.

No frozen confirmation file, locked configuration, seed, gate, failed record,
aggregate, V5 audit, or scientific adjudication was modified. Original-invalid
seeds were rerun only to audit status consistency and could not enter the
mechanism cohort.

## Protocol lineage

- Scientific baseline: `cf76ffe85a78c994351e50b97d013d33a0f01f85`.
- V3 execution-claim commit: `538b866`.
- Environment: Python 3.12.13, PyTorch 2.13.0+cpu, NumPy 2.3.5,
  PyYAML 6.0.3, CPU, float64.
- Preflight used non-study Burgers seed 50 and exercised the real training,
  center, Jacobian, LSQR, explicit Schur, full-Hessian and serialization path.
- V1 and V2 were separately aborted and retained. Neither contributes a
  scientific value to this report.
- Mechanistic identities use the explicit Gauss--Newton Schur solve. The
  historical selected scaled-LSQR value is retained solely for reproduction
  checks.

## Cohort accounting

| Cohort | Planned | Original binding-valid | Rerun center-valid among original-valid | Reproduction pass | Analysis-valid |
|---|---:|---:|---:|---:|---:|
| Burgers | 15 | 12 | 12 | 12 | 12 |
| Allen--Cahn | 10 | 9 | 9 | 9 | 9 |

There were no reproduction mismatches or algebraic/numerical failures among
the 21 original binding-valid seeds. Burgers seeds 57, 61 and 63 and
Allen--Cahn seed 81 remained `CHECKPOINT_INVALID`; no replacement seed was
used. The maximum primary-curvature reproduction relative error was
`3.51e-16`. The maximum selected-LSQR versus explicit-Schur relative error was
`5.70e-11`. Every exact error-identity residual was zero at serialized
precision.

## Exact fixed-state decomposition

All quantities below are descriptive medians over analysis-valid reruns.

| Metric | Burgers (n=12) | Allen--Cahn (n=9) |
|---|---:|---:|
| `E_fix_exact_to_reduced` | 27.749988 | 19.947156 |
| `E_GN_fix_reduced_scale` | 0.156315 | 0.290258 |
| `E_relax` | 0.003081 | 0.002340 |
| `rho_relax` | 1.002442 | 1.002340 |
| `R_freezing_to_GN` | 166.513443 | 65.238090 |

For every analysis-valid seed in both cohorts,
`E_fix_exact_to_reduced > E_GN_fix_reduced_scale`. All 21 seeds had
`E_relax < 0.1`, and all 21 had `0.75 <= rho_relax <= 1.25`. These thresholds
are descriptive only; no new confirmatory p-value or gate is introduced.

The decomposition therefore indicates, for these reconstructed local centers,
that exact state freezing dominates fixed-state Gauss--Newton truncation and
that the Gauss--Newton relaxation correction closely tracks the exact
relaxation correction. This is a post-hoc mechanism result, not an upgrade or
replacement of the original preregistered SAEPS claims.

## Gauss--Newton remainder diagnostic

The sufficient Proposition-2 condition was unavailable for all 21
analysis-valid seeds because `delta >= 1` in every case. Median `delta` was
138,908.16 for Burgers and 475,744.37 for Allen--Cahn. Consequently no finite
bound ratio is interpreted. This is not an experiment failure; it means only
that the sufficient perturbation condition does not hold at these centers.

## Limitations

- This is a deterministic rerun, not the original preregistered confirmation.
- Inclusion requires original binding validity plus center reproduction,
  primary-curvature reproduction and valid full-Hessian numerics.
- Results apply to local finite-damping curvature in the original log-parameter
  coordinate and do not establish global identifiability.
- The theoretical GN bound is non-applicable for all analysis-valid seeds.
- V1 and V2 failures demonstrate that post-hoc runner correctness required
  explicit versioned correction; their failed records remain visible.
- A mechanism figure was intentionally omitted at the author's direction.

Machine-readable raw records, complete exact/GN matrices, aggregate JSON and
CSV, execution claim, preflight, canary audit, logs and SHA-256 manifest are
stored under `outputs/posthoc/exact_fixed_state_v3/` and `docs/evidence/`.
