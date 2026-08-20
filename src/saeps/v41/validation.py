"""Validate v4.1 development cohorts and repaired gate semantics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_v41_cohort(repo_root: str | Path, role: str) -> dict[str, Any]:
    root = Path(repo_root)
    destination = root / "outputs/runs/v4_1_post_confirmation_development" / role.lower()
    manifest = _json(destination / "manifest.json")
    summary = _json(destination / "summary.json")
    expected = [45, 46, 47, 48, 49] if role == "ENGINEERING_INTEGRATION" else [50, 51, 52, 53, 54]
    checks: dict[str, Any] = {}
    rows = manifest["records"]
    complete = manifest["planned"] == 5 and [row["seed"] for row in rows] == expected
    records = []
    hashes = True
    for row in rows:
        path = destination / row["path"]
        hashes = hashes and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        record = _json(path)
        hashes = hashes and record["seed"] == row["seed"] and record["status"] == row["status"]
        records.append(record)
    checks["manifest_and_completeness"] = {
        "status": "PASS" if complete and hashes else "FAIL",
        "seeds": expected,
    }
    semantic_rows = [
        record
        for record in records
        if record["statuses"]["score_solver_status"] == "SOLVER_FAILURE"
    ]
    semantic_pass = bool(semantic_rows) and all(
        record["statuses"]["parameter_reference_status"] == "PASS"
        and record["statuses"]["curvature_solver_status"] == "PASS"
        and record["gate_graph"]["CURVATURE_GATE"] == "PASS"
        and record["binding_valid"]
        for record in semantic_rows
    )
    checks["score_is_nonbinding"] = {
        "status": "PASS" if semantic_pass else "FAIL",
        "score_failed_but_binding_valid_count": sum(record["binding_valid"] for record in semantic_rows),
    }
    center_valid = [record for record in records if record["statuses"]["center_status"] == "PASS"]
    all_computable = all(
        all(record[key] is not None for key in ["F_raw", "F_se_explicit", "F_se_GN", "H_red_exact_gamma"])
        for record in center_valid
    )
    checks["fail_soft_record_completeness"] = {
        "status": "PASS" if all_computable else "FAIL",
        "center_valid_denominator": len(center_valid),
        "all_core_quantities_count": sum(
            all(record[key] is not None for key in ["F_raw", "F_se_explicit", "F_se_GN", "H_red_exact_gamma"])
            for record in center_valid
        ),
    }
    binding_valid = sum(record["binding_valid"] for record in records)
    summary_pass = (
        summary["binding_valid_count"] == binding_valid
        and summary["scientific_gate"] == "NONE_DEVELOPMENT_ONLY"
        and summary["provenance"]["git_dirty"] is False
    )
    checks["summary_and_provenance"] = {
        "status": "PASS" if summary_pass else "FAIL",
        "binding_valid_count": binding_valid,
        "scientific_gate": summary["scientific_gate"],
    }
    heldout_gate = None
    if role == "HELDOUT_DEVELOPMENT":
        heldout_gate = "PASS" if binding_valid == 5 and semantic_pass and all_computable else "FAIL"
        checks["heldout_full_chain"] = {
            "status": "PASS" if heldout_gate == "PASS" else "FAIL",
            "binding_valid_count": binding_valid,
            "required": 5,
        }
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V4_1_POST_CONFIRMATION_DEVELOPMENT",
        "role": role,
        "status": status,
        "checks": checks,
        "binding_valid_count": binding_valid,
        "heldout_full_chain_gate": heldout_gate,
        "confirmation_55_69_authorized": False,
    }

