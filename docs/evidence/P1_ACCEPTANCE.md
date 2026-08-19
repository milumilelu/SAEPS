# P1 SAEPS Core Verification — Acceptance Evidence

**Status:** `PASSED`  
**Validation date:** 2026-08-19  
**Validated implementation commit:** `c4becc79f1e6d0968f55c27ae90c36898798e5af`

## Environment and actual test object

- Python 3.12.13; PyTorch 2.13.0; NumPy 2.3.5
- float64 / CPU / Windows 11 AMD64
- Config hash: `5ec8fb4209850b1d2d3d5c28b1a69f5ffdc7c0ffc521981fa3a8de2b5c966e5d`
- Run ID: `p1-core-s20260819-20260819T065755.242464+0000-dfcb22fd2b2b`
- Git provenance inside result: implementation commit above, `git_dirty=false`
- Test residual: 13-state-parameter, two-positive-physical-parameter neural ODE/PINN residual with 34 weighted residual components. Both physical parameters have nonzero sensitivity.

## Actual acceptance commands

```text
pytest -q
............. [100%]
13 passed in 3.13s

python scripts/01_validate_core.py
status: PASS

python scripts/00_smoke_test.py
status: PASS

python -m pip check
No broken requirements found.
```

The 18 pytest warnings are PyTorch 2.13.0 internal deprecation warnings for `torch.jit.script`; no repository code calls that API and no numerical check was suppressed.

## Numerical gates

| Gate | Actual | Threshold | Decision |
|---|---:|---:|---|
| max operator relative error, 10 random vectors | `9.07617867654501e-15` | `<1e-6` | PASS |
| curvature relative error | `1.3919433666028684e-13` | `<1e-6` | PASS |
| score relative error | `6.756196003611306e-14` | `<1e-6` | PASS |
| symmetry relative error | `3.926716887141203e-14` | `<1e-8` | PASS |
| minimum eigenvalue of Fse | `0.05311907298541512` | PSD tolerance | PASS |
| minimum eigenvalue of Fraw-Fse | `0.012139096465286436` | PSD tolerance | PASS |
| max formal CG relative residual | `1.8073294431554353e-11` | `<=1e-8` | PASS |
| finite-difference theta relative error | `1.8324275812944072e-10` | `<2e-5` | PASS |
| finite-difference parameter relative error | `1.68936304717265e-10` | `<2e-5` | PASS |
| repeat max absolute error | `0.0` | `<=1e-13` | PASS |

Retained sensitivities are `[0.12842721109728797, 0.3207511640169977]`, both within the preregistered scalar interval. The matrix-free path recorded 140 JVPs, 140 VJPs, two parameter JVP columns, and zero explicit-Jacobian calls.

## Regularization disclosure

P1 uses the fixed numerical-validation rule

```text
gamma = 1e-4 * lambda_max(J_theta^T J_theta)
```

giving `lambda_max=135.58509246160415` and `gamma=0.013558509246160415`. This regularization stabilizes the state normal equation and tests the same explicit and matrix-free Tikhonov operator; it was not selected from any paper-facing result. The later development-phase gamma sweep and LOCK rules remain unchanged.

## Gate decision

All P1 engineering gates passed on a clean committed implementation. P2 is authorized only after this evidence commit leaves a clean worktree.

