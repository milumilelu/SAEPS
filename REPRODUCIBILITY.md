# SAEPS reproducibility and evidence audit

This guide targets reviewers and public users of the **V5 final-audit** repository state. The frozen scientific evidence baseline is commit `cf76ffe85a78c994351e50b97d013d33a0f01f85`.

## Environment

- CPython: exactly `3.12.13` (also recorded in `.python-version`)
- Locked packages: `requirements-lock.txt`
- Package metadata and Python constraint: `pyproject.toml`
- Default scientific dtype: float64, as recorded by the relevant frozen configurations and run manifests

Create an isolated environment on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

Use CPython 3.12.13 directly if the `py` launcher is unavailable. The lock file is the authoritative dependency set; do not replace it with unpinned upgrades when auditing the published evidence.

## Validation levels

Run the unit suite:

```powershell
pytest -q
```

Run the lightweight real-data/process smoke and numerical-core checks:

```powershell
python scripts/00_smoke_test.py --output-root "$env:TEMP/saeps-smoke"
python scripts/01_validate_core.py --output-root "$env:TEMP/saeps-core"
python scripts/04_validate_profile.py --output-root "$env:TEMP/saeps-profile"
```

The explicit temporary output roots are required: the checked-in `outputs/runs/` tree is protected historical evidence and must not receive validation-only runs.

Run the binding V5 final repository validator:

```powershell
python scripts/validate_v5_repository.py
```

A passing V5 validation confirms:

- all registered cohorts remain exact and disjoint;
- frozen protocol/executable hashes match;
- pre-V5 raw-output tree digests remain unchanged;
- all 29 one-attempt checkpoint records remain reloadable and lineage-complete;
- raw records match the aggregate source hashes;
- profile `NOT_SUPPORTED`, two-parameter `INCONCLUSIVE`, and the other V5 adjudications remain unchanged;
- the final V5 report rebuilds exactly from source aggregates; and
- all V5 paper artifacts match `paper_artifacts/v5/manifest.json`.

The checked-in machine-readable result is `docs/evidence/v5_final_validation.json`. The command above recomputes the validation against the current checkout and exits nonzero on failure.

## Audit paper-facing numbers without retraining

Ordinary reviewer reproduction does **not** require rerunning locked confirmation training. The repository contains sufficient records for an evidence audit:

1. Start from `docs/evidence/v5_final_audit.json` for the claim-to-evidence map and source hashes.
2. Inspect the referenced aggregate JSON files in `docs/evidence/v5/` and the inherited V4 scalar confirmation aggregates in `docs/evidence/`.
3. Follow every aggregate's `source_records` entries to the immutable raw JSON/manifests in `outputs/runs/`.
4. Run `python scripts/validate_v5_repository.py` to verify raw hashes, aggregate lineage, checkpoint lineage, frozen files, scientific adjudications, and deterministic final-report reconstruction.
5. Verify publication artifacts against `paper_artifacts/v5/manifest.json`.

This audit retains invalid checkpoints, failed numerical cells, and all planned denominators. Do not manually filter failures or recompute statistics from only successful seeds.

## Confirmation reruns are outside the reviewer audit

Do not invoke training/confirmation scripts merely to validate the publication package. Locked confirmation experiments are frozen historical scientific executions; this repository's public audit is intentionally based on their retained raw records, manifests, aggregates, and hashes. Any future scientific rerun would require separate protocol authorization and must not overwrite the existing evidence.

## CI scope

GitHub Actions installs the locked package, runs `pytest -q`, executes the lightweight smoke/core/profile validations, and runs the V5 final repository validator. CI does not retrain or rerun frozen confirmation experiments. The final validator already performs the deterministic report-rebuild equality and paper-artifact hash checks.

## Data and code availability

The repository directly supports public audit of the reported evidence through:

- versioned source code and locked dependencies;
- frozen configurations and executable hashes;
- raw run records and manifests, including invalid/failed cases;
- aggregate source hashes and checkpoint provenance;
- machine-readable scientific and repository audits; and
- hashed final tables and figures.

Before manuscript publication, the authors must supply the final public repository URL in the paper's Data Availability statement, make the repository publicly visible, choose whether to adopt an open-source license, and optionally archive the tagged release with Zenodo.
