"""Read-only recomputation of the E3/E6 error decomposition under the manuscript definitions.

Why this exists
---------------
``E_GN_fix`` was reported wrongly.  The manuscript defines the fixed-state Gauss-Newton
truncation as

    Delta_GN,fix = F_raw - H_fix_exact
    E_GN,fix     = |F_raw - H_fix_exact| / (|H_red_exact| + eps)

with the companion identity

    F_se - H_red = (F_raw - H_fix) - (C_GN - C_exact),
    C_exact = H_fix - H_red,   C_GN = F_raw - F_se.

The runner instead emitted ``|F_se - F_raw| / (|H_fix| + eps)``, which is a different
ratio: the numerator was the relaxation correction rather than the fixed-state
truncation, and the denominator used the fixed-state block rather than the reduced
reference.  ``E_raw``, ``E_SAEPS``, ``E_fix`` and ``E_relax`` were correct.

This script recomputes the decomposition from the saved four curvature values.  It never
trains, never overwrites a historical file, and keeps the reported value beside the
corrected one.  The frozen training script is deliberately not edited; the correction
lives here so that the frozen hash -- and therefore the E3 held-out authorisation --
stays valid.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

EPSILON = 1.0e-8  # manuscript denominator floor for the scalar-scale metrics

# cohort label -> path relative to the namespace, in the order the report uses them
COHORTS = {
    "e3_development_1e5": "outputs/development/e3/e3_all_fits.csv",
    "e3_heldout_1e5": "outputs/heldout/e3/e3_all_fits.csv",
    "e3_budget_control_1e4": "outputs/development/e3_budget_control_1e4/e3_all_fits.csv",
    "e3_budget_control_1e5": "outputs/development/e3_budget_control_1e5/e3_all_fits.csv",
}
E6_COHORT = "e6_architecture_accuracy.csv"
E6_PATH = "outputs/development/e6/e6_architecture_accuracy.csv"

FIELDS = [
    "cohort",
    "data_seed",
    "initialization_seed",
    "noise_level",
    "status",
    "F_raw",
    "F_se_GN",
    "H_fix_exact",
    "H_red_exact",
    "C_exact",
    "C_GN",
    "E_raw",
    "E_SAEPS",
    "E_fix",
    "E_GN_fix_reported",
    "E_GN_fix_recomputed",
    "E_GN_fix_difference",
    "E_relax",
    "identity_residual",
    "identity_holds",
    "source_path",
    "source_sha256",
]


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def recompute(row: dict) -> dict:
    """Recompute all five metrics from the saved curvature values."""
    f_raw = number(row.get("F_raw"))
    f_se = number(row.get("F_se_GN"))
    h_fix = number(row.get("H_fix_exact"))
    h_red = number(row.get("H_red_exact"))
    reported = number(row.get("E_GN_fix"))
    result = {
        "data_seed": row.get("data_seed"),
        "initialization_seed": row.get("initialization_seed"),
        "noise_level": row.get("noise_level"),
        "status": row.get("status"),
        "F_raw": f_raw,
        "F_se_GN": f_se,
        "H_fix_exact": h_fix,
        "H_red_exact": h_red,
        "E_GN_fix_reported": reported,
    }
    if None in (f_raw, f_se, h_fix, h_red):
        result.update({"E_GN_fix_recomputed": None, "identity_holds": None})
        return result

    denominator = abs(h_red) + EPSILON
    c_exact = h_fix - h_red
    c_gn = f_raw - f_se
    identity_left = f_se - h_red
    identity_right = (f_raw - h_fix) - (c_gn - c_exact)
    residual = abs(identity_left - identity_right)

    recomputed = abs(f_raw - h_fix) / denominator
    result.update(
        {
            "C_exact": c_exact,
            "C_GN": c_gn,
            "E_raw": abs(f_raw - h_red) / denominator,
            "E_SAEPS": abs(f_se - h_red) / denominator,
            "E_fix": abs(h_fix - h_red) / denominator,
            "E_GN_fix_recomputed": recomputed,
            "E_GN_fix_difference": (
                None if reported is None else recomputed - reported
            ),
            "E_relax": abs(c_gn - c_exact) / (abs(c_exact) + EPSILON),
            "identity_residual": residual,
            "identity_holds": residual <= 1.0e-9 * max(abs(identity_left), 1.0),
        }
    )
    return result


def read_cohort(namespace: Path, relative: str) -> tuple[list[dict], str]:
    path = namespace / relative
    if not path.is_file():
        return [], ""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle)), digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    namespace = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    audit_rows = []
    corrected_rows = []
    for label, relative in COHORTS.items():
        rows, digest = read_cohort(namespace, relative)
        for row in rows:
            recomputed = recompute(row)
            recomputed["cohort"] = label
            recomputed["source_path"] = relative
            recomputed["source_sha256"] = digest
            audit_rows.append(recomputed)
            if recomputed.get("E_GN_fix_recomputed") is not None:
                corrected_rows.append(
                    {
                        "cohort": label,
                        "data_seed": recomputed["data_seed"],
                        "initialization_seed": recomputed["initialization_seed"],
                        "noise_level": recomputed["noise_level"],
                        "E_raw": recomputed["E_raw"],
                        "E_SAEPS": recomputed["E_SAEPS"],
                        "E_fix": recomputed["E_fix"],
                        "E_GN_fix": recomputed["E_GN_fix_recomputed"],
                        "E_relax": recomputed["E_relax"],
                        "identity_residual": recomputed["identity_residual"],
                    }
                )

    write_csv(out / "metric_definition_audit.csv", FIELDS, audit_rows)
    write_csv(
        out / "e3_metrics_corrected.csv",
        ["cohort", "data_seed", "initialization_seed", "noise_level", "E_raw",
         "E_SAEPS", "E_fix", "E_GN_fix", "E_relax", "identity_residual"],
        corrected_rows,
    )

    # E6 uses the same field name; audit whether it inherited the same definition
    e6_rows, e6_digest = read_cohort(namespace, E6_PATH)
    e6_audit = []
    for row in e6_rows:
        item = recompute(row)
        item["architecture"] = row.get("label")
        item["state_parameters"] = row.get("state_parameters")
        item["source_path"] = E6_PATH
        item["source_sha256"] = e6_digest
        e6_audit.append(item)
    write_csv(out / "e6_metric_dependency_audit.csv", ["architecture", "state_parameters"] + FIELDS, e6_audit)

    # regression fixture: the manuscript-exact case quoted in the review
    fixture = next(
        (
            r
            for r in audit_rows
            if r["cohort"] == "e3_heldout_1e5"
            and r["data_seed"] == "916101"
            and r["initialization_seed"] == "926001"
            and r["noise_level"] == "0.0"
        ),
        None,
    )
    checks = {
        "regression_row_found": fixture is not None,
        "regression_recomputed_matches_expected": (
            fixture is not None
            and abs(fixture["E_GN_fix_recomputed"] - 0.0016107401482815197) < 1.0e-15
        ),
        "regression_reported_matches_expected": (
            fixture is not None
            and abs(fixture["E_GN_fix_reported"] - 0.9482289039492354) < 1.0e-12
        ),
        "all_identity_residuals_hold": all(
            r["identity_holds"] is not False for r in audit_rows
        ),
        "degenerate_case_gives_zero": degenerate_check(),
        "e_raw_and_e_saeps_unchanged": e_raw_unchanged(audit_rows, namespace),
    }

    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "metric_definition_correction",
        "manuscript_definitions": {
            "C_exact": "H_fix_exact - H_red_exact",
            "C_GN": "F_raw - F_se_GN",
            "E_raw": "|F_raw - H_red| / (|H_red| + eps)",
            "E_SAEPS": "|F_se - H_red| / (|H_red| + eps)",
            "E_fix": "|H_fix - H_red| / (|H_red| + eps)",
            "E_GN_fix": "|F_raw - H_fix| / (|H_red| + eps)",
            "E_relax": "|C_GN - C_exact| / (|C_exact| + eps)",
            "identity": "F_se - H_red = (F_raw - H_fix) - (C_GN - C_exact)",
            "epsilon": EPSILON,
        },
        "reported_definition_that_was_wrong": "|F_se - F_raw| / (|H_fix| + eps)",
        "unaffected_metrics": ["E_raw", "E_SAEPS", "E_fix", "E_relax"],
        "rows_audited": len(audit_rows),
        "rows_corrected": len(corrected_rows),
        "max_identity_residual": max(
            (r["identity_residual"] for r in audit_rows if r.get("identity_residual") is not None),
            default=None,
        ),
        "median_E_GN_fix_reported": median(
            [r["E_GN_fix_reported"] for r in audit_rows if r.get("E_GN_fix_reported") is not None]
        ),
        "median_E_GN_fix_recomputed": median(
            [r["E_GN_fix_recomputed"] for r in audit_rows if r.get("E_GN_fix_recomputed") is not None]
        ),
        "checks": checks,
        "frozen_files_modified": False,
        "note": (
            "The frozen training script is not edited. This correction is a derived, "
            "read-only recomputation; the old column is retained as "
            "E_GN_fix_reported and the new one is E_GN_fix_recomputed."
        ),
    }
    (out / "metric_correction_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (out / "metric_correction_report.md").write_text(
        correction_report(summary), encoding="utf-8"
    )
    print(out)


def degenerate_check() -> bool:
    """If F_raw equals H_fix then E_GN_fix must be zero even when relaxation is present."""
    row = {
        "F_raw": "2.5", "F_se_GN": "0.1", "H_fix_exact": "2.5", "H_red_exact": "0.4",
        "E_GN_fix": "0.0",
    }
    return abs(recompute(row)["E_GN_fix_recomputed"]) < 1.0e-15


def e_raw_unchanged(audit_rows: list[dict], namespace: Path) -> bool:
    """E_raw and E_SAEPS must be untouched by the correction."""
    for label, relative in COHORTS.items():
        rows, _ = read_cohort(namespace, relative)
        for original in rows:
            recomputed = recompute(original)
            if recomputed.get("E_raw") is None:
                continue
            if abs(recomputed["E_raw"] - float(original["E_raw"])) > 1.0e-12:
                return False
            if abs(recomputed["E_SAEPS"] - float(original["E_SAEPS"])) > 1.0e-12:
                return False
    return True


def median(values: list[float]):
    import statistics

    clean = [v for v in values if v is not None]
    return statistics.median(clean) if clean else None


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def correction_report(summary: dict) -> str:
    checks = summary["checks"]
    return f"""# 指标定义更正报告

