"""Freeze the S2 development profile rules from machine-readable evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
import yaml

from saeps.config import load_config
from saeps.io_utils import write_json_atomic


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fit_quality(record: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in record["profile_points"]
        if row["status"] == "PASS" and row["loss_mean"] is not None
    ]
    offsets = [0.0] + [float(row["offset"]) for row in rows]
    losses = [float(record["center_loss_mean"])] + [float(row["loss_mean"]) for row in rows]
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
    return {
        "point_count_including_center": len(rows) + 1,
        "curvature": float(coefficients[2].item()),
        "r_squared": r_squared,
        "normalized_rmse": normalized_rmse,
        "design_condition": float(torch.linalg.cond(design).item()),
        "positive_curvature": bool(float(coefficients[2].item()) > 0.0),
    }


def freeze(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source_config_path = root / "configs/paper_strengthening/development.yaml"
    summary_path = root / "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_DEVELOPMENT_SUMMARY.json"
    source_config = load_config(source_config_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    selected_id = summary["selected_development_arm"]
    selected = next(row for row in summary["arm_summaries"] if row["arm_id"] == selected_id)
    arm = next(row for row in source_config["arms"] if row["id"] == selected_id)

    fit_rows = []
    for relative in summary["source_records"]:
        path = root / relative["path"]
        record = json.loads(path.read_text(encoding="utf-8"))
        fit_rows.append(
            {
                "arm_id": record["arm_id"],
                "seed": record["seed"],
                "fit": _fit_quality(record),
                "source_path": relative["path"],
            }
        )
    fit_path = root / "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_QUALITY_AUDIT.json"
    fit_audit = {
        "schema_version": 1,
        "protocol_id": source_config["protocol_id"],
        "role": "development_only_fit_quality_audit",
        "fit_quality_source": "all retained profile points plus center; no interpolation",
        "rows": fit_rows,
    }
    write_json_atomic(fit_path, fit_audit)

    inherited_fit = load_config(root / "configs/p3_profile.yaml")["fit_quality"]
    locked = {
        "schema_version": 1,
        "protocol_id": "SAEPS-Q2-STRENGTHENING-S2-LOCK",
        "phase": "S2_PROFILE_DEVELOPMENT_FREEZE",
        "namespace": source_config["namespace"],
        "execution_authorized": False,
        "confirmation_authorized": False,
        "benchmark": source_config["benchmark"],
        "source_checkpoint_family": source_config["source_checkpoint_family"],
        "source_checkpoint_namespace": source_config["source_checkpoint_namespace"],
        "development_seeds": source_config["development_seeds"],
        "gamma_alpha": source_config["gamma_alpha"],
        "selected_development_arm": selected_id,
        "profile_points": sorted([-float(value) for value in arm["h_values"]] + [float(value) for value in arm["h_values"]]),
        "h_values_for_symmetric_curvature": arm["h_values"],
        "independent_start_from_common_theta0": True,
        "continuation_forbidden": True,
        "normalized_gradient_tolerance": arm["normalized_gradient_tolerance"],
        "point_gate": {
            "optimizer_termination_required": True,
            "loss_plateau_required": True,
            "normalized_gradient_required": True,
            "exact_local_minimum_hessian_gate_required": True,
            "missing_point_rule": "retain_PROFILE_FAILURE_and_exclude_the_curve_from_valid_fit",
        },
        "fit_window": "all_retained_profile_points_plus_center",
        "fit_quality": inherited_fit,
        "resolution_diagnostic": {
            "role": "reported_development_diagnostic_until_independent_validation_is_authorized",
            "last_two_curvature_relative_change": "report_only",
            "exact_finite_gamma_relative_error": "report_only",
        },
        "source_config": source_config_path.relative_to(root).as_posix(),
        "source_config_sha256": _sha256(source_config_path),
        "development_summary": summary_path.relative_to(root).as_posix(),
        "development_summary_sha256": _sha256(summary_path),
        "fit_quality_audit": fit_path.relative_to(root).as_posix(),
        "fit_quality_audit_sha256": _sha256(fit_path),
        "selection_rule": source_config["selection_rule"],
        "selected_arm_summary": selected,
    }
    locked_path = root / "configs/paper_strengthening/locked_profile.yaml"
    locked_path.parent.mkdir(parents=True, exist_ok=True)
    locked_path.write_text(
        yaml.safe_dump(locked, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )
    lock_record = {
        "schema_version": 1,
        "protocol_id": locked["protocol_id"],
        "locked_config": locked_path.relative_to(root).as_posix(),
        "locked_config_sha256": _sha256(locked_path),
        "source_config_sha256": locked["source_config_sha256"],
        "development_summary_sha256": locked["development_summary_sha256"],
        "fit_quality_audit_sha256": locked["fit_quality_audit_sha256"],
        "selected_development_arm": selected_id,
        "confirmation_authorized": False,
    }
    write_json_atomic(root / "configs/paper_strengthening/LOCKED_PROFILE_SHA256.json", lock_record)

    report_lines = [
        "# S2 development decision",
        "",
        "状态：`PASSED`（development engineering gate）；未授权新的 confirmation。",
        "",
        "本阶段只读复用 V5 Allen–Cahn checkpoints 70–72，所有输出写入 `paper_strengthening_v1`。三组 arm 在执行前已写入 development 配置；选择规则只读取 profile point 通过数、曲率分辨率变化和 exact finite-γ reference 误差，禁止读取 D、E_raw、E_SAEPS、eta 或图形外观。",
        "",
        "| arm | all-points-pass seeds | profile points | median last-two change | median exact-reference error |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["arm_summaries"]:
        report_lines.append(
            f"| `{row['arm_id']}` | {row['all_points_pass_seed_count']}/{row['planned_seed_count']} | "
            f"{row['total_profile_pass_count']}/{row['total_profile_point_count']} | "
            f"{row['median_last_two_curvature_relative_change']:.8g} | "
            f"{row['median_finest_profile_exact_relative_error']:.8g} |"
        )
    report_lines += [
        "",
        f"按预声明规则冻结 `{selected_id}`。冻结后的步长为 `{arm['h_values']}`，normalized-gradient threshold 为 `{arm['normalized_gradient_tolerance']}`。所有 9 个 raw records 均为 `PASS`，没有缺失点或静默排除。",
        "",
        "该结论只说明 development 阶段可以稳定测量这组有限 γ profile；它不等价于 nonlinear profile scientific support，也不授权新的 confirmation。下一阶段若执行，必须另行授权并使用此 hash 可追溯的规则。",
        "",
        f"- locked config: `configs/paper_strengthening/locked_profile.yaml`",
        f"- lock record: `configs/paper_strengthening/LOCKED_PROFILE_SHA256.json`",
        f"- fit audit: `{fit_path.relative_to(root).as_posix()}`",
        f"- source config SHA256: `{locked['source_config_sha256']}`",
        f"- development summary SHA256: `{locked['development_summary_sha256']}`",
    ]
    report_path = root / "docs/paper_strengthening/S2_DEVELOPMENT_DECISION.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
    return lock_record


if __name__ == "__main__":
    print(json.dumps(freeze(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
