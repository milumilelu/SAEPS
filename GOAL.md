# GOAL.md

> 执行阶段、冲突裁决和验收接口以 `docs/EXECUTION_CONTRACT.md` 为最高优先级协议。

> **当前研究状态（2026-08-21）：** 下方勾选项与 `FINAL_VALIDATION_REPORT.md` 记录的是已完成的 v2 历史协议，不是整个 v4 research program 的最终完成。v4.2 已独立确认 Burgers scalar-curvature comparative claim 为 `SUPPORTED`，但外部 scalar replication、fresh controlled-mechanism closure、two-parameter exact geometry 与 practical scalability 尚未完成。当前后续执行契约为 `docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md`；任何历史 lock 和结果保持不变。

## 顶层目标

从零建立一个独立、可复现、可审计的 SAEPS 实验仓库，完成 Journal of Computational Physics 方法论文强度的最小实验闭环，并回答：

> SAEPS 的局部 neural-state elimination，是否比 raw fixed-network sensitivity 更准确地预测“固定物理参数扰动后重新优化神经网络状态”所形成的 nonlinear reduced objective 局部几何？

本项目评价的是验证协议是否被正确执行，而不是是否得到阳性结果。不得为了获得 `SUPPORTED` 而修改已锁定实验设计。

## 必须交付的科学证据

1. SAEPS explicit 与 matrix-free 实现的数值一致性证据；
2. controlled tangent-geometry benchmark；
3. nonlinear state-reoptimized profile engine；
4. 至少一个 scalar physical inverse-PDE confirmation benchmark；
5. 一个完整使用二维曲率矩阵的 two-parameter joint-geometry benchmark；
6. 最小 noise / observation-fraction robustness 实验；
7. raw fixed-network sensitivity、SAEPS 和 nonlinear reoptimized profile 的自动比较；
8. 明确的科学结论与论文 Go/No-Go 建议。
9. SAEPS 与 full nonlinear profiling 的计算成本证据。

核心 confirmation 使用 10 个锁定 seeds `[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]`。Scalar 主结论采用同一 checkpoint 内的 paired comparison，并同时报告 9/10 胜出、\(median(D)\) 和 paired bootstrap 95% CI；10 seeds 只用于支撑 across-seed reproducibility，不得被表述为跨所有问题的普适性证据。

## v2 Historical Definition of Done

只有同时满足以下条件，Goal 才能标记为完成：

- [x] 仓库可在干净环境中按文档安装并运行；
- [x] P0–P9 mandatory engineering work 均完成；
- [x] SAEPS explicit 与 matrix-free 数值一致性测试通过；
- [x] controlled tangent-geometry、nonlinear profile、scalar confirmation 和 two-parameter joint-geometry 实验完成；
- [x] development 与 confirmation 数据、配置和 seed 严格分离；
- [x] confirmation 配置已锁定，SHA256 hash 可验证；
- [x] 所有预注册 confirmation runs 均有最终状态；失败 run 均保留并说明原因；
- [x] 所有正式 SAEPS checkpoint 均执行 stationarity gate；无效 checkpoint 未被描述为有效验证；
- [x] 所有 paper-facing 数值由 raw machine-readable results 自动聚合；
- [x] 单一命令可重新生成最终 figures、tables、summary 并检查其一致性；
- [x] `python scripts/validate_repository.py` 返回 `0`；
- [x] `FINAL_VALIDATION_REPORT.md` 已自动生成并包含全部偏差和失败 run；
- [x] 报告科学结论为 `PARTIALLY_SUPPORTED`；
- [x] 报告建议为 `INVESTIGATE_NUMERICS`；
- [x] computational-cost evidence 包含 \(T_{reoptimized\ profile}/T_{SAEPS}\)；
- [x] 测试通过，`git status` 干净，阶段 commits、最终 commit 与全部结果可追溯。

科学 gate 失败不妨碍 Goal 工程完成；缺失实验、违反协议、不可追溯结果或工程验收失败则不允许完成。

## v4 Research Program Definition of Done

- [x] v4.2 Burgers scalar exact-curvature confirmation 完成并永久关闭；
- [x] Allen--Cahn 外部 scalar replication 完成独立 development、lock 与 untouched confirmation；
- [x] controlled tangent mechanism 在 fresh seeds 上完成计划分母验证，或保留阴性结果并收缩 claim；
- [ ] two-parameter exact reduced geometry 完成独立 development 与 confirmation；
- [ ] directional-HVP adequacy diagnostic 完成 explicit 数值一致性及 untouched 外部评价；
- [x] practical scalability 至少覆盖真实 residual 上的约 `10^2--10^5` state-parameter scale；
- [ ] v4-compatible noise/sparsity 与 architecture robustness 完成；
- [ ] 当前总报告从全部不可变历史结果和新 raw outputs 自动生成。

## 最终科学结论规则

最终报告只能选择：

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `NOT_SUPPORTED`

建议的决策映射：

- `PROCEED_TO_PAPER`：P0–P9 mandatory engineering 完成；P1 数值验证、controlled geometry、scalar strong evidence 和 multi-parameter 9/10 gate 通过；robustness 不显示仅限极窄条件；成本体现实用价值；无重大协议违规。
- `PROCEED_WITH_LIMITED_CLAIMS`：controlled mechanism 成立，但 scalar uncertainty 较大或 multi-parameter 仅部分支持。
- `REVISE_METHOD`：数学与工程验证成立，但 scalar SAEPS 未稳定优于 raw baseline，或经验主张仅得到部分支持。
- `INVESTIGATE_NUMERICS`：证据受到未解决的数值问题、stationarity 或 profile 质量限制。
- `STOP`：explicit 与 matrix-free 长期不一致、reoptimized profile 系统性反驳 \(F^{se}\)、SAEPS 对 damping 极端敏感且无稳定区间，或主要结论仅在 development seeds 成立。

## 非目标

本项目不证明全局可辨识性，不建立因果结论，也不以挑选成功 benchmark、seed 或 gamma 的方式“让论文成立”。