日期：2026-09-18。分类：**事后只读重算**，非预注册实验。
不重新训练，不覆盖历史输出，不修改冻结脚本。

## 问题

`E_GN_fix` 的计算与论文定义不符。

论文定义（`paper/manuscript.tex`，Eq. `fixed_state_exact_error`）：

```
Delta_GN,fix = F_raw - H_fix_exact
E_GN,fix     = |F_raw - H_fix_exact| / (|H_red_exact| + 1e-8)
```

运行脚本实际输出的是：

```
|F_se - F_raw| / (|H_fix| + 1e-8)
```

分子是松弛校正而非固定状态截断，分母用了固定状态块而非约化参照。**分子与分母都不对。**

## 真实回归例（来自本命名空间归档记录）

来源：`outputs/heldout/e3/e3_all_fits.csv`，data=916101，init=926001，noise=0。

| 量 | 值 |
|---|---|
| F_raw | 31.691529364882115 |
| F_se_GN | 1.6381987355663945 |
| H_fix_exact | 31.694172677784533 |
| H_red_exact | 1.6410548213691847 |
| 旧 E_GN_fix（错误） | 0.9482289039492354 |
| **新 E_GN_fix（论文定义）** | **0.0016107401482815197** |

回归校验通过：`{checks['regression_recomputed_matches_expected']}`。

