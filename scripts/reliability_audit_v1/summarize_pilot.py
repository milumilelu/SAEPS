#!/usr/bin/env python3
"""Create denominator-preserving RI-2 summary metrics from raw manifests."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.reliability_audit_v1.reliability import selective_metrics, target_log_error


def _manifests(runs_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(runs_dir.glob("B*_data*_opt*/manifest.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["manifest_path"] = str(path)
        rows.append(row)
    return rows


def summarize(runs_dir: Path, analysis_path: Path | None = None) -> dict:
    rows = _manifests(runs_dir)
    analysis_rows = {}
    if analysis_path and analysis_path.is_file():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        analysis_rows = {str(row.get("run_id")): row for row in analysis.get("records", [])}
    by_benchmark: dict[str, list[dict]] = defaultdict(list)
    records = []
    for row in rows:
        record = dict(row)
        analysis_row = analysis_rows.get(str(row.get("run_id")))
        if analysis_row:
            record["decision_record"] = analysis_row.get("decision_record")
        error = target_log_error(record)
        record["target_log_error"] = error
        benchmark = str(record.get("benchmark", "UNKNOWN"))
        by_benchmark[benchmark].append(record)
        records.append(record)
    benchmark_summary = {}
    for benchmark, group in sorted(by_benchmark.items()):
        errors = [float(r["target_log_error"]) for r in group if r.get("target_log_error") is not None]
        estimates = {}
        for name in ("k", "C", "a"):
            values = [float(r["parameter_estimates"][name]) for r in group if name in (r.get("parameter_estimates") or {})]
            if values:
                estimates[name] = {"median": float(sorted(values)[len(values)//2]), "mean": float(sum(values)/len(values)), "count": len(values)}
        benchmark_summary[benchmark] = {
            "planned": len(group),
            "computable": sum(r.get("execution_status") == "PASS" for r in group),
            "fit_qualified": sum(r.get("fit_status") == "PASS" for r in group),
            "profile_eligible": sum(r.get("profile_status") == "PASS" for r in group),
            "decision_counts": {label: sum((r.get("decision_record") or {}).get("decision") == label for r in group) for label in ("SUPPORTED_COMBINATION", "WEAK_OR_CONFOUNDED", "UNRESOLVED_NUMERICAL", "INVALID_CHECKPOINT")},
            "target_log_error": {"count": len(errors), "mean": (sum(errors)/len(errors) if errors else None), "rmse": ((sum(e*e for e in errors)/len(errors))**0.5 if errors else None), "max": (max(errors) if errors else None)},
            "parameter_estimates": estimates,
        }
    metrics = selective_metrics(records) if analysis_rows else None
    return {
        "schema_version": 1,
        "protocol_id": "reliability_audit_v1",
        "phase": "RI-2",
        "scope": "development only",
        "source_runs_dir": str(runs_dir),
        "planned_denominator": len(records),
        "computed": sum(r.get("execution_status") == "PASS" for r in records),
        "fit_qualified": sum(r.get("fit_status") == "PASS" for r in records),
        "profile_eligible": sum(r.get("profile_status") == "PASS" for r in records),
        "by_benchmark": benchmark_summary,
        "selective_metrics": metrics,
        "truth_used_only_for_evaluation": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.runs_dir, args.analysis)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"planned_denominator": result["planned_denominator"], "fit_qualified": result["fit_qualified"], "profile_eligible": result["profile_eligible"]}))


if __name__ == "__main__":
    main()
