# Phase 2 actual execution report

**未实际补算：E0-C 的 14 个历史状态/完整块缺失。条件停止位置：{"E2": 20, "E3": 160, "E4C": 0, "E5C": 0, "E6P": 25, "E4D": 0, "E6D": 0, "E1": 0, "E5AB": 0}。**

E1 独立 scalar 结论：PARTIALLY_SUPPORTED。burgers valid 0/10、SO 严格胜出 0/10；allen_cahn valid 0/10、SO 严格胜出 0/10.

E2：0/20 roots 实际分析，Gate C 通过 0，E3 可用 0。失败/截尾不能解释成物理分支不存在。

E3：实际候选 0/160，有效 0，接受 0；完整双侧配对 roots 0/20，SO 实际下降严格胜出 0/20。

E4-C：PARTIALLY_SUPPORTED，valid 0/10，Frobenius wins 0/10。旧 V5 裁决保持原样。

E5：四中心 MF/AD 工程核验通过；大规模 cost-only 完成有效计时 40/45。

E6-D k=8 oracle 有效度中位数 66.3405，门槛 3；E6-P 放行=False。当前证据不支持实用的低成本误差认证。

累计 Phase2 实测活动 1600.673 秒；中断上界估计另列 0.000 秒。最终聚合/绘图耗时另见 VALIDATION.json。

所有图、表、正文数值同源于 final/SUMMARY.json 和原始 run manifests。训练失败、数值失败和开发修复前尝试全部保留。