## 未受影响的量

`E_raw`、`E_SAEPS`、`E_fix`、`E_relax` 的定义与实现一致，未变。
其中 `E_relax` 之所以不受影响，是因为它与代码所用的符号约定同时反号，差值绝对值不变。

校验 `E_raw`/`E_SAEPS` 未被更动：`{checks['e_raw_and_e_saeps_unchanged']}`。

## 代数恒等式

```
F_se - H_red = (F_raw - H_fix) - (C_GN - C_exact)
C_exact = H_fix - H_red,   C_GN = F_raw - F_se
```

全部 {summary['rows_audited']} 行核验通过：`{checks['all_identity_residuals_hold']}`，
最大残差 {summary['max_identity_residual']:.3e}。

退化校验（`F_raw = H_fix` 时 `E_GN_fix` 必须为 0，即使存在状态松弛）：`{checks['degenerate_case_gives_zero']}`。

## 汇总影响

| 口径 | 中位 E_GN,fix |
|---|---|
| 旧（错误字段） | {summary['median_E_GN_fix_reported']:.6g} |
| 新（论文定义） | {summary['median_E_GN_fix_recomputed']:.6g} |

## 对论文的含义

- 这个错误**不推翻** `E_raw`/`E_SAEPS` 的排序：两者独立计算，未使用该字段。
- **但所有"固定状态 GN 截断约为 0.94"的机制叙述必须撤回重算。**
- 修正后真正的固定状态截断误差比原报小数个量级，且与该中心的 `E_SAEPS` 接近——
  这才是值得继续核验的机制关系，不能用错误字段替代。

## 产出

- `metric_definition_audit.csv`：逐行旧值、新值与差值，含源路径与源哈希。
- `e3_metrics_corrected.csv`：修正后的 E3 指标表。
- `e6_metric_dependency_audit.csv`：E6 同名字段的依赖审查。
- `metric_correction_summary.json`：机器可读汇总与校验结果。

旧列保留为 `E_GN_fix_reported`，新列为 `E_GN_fix_recomputed`，没有静默覆盖。
"""


if __name__ == "__main__":
    main()
