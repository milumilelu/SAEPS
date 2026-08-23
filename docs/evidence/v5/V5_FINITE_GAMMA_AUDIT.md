# V5.1 Finite-Gamma / Effective-Rank Audit

- Engineering status: `PASSED`
- Terminal records: `42/42`
- Numerical PASS: `38/42`
- Failed terminal records retained: `4`
- Scientific win gate: none (descriptive audit)
- Nominal gamma recalibration: forbidden and not performed

## Alpha summary (all computable quantities retained)

| alpha | PASS/6 | median eta | median effective rank | median E_SAEPS | median E_raw |
|---:|---:|---:|---:|---:|---:|
| 1e-10 | 2/6 | 0.045627 | 41.1599 | 0.2587670789561957 | 22.381842243666792 |
| 1e-08 | 6/6 | 0.0482649 | 35.7827 | 0.16299673884131713 | 22.68105487442387 |
| 1e-06 | 6/6 | 0.065335 | 27.0456 | 0.13790000442060107 | 15.662217440317626 |
| 1e-04 | 6/6 | 0.130094 | 16.3312 | 0.06018903585662204 | 6.5077688387180554 |
| 1e-02 | 6/6 | 0.57982 | 6.575 | 0.018494404591106548 | 0.746512710652403 |
| 1e+00 | 6/6 | 0.968803 | 0.949496 | 0.011628304784936302 | 0.03824592529180781 |
| 1e+02 | 6/6 | 0.999637 | 0.0151977 | 0.011178912218072082 | 0.010915740485819368 |

## Registered limit checks

At alpha=1e2, median relative |Fse_GN-Fraw|/|Fraw| is `0.000362808` and the maximum is `0.00127042`.
Eta is nondecreasing over the registered grid for all six checkpoints: `true`.
No analogous high-gamma convergence claim is imposed on the exact Hessian.

## Failed terminal records

| Family | Seed | alpha | Status | Stage | Reason |
|---|---:|---:|---|---|---|
| burgers | 45 | 1e-10 | NUMERICAL_FAILURE | exact_reference | exact finite-gamma reduction gate failed |
| burgers | 46 | 1e-10 | SOLVER_FAILURE | curvature_solver | frozen V5.1 solver gate failed |
| burgers | 47 | 1e-10 | SOLVER_FAILURE | curvature_solver | frozen V5.1 solver gate failed |
| allen_cahn | 72 | 1e-10 | NUMERICAL_FAILURE | exact_reference | exact finite-gamma reduction gate failed |
