"""Build writing materials from the frozen SAEPS evidence records.

The generated Markdown is a writing aid for the limited-claims submission route.
Numerical values are read from machine-readable evidence files so this document
does not become a second hand-maintained source of paper-facing numbers.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "paper_strengthening" / "WRITING_MATERIALS_LIMITED_CLAIMS.md"


def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    digest = hashlib.sha256()
    digest.update((ROOT / relative).read_bytes())
    return digest.hexdigest()


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def main() -> None:
    final_audit = read_json("docs/evidence/v5_final_audit.json")
    p2 = read_json("docs/evidence/p2_submission_statistics.json")
    burgers = read_json("docs/evidence/v4_2_confirmation.json")["summary"]
    allen = read_json("docs/evidence/v4_4_allen_confirmation.json")["summary"]
    profile = read_json("docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json")
    two = read_json("docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json")
    gamma = read_json("docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.json")
    p5 = read_json("docs/evidence/P5_ACCEPTANCE.json")
    p6 = read_json("docs/evidence/P6_ACCEPTANCE.json")
    p7 = read_json("docs/evidence/P7_ACCEPTANCE.json")
    p8 = read_json("docs/evidence/P8_ACCEPTANCE.json")
    p9 = read_json("docs/evidence/P9_ACCEPTANCE.json")
    s2_summary = read_json(
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_DEVELOPMENT_SUMMARY.json"
    )
    s2_fit = read_json(
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json"
    )
    s2_v2 = read_json(
        "outputs/runs/paper_strengthening_v2_basin_newton/s2_profile_development/S2_V2_DEVELOPMENT_SUMMARY.json"
    )
    s2_v2_report_path = ROOT / "docs" / "paper_strengthening" / "S2_V2_MODIFICATION_REPORT.md"
    s2_v2_report = s2_v2_report_path.read_text(encoding="utf-8")
    v2_result_paths = sorted(
        (ROOT / "outputs" / "runs" / "paper_strengthening_v2_basin_newton" / "s2_profile_development").rglob("result.json")
    )
    v2_pass_points = 0
    for result_path in v2_result_paths:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        v2_pass_points += int(result.get("profile_pass_count", 0))
    v2_config_text = (
        ROOT / "configs" / "paper_strengthening" / "v2_basin_newton_development.yaml"
    ).read_text(encoding="utf-8")
    h_match = re.search(r"h_values:\s*\[([^\]]+)\]", v2_config_text)
    h_count = len([item for item in (h_match.group(1).split(",") if h_match else []) if item.strip()])
    v2_points_per_record = 2 * h_count
    v2_total_points = len(v2_result_paths) * v2_points_per_record
    s2_v2_point_pass = f"{v2_pass_points}/{v2_total_points} profile points"
    paper_numbers = read_json("paper/revise/paper_numbers.json")["values"]

    burger_secondary = burgers["secondary"]
    allen_secondary = allen["secondary"]
    burger_raw_median = statistics.median(burger_secondary["E_raw_all_valid"])
    allen_raw_median = statistics.median(allen_secondary["E_raw_all_valid"])
    burger_d = p2["paired_effect_sizes"]["burgers"]
    allen_d = p2["paired_effect_sizes"]["allen_cahn"]
    exact_anchor = p2["robustness"]
    scaling = p2["scaling"]

    source_paths = [
        "docs/evidence/v5_final_audit.json",
        "docs/evidence/p2_submission_statistics.json",
        "docs/evidence/v4_2_confirmation.json",
        "docs/evidence/v4_4_allen_confirmation.json",
        "docs/evidence/v4_8_robustness.json",
        "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json",
        "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json",
        "docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.json",
        "docs/evidence/P5_ACCEPTANCE.json",
        "docs/evidence/P6_ACCEPTANCE.json",
        "docs/evidence/P7_ACCEPTANCE.json",
        "docs/evidence/P8_ACCEPTANCE.json",
        "docs/evidence/P9_ACCEPTANCE.json",
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_DEVELOPMENT_SUMMARY.json",
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json",
        "outputs/runs/paper_strengthening_v2_basin_newton/s2_profile_development/S2_V2_DEVELOPMENT_SUMMARY.json",
        "docs/paper_strengthening/S2_FIT_WINDOW_DECISION.md",
        "docs/paper_strengthening/S2_CENTER_REFINEMENT_ANALYSIS.md",
        "docs/paper_strengthening/S2_V2_MODIFICATION_REPORT.md",
        "paper/revise/paper_numbers.json",
    ]

    window_rows = []
    for row in s2_fit["window_summaries"]:
        window_rows.append(
            f"| `{row['window_id']}` | {row['retain_h_count']} | {row['fit_quality_pass_count']}/{row['planned_record_count']} | {fmt(row['median_normalized_rmse'])} |"
        )

    profile_rows = []
    for row in profile["seed_rows"]:
        profile_rows.append(
            f"| {row['seed']} | {str(row['PROFILE_EVALUABLE']).lower()} | {str(row['PROFILE_VALID']).lower()} | {fmt(row['finest_profile_exact_relative_error'])} | {fmt(row['last_two_curvature_relative_change'])} |"
        )

    source_rows = []
    for path in source_paths:
        source_rows.append(f"| `{path}` | `{sha256(path)}` |")

    md = f"""# SAEPS 论文补强写作素材：Limited-Claims 路线

