# 恢复报告（P1B-B）

run_id=day2；固定流程重放（v1 重建路径未改动，仅增加状态导出与比对）；无 seed 替换、无重复重放。

## 预定清单（任务书 §3.1 规则，代码 p1b_recover.py::select_centers）

- 变差案例：burgers_59、burgers_67（预定）。
- 对照：burgers_55（GN 相对误差 0.0789617，距该 PDE 历史中位数 0.00393，并列候选 ['burgers_62', 'burgers_55']，按最低历史 ID 裁定）。
- 对照：allen_cahn_84（GN 相对误差 0.278567，距该 PDE 历史中位数 0，并列候选 ['allen_cahn_84']，按最低历史 ID 裁定）。

## 重放结果（每中心恰 1 次固定流程重放）

| 中心 | 状态 | 重放用时 | 冻结复现最大相对误差 | 与 day1 矩阵值最大相对误差 | center 门 | 数据逐位一致 | 检查点 |
|---|---|---|---|---|---|---|---|
| burgers_59 | historical_center_replayed | 219.3 s | 9e-12 | 5.75e-14 | True | 0.0 | state_checkpoint.npz |
| burgers_67 | historical_center_replayed | 36.88 s | 7.13e-12 | 8.55e-14 | True | 0.0 | state_checkpoint.npz |
| burgers_55 | historical_center_replayed | 69.57 s | 1.15e-11 | 3.72e-14 | True | 0.0 | state_checkpoint.npz |
| allen_cahn_84 | historical_center_replayed | 95.26 s | 5.56e-13 | 2.05e-14 | True | 0.0 | state_checkpoint.npz |

## 复现层级判定

- 4/4 达到 `historical_center_replayed`：冻结口径（rtol 1e-6 / atol 1e-10，继承 v3 协议）下F_raw / F_SAEPS(GN Schur) / H_red_exact 全部通过；与 day1 矩阵重算值逐块一致（≤8.6e-14）；center 平稳性门通过且 G_theta 与历史存档逐位相同；重建数据与训练闭包残差逐位一致（=0.0）。
- 未宣称逐张量历史恢复：历史训练时 RNG 状态不可得（存档中不存在），导出的是重放状态；与历史的一致性由上述冻结口径比对支撑，层级如实标注。
- 失败尝试 2 次（运行环境缺 float64 默认 dtype；导出段 retain_graph 缺陷）——原因、墙钟与不采用声明见 p1b_cost_ledger.json；未以任何方式替换 seed 或放宽门槛。

## 检查点内容（每中心 state_checkpoint.npz + provenance.json）

theta（打包顺序 wx/wt/hidden bias/output/output bias）、log λ 与物理 λ、网络架构/激活/dtype、全部配点与观测数据及噪声、正演真解、残差权重与归一化（runtime 配置内嵌+哈希）、固定 γ 及其构造规则（α·λ_max(G_tt)）、mean/sum 两种目标形式的状态与参数梯度张量、G/H 块、GN 响应 Z、重放导出时 torch RNG 状态（明确标注非历史训练态）、代码提交/协议/环境/设备/线程、父历史中心 ID 与全部文件 sha256。