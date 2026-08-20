"""Recompute v4.1 status-count fields from immutable per-seed records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["ENGINEERING_INTEGRATION", "HELDOUT_DEVELOPMENT"])
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "outputs/runs/v4_1_post_confirmation_development" / arguments.role.lower()
    summary_path = destination / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((destination / "records").glob("seed_*.json"))
    ]
    summary["score_computed_count"] = sum(
        record["statuses"]["score_solver_status"] != "NOT_COMPUTED" for record in records
    )
    summary["score_failure_count"] = sum(
        record["statuses"]["score_solver_status"] == "SOLVER_FAILURE" for record in records
    )
    summary_path.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
