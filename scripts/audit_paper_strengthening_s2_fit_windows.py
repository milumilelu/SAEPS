"""Audit predeclared profile fit windows against the unchanged P3 gates."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

import torch

from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fit(record: dict[str, Any], h_values: list[float]) -> dict[str, Any]:
    rows = [
        row
        for row in record["profile_points"]
        if row["status"] == "PASS" and abs(float(row["h"])) in h_values
    ]
    offsets = [0.0] + [float(row["offset"]) for row in rows]
    losses = [float(record["center_loss_mean"])] + [float(row["loss_mean"]) for row in rows]
    if len(rows) != 2 * len(h_values):
        return {
            "point_count": len(rows),
            "status": "PROFILE_FAILURE",
            "failure_reason": "one or more required profile points failed",
        }
    x = torch.tensor(offsets, dtype=torch.float64)
    y = torch.tensor(losses, dtype=torch.float64)
    design = torch.stack([torch.ones_like(x), x, 0.5 * x.square()], dim=1)
    coefficients = torch.linalg.lstsq(design, y).solution
    prediction = design @ coefficients
    residual = y - prediction
    total = y - y.mean()
    residual_sum = float(torch.dot(residual, residual).item())
    total_sum = float(torch.dot(total, total).item())
    r_squared = 1.0 if total_sum == 0.0 else 1.0 - residual_sum / total_sum
    normalized_rmse = float(torch.sqrt(torch.mean(residual.square())).item()) / max(
        float((y.max() - y.min()).item()), torch.finfo(y.dtype).eps
    )
    condition = float(torch.linalg.cond(design).item())
    curvature = float(coefficients[2].item())
    return {
        "point_count": len(rows),
        "status": "PASS",
        "r_squared": r_squared,
        "normalized_rmse": normalized_rmse,
        "design_condition": condition,
        "curvature": curvature,
    }


def audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_path = root / "configs/paper_strengthening/fit_window_development.yaml"
    config = load_config(config_path)
    gate = config["selection_rule"]["required_fit_quality_gates"]
    summary_path = root / config["source_summary"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_rows = []
    for relative in summary["source_records"]:
        path = root / relative["path"]
        source_rows.append(json.loads(path.read_text(encoding="utf-8")))

    rows = []
    window_summaries = []
    for window in config["candidate_windows"]:
        arm_rows = []
        for record in source_rows:
            h_values = [float(value) for value in window["relative_h_values"]]
            fit = _fit(record, h_values)
            fit_pass = (
                fit["status"] == "PASS"
                and fit["r_squared"] >= float(gate["minimum_r_squared"])
                and fit["normalized_rmse"] <= float(gate["maximum_normalized_rmse"])
                and fit["design_condition"] <= float(gate["maximum_design_condition"])
                and (not gate["positive_curvature_required"] or fit["curvature"] > 0.0)
            )
            row = {
                "window_id": window["id"],
                "arm_id": record["arm_id"],
                "seed": record["seed"],
                "fit": fit,
                "fit_quality_gate": "PASS" if fit_pass else "FAIL",
                "source_path": next(
                    item["path"]
                    for item in summary["source_records"]
                    if item["arm_id"] == record["arm_id"] and item["seed"] == record["seed"]
                ),
            }
            rows.append(row)
            arm_rows.append(row)
        passing = [row for row in arm_rows if row["fit_quality_gate"] == "PASS"]
        rmses = [
            row["fit"]["normalized_rmse"]
            for row in arm_rows
            if row["fit"]["status"] == "PASS"
        ]
        window_summaries.append(
            {
                "window_id": window["id"],
                "retain_h_count": window["retain_h_count"],
                "planned_record_count": len(arm_rows),
                "fit_quality_pass_count": len(passing),
                "fit_quality_pass_fraction": len(passing) / max(len(arm_rows), 1),
                "median_normalized_rmse": statistics.median(rmses) if rmses else None,
            }
        )

    def selection_key(value: dict[str, Any]) -> list[Any]:
        return [
            -int(value["retain_h_count"]),
            -int(value["fit_quality_pass_count"]),
            value["median_normalized_rmse"]
            if value["median_normalized_rmse"] is not None
            else math.inf,
            value["window_id"],
        ]

    selected = min(window_summaries, key=selection_key)
    all_seed_pass = selected["fit_quality_pass_count"] == len(source_rows)
    result = {
        "schema_version": 1,
        "protocol_id": config["protocol_id"],
        "phase": config["phase"],
        "namespace": config["namespace"],
        "config_hash": config_hash(config),
        "config_sha256": _sha256(config_path),
        "source_summary": config["source_summary"],
        "source_summary_sha256": _sha256(summary_path),
        "fit_quality_source": config["fit_quality_source"],
        "fit_quality_source_sha256": _sha256(root / config["fit_quality_source"]),
        "selection_rule": config["selection_rule"],
        "window_summaries": window_summaries,
        "selected_window": selected["window_id"],
        "selected_window_passes_all_records": all_seed_pass,
        "engineering_gate": "PASSED" if all_seed_pass else "FAILED",
        "scientific_profile_claim_authorized": False,
        "rows": rows,
    }
    write_json_atomic(root / config["output_path"], result)

    report = [
        "# S2 fit-window development audit",
        "",
        f"工程门：`{result['engineering_gate']}`；fit-quality threshold 保持 P3 锁定值，未放宽。",
        "",
        "| window | retained h scales | fit-quality PASS | median normalized RMSE |",
        "|---|---:|---:|---:|",
    ]
    for row in window_summaries:
        median = "NA" if row["median_normalized_rmse"] is None else f"{row['median_normalized_rmse']:.8g}"
        report.append(
            f"| `{row['window_id']}` | {row['retain_h_count']} | "
            f"{row['fit_quality_pass_count']}/{row['planned_record_count']} | {median} |"
        )
    report += [
        "",
        f"按预声明规则选择 `{selected['window_id']}`，但该 window 的全部记录通过条件为 `{str(all_seed_pass).lower()}`。",
        "",
        "由于没有一个候选 window 在全部保留 records 上同时通过未改变的 R²、normalized RMSE、design-condition 和正曲率门槛，S2 不能形成可用于独立 confirmation 的 profile fit freeze。该结果保留所有 raw records，不能通过缩小窗口、放宽 threshold 或删除 seed 修复。",
        "",
        f"机器可读结果：`{config['output_path']}`",
    ]
    (root / "docs/paper_strengthening/S2_FIT_WINDOW_DECISION.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8", newline="\n"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(audit(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