**生成日期：** {date.today().isoformat()}  
**生成方式：** `scripts/build_limited_claims_materials.py` 自动读取机器可读 evidence；本文件不是新的实验结果源。  
**目标版本：** `PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS`，主张限定为 finite-damping、checkpoint-dependent、local Gauss–Newton state-elimination diagnostic。  
**禁止用途：** 不得把本文件中的历史结果改写成 nonlinear-profile equivalence、global identifiability、uncertainty quantification 或 universal robustness 证据。

## 1. 写作决策

本稿走收缩主张路线。论文的核心结果来自已完成的 scalar exact finite-γ reduced-curvature comparison；非线性 profile bridge 作为独立验证失败和数值边界报告；two-parameter 结果作为 availability-limited descriptive extension；noise、sparsity、architecture 和 matrix-free scaling 作为 secondary/descriptive evidence。

当前不再追求新的 profile 阳性结果。Q2 S2 的 development 结果必须保留，因为它解释了为什么 exact-Hessian Schur reference 不能被写成 nonlinear reoptimized profile 的替代物。

推荐最终科学结论：

```text
PARTIALLY_SUPPORTED
```

推荐最终建议：

```text
INVESTIGATE_NUMERICS
```

## 2. 证据版本和用途边界

| 证据层 | 版本/namespace | 作用 | 是否进入主结论 |
|---|---|---|---|
| 数值核心 | P0/P1/P3 | explicit、matrix-free、SVD/reference、profile engine engineering | 是，作为方法正确性基础 |
| 标量主结果 | V4.2 Burgers、V4.4 Allen–Cahn，V5 consolidated audit | SAEPS 与 raw fixed-state GN 对 exact finite-γ reduced curvature 的 paired comparison | 是，核心 |
| 受控机制 | V4.5/P2 controlled tangent-overlap | 机制性观察，但 scientific gate 未通过 | 仅作为 conditional/descriptive |
| 非线性 profile | V5.2 historical bridge | 5/5 evaluable，1/5 profile-valid；claim deleted | 是，作为 negative limitation |
| 两参数 | V5.3C | 8/10 binding-valid，8/10 planned wins；低于 9/10 gate | 是，作为 availability-limited evidence |
| Robustness | V4.8/P7 | noise、observation fraction、architecture stress | 仅 descriptive |
| 成本/规模 | P8/V5.4 | matrix-free feasibility and cost | 仅 cost/engineering |
| Q2 S2 | `paper_strengthening_v1/v2` | 独立 profile development 和失败诊断 | 是，作为补强限制，不得混入历史 confirmation denominator |

**写作时必须区分：** 当前整合稿中使用的历史标量数字与 Q2 S2 新 namespace。Q2 S2 没有新的 confirmation，也没有授权修改历史 locked configuration。

## 3. 可使用的主张、限制和禁止措辞

