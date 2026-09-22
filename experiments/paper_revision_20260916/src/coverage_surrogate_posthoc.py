"""Compute an analytic local-Gaussian Wald-coverage surrogate from saved blocks.

For a scalar estimator whose local actual information is H and whose reported
information is F, the nominal-z interval has coverage

    2 Phi(z * sqrt(H/F)) - 1.

This is a feasibility screen only.  It is not an empirical coverage experiment:
there is no noisy-data refitting, no new checkpoint and no claim about finite-sample
or nonlinear coverage.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


LEVELS = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def surrogate_coverage(reported_information: float, actual_information: float, z: float) -> float:
    if reported_information <= 0.0 or actual_information <= 0.0:
        return float("nan")
    return 2.0 * normal_cdf(z * math.sqrt(actual_information / reported_information)) - 1.0


def load_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/seed_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not record.get("analysis_valid") or record.get("numerical_status") != "PASS":
            excluded.append(
                {
                    "path": str(path),
                    "benchmark": record.get("benchmark"),
                    "seed": record.get("seed"),
                    "failure_reason": record.get("failure_reason"),
                    "original_status": record.get("original_status"),
                }
            )
            continue
        gn = record["GN_blocks"]
        exact = record["exact_blocks"]
        f_raw = float(gn["G_ll"][0][0])
        h_ll = float(exact["H_ll"][0][0])
        g_lt = gn["G_lt"]
        g_tl = gn["G_tl"]
        g_tt = gn["G_tt"]
        gamma = float(record["gamma"])
        import numpy as np

        matrix = np.asarray(g_tt, dtype=float)
        cross = np.asarray(g_lt, dtype=float) @ np.linalg.solve(
            matrix + gamma * np.eye(matrix.shape[0]), np.asarray(g_tl, dtype=float)
        )
        f_se = f_raw - float(cross[0, 0])
        f_block = f_se + h_ll - f_raw
        h_red = float(record["rerun"]["H_red_exact"])
        rows.append(
            {
                "benchmark": record["benchmark"],
                "seed": int(record["seed"]),
                "F_raw": f_raw,
                "F_SAEPS": f_se,
                "F_block": f_block,
                "H_red_exact": h_red,
                "state_parameters": matrix.shape[0],
            }
        )
    return rows, excluded


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
    source = repo / "outputs/posthoc/exact_fixed_state_v3"
    base_rows, excluded = load_rows(source)
    rows: list[dict[str, Any]] = []
    for base in base_rows:
        for nominal, z in LEVELS.items():
            for method, key in [("raw", "F_raw"), ("SAEPS", "F_SAEPS"), ("block", "F_block")]:
                rows.append(
                    {
                        **base,
                        "nominal_level": nominal,
                        "method": method,
                        "surrogate_coverage": surrogate_coverage(base[key], base["H_red_exact"], z),
                    }
                )
    fields = list(rows[0].keys())
    with (out / "coverage_surrogate_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[tuple[str, float, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["benchmark"], row["nominal_level"], row["method"])].append(row["surrogate_coverage"])
    summary_rows = [
        {
            "benchmark": benchmark,
            "nominal_level": nominal,
            "method": method,
            "valid_rows": len(values),
            "median_surrogate_coverage": median(values),
            "min_surrogate_coverage": min(values),
            "max_surrogate_coverage": max(values),
        }
        for (benchmark, nominal, method), values in sorted(grouped.items())
    ]
    with (out / "coverage_surrogate_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    summary = {
        "schema_version": 1,
        "classification": "POSTHOC_LOCAL_GAUSSIAN_COVERAGE_SURROGATE",
        "protocol": "configs/paper_strengthening/coverage_surrogate_posthoc_v1.yaml",
        "new_training": False,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "planned_exact_files": len(base_rows) + len(excluded),
        "valid_exact_files": len(base_rows),
        "excluded_exact_files": excluded,
        "nominal_levels": list(LEVELS),
        "summary": summary_rows,
        "claim_boundary": "Analytic local-Gaussian feasibility screen only; empirical coverage requires repeated noisy-data refitting.",
    }
    (out / "coverage_surrogate_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Local-Gaussian coverage surrogate audit",
        "",
        "This is a feasibility screen derived from saved exact reduced curvatures. It is not an empirical Monte Carlo coverage experiment.",
        "",
        "| benchmark | nominal | method | rows | median surrogate coverage | range |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['benchmark']} | {row['nominal_level']:.2f} | {row['method']} | {row['valid_rows']} | "
            f"{row['median_surrogate_coverage']:.4f} | {row['min_surrogate_coverage']:.4f}–{row['max_surrogate_coverage']:.4f} |"
        )
    lines += [
        "",
        f"The audit retains {len(excluded)} excluded exact-block files in the planned denominator.",
        "The signal supports proceeding to an end-to-end refitting pilot, but cannot establish finite-sample CI coverage or a statistical guarantee.",
    ]
    (out / "COVERAGE_SURROGATE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"valid": len(base_rows), "excluded": len(excluded), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
