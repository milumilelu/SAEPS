"""One-shot cohort execution for locked Allen--Cahn confirmation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.provenance import environment_provenance
from saeps.v44.aggregation import aggregate_allen_confirmation
from saeps.v44.pipeline import run_allen_confirmation_seed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_v44_confirmation(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_path = root / "configs/v4_4/locked_allen_cahn_confirmation.yaml"
    lock = json.loads((root / "configs/v4_4/LOCK_RECORD.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (root / "configs/v4_4/EXECUTION_AUTHORIZATION.json").read_text(encoding="utf-8")
    )
    preflight = json.loads((root / "docs/evidence/V4_4_PRE_CONFIRMATION_AUDIT.json").read_text(encoding="utf-8"))
    if _sha256(config_path) != lock["locked_config_sha256"]:
        raise RuntimeError("v4.4 locked config hash mismatch")
    if authorization.get("state") != "AUTHORIZED_ONCE":
        raise RuntimeError("v4.4 execution not authorized")
    if preflight.get("status") != "PASSED" or preflight.get("confirmation_runs_observed") != 0:
        raise RuntimeError("v4.4 clean preflight is absent")
    destination = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    if destination.exists():
        raise RuntimeError("v4.4 one-shot output already exists; rerun forbidden")
    specification = load_config(config_path)
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("v4.4 confirmation must start from a clean commit")
    destination.mkdir(parents=True, exist_ok=False)
    claim = {
        "schema_version": 1,
        "state": "V4_4_EXECUTION_CLAIMED_ONE_SHOT",
        "planned_seeds": specification["planned_seeds"],
        "locked_config_sha256": lock["locked_config_sha256"],
        "git_commit": provenance["git_commit"],
        "timestamp": provenance["timestamp"],
        "rerun_forbidden": True,
    }
    _write(destination / "execution_claim.json", claim)
    records = [
        run_allen_confirmation_seed(
            int(seed), config_path, destination, root, width=8, provenance_override=provenance
        )
        for seed in specification["planned_seeds"]
    ]
    summary = aggregate_allen_confirmation(records, specification)
    summary.update(
        locked_config_sha256=lock["locked_config_sha256"],
        lock_commit=lock["lock_commit"],
        execution_claim=claim,
        provenance=provenance,
    )
    _write(destination / "summary.json", summary)
    rows = []
    for record in records:
        path = destination / f"records/seed_{record['seed']}/result.json"
        rows.append(
            {
                "seed": record["seed"],
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "path": str(path.relative_to(destination)).replace("\\", "/"),
                "sha256": _sha256(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "planned": len(records),
        "records": rows,
        "raw_records_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    _write(destination / "manifest.json", manifest)
    _write(
        destination / "failed_seeds.json",
        {
            "schema_version": 1,
            "failed": [
                {
                    "seed": record["seed"],
                    "status": record["status"],
                    "failure_reason": record["failure_reason"],
                }
                for record in records
                if record["status"] != "PASS"
            ],
        },
    )
    return summary