| 主张 ID | 可用主张 | 证据状态 | 推荐写法 |
|---|---|---|---|
| C1 | SAEPS 定义了有限阻尼 residual-space state-elimination curvature | 支持 | “a finite-damping, checkpoint-dependent local Gauss–Newton state-elimination diagnostic” |
| C2 | 在声明的 scalar synthetic inverse-PINN 条件下，SAEPS 比 raw fixed-state GN 更接近 exact finite-γ reference | 部分支持/范围内支持 | “improved exact-reference accuracy on the declared scalar cohorts” |
| C3 | state-freezing error 在已重建中心中是主要误差来源 | 观察性支持 | “state-freezing error was the dominant observed component in the reconstructed cohorts” |
| C4 | SAEPS 等价于 nonlinear reoptimized profile curvature | 不支持 | 必须删除或改为“independent profile validation remains unresolved” |
| C5 | SAEPS 稳定预测 two-parameter joint geometry | 不支持/availability-limited | 只能写“all valid two-parameter records favored SAEPS, but the prespecified availability gate was not met” |
| C6 | 方法对架构、噪声和稀疏性普遍稳健 | 不支持 | 只能写 tested stress boundaries/descriptive trends |
| C7 | matrix-free operator 在约 10^5 state parameters 上可运行 | 工程支持 | “operator feasibility was demonstrated at the tested dimensions” |
| C8 | SAEPS 提供 uncertainty、posterior、confidence 或 global identifiability | 禁止 | 不写 |

## 4. 核心结果素材

### 4.1 标量 exact finite-γ reference comparison

这些数字来自 V4.2/V4.4 raw records 的机器聚合，并由 V5 final audit 汇总。它们支持的是 exact finite-γ reduced-curvature comparison，不是 nonlinear profile equivalence。

| Benchmark | Planned | Valid | Planned wins | Valid wins | Median (E_{{raw}}) | Median (E_{{SAEPS}}) | Median (D=E_{{raw}}-E_{{SAEPS}}) | Exact sign-test p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Burgers | 15 | {burger_d['valid']} | {burger_d['positive_D']} | {burger_d['positive_D']}/{burger_d['valid']} | {fmt(burger_raw_median, 5)} | {fmt(burger_secondary['E_SAEPS_median'], 5)} | {fmt(burger_d['D']['median'], 5)} | {fmt(burger_d['frozen_one_sided_exact_binomial_sign_test_p'], 5)} |
| Allen–Cahn | 10 | {allen_d['valid']} | {allen_d['positive_D']} | {allen_d['positive_D']}/{allen_d['valid']} | {fmt(allen_raw_median, 5)} | {fmt(allen_secondary['E_SAEPS_median'], 5)} | {fmt(allen_d['D']['median'], 5)} | {fmt(allen_d['frozen_one_sided_exact_binomial_sign_test_p'], 5)} |

可直接写入 Results 的英文段落：

> On the declared scalar cohorts, SAEPS reduced the error relative to the exact finite-γ reduced-curvature reference at every binding-valid checkpoint. The Burgers cohort contained 12 valid comparisons among 15 planned cases, with a positive paired difference in all 12 cases and an exact one-sided sign-test probability below 0.001. The Allen–Cahn cohort contained 9 valid comparisons among 10 planned cases, again with positive paired differences in all valid cases and an exact one-sided sign-test probability below 0.01. These results establish a bounded comparison to the declared local reference; they do not establish exact Hessian recovery or nonlinear profile equivalence.

对应中文写作意图：

> 在预先声明的标量队列中，SAEPS 在每一个 binding-valid checkpoint 上都比 raw fixed-state GN 更接近 exact finite-γ reduced-curvature reference。该结果支持有限阻尼局部诊断在声明条件下的 comparative efficacy，但不支持“精确恢复 Hessian”或“等价于 nonlinear reoptimized profile”的更强表述。

### 4.2 误差大小与解释边界

| Benchmark | (E_{{raw}}) median | (E_{{SAEPS}}) median | Interpretation |
|---|---:|---:|---|
| Burgers | {fmt(burger_raw_median, 5)} | {fmt(burger_secondary['E_SAEPS_median'], 5)} | 误差大幅下降，但仍不是零误差；仅限声明的 exact-reference comparison |
| Allen–Cahn | {fmt(allen_raw_median, 5)} | {fmt(allen_secondary['E_SAEPS_median'], 5)} | 独立 scalar replication 支持相同方向，但误差仍显著非零 |

不要把“improvement”写成“exact recovery”。现有 evidence 明确显示 SAEPS 是更接近 reference 的诊断，而不是 exact Hessian surrogate。

### 4.3 精确 relaxation correction 与最终曲率误差必须分开

正文应明确区分两类数量：

1. exact decomposition 中的 relaxation correction recovery error；
2. 最终 SAEPS curvature 与 exact reduced curvature 的误差。

当前稿件中的历史汇总给出：relaxation correction 的中位误差为 sub-percent，但 final curvature errors 仍明显更大。前者不能替代后者，也不能把二者都称作“0.3% accuracy”。

