"""Read-only recomputation of the E3 statistics at the declared statistical unit.

The problem
-----------
The E3 held-out design is

    6 data seeds x 2 initializations x 2 noise levels = 24 fits,

and the protocol declares the *data seed* as the statistical unit, with the median taken
across initializations inside a seed.  The report nevertheless quoted a one-sided sign
test of ``p = 5.96e-08``, which is exactly ``2^-24``: it treated 24 correlated fits as 24
independent units.  The same file also declared ``statistical_unit: data_seed``.  The two
statements cannot both be the primary result.

What this script does
---------------------
Rebuilds the summaries from the planned identities recorded in the frozen protocol, not
from whichever runs happened to succeed.  Three layers are written out separately, each
stating its own aggregation unit:

    fit level           24 rows, descriptive only, no independence claimed
    data-seed level     6 units, initializations pooled by median (frozen rule)
    per noise layer     6 units per layer, because the layers share seeds

The primary inference is the data-seed level.  Both improvement ratios are reported,
because they are different numbers and must not be substituted for one another.

Nothing is trained, no historical file is overwritten, and the frozen protocol is only
read.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

HELDOUT_PATH = "outputs/heldout/e3/e3_all_fits.csv"
DEVELOPMENT_PATH = "outputs/development/e3/e3_all_fits.csv"


def sign_test(wins: int, non_ties: int) -> float | None:
    """One-sided exact sign test; the denominator is the number of independent units."""
    if non_ties == 0:
        return None
    return sum(math.comb(non_ties, i) for i in range(wins, non_ties + 1)) / 2**non_ties


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def planned_identities(protocol: dict) -> list[tuple[int, int, float]]:
    """The full planned grid, read from the protocol rather than from successful runs."""
    e3 = protocol["E3"]
    return [
        (int(data_seed), int(init_seed), float(noise))
        for data_seed in e3["heldout_data_seeds"]
        for init_seed in e3["initialization_seeds"]
        for noise in e3["noise_levels"]
    ]


def main() -> None:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fit-metrics", type=Path, default=None,
                        help="corrected metrics csv; defaults to the raw cohort file")
    args = parser.parse_args()

    repo = args.repo.resolve()
    namespace = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    protocol = yaml.safe_load((namespace / "protocol.yaml").read_text(encoding="utf-8"))
    planned = planned_identities(protocol)

    source = args.fit_metrics or (namespace / HELDOUT_PATH)
    source_relative = (
        str(source.relative_to(namespace)).replace("\\", "/")
        if namespace in source.parents
        else str(source)
    )
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open(encoding="utf-8") as handle:
        observed = list(csv.DictReader(handle))

    by_key = {}
    duplicates = []
    for row in observed:
        key = (int(row["data_seed"]), int(row["initialization_seed"]), float(row["noise_level"]))
        if key in by_key:
            duplicates.append(key)
        by_key[key] = row

    # membership: planned identity -> observed status, so missing and duplicate are explicit
    membership = []
    for data_seed, init_seed, noise in planned:
        row = by_key.get((data_seed, init_seed, noise))
        membership.append(
            {
                "data_seed": data_seed,
                "initialization_seed": init_seed,
                "noise_level": noise,
                "observed": row is not None,
                "status": row.get("status") if row else "MISSING",
                "valid": bool(row is not None and row.get("status") == "PASS"),
                "duplicate": (data_seed, init_seed, noise) in duplicates,
            }
        )
    unexpected = [
        k for k in by_key if k not in set(planned)
    ]

    def fit_rows(noise: float | None = None):
        for data_seed, init_seed, level in planned:
            if noise is not None and level != noise:
                continue
            row = by_key.get((data_seed, init_seed, level))
            if row is None or row.get("status") != "PASS":
                continue
            E_raw, E_saeps = number(row.get("E_raw")), number(row.get("E_SAEPS"))
            if E_raw is None or E_saeps is None:
                continue
            yield {
                "data_seed": data_seed,
                "initialization_seed": init_seed,
                "noise_level": level,
                "E_raw": E_raw,
                "E_SAEPS": E_saeps,
                "paired_ratio": E_raw / E_saeps if E_saeps else None,
                "improved": E_saeps < E_raw,
            }

    fits = list(fit_rows())

    # layer 1: per fit, descriptive only
    fit_level = {
        "aggregation_unit": "fit",
        "independence_claimed": False,
        "fits_planned": len(planned),
        "fits_observed": len(observed),
        "fits_valid": len(fits),
        "fits_improved": sum(1 for f in fits if f["improved"]),
        "median_E_raw": statistics.median([f["E_raw"] for f in fits]) if fits else None,
        "median_E_SAEPS": statistics.median([f["E_SAEPS"] for f in fits]) if fits else None,
        "ratio_of_medians": (
            statistics.median([f["E_raw"] for f in fits])
            / statistics.median([f["E_SAEPS"] for f in fits])
            if fits
            else None
        ),
        "median_paired_ratio": statistics.median([f["paired_ratio"] for f in fits if f["paired_ratio"]])
        if fits
        else None,
        "note": "descriptive; these 24 fits are not 24 independent data sets",
    }

    # layer 2: per noise layer, initializations pooled inside a seed (frozen rule)
    by_noise = {}
    for level in sorted({f["noise_level"] for f in fits}):
        group = [f for f in fits if f["noise_level"] == level]
        seeds = sorted({f["data_seed"] for f in group})
        seed_medians = []
        wins = 0
        for seed in seeds:
            rows = [f for f in group if f["data_seed"] == seed]
            med_raw = statistics.median([f["E_raw"] for f in rows])
            med_saeps = statistics.median([f["E_SAEPS"] for f in rows])
            seed_medians.append((seed, med_raw, med_saeps))
            wins += med_saeps < med_raw
        by_noise[str(level)] = {
            "aggregation_unit": "data_seed",
            "initializer_aggregation": "median within data seed",
            "independent_units": len(seeds),
            "fits_valid": len(group),
            "seeds_improved": wins,
            "one_sided_sign_test_p": sign_test(wins, len(seeds)),
            "median_E_raw": statistics.median([m[1] for m in seed_medians]) if seed_medians else None,
            "median_E_SAEPS": statistics.median([m[2] for m in seed_medians]) if seed_medians else None,
            "note": "the two noise layers share data seeds and are not independent of each other",
        }

    # layer 3: data-seed level, all four fits per seed pooled by median
    seed_groups = {}
    for f in fits:
        seed_groups.setdefault(f["data_seed"], []).append(f)
    seed_summary = []
    wins = 0
    for seed in sorted(seed_groups):
        rows = seed_groups[seed]
        med_raw = statistics.median([f["E_raw"] for f in rows])
        med_saeps = statistics.median([f["E_SAEPS"] for f in rows])
        improved = med_saeps < med_raw
        wins += improved
        seed_summary.append(
            {
                "data_seed": seed,
                "fits_valid": len(rows),
                "median_E_raw": med_raw,
                "median_E_SAEPS": med_saeps,
                "improved": improved,
            }
        )
    units = len(seed_summary)
    data_seed_level = {
        "aggregation_unit": "data_seed",
        "initializer_aggregation": "median within data seed",
        "noise_aggregation": "median across noise layers within data seed (POST HOC: the "
        "protocol fixes the initializer rule but does not fix a noise-merge rule)",
        "independent_units": units,
        "units_improved": wins,
        "one_sided_sign_test_p": sign_test(wins, units),
        "median_E_raw": statistics.median([s["median_E_raw"] for s in seed_summary]) if seed_summary else None,
        "median_E_SAEPS": statistics.median([s["median_E_SAEPS"] for s in seed_summary]) if seed_summary else None,
        "ratio_of_medians": (
            statistics.median([s["median_E_raw"] for s in seed_summary])
            / statistics.median([s["median_E_SAEPS"] for s in seed_summary])
            if seed_summary
            else None
        ),
        "median_paired_ratio": statistics.median([f["paired_ratio"] for f in fits if f["paired_ratio"]])
        if fits
        else None,
        "per_seed": seed_summary,
    }

    document = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "statistics_correction",
        "source_path": source_relative,
        "source_sha256": digest,
        "declared_statistical_unit": protocol["E3"]["statistical_unit"],
        "declared_initializer_aggregation": protocol["E3"]["initializer_aggregation"],
        "planned_grid_size": len(planned),
        "membership_duplicates": [list(d) for d in duplicates],
        "membership_missing": [
            [m["data_seed"], m["initialization_seed"], m["noise_level"]]
            for m in membership
            if not m["observed"]
        ],
        "membership_unexpected": [list(u) for u in unexpected],
        "fit_level_summary": fit_level,
        "per_noise_layer": by_noise,
        "data_seed_level_summary": data_seed_level,
        "primary_inference": "data_seed_level_summary",
        "multiple_comparison_note": (
            "The two noise layers are two tests over the same six seeds. If they are "
            "treated as one family the layer p-values must be reported as unadjusted, "
            "with the shared-seed dependence disclosed; they must not be combined into "
            "twelve independent units."
        ),
    }
    (out / "data_seed_level_summary.json").write_text(
        json.dumps(data_seed_level, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (out / "fit_level_summary.json").write_text(
        json.dumps(fit_level, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (out / "e3_cluster_statistics.json").write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    with (out / "e3_cluster_membership.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["data_seed", "initialization_seed", "noise_level", "observed",
                        "status", "valid", "duplicate"],
        )
        writer.writeheader()
        writer.writerows(membership)

    (out / "statistics_correction_report.md").write_text(
        correction_report(document), encoding="utf-8"
    )
    print(out)


def correction_report(document: dict) -> str:
    fit = document["fit_level_summary"]
    seed = document["data_seed_level_summary"]
    layers = document["per_noise_layer"]
    return f"""# 统计单位更正报告

