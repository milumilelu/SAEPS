# V3.4 Curvature-Validation Acceptance

## Outcome

- Engineering validation: `PASSED`
- Protocol seed20 readiness: `PASS`
- Evaluation full readiness: `0/4`
- Development generalization: `NOT_ESTABLISHED`
- Confirmation 30--44: not authorized
- Frozen config hash: `89374e212ee3960d944600d08b4c18821db6d7622096fabe81334dd10949ec6f`

## Accepted clean-provenance evaluation

| Seed | Center | Curvature solver | Exact local | GN <=5% | Finite radius | Full readiness |
|---:|---|---|---|---|---|---|
| 21 | FAIL | N/A | N/A | N/A | N/A | FAIL |
| 22 | PASS | PASS | PASS | FAIL (8.24%) | FAIL | FAIL |
| 23 | PASS | PASS | PASS | FAIL (9.33%) | PASS | FAIL |
| 24 | PASS | FAIL | PASS | PASS (4.97%) | FAIL | FAIL |

The median GN-to-exact error among the three evaluation seeds with a valid local reference is `8.24%`; only `1/3` passes the frozen 5% gate. Raw curvature exceeds exact reduced curvature in `3/3`, preserving strong qualitative evidence of neural-state absorption, but seed20's 1.17% quantitative agreement does not generalize under the current gate.

Curvature solver validation passes `2/3` center-valid evaluation seeds. Seed24's augmented-LSQR curvature differs from explicit by only `2.08e-7`, but its parameter relative normal residual is `1.27e-6`, so the registered solver gate correctly remains failed. Score solving passes `0/3` and stays nonbinding.

Finite-radius validation passes `1/3` center-valid evaluation seeds. Branch audits are complete for `3/3`, with maximum parent-relative function distances below `0.0064`; there is no large function-space discontinuity under the nonbinding 25% alert, but this does not repair GN or resolution failures.

Three first attempts for seeds 22--24 had dirty provenance due to sequential untracked outputs. They are retained, excluded by provenance alone, and exactly reproduced by separately committed clean runs.

## Decision

V3.4 successfully separates the numerical objects and validates the resolution-certificate machinery, but it refutes moving directly to confirmation. The next work, if authorized, must investigate cross-seed GN second-derivative variation, center-minimum robustness, and scalable solver residual behavior without changing or rerunning this frozen evidence.

