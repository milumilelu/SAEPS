# P0 Repository Bootstrap — Acceptance Evidence

**Status:** `PASSED`  
**Validation date:** 2026-08-19  
**Validated implementation commit:** `6c88a860dbaf95988ae75b30b9f0efcdd951623c`

## Environment

- Python: 3.12.13
- PyTorch: 2.13.0
- NumPy: 2.3.5
- dtype/device: float64 / CPU
- Platform: Windows 11, AMD64
- Dependency closure: `requirements-lock.txt`
- Config hash: `dc4934cc4ac8d5d7f8381f4546f0b163d98c9def1b9bdce3188209813f078246`

## Actual acceptance commands

```text
pytest -q
......... [100%]
9 passed in 2.47s

python scripts/00_smoke_test.py
status: PASS
```

Additional environment checks:

```text
python -m pip check
No broken requirements found.

python -m pip install -r requirements-lock.txt --dry-run
All pinned requirements already satisfied.
```

## End-to-end smoke result

- Run ID: `p0-smoke-s0-20260819T064626.194214+0000-003d4f3d7749`
- Benchmark: tiny PINN for \(u_t+u=0,\ u(0)=1\)
- Training: 600 deterministic Adam steps
- State RMSE: `0.0030674738759413475` (gate `<=0.03`)
- Prediction round-trip max absolute error: `0.0`
- PDE-residual round-trip max absolute error: `0.0`
- Round-trip gate: `<=1e-12`
- Git provenance in run metadata: commit above, `git_dirty=false`
- Saved artifacts: checkpoint, metadata JSON, validation JSON, structured JSONL log

The test suite independently performs another real tiny-PINN training and checkpoint round-trip; it does not replace the separate smoke command with a mock.

## Gate decision

P0 engineering gate is `PASSED`. P1 is authorized after this evidence is committed and the worktree is clean.

