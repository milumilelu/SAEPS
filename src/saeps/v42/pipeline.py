"""One-shot runner for the separately locked v4.2 confirmation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import config_hash, load_config
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance
from saeps.scalar import solve_truth
from saeps.v41.pipeline import _run_seed
from saeps.v42.aggregation import aggregate_v42


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_v42_confirmation(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
    authorization_path: str | Path,
    preflight_path: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    destination = Path(output_root).resolve()
    if destination.exists():
        raise RuntimeError("v4.2 one-shot output already exists; rerun forbidden")
    v42 = load_config(config_path)
    if v42["planned_seeds"] != list(range(55, 70)):
        raise RuntimeError("v4.2 planned seeds changed")
    lock_record = json.loads((root / "configs/v4_2/LOCK_RECORD.json").read_text(encoding="utf-8"))
    if _sha256(Path(config_path)) != lock_record["locked_config_sha256"]:
        raise RuntimeError("v4.2 lock hash mismatch")
    for path_name, expected in lock_record["file_sha256"].items():
        if _sha256(root / path_name) != expected:
            raise RuntimeError(f"v4.2 executable lock mismatch: {path_name}")
    authorization = json.loads(Path(authorization_path).read_text(encoding="utf-8"))
    if authorization.get("execution_authorized") is not True:
        raise RuntimeError("v4.2 execution is not separately authorized")
    preflight = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
    if preflight.get("status") != "PASSED" or preflight.get("prior_runs") != 0:
        raise RuntimeError("v4.2 preflight did not pass")
    v36_path = root / v42["source_v3_6_scientific_protocol"]["path"]
    v36 = load_config(v36_path)
    scalar_path = root / v36["source_files"]["scalar_config"]["path"]
    scalar = load_config(scalar_path)
    runtime = _runtime_config(scalar)
    provenance = environment_provenance(root, scalar["dtype"], scalar["device"])
    if provenance["git_dirty"]:
        raise RuntimeError("v4.2 formal execution requires clean provenance")
    destination.mkdir(parents=True, exist_ok=False)
    records_dir = destination / "records"
    records_dir.mkdir()
    claim = {
        "schema_version": 1,
        "state": "V4_2_EXECUTION_CLAIMED_ONE_SHOT",
        "planned_seeds": v42["planned_seeds"],
        "locked_config_sha256": lock_record["locked_config_sha256"],
        "runner_commit": lock_record["runner_commit"],
        "execution_commit": provenance["git_commit"],
        "timestamp": provenance["timestamp"],
        "rerun_forbidden": True,
    }
    _write(destination / "execution_claim.json", claim)
    truth = solve_truth(runtime, "Burgers")
    digest = config_hash(v42)
    records = []
    manifest_rows = []
    for seed in v42["planned_seeds"]:
        record = _run_seed(
            int(seed),
            "V4_2_UNTOUCHED_CONFIRMATION",
            v42,
            v36,
            runtime,
            truth,
            provenance,
            digest,
        )
        record["phase"] = "V4_2_CORRECTED_UNTOUCHED_CONFIRMATION"
        record["split"] = "untouched_confirmation"
        path = records_dir / f"seed_{seed}.json"
        _write(path, record)
        manifest_rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "path": str(path.relative_to(destination)).replace("\\", "/"),
                "sha256": _sha256(path),
            }
        )
        records.append(record)
    aggregate = aggregate_v42(records, v42, v36)
    aggregate.update(
        config_sha256=lock_record["locked_config_sha256"],
        lock_commit=lock_record["lock_commit"],
        provenance=provenance,
        execution_claim=claim,
    )
    _write(destination / "summary.json", aggregate)
    _write(
        destination / "failed_seeds.json",
        {
            "schema_version": 1,
            "failed": [
                {
                    "seed": record["seed"],
                    "status": record["status"],
                    "failure_reason": record["failure_reason"],
                    "statuses": record["statuses"],
                }
                for record in records
                if record["status"] != "PASS"
            ],
        },
    )
    manifest = {
        "schema_version": 1,
        "planned": 15,
        "records": manifest_rows,
        "raw_records_sha256": hashlib.sha256(
            json.dumps(manifest_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    _write(destination / "manifest.json", manifest)
    return aggregate

