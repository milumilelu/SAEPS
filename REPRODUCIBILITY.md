# SAEPS reproducibility and evidence audit

This guide targets reviewers and public users of the V5 final-audit repository state. The frozen primary scientific evidence baseline is commit `cf76ffe85a78c994351e50b97d013d33a0f01f85`.

## Environment and installation

- CPython 3.12.13, recorded in `.python-version`
- Locked dependencies in `requirements-lock.txt`
- Package metadata in `pyproject.toml`
- Scientific dtype float64 where specified by locked configurations and manifests

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

Do not substitute unpinned dependency upgrades when auditing the published snapshot.

## Validation levels

```powershell
pytest -q
python scripts/00_smoke_test.py --output-root "$env:TEMP/saeps-smoke"
python scripts/01_validate_core.py --output-root "$env:TEMP/saeps-core"
python scripts/04_validate_profile.py --output-root "$env:TEMP/saeps-profile"
python scripts/validate_repository.py
python scripts/validate_v5_repository.py
```

The V5 validator checks frozen hashes, protected historical bytes, raw-to-aggregate and checkpoint lineage, retained failures, scientific adjudications, deterministic report reconstruction, and paper-artifact manifests. Temporary output roots prevent validation-only runs from entering the frozen evidence tree.

## Audit paper-facing numbers without retraining

Ordinary reviewer reproduction does not require rerunning locked confirmation training:

1. Begin with `docs/evidence/v5_final_audit.json` and `V5_FINAL_JCP_AUDIT_REPORT.md`.
2. Follow aggregate `source_records` entries to immutable records and manifests under `outputs/runs/`.
3. Retain all invalid/failed cases and planned denominators when checking summaries.
4. Verify paper artifacts against their manifests under `paper_artifacts/`.
5. Audit secondary post-hoc analyses through separately classified configurations, records, and reports under `configs/`, `outputs/posthoc/`, and `docs/evidence/`.

Do not run confirmation/training scripts merely to validate this repository package. Any future scientific execution requires a new protocol and must not overwrite historical records.

## Post-hoc evidence

- Exact fixed-state decomposition: `docs/evidence/POSTHOC_EXACT_FIXED_STATE_V3.md`
- Variable-projection baseline: `docs/evidence/POSTHOC_VARIABLE_PROJECTION_V1.md`
- Whitening stabilizer sensitivity: `docs/evidence/POSTHOC_WHITENING_SENSITIVITY_V1.md`

These analyses are nonbinding and do not change preregistered evidence levels.

## CI scope

CI installs the locked environment, runs unit tests and lightweight validations, and executes the repository validators. It does not retrain or rerun frozen confirmation experiments. Validation outputs are directed to runner-temporary paths.

## Data and code availability

The repository contains source code, frozen configurations, raw records and manifests, failed/invalid cases, aggregate source hashes, checkpoint provenance, and machine-readable audits. The release tag identifies the public submission snapshot; no DOI is claimed until an archival service issues one.

