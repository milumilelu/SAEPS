# Phase 2 actual execution report

**未实际补算：E0-C 的 14 个历史状态/完整块缺失。条件停止位置：{"E2": 20, "E3": 160, "E4C": 0, "E5C": 4, "E6P": 25, "E4D": 0, "E6D": 0, "E1": 0, "E5AB": 0}。**

E1 独立 scalar 结论：PARTIALLY_SUPPORTED。burgers valid 0/10、SO 严格胜出 0/10；allen_cahn valid 0/10、SO 严格胜出 0/10.

E2：0/20 roots 实际分析，Gate C 通过 0，E3 可用 0。失败/截尾不能解释成物理分支不存在。

E3：实际候选 0/160，有效 0，接受 0；完整双侧配对 roots 0/20，SO 实际下降严格胜出 0/20。

E4-C：PARTIALLY_SUPPORTED，valid 0/10，Frobenius wins 0/10。旧 V5 裁决保持原样。

E5：四中心 MF/AD 工程核验通过；大规模 cost-only 完成有效计时 40/45。

E6-D k=8 oracle 有效度中位数 66.3405，门槛 3；E6-P 放行=False。当前证据不支持实用的低成本误差认证。

累计 Phase2 实测活动 1634.471 秒；中断上界估计另列 0.000 秒。最终聚合/绘图耗时另见 VALIDATION.json。

所有图、表、正文数值同源于 final/SUMMARY.json 和原始 run manifests。训练失败、数值失败和开发修复前尝试全部保留。

## Reporting audit

独立比较有效根为 0/30；PARTIALLY_SUPPORTED 是冻结规则的可用性不足分类，不表示 SO 已获得独立支持。失败根的诊断曲率不能进入科学主比较。

E5-C: {"planned": 45, "valid": 40, "failed_started": 1, "not_started": 4, "planned_cells": 9, "completed_cells": 8}。冷启动因 resource_limit 中断；warmup 和三次 steady 未启动，numerical_status=null。无实验重跑。

成本是已记录活动之和，不是整个会话耗时。原最终聚合/绘图 3.6062862999970093 秒另列；早期未计时命令、下载等待、模型推理未计入。历史重构单列。