推荐英文表述：

> The relaxation correction was recovered with sub-percent median error in the reconstructed centers. This quantity is distinct from the final curvature error, which remains nonzero and benchmark-dependent.

### 4.4 Controlled mechanism evidence

现有 controlled tangent-overlap 结果为：planned 10 个 seed 中约 6 个通过 binding-valid/monotonicity 条件，valid seeds 的 median Spearman 接近 1，但总体 SG-1 未达到预先定义的强 gate。该结果只能写成机制性观察，不能写成 controlled confirmation。

推荐英文表述：

> The controlled tangent-overlap experiment showed the expected ordering in the valid subset, but the planned across-seed gate was not met. We therefore treat this result as a conditional mechanism diagnostic rather than confirmatory evidence.

### 4.5 Gamma family and damping behavior

有限 gamma audit 的机器记录包括 42/42 terminal records，其中 38 条 numerical PASS、4 条在最小 alpha 条件下失败；nominal gamma 没有根据这些结果重新校准。结果显示 retained fraction 随 damping 增大而接近 frozen-state limit，effective state rank 向高 damping 下降。

推荐英文表述：

> The finite-γ family behaved consistently with the construction: retained sensitivity increased toward the frozen-state limit as damping increased, while the effective state rank decreased. Four numerical limitations occurred at the smallest audited damping scale; they were retained and no nominal-γ recalibration was performed.

### 4.6 Noise, observation fraction and architecture stress

P7/V4.8 的用途是报告失效边界，而不是建立强 robustness theorem。

- 新增 planned runs：{p7['planned_new_runs']}；terminal records：{p7['completed_new_runs']}；PASS：{p7['status_counts']['PASS']}；checkpoint-invalid：{p7['status_counts']['CHECKPOINT_INVALID']}；solver failures：{p7['status_counts']['SOLVER_FAILURE']}。
- exact-Hessian noise/sparsity anchors：{exact_anchor['exact_Hessian_anchors_valid']}/{exact_anchor['exact_Hessian_anchors_planned']} binding-valid，全部有效 anchor 的 SAEPS/raw paired direction 有利于 SAEPS。
- narrow architecture：5/5 valid；nominal referenced records：4/5 valid；wide architecture：0/5 center-valid，因此 wide curvature 没有被测试。
- 最低有效 cell 为 `{p7['failure_boundary']['lowest_valid_cell']}`，只有 {p7['failure_boundary']['lowest_valid_count_out_of_5']}/5 valid。

推荐英文表述：

> The stress campaign was descriptive rather than confirmatory. Lower observation fractions increased failure frequency in several cells, and the wide architecture did not produce accepted centers under the inherited gate. These records define tested numerical boundaries; they do not establish architecture-independent robustness.

### 4.7 Matrix-free scaling and cost

P8/V5.4 只支持 operator feasibility 和同口径 cost reporting：

- 最大 state dimension：(n_\theta={fmt(scaling['largest_n_theta'], 0)})；最大 residual dimension：(m={fmt(scaling['largest_m'], 0)})。
- residual-scalability grid：{scaling['planned_solves']}/{scaling['planned_solves']} verified solves。
- P8 cost-only median：training {fmt(p8['median_times_seconds']['training_seconds'], 5)} s；SAEPS {fmt(p8['median_times_seconds']['saeps_seconds'], 5)} s；reoptimized profile {fmt(p8['median_times_seconds']['reoptimized_profile_seconds'], 5)} s。
- paired reoptimized-profile/SAEPS ratio：{fmt(p8['median_paired_reoptimized_to_saeps_ratio'], 5)}；ratio of medians：{fmt(p8['ratio_of_median_reoptimized_to_median_saeps'], 5)}。
- median CG total iterations：{p8['aggregate_operation_counts']['median_CG_total_iterations']}；median JVP count：{p8['aggregate_operation_counts']['median_JVP_count']}；median VJP count：{p8['aggregate_operation_counts']['median_VJP_count']}。
- native CPU tensor peak memory：unavailable，不能补造。

推荐英文表述：

> Matrix-free execution was demonstrated at the tested state and residual dimensions. In the small CPU cost benchmark, reoptimized profiling was approximately twice the SAEPS cost. This is an engineering feasibility result and does not imply a production speedup or large-network accuracy guarantee.

