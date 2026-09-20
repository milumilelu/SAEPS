"""Close S2 after the fit-quality audit, preserving the failed freeze attempt."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import yaml

from saeps.io_utils import write_json_atomic


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    report = root / "docs/paper_strengthening/S2_DEVELOPMENT_DECISION.md"
    initial_report = root / "docs/paper_strengthening/S2_INITIAL_ARM_SELECTION.md"
    if report.exists() and not initial_report.exists():
        shutil.copyfile(report, initial_report)

    fit_path = root / "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json"
    fit = json.loads(fit_path.read_text(encoding="utf-8"))
    locked_path = root / "configs/paper_strengthening/locked_profile.yaml"
    locked = yaml.safe_load(locked_path.read_text(encoding="utf-8"))
    locked["phase"] = "S2_PROFILE_DEVELOPMENT_CLOSED_WITH_FIT_FAILURE"
    locked["status"] = "FAILED"
    locked["engineering_gate"] = "FAILED"
    locked["scientific_profile_claim_authorized"] = False
    locked["confirmation_authorized"] = False
    locked["failure_reason"] = (
        "No predeclared fit window passed unchanged P3 R2, normalized-RMSE, "
        "condition-number and positive-curvature gates for all retained records."
    )
    locked["fit_window_audit"] = fit_path.relative_to(root).as_posix()
    locked["fit_window_audit_sha256"] = _sha256(fit_path)
    locked_path.write_text(
        yaml.safe_dump(locked, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )
    lock_record_path = root / "configs/paper_strengthening/LOCKED_PROFILE_SHA256.json"
    lock_record = json.loads(lock_record_path.read_text(encoding="utf-8"))
    lock_record.update(
        {
            "status": "FAILED",
            "engineering_gate": "FAILED",
            "scientific_profile_claim_authorized": False,
            "confirmation_authorized": False,
            "locked_config_sha256": _sha256(locked_path),
            "fit_window_audit": fit_path.relative_to(root).as_posix(),
            "fit_window_audit_sha256": _sha256(fit_path),
        }
    )
    write_json_atomic(lock_record_path, lock_record)

    lines = [
        "# S2 development decision",
        "",
        "状态：`FAILED`（profile fit-quality engineering gate）；没有授权新的 confirmation。",
        "",
        "第一轮 development 队列的 9 个 profile records 均完成了独立优化、stationarity 和 exact local-minimum gate，但这不足以形成可审计的局部二次 profile。随后对预先列明的四类 fit window 运行了只读审计，保持 P3 的 R²、normalized RMSE、design-condition 和正曲率门槛不变。",
        "",
        "| window | 保留尺度数 | fit-quality PASS | 中位 normalized RMSE |",
        "|---|---:|---:|---:|",
    ]
    for row in fit["window_summaries"]:
        median = "NA" if row["median_normalized_rmse"] is None else f"{row['median_normalized_rmse']:.8g}"
        lines.append(
            f"| `{row['window_id']}` | {row['retain_h_count']} | "
            f"{row['fit_quality_pass_count']}/{row['planned_record_count']} | {median} |"
        )
    lines += [
        "",
        f"预声明选择规则在未改变阈值的情况下选择 `{fit['selected_window']}` 作为诊断基准，但 `selected_window_passes_all_records` 为 `{str(fit['selected_window_passes_all_records']).lower()}`。因此本阶段不能把 profile 扩展成独立 scientific evidence。",
        "",
        "该失败被归类为 profile numerical/scientific limitation：profile point 的可优化性通过，而有限步长下的局部二次拟合没有在完整 development cohort 上通过。不得缩小 fit window、放宽阈值、删除 seed 或用单一 finest pair 的恰合拟合替代多尺度证据。后续应采用 Claim Ledger 的收缩主张，除非用户另行授权一份新协议。",
        "",
        "- 首轮 arm 选择记录：`docs/paper_strengthening/S2_INITIAL_ARM_SELECTION.md`",
        "- fit-window 机器结果：`outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json`",
        "- 当前配置状态：`configs/paper_strengthening/locked_profile.yaml`（`FAILED`，不可用于 confirmation）",
        "- lock record：`configs/paper_strengthening/LOCKED_PROFILE_SHA256.json`",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return lock_record


if __name__ == "__main__":
    print(json.dumps(close(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
