"""Finalize P8 aggregate artifacts from immutable raw cost records."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from saeps.provenance import environment_provenance


def finalize_cost_artifacts(run_directory: str | Path, repo_root: str | Path) -> dict[str, Any]:
    run_directory = Path(run_directory)
    manifest = json.loads((run_directory / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for item in manifest["records"]:
        path = run_directory / item["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"raw cost record hash mismatch: {path}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise RuntimeError("no P8 cost records")

    cg_rows = [record["CG_iterations"] for record in records if record.get("CG_iterations")]
    operation_counts = {
        "median_CG_iterations_by_solve": [
            statistics.median(row[index] for row in cg_rows)
            for index in range(len(cg_rows[0]))
        ]
        if cg_rows
        else None,
        "median_CG_total_iterations": statistics.median(
            sum(record["CG_iterations"]) for record in records if record.get("CG_iterations")
        )
        if cg_rows
        else None,
        "median_JVP_count": statistics.median(
            record["JVP_count"] for record in records if record.get("JVP_count") is not None
        ),
        "median_VJP_count": statistics.median(
            record["VJP_count"] for record in records if record.get("VJP_count") is not None
        ),
    }
    summary_path = run_directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["aggregate_operation_counts"] = operation_counts
    summary["artifact_finalization"] = {
        "method": "manifest-verified aggregation from immutable raw records",
        "provenance": environment_provenance(repo_root, "float64", "cpu"),
    }
    summary_path.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary
