"""Read-only validation and failure audit for the closed v3.6 run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.v36.pipeline import _aggregate


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_v3_6_result(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    run = root / "outputs/runs/v3_6_scalar_confirmation"
    specification = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    lock_record = _json(root / "configs/v3_6/LOCK_RECORD.json")
    manifest = _json(run / "manifest.json")
    summary = _json(run / "summary.json")
    checks: dict[str, Any] = {}

    seeds = [row["seed"] for row in manifest["records"]]
    checks["planned_completeness"] = {
        "status": "PASS" if manifest["planned"] == 15 and seeds == list(range(30, 45)) else "FAIL",
        "planned": manifest["planned"],
        "seeds": seeds,
    }
    records = []
    hashes_pass = True
    for row in manifest["records"]:
        path = run / row["path"]
        hashes_pass = hashes_pass and path.is_file() and _sha256(path) == row["sha256"]
        record = _json(path)
        hashes_pass = hashes_pass and record["seed"] == row["seed"] and record["status"] == row["status"]
        records.append(record)
    recomputed_raw_hash = hashlib.sha256(
        json.dumps(manifest["records"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    checks["raw_manifest_hashes"] = {
        "status": "PASS"
        if hashes_pass and recomputed_raw_hash == manifest["raw_records_sha256"]
        else "FAIL",
        "raw_records_sha256": recomputed_raw_hash,
    }
    recomputed = _aggregate(records, specification)
    aggregate_keys = [
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
    aggregate_pass = all(recomputed[key] == summary[key] for key in aggregate_keys)
    checks["raw_to_aggregate"] = {
        "status": "PASS" if aggregate_pass else "FAIL",
        "scientific_status": recomputed["scientific_status"],
        "valid": recomputed["valid"],
        "invalid": recomputed["invalid"],
    }
    lock_pass = (
        _sha256(root / "configs/v3_6/locked_scalar_confirmation.yaml")
        == lock_record["locked_config_sha256"]
        == summary["config_sha256"]
    )
    checks["locked_lineage"] = {
        "status": "PASS" if lock_pass else "FAIL",
        "config_sha256": lock_record["locked_config_sha256"],
        "lock_commit": lock_record["lock_commit"],
        "execution_commit": summary["execution_claim"]["git_commit"],
    }

    score_coupling_rows = []
    for record in records:
        solver = record.get("solver")
        if record["status"] != "SOLVER_FAILURE" or solver is None:
            continue
        explicit = solver["explicit_reference"]
        parameter_pass = (
            explicit["right_hand_side_relative_normal_residuals"][0] <= 1.0e-10
            and explicit["objective_projection_identity_relative_error"] <= 1.0e-10
        )
        selected_pass = (
            solver["verified_original_relative_normal_residual"] <= 1.0e-8
            and solver["selected_vs_explicit_relative_error"] <= 1.0e-6
        )
        score_failed = explicit["right_hand_side_relative_normal_residuals"][1] > 1.0e-10
        score_coupling_rows.append(
            {
                "seed": record["seed"],
                "parameter_reference_pass": parameter_pass,
                "selected_curvature_solver_pass": selected_pass,
                "score_rhs_failed_1e-10": score_failed,
                "parameter_rhs_relative_normal_residual": explicit[
                    "right_hand_side_relative_normal_residuals"
                ][0],
                "score_rhs_relative_normal_residual": explicit[
                    "right_hand_side_relative_normal_residuals"
                ][1],
                "selected_relative_normal_residual": solver[
                    "verified_original_relative_normal_residual"
                ],
                "selected_vs_explicit_relative_error": solver[
                    "selected_vs_explicit_relative_error"
                ],
            }
        )
    isolated = (
        len(score_coupling_rows) == 14
        and all(
            row["parameter_reference_pass"]
            and row["selected_curvature_solver_pass"]
            and row["score_rhs_failed_1e-10"]
            for row in score_coupling_rows
        )
    )
    checks["implementation_failure_audit"] = {
        "status": "PASS" if isolated else "FAIL",
        "classification": "implementation failure: excluded score RHS was bound into curvature-only explicit gate",
        "affected_seed_count": len(score_coupling_rows),
        "rows": score_coupling_rows,
    }
    terminal = all(
        record["status"]
        in {"PASS", "CHECKPOINT_INVALID", "PROFILE_FAILURE", "SOLVER_FAILURE", "NUMERICAL_FAILURE"}
        for record in records
    )
    checks["terminal_statuses"] = {
        "status": "PASS" if terminal and len(records) == 15 else "FAIL",
        "status_counts": recomputed["status_counts"],
    }
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_6_CONFIRMATION_RESULT_AUDIT",
        "status": status,
        "scientific_status": summary["scientific_status"],
        "scientific_interpretation": "NOT_SUPPORTED due zero valid pairs; comparative hypothesis not tested",
        "confirmation_execution_status": "PERMANENTLY_CLOSED_IMPLEMENTATION_FAILURE",
        "rerun_permitted": False,
        "checks": checks,
        "raw_records_sha256": manifest["raw_records_sha256"],
    }

