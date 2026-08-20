"""Independent raw-to-aggregate audit for the closed v4.2 confirmation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.v42.aggregation import aggregate_v42


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _adapt(record: dict[str, Any]) -> dict[str, Any]:
    if record["status"] == "PASS":
        stage = None
    elif record["statuses"]["center_status"] != "PASS":
        stage = "center"
    elif record["statuses"]["exact_reference_status"] != "PASS":
        stage = "exact_reference"
    elif record["statuses"]["curvature_solver_status"] != "PASS":
        stage = "solver"
    else:
        stage = "finite_primary"
    return {**record, "failure_stage": stage}


def validate_v42_result(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    run = root / "outputs/runs/v4_2_corrected_confirmation"
    manifest = _json(run / "manifest.json")
    summary = _json(run / "summary.json")
    v42 = load_config(root / "configs/v4_2/locked_corrected_confirmation.yaml")
    v36 = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    lock = _json(root / "configs/v4_2/LOCK_RECORD.json")
    checks: dict[str, Any] = {}
    rows = manifest["records"]
    records = []
    hashes_pass = manifest["planned"] == 15 and [row["seed"] for row in rows] == list(range(55, 70))
    for row in rows:
        path = run / row["path"]
        hashes_pass = hashes_pass and _sha256(path) == row["sha256"]
        record = _json(path)
        hashes_pass = hashes_pass and record["seed"] == row["seed"] and record["status"] == row["status"]
        records.append(record)
    raw_hash = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    checks["raw_manifest_and_completeness"] = {
        "status": "PASS" if hashes_pass and raw_hash == manifest["raw_records_sha256"] else "FAIL",
        "raw_records_sha256": raw_hash,
        "seeds": [record["seed"] for record in records],
    }
    recomputed = aggregate_v42([_adapt(record) for record in records], v42, v36)
    compared = [
        "scientific_status",
        "primary_conditions",
        "planned",
        "valid",
        "invalid",
        "strict_wins_out_of_planned_15",
        "strict_losses",
        "ties",
        "sign_test_non_tied_denominator",
        "exact_one_sided_sign_p",
        "median_D",
        "status_counts",
        "secondary",
        "gn_indicator",
        "per_seed",
    ]
    aggregate_pass = all(recomputed[key] == summary[key] for key in compared)
    checks["independent_raw_to_aggregate"] = {
        "status": "PASS" if aggregate_pass else "FAIL",
        "scientific_status": recomputed["scientific_status"],
        "primary_conditions": recomputed["primary_conditions"],
    }
    valid = [record for record in records if record["binding_valid"]]
    node_pass = len(valid) == 12 and all(
        record["statuses"][node] == "PASS"
        for record in valid
        for node in v42["required_binding_nodes"]
    )
    score_nonbinding = all(
        record["gate_graph"]["CURVATURE_GATE"] == "PASS"
        and record["statuses"]["score_solver_status"] == "SOLVER_FAILURE"
        for record in valid
    )
    checks["binding_graph"] = {
        "status": "PASS" if node_pass and score_nonbinding else "FAIL",
        "valid_binding_chains": len(valid),
        "valid_with_nonbinding_score_failure": sum(
            record["statuses"]["score_solver_status"] == "SOLVER_FAILURE" for record in valid
        ),
    }
    invalid = [record for record in records if not record["binding_valid"]]
    invalid_pass = len(invalid) == 3 and all(
        record["status"] == "CHECKPOINT_INVALID" and record["statuses"]["center_status"] == "CHECKPOINT_INVALID"
        for record in invalid
    )
    checks["invalid_planned_seeds"] = {
        "status": "PASS" if invalid_pass else "FAIL",
        "seeds": [record["seed"] for record in invalid],
        "count_as_planned_nonwins": True,
    }
    executable_pass = (
        _sha256(root / "configs/v4_2/locked_corrected_confirmation.yaml") == lock["locked_config_sha256"]
        and all(_sha256(root / path_name) == expected for path_name, expected in lock["file_sha256"].items())
    )
    checks["locked_protocol_and_executable"] = {
        "status": "PASS" if executable_pass else "FAIL",
        "locked_config_sha256": lock["locked_config_sha256"],
        "runner_commit": lock["runner_commit"],
        "aggregator_file_sha256": lock["aggregator_file_sha256"],
    }
    v36_record = _json(root / "configs/v3_6/CONFIRMATION_RESULT_RECORD.json")
    checks["v3_6_unchanged"] = {
        "status": "PASS" if v36_record["rerun_permitted"] is False and v36_record["raw_records_sha256"] == "3c7061a963710d28579661ae5792e9e55642119a6777e7d04097d5c16b544aa9" else "FAIL",
        "scientific_status": v36_record["scientific_status"],
    }
    recovery = summary.get("aggregation_recovery", {})
    recovery_pass = (
        manifest.get("aggregation_recovered_without_seed_rerun") is True
        and recovery.get("seed_computation_repeated") is False
        and recovery.get("raw_record_count") == 15
        and recovery.get("aggregator_file_sha256") == lock["aggregator_file_sha256"]
    )
    checks["aggregation_schema_recovery"] = {
        "status": "PASS" if recovery_pass else "FAIL",
        "classification": "non-scientific schema adapter; no seed or primary quantity recomputed",
        "detail": recovery,
    }
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V4_2_CONFIRMATION_RESULT_AUDIT",
        "status": status,
        "scientific_status": summary["scientific_status"],
        "checks": checks,
        "raw_records_sha256": manifest["raw_records_sha256"],
        "rerun_permitted": False,
    }

