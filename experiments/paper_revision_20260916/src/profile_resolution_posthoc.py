"""Summarise the saved E7 rescue cohort by finite-difference step size."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


REFERENCE_TOLERANCE = 0.10


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for run in document["runs"]:
        for branch in run["branches"]:
            rows.append(
                {
                    "data_seed": int(branch["data_seed"]),
                    "step": float(branch["step"]),
                    "reference": float(branch["reference"]),
                    "curvature": float(branch["curvature"]),
                    "relative_difference": float(branch["relative_difference"]),
                    "reference_agreement": float(branch["relative_difference"]) <= REFERENCE_TOLERANCE,
                    "profile_point_valid": bool(branch["profile_point_valid"]),
                    "branches_comparable": bool(branch["plus_start_agreement"] and branch["minus_start_agreement"]),
                    "all_normalized_gradient_ok": bool(branch["all_normalized_gradient_ok"]),
                    "all_positive_hessian": bool(branch["all_positive_hessian"]),
                    "all_objective_bounds_ok": bool(branch["all_objective_bounds_ok"]),
                    "plus_start_gap": branch["plus_start_gap"],
                    "minus_start_gap": branch["minus_start_gap"],
                }
            )
    return rows


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["step"]].append(row)
    result = []
    for step, group in sorted(groups.items(), reverse=True):
        result.append(
            {
                "step": step,
                "planned_points": len(group),
                "reference_agreement_count": sum(r["reference_agreement"] for r in group),
                "profile_point_valid_count": sum(r["profile_point_valid"] for r in group),
                "branch_comparable_count": sum(r["branches_comparable"] for r in group),
                "gradient_gate_count": sum(r["all_normalized_gradient_ok"] for r in group),
                "positive_hessian_count": sum(r["all_positive_hessian"] for r in group),
                "objective_bound_count": sum(r["all_objective_bounds_ok"] for r in group),
                "median_relative_difference": sorted(r["relative_difference"] for r in group)[len(group) // 2],
                "max_relative_difference": max(r["relative_difference"] for r in group),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    source = repo / "outputs/posthoc/paper_strengthening/e7_rescue_v2_summary.json"
    rows = load_rows(source)
    summary_rows = aggregate(rows)
    fields = list(rows[0].keys())
    with (out / "profile_resolution_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with (out / "profile_resolution_by_step.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    document = json.loads(source.read_text(encoding="utf-8"))
    output = {
        "schema_version": 1,
        "classification": "POSTHOC_READ_ONLY_PROFILE_RESOLUTION_AUDIT",
        "protocol": "configs/paper_strengthening/profile_resolution_posthoc_v1.yaml",
        "new_training": False,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "planned_points": len(rows),
        "reference_tolerance": REFERENCE_TOLERANCE,
        "by_step": summary_rows,
        "centre_fit_rows": [run["summary"]["fit_rows"] for run in document["runs"]],
        "source_sha256": sha256(source),
        "claim_boundary": "Reference agreement and full profile-point validity are separate counts; this audit does not certify a nonlinear profile.",
    }
    (out / "profile_resolution_summary.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# E7 profile resolution posthoc audit",
        "",
        "This report reuses the corrected rescue output and does not rerun or retrain any point.",
        "",
        "| h | planned | reference within 10% | full point certificate | branch comparable | gradient gate | positive Hessian | objective bound | median relative difference |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['step']:g} | {row['planned_points']} | {row['reference_agreement_count']}/{row['planned_points']} | "
            f"{row['profile_point_valid_count']}/{row['planned_points']} | {row['branch_comparable_count']}/{row['planned_points']} | "
            f"{row['gradient_gate_count']}/{row['planned_points']} | {row['positive_hessian_count']}/{row['planned_points']} | "
            f"{row['objective_bound_count']}/{row['planned_points']} | {row['median_relative_difference']:.6g} |"
        )
    lines += [
        "",
        "The table separates numerical agreement with the local Schur reference from the stricter point certificate. At h=0.01 all three saved branches are within 10% of the reference, but only two have the complete certificate; the smaller steps show larger discrepancies and/or basin and positive-Hessian failures. This is a resolution and branch-control observation, not a convergence proof or a GN-causality result.",
    ]
    (out / "PROFILE_RESOLUTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"planned_points": len(rows), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
