from __future__ import annotations

import json
from pathlib import Path

from scripts.reliability_audit_v1.aggregate_ri2 import aggregate_ri2


def test_ri2_aggregation_preserves_missing_and_failed_runs(tmp_path: Path) -> None:
    plan = {
        "protocol_id": "reliability_audit_v1",
        "phase": "RI-2",
        "planned_runs": 4,
        "records": [
            {"run_id": "r0", "benchmark": "B1", "execution_status": "NOT_STARTED"},
            {"run_id": "r1", "benchmark": "B1", "execution_status": "NOT_STARTED"},
            {"run_id": "r2", "benchmark": "B2", "execution_status": "NOT_STARTED"},
            {"run_id": "r3", "benchmark": "B2", "execution_status": "NOT_STARTED"},
        ],
    }
    plan_path = tmp_path / "run_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    records = tmp_path / "records"
    records.mkdir()
    (records / "r0.json").write_text(json.dumps({"run_id": "r0", "status": "PASS"}), encoding="utf-8")
    (records / "r1.json").write_text(
        json.dumps({"run_id": "r1", "execution_status": "SOLVER_FAILURE", "failure_reason": "diverged"}),
        encoding="utf-8",
    )
    (records / "orphan.json").write_text(
        json.dumps({"run_id": "unexpected", "status": "NUMERICAL_FAILURE"}),
        encoding="utf-8",
    )
    (records / "r2.json").write_text(
        json.dumps({"run_id": "r2", "execution_status": None, "status": "FAILED"}),
        encoding="utf-8",
    )

    summary = aggregate_ri2(plan_path, records)
    assert summary["planned"] == 4
    assert summary["completed"] == 3
    assert summary["not_started"] == 1
    assert summary["terminal"] == 3
    assert summary["status_counts"] == {"FAILED": 1, "NOT_STARTED": 1, "PASS": 1, "SOLVER_FAILURE": 1}
    assert len(summary["records"]) == 4
    assert summary["records"][2]["status"] == "FAILED"
    assert summary["records"][3]["status"] == "NOT_STARTED"
    assert summary["records"][1]["failure_reason"] == "diverged"
    assert summary["unknown_observed_run_ids"] == ["unexpected"]
    assert summary["orphan_records"][0]["status"] == "NUMERICAL_FAILURE"


def test_ri2_aggregation_accepts_a_records_json_list(tmp_path: Path) -> None:
    plan_path = tmp_path / "run_plan.json"
    plan_path.write_text(
        json.dumps({"planned_runs": 1, "records": [{"run_id": "r0", "benchmark": "B1"}]}),
        encoding="utf-8",
    )
    records = tmp_path / "records"
    records.mkdir()
    (records / "records.json").write_text(json.dumps([{"run_id": "r0", "status": "PASS"}]), encoding="utf-8")
    assert aggregate_ri2(plan_path, records)["status_counts"] == {"PASS": 1}