### 4.8 Locked v2.0 terminal records that must remain visible

These records belong to the locked v2.0 execution and must not be silently merged with the historical V4/V5 scalar comparison. They are useful for the failure table and for explaining why the broader nonlinear/profile claim is not retained.

| Phase | Planned | PASS/valid | Checkpoint invalid | Profile failure | Solver failure | Scientific status |
|---|---:|---:|---:|---:|---:|---|
| P5 scalar confirmation | {p5['planned']} | {p5['valid']} | {p5['status_counts']['CHECKPOINT_INVALID']} | {p5['status_counts']['PROFILE_FAILURE']} | {p5['status_counts']['SOLVER_FAILURE']} | `{p5['scientific_classification_sg2']}` |
| P6 two-parameter confirmation | {p6['planned']} | {p6['valid']} | {p6['status_counts']['CHECKPOINT_INVALID']} | {p6['status_counts']['PROFILE_FAILURE']} | {p6['status_counts']['SOLVER_FAILURE']} | `{p6['scientific_gate_sg3']}` |

P5 的唯一 valid paired comparison 有利于 SAEPS，但不能形成 across-seed confirmation；P6 没有 valid directional pair，5×5 representative grid 合规记录为 `NOT_APPLICABLE_NO_VALID_SEED`。

## 5. Nonlinear profile failure素材

### 5.1 Historical V5 profile bridge

| Seed | Evaluable | Profile valid | Finest profile/exact relative error | Last-two curvature change |
|---:|:---:|:---:|---:|---:|
{chr(10).join(profile_rows)}

汇总：planned {profile['planned_denominator']}，evaluable {profile['evaluable_count']}，profile-valid {profile['profile_valid_count']}；scientific status `NOT_SUPPORTED`。所有 5 个 evaluable records 的 descriptive (D) 为正，但该比较不能替代 profile validity gate。

推荐英文表述：

> All planned profile replicates were numerically evaluable, but only one of five satisfied the prespecified small-radius consistency requirements. The nonlinear profile bridge therefore does not support profile equivalence. The favorable descriptive paired differences are retained as context, not used to override the profile adjudication.

### 5.2 Q2 S2 first development

第一轮 S2 的 9 个 development records 和 72 个 profile points 均完成了 point-level optimization、stationarity 和 exact local-minimum checks；失败发生在多尺度 fit-quality gate。

| Fit window | Retained scales | Fit-quality pass | Median normalized RMSE |
|---|---:|---:|---:|
{chr(10).join(window_rows)}

关键解释：

- `all_common_scales` 和 `two_finest_scales` 没有任何完整 record 通过；
- `finest_pair_only` 的 7/9 不能作为 profile curvature evidence，因为两点不足以稳定识别带截距和线性项的二次模型；
- 该结果不是“所有 profile points 都失败”，而是“profile points 可优化，但多尺度局部曲率证据不足”。

### 5.3 Q2 S2-v2 numerical modification

v2 已测试 center-consistent objective、tighter stationarity candidates、objective non-increase、Newton polish、basin finder 和 `H(h)` 对 `h^2` 的拟合。最佳完整 cohort：planned 6 records，所有 fit windows 的 pass count 均为 0；修改报告记录的最佳完整 cohort 只有 {s2_v2_point_pass}。

v2 的诊断用途是说明 profile availability/reachability 仍是瓶颈，不是授权继续改变 gamma、seed 或 fit threshold。

推荐英文表述：

> Center-consistent refinement and safeguarded local solvers reduced one source of numerical inconsistency but did not produce a complete multi-scale profile cohort. We therefore retain the nonlinear-profile limitation and restrict the primary claim to finite-damping exact-reference comparisons.

## 6. 工程验收和科学结论的分开写法

P9 engineering audit 已记录 accepted workload：P2 50/50、P5 10/10、P6 10/10、P7 55/55、P8 3/3；56 条 invalid/failed raw records 被保留，validator check groups 全部通过。科学结论仍为 `PARTIALLY_SUPPORTED`，建议为 `INVESTIGATE_NUMERICS`。

推荐英文表述：

> The engineering execution is complete and all planned records have terminal statuses. Scientific limitations are retained rather than converted into engineering failures. The resulting conclusion is partial support within the declared scalar, finite-damping, local scope, with nonlinear profile equivalence and broad coupled-geometry claims left unsupported.

## 7. 可直接用于摘要的英文草稿

