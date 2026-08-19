# V3.3 Seed-20 Numerical-Decomposition Acceptance

## Outcome

- Engineering gate: `PASSED`
- Registered all-gates chain: `FAIL`
- Reporting scope: `NONBINDING_DIAGNOSTIC_ONLY`
- Seed expansion: forbidden
- Confirmation: unauthorized
- Run: `v3-3-num-decomp-s20-20260819T142127.327595+0000-3b23a23db90f`
- Clean implementation commit: `b0c317c8d13d49db5942dee5203c964cb74bb482`
- Config hash: `83c190d1d76600671ae5558e93b50720ef96169e7bd43fab073f874237029bae`

## Common center

The reproduced center passed all registered gates: `G_theta=5.6518790e-7`, `S_theta=2.0045785e-6`, and the exact numerical state-minimum candidate gate. `S_lambda=0.0971141` was recorded. Gamma was `0.0755582230734139`.

## Four-node decomposition

| Node | Value | Registered status |
|---|---:|---|
| `Fraw` | 803.419013120337 | diagnostic |
| `Fse_GN_matrix_free_CG` | 36.274206744895 | `SOLVER_FAILURE` |
| `Fse_GN_explicit_direct` | 36.274206651407 | `NUMERICAL_FAILURE` on auxiliary residual RHS audit |
| `Fse_GN_augmented_LSQR` | 36.274206659206 | `SOLVER_FAILURE` on auxiliary residual RHS audit |
| `Hred_exact_gamma` | 35.853846001863 | `PASS` |
| `Hprofile_gamma` | 33.494252744023 | `PROFILE_FAILURE` |

The finite parameter-curvature values remain diagnostic even when their full solver gate fails. Standard CG's parameter-column solve passed with relative residual `5.78e-11`; its auxiliary residual RHS failed at `1.20e-7`. Augmented LSQR's parameter-column solve reached relative normal residual `1.78e-9` and matched the explicit curvature to `2.15e-10`; its auxiliary residual RHS stopped at `2.91e-6`. Jacobi-PCG remained inaccurate.

## Registered segment errors

| Segment | Relative error |
|---|---:|
| CG → explicit direct | 2.5773e-9 |
| Jacobi-PCG → explicit direct | 6.6760e-4 |
| augmented LSQR → explicit direct | 2.1501e-10 |
| explicit GN → exact gamma reduction | 1.17243% |
| exact gamma reduction → nonlinear profile | 7.04477% |
| explicit GN → nonlinear profile total | 8.29979% |

This isolates the seed-20 diagnosis. Normal-equation robustness remains a real engineering problem under the full RHS gate, but the standard-CG parameter curvature is not materially biased here. GN approximation error is modest relative to the nonlinear/profile discrepancy. The largest observed segment is exact-to-profile, whose endpoint remains invalid because the strict profile failed its finest multiscale and optimization-accuracy gates. Therefore this result locates the dominant discrepancy but does not establish a paper-facing scientific comparison.

