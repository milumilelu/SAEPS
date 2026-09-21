"""Recompute a low-dimensional exact-parameter-block correction from saved outputs.

This is a read-only development analysis.  It never retrains a checkpoint and never
changes the locked SAEPS or profile protocol.  For each scalar record it computes

    F_block = H_ll - G_lt (G_tt + gamma I)^-1 G_tl

and verifies the equivalent identity

    F_block = F_se_GN + H_ll - G_ll.

The output keeps signed errors relative to the exact reduced reference, because a
correction can improve or worsen the absolute error when GN and relaxation terms
cancel.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


FLOOR = 1.0e-8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def scalar(value: Any) -> float:
    array = np.asarray(value, dtype=float)
    return float(array.reshape(-1)[0])


def base_row(
    *,
    source: str,
    group: str,
    seed: int,
    state_parameters: int,
    f_raw: float,
    f_se: float,
    h_ll: float,
    h_red: float,
    gamma: float | None,
    data_seed: int | None = None,
    initialization_seed: int | None = None,
) -> dict[str, Any]:
    f_block = f_se + h_ll - f_raw
    denominator = abs(h_red) + FLOOR
    signed_raw = f_raw - h_red
    signed_se = f_se - h_red
    signed_block = f_block - h_red
    identity_residual = f_block - (f_se + h_ll - f_raw)
    return {
        "source": source,
        "group": group,
        "seed": seed,
        "data_seed": data_seed,
        "initialization_seed": initialization_seed,
        "state_parameters": state_parameters,
        "gamma": gamma,
        "F_raw": f_raw,
        "F_se_GN": f_se,
        "H_ll_exact": h_ll,
        "H_red_exact": h_red,
        "F_block": f_block,
        "signed_error_raw": signed_raw,
        "signed_error_se": signed_se,
        "signed_error_block": signed_block,
        "E_raw": abs(signed_raw) / denominator,
        "E_SAEPS": abs(signed_se) / denominator,
        "E_block": abs(signed_block) / denominator,
        "block_vs_se_improvement": abs(signed_block) < abs(signed_se),
        "block_vs_raw_improvement": abs(signed_block) < abs(signed_raw),
        "identity_absolute_residual": identity_residual,
        "identity_pass": abs(identity_residual) <= 1.0e-10,
        "signed_cancellation_ratio": abs(signed_se) / (abs(signed_raw) + FLOOR),
    }


def read_architecture(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            if record["available"].strip().lower() != "true":
                continue
            rows.append(
                base_row(
                    source="E6_architecture",
                    group=record["label"],
                    seed=int(record["data_seed"]),
                    state_parameters=int(record["state_parameters"]),
                    f_raw=float(record["F_raw"]),
                    f_se=float(record["F_se_GN"]),
                    h_ll=float(record["H_fix_exact"]),
                    h_red=float(record["H_red_exact"]),
                    gamma=float(record["gamma"]),
                    data_seed=int(record["data_seed"]),
                    initialization_seed=int(record["initialization_seed"]),
                )
            )
    return rows


def read_exact_blocks(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/seed_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not record.get("analysis_valid") or record.get("numerical_status") != "PASS":
            continue
        gn = record["GN_blocks"]
        exact = record["exact_blocks"]
        g_tt = np.asarray(gn["G_tt"], dtype=float)
        g_lt = np.asarray(gn["G_lt"], dtype=float)
        g_tl = np.asarray(gn["G_tl"], dtype=float)
        gamma = float(record["gamma"])
        f_raw = scalar(gn["G_ll"])
        h_ll = scalar(exact["H_ll"])
        h_red = float(record["rerun"]["H_red_exact"])
        f_se = f_raw - scalar(g_lt @ np.linalg.solve(g_tt + gamma * np.eye(g_tt.shape[0]), g_tl))
        rows.append(
            base_row(
                source="exact_fixed_state_v3",
                group=str(record["benchmark"]),
                seed=int(record["seed"]),
                state_parameters=int(g_tt.shape[0]),
                f_raw=f_raw,
                f_se=f_se,
                h_ll=h_ll,
                h_red=h_red,
                gamma=gamma,
            )
        )
    return rows


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['source']}::{row['group']}"] .append(row)

    result: dict[str, Any] = {}
    for key, group in sorted(grouped.items()):
        result[key] = {
            "planned_rows": len(group),
            "median_E_raw": float(np.median([r["E_raw"] for r in group])),
            "median_E_SAEPS": float(np.median([r["E_SAEPS"] for r in group])),
            "median_E_block": float(np.median([r["E_block"] for r in group])),
            "block_vs_se_wins": sum(r["block_vs_se_improvement"] for r in group),
            "block_vs_raw_wins": sum(r["block_vs_raw_improvement"] for r in group),
            "all_identity_checks_pass": all(r["identity_pass"] for r in group),
            "signed_error_median_raw": float(np.median([r["signed_error_raw"] for r in group])),
            "signed_error_median_se": float(np.median([r["signed_error_se"] for r in group])),
            "signed_error_median_block": float(np.median([r["signed_error_block"] for r in group])),
        }
    return result


def git_commit(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


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

    architecture_path = repo / "experiments/paper_revision_20260916/outputs/development/e6/e6_architecture_accuracy.csv"
    exact_root = repo / "outputs/posthoc/exact_fixed_state_v3"
    rows = read_architecture(architecture_path) + read_exact_blocks(exact_root)
    if not rows:
        raise RuntimeError("no valid rows found")
    if not all(row["identity_pass"] for row in rows):
        raise RuntimeError("parameter-block identity failed")

    fields = list(rows[0].keys())
    with (out / "parameter_block_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    exact_paths = sorted(exact_root.glob("*/seed_*.json"))
    exact_excluded = []
    for path in exact_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not record.get("analysis_valid") or record.get("numerical_status") != "PASS":
            exact_excluded.append(
                {
                    "path": str(path.relative_to(repo)),
                    "benchmark": record.get("benchmark"),
                    "seed": record.get("seed"),
                    "analysis_valid": record.get("analysis_valid"),
                    "numerical_status": record.get("numerical_status"),
                    "failure_reason": record.get("failure_reason"),
                    "original_status": record.get("original_status"),
                }
            )
    source_paths = [architecture_path, *exact_paths]
    summary = {
        "schema_version": 1,
        "classification": "POSTHOC_READ_ONLY_MECHANISM_ANALYSIS",
        "protocol": "configs/paper_strengthening/parameter_block_correction_v1.yaml",
        "git_commit": git_commit(repo),
        "new_training": False,
        "planned_rows": len(rows),
        "identity_pass_rows": sum(r["identity_pass"] for r in rows),
        "architecture_rows": sum(r["source"] == "E6_architecture" for r in rows),
        "exact_block_rows": sum(r["source"] == "exact_fixed_state_v3" for r in rows),
        "exact_block_planned_files": len(exact_paths),
        "exact_block_excluded_files": exact_excluded,
        "groups": summarise(rows),
        "source_sha256": {str(path.relative_to(repo)): sha256(path) for path in source_paths},
        "claim_boundary": (
            "The correction is a paired posthoc candidate. Rows share data seeds and "
            "initialisations within cohorts; this is not an independent confirmation or "
            "a universal dominance result."
        ),
    }
    (out / "parameter_block_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Parameter-block correction posthoc audit",
        "",
        "This development-only audit reuses saved curvature blocks and performs no training.",
        "It reports signed errors relative to the exact finite-damping reduced Hessian.",
        "",
        "| Source / group | rows | median E_raw | median E_SAEPS | median E_block | block improves SAEPS | block improves raw |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, values in summary["groups"].items():
        lines.append(
            f"| {key} | {values['planned_rows']} | {values['median_E_raw']:.6g} | "
            f"{values['median_E_SAEPS']:.6g} | {values['median_E_block']:.6g} | "
            f"{values['block_vs_se_wins']}/{values['planned_rows']} | "
            f"{values['block_vs_raw_wins']}/{values['planned_rows']} |"
        )
    lines += [
        "",
        f"All {summary['identity_pass_rows']}/{summary['planned_rows']} rows satisfy "
        "F_block = F_se_GN + H_ll_exact - G_ll to the 1e-10 absolute check.",
        f"The exact-block source contains {summary['exact_block_planned_files']} planned files; "
        f"{len(summary['exact_block_excluded_files'])} are excluded by their saved invalid status "
        "and remain listed in parameter_block_summary.json.",
        "",
        "The signed rows retain cases where the correction worsens absolute error. "
        "No row is removed because of that outcome, and no nonlinear-profile or "
        "covariance claim is inferred.",
    ]
    (out / "PARAMETER_BLOCK_CORRECTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
