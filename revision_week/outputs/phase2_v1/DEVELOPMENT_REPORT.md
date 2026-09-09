# Phase 2 开发验收实测报告

本文仅报告开发数据；独立 confirmation 尚未开始。

E0：21/25 历史中心可用，机制分类 {'appropriate': 19, 'wrong_direction': 1, 'overshoot': 1, 'unresolved': 0}。gamma 计划格 150。E0-C 14 个原始状态缺失，未补算。

二维开发：8/8 同时改善 Frobenius 和 spectral 误差；E4-C 放行=True。

Lanczos 终点 k=8：覆盖 21/21，有效度中位数 66.3405，90%分位 275.657；E6-P 放行=False。

MF 完整链工程通过=True；逐中心 AD HVP、曲率与算子计数见 DEVELOPMENT_SUMMARY.json。

真实旧状态求解器开发记录 2，正确分类检查=True。不能把开发精化后的状态当作历史原状态。

已核验 28 个 run manifests；累计实测活动 153.371 秒。失败开发尝试包含在 COST_LEDGER.json，未删除或覆盖。

新 seed 与下游配置仍待实现完整性验收后一次冻结。
