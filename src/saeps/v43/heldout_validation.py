"""Independent validation of frozen Allen--Cahn held-out development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.v43.validation import validate_record_schema


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_allen_heldout(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    freeze = json.loads(
        (root / "configs/v4_3/ALLEN_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    for relative_path, expected in freeze["file_sha256"].items():
        if _sha256(root / relative_path) != expected:
            raise RuntimeError(f"frozen executable mismatch: {relative_path}")
    seeds = [int(value) for value in freeze["heldout_development_seeds"]]
    records = []
    hashes = {}
    for seed in seeds:
        directory = root / f"outputs/runs/v4_3_allen_cahn_development/heldout/seed_{seed}"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        result_path = directory / "result.json"
        if _sha256(result_path) != manifest["result_sha256"]:
            raise RuntimeError(f"held-out result hash mismatch for seed {seed}")
        record = json.loads(result_path.read_text(encoding="utf-8"))
        validate_record_schema(record)
        if int(record["seed"]) != seed or int(record["architecture"]["hidden_width"]) != 8:
            raise RuntimeError(f"held-out identity mismatch for seed {seed}")
        records.append(record)
        hashes[str(seed)] = manifest["result_sha256"]
    result = {
        "schema_version": 1,
        "phase": "V4_3_ALLEN_CAHN_HELDOUT_DEVELOPMENT_VALIDATION",
        "status": "PASSED" if all(record["binding_valid"] for record in records) else "FAILED",
        "scientific_gate": "NONE_DEVELOPMENT_ONLY",
        "seeds": seeds,
        "record_hashes": hashes,
        "binding_valid_count": sum(record["binding_valid"] for record in records),
        "score_failure_nonbinding_count": sum(
            record["statuses"]["score_solver_status"] == "SOLVER_FAILURE" for record in records
        ),
        "profile_bridge_pass_count": sum(
            record["statuses"]["profile_status"] == "PASS" for record in records
        ),
        "directional_indicator_pass_count": sum(
            record["statuses"]["directional_indicator_status"] == "PASS" for record in records
        ),
        "state_rmse": [float(record["training"]["state_rmse_validation_only"]) for record in records],
        "freeze_basis_commit": freeze["freeze_basis_commit"],
        "frozen_file_count": len(freeze["file_sha256"]),
        "comparative_quantities_used_for_acceptance": False,
        "confirmation_authorized": False,
    }
    if result["status"] != "PASSED" or result["directional_indicator_pass_count"] != len(seeds):
        raise RuntimeError("Allen-Cahn held-out full-chain validation failed")
    return result