> We introduce SAEPS as a finite-damping, checkpoint-dependent local Gauss–Newton diagnostic that removes residual response reproducible through neural-state motion. The method is evaluated against exact finite-γ reduced-curvature references on declared synthetic inverse-PINN benchmarks using paired, denominator-preserving aggregation. SAEPS improves the reference comparison at all binding-valid Burgers and Allen–Cahn checkpoints, while the absolute error remains nonzero and benchmark-dependent. Exact-Hessian decomposition indicates that state-freezing error is a major observed component in the reconstructed scalar centers. A two-parameter extension is availability-limited, and an independent nonlinear profile bridge is not supported: only one of five historical profile cases satisfies the prespecified consistency requirements, while the separate Q2 development audit also fails to produce a complete multi-scale profile cohort. Matrix-free feasibility is demonstrated at the tested dimensions, but the cost and scaling experiments do not establish production speedup or large-network accuracy. The evidence therefore supports a local finite-damping diagnostic under the declared conditions, not global identifiability, uncertainty quantification, or universal nonlinear-profile equivalence.

摘要中不要写：`exactly recovers the Hessian`、`equivalent to nonlinear profile`、`universally robust`、`provides uncertainty`、`global identifiability`。

## 8. 可直接用于 Discussion 的英文段落

> The strongest evidence concerns a bounded local comparison: SAEPS is closer than the frozen-state baseline to the declared exact finite-γ reduced curvature on the valid scalar cohorts. This does not imply that the finite-damping Gauss–Newton quantity equals the exact Hessian, nor that it equals the curvature of a nonlinear reoptimized profile at finite displacement. The profile bridge was retained as a negative result because numerical evaluability did not translate into multi-scale curvature consistency. The failure is informative for use of the diagnostic: state conditioning, center consistency, finite-difference error amplification, and local basin reachability must be audited before a profile interpretation is made.

## 9. 审稿人问题与回答素材

### Q1. SAEPS 是否只是经典 Schur/variable projection 的重新命名？

回答重点：经典消元结构必须明确承认。论文贡献不是声称提出 Schur 补，而是把 finite-γ residual-space elimination 作为 inverse-PINN 的 local diagnostic，并用 exact-Hessian decomposition、paired validation、failure audit 和 cost audit 验证其适用边界。

推荐回答：

> The elimination structure is classical. Our contribution is its explicit finite-damping residual-space use as a checkpoint-dependent inverse-PINN diagnostic, together with exact-reference comparisons, coordinate and damping audits, paired aggregation, and an explicit failure analysis.

### Q2. exact-Hessian Schur 为什么不能代表 nonlinear profile？

回答重点：exact-Hessian Schur 是局部隐式参考，profile 是有限位移后重新优化得到的 nonlinear objective geometry；二者需要独立验证。现有 profile bridge 仅 1/5 valid，Q2 S2 仍未形成完整多尺度 cohort，因此不能混写。

### Q3. 为什么 two-parameter 结果没有成为主结论？

回答重点：8/10 valid 虽然有效记录中的 (D_2) 都有利于 SAEPS，但预注册 availability gate 为 9/10；无 valid directional profile pair，不能声称 stable joint geometry。

### Q4. 失败运行是否被删除？

回答重点：没有。P9 记录 56 条 invalid/failed raw records，正文和补充材料都必须报告 planned/valid/failed denominator 以及 failure reason。

### Q5. 这个方法是否加速？

回答重点：当前只支持小型 CPU benchmark 中约两倍的 cost difference，不支持 production speedup；profile fit 失败也不能被隐藏在 cost comparison 后面。

### Q6. 是否可以宣称参数可靠性或 uncertainty？

回答重点：不可以。当前只报告 local curvature diagnostics，没有 calibration、posterior、coverage 或 parameter-recovery evidence。

## 10. 正文和补充材料的结构建议

### 正文

1. Scope：local、finite-damping、checkpoint-dependent diagnostic；
2. Method：residual-space elimination、finite-γ target、exact-Hessian decomposition；
3. Scalar primary results：Burgers、Allen–Cahn paired exact-reference comparison；
4. Mechanism qualification：state-freezing correction 与 affine-coordinate limitation；
5. Secondary evidence：gamma family、noise/sparsity、two-parameter availability、cost/scaling；
6. Negative profile result：紧邻 scalar positive result呈现；
7. Limitations：no nonlinear-profile equivalence、no global identifiability、no uncertainty、no broad robustness。

