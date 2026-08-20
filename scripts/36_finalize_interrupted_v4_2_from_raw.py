"""Recover only v4.2 aggregation after all 15 raw records were written."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from saeps.config import load_config
from saeps.provenance import environment_provenance
from saeps.v42.aggregation import aggregate_v42


def _write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    destination = root / "outputs/runs/v4_2_corrected_confirmation"
    summary_path = destination / "summary.json"
    manifest_path = destination / "manifest.json"
    if summary_path.exists() or manifest_path.exists():
        raise RuntimeError("aggregation artifacts already exist; recovery rerun forbidden")
    paths = sorted((destination / "records").glob("seed_*.json"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if [record["seed"] for record in records] != list(range(55, 70)):
        raise RuntimeError("all 15 exact raw seeds are required for aggregation recovery")
    claim = json.loads((destination / "execution_claim.json").read_text(encoding="utf-8"))
    v42 = load_config(root / "configs/v4_2/locked_corrected_confirmation.yaml")
    v36 = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    lock = json.loads((root / "configs/v4_2/LOCK_RECORD.json").read_text(encoding="utf-8"))
    adapted_records = []
    for record in records:
        if record["status"] == "PASS":
            failure_stage = None
        elif record["statuses"]["center_status"] != "PASS":
            failure_stage = "center"
        elif record["statuses"]["exact_reference_status"] != "PASS":
            failure_stage = "exact_reference"
        elif record["statuses"]["curvature_solver_status"] != "PASS":
            failure_stage = "solver"
        else:
            failure_stage = "finite_primary"
        adapted_records.append({**record, "failure_stage": failure_stage})
    aggregate = aggregate_v42(adapted_records, v42, v36)
    recovery_environment = environment_provenance(root, "float64", "cpu")
    aggregate.update(
        config_sha256=lock["locked_config_sha256"],
        lock_commit=lock["lock_commit"],
        execution_claim=claim,
        execution_provenance={
            "git_commit": claim["execution_commit"],
            "git_dirty": False,
            "timestamp": claim["timestamp"],
            "source": "execution_claim_and_clean_preflight",
        },
        aggregation_recovery={
            "reason": "runner aggregation failed after seed_69 because frozen aggregator expected a non-scientific failure_stage field absent from the fail-soft raw schema",
            "seed_computation_repeated": False,
            "raw_record_count": 15,
            "aggregator_file_sha256": lock["aggregator_file_sha256"],
            "schema_adapter": "failure_stage derived in memory from independent node statuses; no raw or primary value changed",
            "recovery_environment": recovery_environment,
        },
    )
    _write(summary_path, aggregate)
    failed = [record for record in records if record["status"] != "PASS"]
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
                for record in failed
            ],
        },
    )
    manifest_rows = [
        {
            "seed": record["seed"],
            "status": record["status"],
            "binding_valid": record["binding_valid"],
            "path": f"records/seed_{record['seed']}.json",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path, record in zip(paths, records)
    ]
    _write(
        manifest_path,
        {
            "schema_version": 1,
            "planned": 15,
            "records": manifest_rows,
            "raw_records_sha256": hashlib.sha256(
                json.dumps(manifest_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "aggregation_recovered_without_seed_rerun": True,
        },
    )