日期：2026-09-18。分类：**事后只读重算**，非预注册实验。
来源：`{document['source_path']}`
哈希：`{document['source_sha256']}`

## 问题

E3 留出设计为 6 个数据种子 × 2 个初始化 × 2 档噪声 = 24 个拟合。
协议声明统计单位是**数据种子**，初始化在种子内取中位。

但报告同时给出了"24/24 胜出，p = 5.96e-08"。
该数字等于 $2^{{-24}}$，即把 24 个相关拟合当成 24 个独立单位。
同一份汇总文件又写着 `statistical_unit: data_seed`。
两者不可能同时作为主推断。

## 三层结果（各自声明聚合单位）

### 第一层：逐拟合（**不主张独立性**）

| 量 | 值 |
|---|---|
| 计划 / 观测 / 有效 | {fit['fits_planned']} / {fit['fits_observed']} / {fit['fits_valid']} |
| 改善拟合数 | {fit['fits_improved']} / {fit['fits_valid']} |
| 中位 E_raw | {fit['median_E_raw']:.4g} |
| 中位 E_SAEPS | {fit['median_E_SAEPS']:.4g} |
| 中位数之比 | {fit['ratio_of_medians']:.1f} |
| 配对比值中位数 | {fit['median_paired_ratio']:.1f} |

