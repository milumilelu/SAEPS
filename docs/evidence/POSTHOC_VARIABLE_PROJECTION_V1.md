# Post-hoc variable-projection baseline, protocol v1

Classification: `POSTHOC_NONBINDING_BASELINE_ANALYSIS`.

This analysis uses only the complete Gauss--Newton and exact-Hessian blocks saved by V3 at commit `39343bc32ae38ea2ad118011105cf4cb2c2f3241`. It involved no training, no new PDE experiment, no confirmation rerun, and no change to any preregistered or V5 adjudication.

## Result

| Cohort | V3-valid / planned input | Median numerical rank | Median nullity | Median finite-vs-undamped relative difference | Exact gamma=0 classically admissible |
|---|---:|---:|---:|---:|---:|
| Burgers | 12 / 12 | 60 | 5 | 0.232071 | 0 / 12 |
| Allen--Cahn | 9 / 9 | 32 | 1 | 0.0596703 | 0 / 9 |

The resolved condition numbers are very large: cohort medians are `2.70e13` for Burgers and `7.37e12` for Allen--Cahn. Under the pre-frozen historical positive-definiteness rule, none of the 21 exact state Hessians admits the ordinary, unregularized classical Schur complement. Consequently, no `H_red_exact_0`, `E_VP0_exact0`, or `E_raw_exact0` is reported.

All scalar pseudoinverse values satisfy `F_VP0 <= F_raw` within the frozen numerical tolerance; no scientific value was clamped. No numerical or algebraic execution failure occurred.

## Fixed TSVD sensitivity

Relative differences below compare each pre-frozen TSVD cutoff with the default machine-rule Moore--Penrose result.

| Cohort | cutoff | median relative difference | maximum relative difference | rank range |
|---|---:|---:|---:|---:|
| Burgers | 1e-8 | 0.157848 | 0.485122 | 44--52 |
| Burgers | 1e-10 | 0.067366 | 0.120630 | 46--57 |
| Burgers | 1e-12 | 0.026514 | 0.077213 | 50--61 |
| Allen--Cahn | 1e-8 | 0.052658 | 0.233691 | 22--28 |
| Allen--Cahn | 1e-10 | 0.044243 | 0.121169 | 26--31 |
| Allen--Cahn | 1e-12 | 0.004987 | 0.104610 | 29--33 |

The cutoff dependence and the absence of classically admissible exact gamma=0 centers must remain visible. The result is mixed: finite damping differs more from the undamped GN projection in Burgers than in Allen--Cahn, while exact unregularized nonlinear elimination is unavailable under the frozen admissibility rule in both cohorts. This is descriptive post-hoc evidence, not a new confirmatory gate.

## Provenance

- Frozen protocol: `configs/posthoc_variable_projection_v1.yaml`
- Machine-readable aggregate and per-seed records: `docs/evidence/posthoc_variable_projection_v1.json`
- Flat table: `docs/evidence/posthoc_variable_projection_v1.csv`
- Per-seed derived records: `outputs/posthoc/variable_projection_v1/`
- Recorded analysis runtime: 0.133 seconds (matrix analysis only)