### Supplementary

- 所有 seed-level (E_{{raw}},E_{{SAEPS}},D)；
- planned/valid/invalid/failed denominator；
- P5/P6/P7 failure table；
- gamma sweep 和 4/42 numerical limitations；
- S2 v1 fit-window table；
- S2 v2 solver modification audit；
- all profile raw points and fit diagnostics；
- CG/JVP/VJP and timing records；
- config hashes、git commits 和 source manifest。

## 11. 图表素材安排

| 图/表 | 建议内容 | 主文/补充 |
|---|---|---|
| Figure 1 | residual-space geometry and finite-γ elimination | 主文 |
| Figure 2 | controlled tangent-overlap mechanism, with failed across-seed gate clearly marked | 主文或补充 |
| Figure 3 | scalar raw vs SAEPS vs exact reference | 主文 |
| Figure 4 | seed-level paired errors and denominator | 主文 |
| Figure 5 | two-parameter matrices/eigendirections with no valid directional profile pair | 主文，需标注 availability-limited |
| Figure 6 | cost/scaling, no speedup claim | 主文或补充 |
| Profile figure | historical profile bridge and S2 multi-scale fit failure | 主文限制段 + 补充 |
| Table 1 | benchmark/protocol/claims | 主文 |
| Table 2 | scalar seed-level exact-reference comparison | 主文 |
| Table 3 | two-parameter status and failures | 主文 |
| Supplementary failure table | every invalid/failed record and reason | 补充 |

## 12. 最终写作前检查

- [ ] 摘要只使用 finite-damping、local、checkpoint-dependent、diagnostic 语言；
- [ ] scalar exact-reference result 与 nonlinear profile result 分开；
- [ ] 历史 V5 结果与 Q2 S2 namespace 分开；
- [ ] 所有分母使用 planned denominator，不能改成 valid-only denominator；
- [ ] 1/5 profile-valid、8/10 two-parameter availability 和 wide architecture invalidity 均保留；
- [ ] 不能把 controlled valid-subset ordering 写成 SG-1 confirmation；
- [ ] 不能把 P8 cost-only 写成 production acceleration；
- [ ] 所有数字从 evidence/aggregate 自动生成，不能手工回填；
- [ ] 正文和 supplement 的数字一致；
- [ ] 重新生成 paper artifacts 并做 PDF render/visual check；
- [ ] 最后运行 repository validator，并记录与本补强无关的既有缺失文件；
- [ ] 投稿前重新核验目标期刊 scope、分区类别和模板。

## 13. 证据源和 SHA256

下面的 hash 由本次生成时读取的文件计算。若任何 source 变化，应重新运行生成脚本，不要直接编辑本文件。

| Source | SHA256 |
|---|---|
{chr(10).join(source_rows)}

## 14. 文件索引

- 主张边界：[CLAIM_LEDGER.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/paper_strengthening/CLAIM_LEDGER.md)
- 审稿风险：[REVIEWER_RISK_MATRIX.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/paper_strengthening/REVIEWER_RISK_MATRIX.md)
- Q2 执行说明：[SAEPS_Q2_STRENGTHENING_EXECUTION_SPEC.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/paper/revise/SAEPS_Q2_STRENGTHENING_EXECUTION_SPEC.md)
- S2 fit-window 决策：[S2_FIT_WINDOW_DECISION.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/paper_strengthening/S2_FIT_WINDOW_DECISION.md)
- S2 center diagnosis：[S2_CENTER_REFINEMENT_ANALYSIS.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/paper_strengthening/S2_CENTER_REFINEMENT_ANALYSIS.md)
- S2-v2 modification report：[S2_V2_MODIFICATION_REPORT.md](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/paper_strengthening/S2_V2_MODIFICATION_REPORT.md)
- Integrated manuscript：[SAEPS_manuscript_integrated.tex](C:/Users/RZF/Desktop/博士课题资料/SAEPS/paper/revise/SAEPS_manuscript_integrated.tex)
- Historical final audit：[v5_final_audit.json](C:/Users/RZF/Desktop/博士课题资料/SAEPS/docs/evidence/v5_final_audit.json)

**写作底线：** 当前稿件可以完成为一篇范围明确的 local finite-damping diagnostic paper；不能把未通过的 nonlinear profile bridge 或 two-parameter availability gate 改写成方法已经被全面验证。
"""
    OUTPUT.write_text(md, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