这是**描述性**结果。24 个拟合不是 24 个独立数据集。

### 第二层：每档噪声内（种子级）

| 噪声 | 独立单位 | 有效拟合 | 种子改善 | 一侧符号检验 p |
|---|---|---|---|---|
""" + "\n".join(
        f"| {k} | {v['independent_units']} | {v['fits_valid']} | {v['seeds_improved']} | {v['one_sided_sign_test_p']:.6g} |"
        for k, v in sorted(layers.items(), key=lambda kv: float(kv[0]))
    ) + f"""

两档噪声**共享同 6 个种子**，彼此不独立，不能合并成 12 个独立单位。

### 第三层：数据种子级（**主推断**）

| 量 | 值 |
|---|---|
| 独立单位 | {seed['independent_units']} |
| 改善单位 | {seed['units_improved']} |
| **一侧符号检验 p** | **{seed['one_sided_sign_test_p']:.6g}** |
| 中位 E_raw | {seed['median_E_raw']:.4g} |
| 中位 E_SAEPS | {seed['median_E_SAEPS']:.4g} |
| 中位数之比 | {seed['ratio_of_medians']:.1f} |
| 配对比值中位数 | {seed['median_paired_ratio']:.1f} |

`{seed['noise_aggregation']}`

## 结论

- "24/24 拟合改善"**保留为描述**。
- "6/6 数据种子改善"才是**对应独立单位**的陈述，一侧符号检验 p = **{seed['one_sided_sign_test_p']:.6g}**。
- 改善结论仍然成立，但没有原报告暗示的统计强度。原报告的 p 值低估了约 {abs(math.log10(seed['one_sided_sign_test_p']) - math.log10(2**-24)):.1f} 个数量级。
- 两个改善倍数（中位数之比 {seed['ratio_of_medians']:.1f} 与配对比值中位数 {seed['median_paired_ratio']:.1f}）**分别报告，不得互相替换**。

## 汇总文件命名

此前 `e3_cluster_summary.json` 实际是对全部有效拟合取中位数，属**逐拟合**口径
（中位 E_raw 16.80049、中位 E_SAEPS 0.00124664），而报告引用的是**种子级**数字
（16.8165、0.0010603）。差别源于聚合方式不同，不是数据问题；问题在于文件名与统计口径未统一。

现拆分为两个明确命名的文件：

- `fit_level_summary.json`（`aggregation_unit = fit`）
- `data_seed_level_summary.json`（`aggregation_unit = data_seed`）

每个数字都带 `aggregation_unit` 声明。论文主表使用哪一种必须写明。

## 成员核对

- 重复身份：{len(document['membership_duplicates'])} 个
- 缺失身份：{len(document['membership_missing'])} 个
- 计划外身份：{len(document['membership_unexpected'])} 个

计划身份从冻结协议读取，**不是**从成功运行反推，因此分母不随失败而缩小。
"""


if __name__ == "__main__":
    main()
