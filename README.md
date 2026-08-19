# SAEPS Validation

This repository implements the preregistered JCP-level validation protocol in
[`docs/EXECUTION_CONTRACT.md`](docs/EXECUTION_CONTRACT.md). Its purpose is to
test whether SAEPS predicts the nonlinear state-reoptimized residual geometry
of trained inverse PINNs more accurately than raw fixed-network sensitivity.
A negative scientific result is a valid completion.

## Protocol state

- Active contract: `SAEPS-JCP-EXEC-v2.0`
- Current phase: P5 Scalar Confirmation (global protocol LOCKED)
- Confirmation protocol: **LOCKED** at `ad794ca2908c8935d0e21702fab7914ff944cce7`
- Python: 3.12.13
- Default numerical dtype: float64

Do not run confirmation experiments until `docs/LOCKED_PROTOCOL.md` says
`LOCKED` and its hashes have been verified.

## Clean setup

On Windows PowerShell, use an installed Python 3.12.13 interpreter:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

The Codex desktop workspace used during bootstrap exposes Python at a bundled
absolute path because this machine's `python.exe` is a Windows Store placeholder.
That path is an execution convenience, not a repository dependency; clean users
may use any CPython 3.12.13 installation.

## P0 acceptance

With the virtual environment active:

```powershell
pytest -q
python scripts/00_smoke_test.py
python scripts/01_validate_core.py
```

The smoke test trains a real tiny PINN for the ODE \(u_t+u=0\), saves a
checkpoint and structured metadata, reloads into a fresh model, and verifies
prediction/residual equality against the pre-save values.

## Scientific execution

Follow `TASKS.md` phase by phase. Every paper-facing number must follow:

```text
raw run files -> aggregation -> paper_artifacts/data -> figures/tables/report
```

Never manually enter experimental results into paper artifacts.
