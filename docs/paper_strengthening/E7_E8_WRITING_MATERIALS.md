# E7/E8 补强实验写作素材

本文件只汇总本次独立 development/rescue 轨道的机器结果，不改写原 E7、V5 或锁定 confirmation 结果。

## E7：修正 solver 后得到的证据

配置：[`e7_profile_rescue_v2.yaml`](../../configs/paper_strengthening/e7_profile_rescue_v2.yaml)。固定原锚点、原 gamma、三个步长 `0.01/0.003/0.001`，每个正负分支从 implicit-function prediction 和 anchor 两个独立起点启动。求解器把 LBFGS raw-gradient stopping 与 residual-normalised acceptance 分开，并追加 safeguarded Newton polish；只有同时满足 stationarity、positive Hessian、目标误差界、双起点一致性和固定三尺度 (h^2) 拟合的记录才计入 certificate。

| 项目 | 结果 |
|---|---:|
| 计划中心 / profile 点 | 3 / 9 |
| 独立起点记录 | 36 |
| strict raw fallback 记录 | 15/36 |
| 点级 certificate | 5/9 |
| 完整三尺度 profile certificate | 0/3 |

中心级结果：

- `916101`：3/3 点级通过；三尺度 (h^2) 拟合截距 `1.47505`，参考 `1.67923`，(R^2=0.404)，相对误差 `12.2%`，因此不通过完整 profile certificate。
- `916102`：2/3 点级通过；一个中间步长出现独立起点不一致/非正定 Hessian，不能静默选取较低目标值的一支。
- `916103`：0/3 点级通过；严格 fallback 后 displaced branches 仍未形成两个起点共同到达的正定 stationary branch。

可用于正文的结果句：

> We repeated the finite-displacement calculation with a solver whose stopping metric is dimensionally consistent with the reported residual-normalised gradient, followed by safeguarded Newton polishing and independent-start checks. The corrected path produced five certified profile points out of nine, but no centre passed the predeclared three-scale (h^2) profile certificate. The remaining failures separate into finite-displacement curvature drift (916101), branch/basin and positive-Hessian failure (916102), and displaced-branch stationarity failure (916103).

可用于 Discussion 的解释句：

> The original short-budget result therefore contained a real optimisation component, but increasing the budget and correcting the stopping semantics did not restore nonlinear-profile equivalence. At the certified 916101 centre, the finest-scale curvature moved away from the local Schur reference after objective-error control, indicating that the earlier agreement at that scale was partly an (h^{-2})-amplified optimisation-error cancellation.

边界：不能写成“profile convergence established”“SAEPS predicts the nonlinear profile”或“0/21 was merely an over-strict gate”。原始 E7 的 `0/21` 和 V5 的 `1/5` 仍是历史结果。

机器结果：[`e7_rescue_v2_summary.json`](../../outputs/posthoc/paper_strengthening/e7_rescue_v2_summary.json)，明细在三个 `e7_rescue_v2_seed*_final2` 目录；报告见 [`E7_RESCUE_V2_REPORT.md`](E7_RESCUE_V2_REPORT.md)。

## E8：matched-α operator audit

配置：[`e8_matched_alpha_audit.yaml`](../../configs/paper_strengthening/e8_matched_alpha_audit.yaml)。在同一个小型 coupled reaction-diffusion checkpoint（seed 215）上，显式 dense、matrix-free CG 和 scaled LSQR 在每个 (gamma=alphalambda_{max}) 下都与同 gamma 的 dense Cholesky reference 比较。

| (alpha) | 通过 | 最大 verified residual | 最大 dense difference |
|---:|---:|---:|---:|
| (10^{-8}) | 3/3 | (7.01\times10^{-11}) | (2.99\times10^{-8}) |
| (10^{-6}) | 3/3 | (5.02\times10^{-11}) | (2.33\times10^{-9}) |
| (10^{-4}) | 3/3 | (5.61\times10^{-11}) | (2.15\times10^{-10}) |
| (10^{-2}) | 3/3 | (6.20\times10^{-11}) | (2.64\times10^{-11}) |

可用于正文或补充材料的结果句：

> On a small coupled checkpoint, explicit, matrix-free CG and scaled LSQR agreed with a same-γ dense reference across (alpha\in\{10^{-8},10^{-6},10^{-4},10^{-2}\}): all 12 operator records passed, with maximum verified residual (7.01\times10^{-11}) and maximum relative difference (2.99\times10^{-8}).

边界：该 audit 支持“matrix-free operator agreement across the tested damping grid”，不支持把 (alpha=10^{-2}) 的 100001-state cost run 写成 (alpha=10^{-8}) 的大网络 accuracy 结果，也不支持 trained large-network efficacy 或 speedup claim。

机器结果：[`e8_matched_alpha_summary.json`](../../outputs/posthoc/paper_strengthening/e8_matched_alpha_summary.json)，报告见 [`E8_MATCHED_ALPHA_AUDIT.md`](E8_MATCHED_ALPHA_AUDIT.md)。

## 统一主张边界

本轮补强后，最强有证据支持的表述仍是：SAEPS 是一个 checkpoint-dependent、finite-damping、local residual-space state-elimination diagnostic；它的 exact finite-γ local curvature comparison 和同 gamma matrix-free implementation 有可复现证据。有限位移 nonlinear-profile equivalence 仍未建立，因此不能用本轮结果恢复该更强主张。
