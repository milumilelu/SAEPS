# SO-ADAPT 失败拆分（事后真实误差 vs 数值估计判定）

run_id=day2; experiment_id=P1B_A; 父提交 acf848f；容差 0.1（继承第一阶段 adaptive_tolerance）。

## 判据口径（继承原任务书，不得偷换）

- 数值估计判定（算法侧）：有限对角 PCG 修正使用条件谱界 U=||D||²/μ；当 f=||F_SO||>U 时
  用 U/(f−U)≤0.1 判定，`refine()` 返回 `numerical_tolerance_met`。普通 dense eigh 的
  μ 是数值估计（`mu_source=dense_eigh_with_numerical_margin`），**不是严格证书**。
- 事后真实误差（独立参考侧）：E=|F_SO^refined−F_*|，真实相对误差 E/(||F_*||+1e-8)≤0.1。
  参考为独立代数 Schur 解，与候选、缺陷能量输入无关。
- 无法分辨参考尺度的记录：0 条（全部 21 条 |F_*| 远高于分辨率）。

## 四格计数（21 个可比矩阵中心）

| 数值估计判定 | 事后真实误差 | 计数 | 中心 |
|---|---|---:|---|
| 通过 | 通过 | 9 | allen_cahn_75, allen_cahn_76, allen_cahn_77, allen_cahn_78, allen_cahn_79, allen_cahn_80, allen_cahn_82, allen_cahn_83, burgers_55 |
| 不通过 | 通过 | 12 | allen_cahn_84, burgers_56, burgers_58, burgers_59, burgers_60, burgers_62, burgers_64, burgers_65, burgers_66, burgers_67, burgers_68, burgers_69 |
| 不通过 | 不通过 | 0 | 无 |
| 通过 | 不通过 | 0 | 无 |

**结论：真实相对误差 21/21 全部达标（中位数 0.00202）；"9/21 达到容差"
纯粹是数值界过松造成的估计侧假阴性。** 按任务书第 7 节口径：瓶颈在估计实用性，不在近似精度；
不得宣称 SO-ADAPT 在 12 个中心精度失败；不存在"估计通过而真实未通过"的一致性警报象限。

## 界为何松（稠密矩阵上的机制分析，仅离线诊断）

- 界 U=||D||²/μ 用的是 A 的最小特征值（μ≈λ_min−margin），而缺陷能量 q=DᵀA⁻¹D 由 D 实际
  加权的方向决定。定义 D 加权有效特征值 μ_eff=||D||²/q，则界过松倍数=U/E=μ_eff/μ。
- 21 中心中位数：μ_eff=2703.44，λ_min 方向承载 D 的能量占比中位数
  3.25e-05（≈0），界有效度（U/E）中位数 227002。
- 即：最小特征值方向几乎不承载 D 的能量，谱条件数（最大 cond(A)=1.01e+08）
  通过 λ_min 直接惩罚 U。这是谱界对"缺陷能量集中于高特征值方向"这一常态的已知保守性。
- 每条记录字段：`mu_source`、`bound_status`、`dense_assisted=True`、`oracle_spectral_used=False`
  （未使用任何 oracle 谱信息；dense eigh 数值估计仅用于诊断与算法内停止，不是严格认证）。
- 谱分解仅用于本离线机制分析，成本单列（本脚本 analysis_side_spectrum_seconds），不输入任何
  实用停止器后宣称矩阵无关。

原始逐行数据见 `ADAPT_FAILURE_SPLIT.csv`；第一阶段原始自适应轨迹（101 点/中心）保存在
`../day1/raw/*.json`，未修改。
