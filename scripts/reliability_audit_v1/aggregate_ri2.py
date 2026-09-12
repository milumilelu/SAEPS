#!/usr/bin/env python3
"""Aggregate the RI-2 planning denominator and any available run records.

The planner is deliberately denominator preserving: every run in ``run_plan``
appears in the output, including missing records (reported as ``NOT_STARTED``)
and terminal failures.  This utility only aggregates machine-readable records;
it never infers success from a missing or partial result.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {
    "PASS",
    "CHECKPOINT_INVALID",
    "PROFILE_FAILURE",
    "SOLVER_FAILURE",
    "NUMERICAL_FAILURE",
    "FAILED",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"record must be a JSON object: {path}")
    return value


def _read_records_file(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return list(value)
    raise ValueError(f"records file must contain an object or object list: {path}")


def aggregate_ri2(run_plan_path: Path, records_dir: Path | None = None) -> dict[str, Any]:
    """Return denominator-preserving RI-2 status counts.

    ``records_dir`` may contain one JSON object per run.  Planned rows are
    retained even when no corresponding file exists.  A record's status is
    read from ``execution_status`` first (the RI-2 schema), then ``status``;
    absent status is conservatively classified as ``NOT_STARTED``.
    """

    plan = _read_json(run_plan_path)
    planned = plan.get("records")
    if not isinstance(planned, list):
        raise ValueError("run plan must contain a records list")
    declared = plan.get("planned_runs")
    if declared is not None and int(declared) != len(planned):
        raise ValueError("planned_runs does not match records length")

    planned_by_id: dict[str, dict[str, Any]] = {}
    for row in planned:
        if not isinstance(row, dict) or not row.get("run_id"):
            raise ValueError("each planned record requires a run_id")
        run_id = str(row["run_id"])
        if run_id in planned_by_id:
            raise ValueError(f"duplicate planned run_id: {run_id}")
        planned_by_id[run_id] = row

    observed: dict[str, dict[str, Any]] = {}
    unknown: list[str] = []
    orphan_records: list[dict[str, Any]] = []
    if records_dir is not None and records_dir.is_dir():
        # Accept one index/list file plus per-run manifest.json files in case
        # directories. Aggregates are excluded so prior summaries cannot be
        # mistaken for run records.
        candidates = list(records_dir.glob("*.json")) + list(records_dir.rglob("manifest.json"))
        if any(path.name == "manifest.json" for path in candidates):
            # The runner's pilot_index duplicates these per-run manifests.
            candidates = [path for path in candidates if path.name != "pilot_index.json"]
        for path in sorted(set(candidates)):
            if path.name in {"summary.json", "run_plan.json"}:
                continue
            for row in _read_records_file(path):
                run_id = row.get("run_id")
                if not run_id:
                    raise ValueError(f"record lacks run_id: {path}")
                run_id = str(run_id)
                if run_id in observed:
                    raise ValueError(f"duplicate observed run_id: {run_id}")
                if run_id not in planned_by_id:
                    unknown.append(run_id)
                    orphan_records.append(row)
                observed[run_id] = row

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    benchmark_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for run_id, planned_row in planned_by_id.items():
        actual = observed.get(run_id, {})
        status = actual.get("execution_status")
        if status is None:
            status = actual.get("status")
        if status is None:
            status = planned_row.get("execution_status")
        if status is None:
            status = planned_row.get("status")
        if status is None:
            status = "NOT_STARTED"
        status = str(status)
        merged = {**planned_row, **actual, "run_id": run_id, "status": status}
        rows.append(merged)
        status_counts[status] += 1
        benchmark_counts[str(merged.get("benchmark", "UNKNOWN"))][status] += 1

    completed = len(rows) - status_counts.get("NOT_STARTED", 0)
    return {
        "schema_version": 1,
        "protocol_id": plan.get("protocol_id", "reliability_audit_v1"),
        "phase": plan.get("phase", "RI-2"),
        "planned": len(rows),
        "completed": completed,
        "not_started": status_counts.get("NOT_STARTED", 0),
        "terminal": sum(status_counts.get(status, 0) for status in TERMINAL_STATUSES),
        "status_counts": dict(sorted(status_counts.items())),
        "benchmark_status_counts": {
            benchmark: dict(sorted(counts.items()))
            for benchmark, counts in sorted(benchmark_counts.items())
        },
        "unknown_observed_run_ids": sorted(unknown),
        "orphan_records": orphan_records,
        "records": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-plan", type=Path, required=True)
    parser.add_argument("--records-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = aggregate_ri2(args.run_plan, args.records_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("planned", "completed", "not_started", "terminal", "status_counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
