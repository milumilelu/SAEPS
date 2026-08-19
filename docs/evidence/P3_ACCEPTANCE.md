# P3 Nonlinear Profile Engine — Acceptance Evidence

**Engineering gate:** `PASSED`  
**Validation date:** 2026-08-19  
**Validated implementation commit:** `4959f30dd7e5a4b30f51ef69775681efda9ef384`

## Clean-run identity

- Run ID: `p3-profile-s20260819-20260819T073155.389643+0000-212ceee31e5e`
- Config hash: `707a3d7d97d063a4dce9bfb5778533fe7256a7b71e58c8f12b9476758a0c65c9`
- Python 3.12.13, PyTorch 2.13.0, float64 CPU
- Git provenance: implementation commit above, `git_dirty=false`

## Actual commands

```text
pytest -q
.................... [100%]
20 passed in 3.10s

python scripts/04_validate_profile.py
status: PASS

python scripts/01_validate_core.py
status: PASS
```

## Known-curvature optimization test

The actual optimizer test used a two-dimensional state and one-dimensional parameter with known reduced curvature `1.6`, frozen curvature `3.1659999999999995`, and reduced-profile minimum `0.03`.

| Quantity | Estimated | Error |
|---|---:|---:|
| reoptimized curvature | 1.6000000000000005 | relative `2.7755575615628914e-16` |
| frozen curvature | 3.1659999999999964 | relative `9.818775960045607e-16` |
| profile minimum | 0.030000000000000002 | absolute `3.469446951953614e-18` |
| quadratic R-squared | 1.0 | gate `>=0.999999` |
| normalized fit RMSE | 4.097899027589427e-16 | gate `<=1e-6` |

All seven locked offsets passed the simultaneous optimizer-return, loss-plateau, and normalized-gradient rules. Each point independently cloned the same `theta0`; shuffled point order and an independent repeat both had maximum absolute loss difference `0.0`.

A forced one-outer-step run ended as `PROFILE_FAILURE`. Passing that failed point to the quadratic fitter raised `ProfileFitError`; no interpolation occurred.

## Locked-forward rules

The default offsets, combined stopping rules, and fit-quality thresholds in `configs/p3_profile.yaml` passed development validation and must be copied unchanged into the P4 global locked protocol unless a documented pre-confirmation amendment is required by P4 feasibility. No paper-facing confirmation result may be used to alter them.

