# AGENTS.md

## 1. 项目性质与唯一目标

本仓库是 SAEPS（State-Adapted Effective Parameter Signals）科学验证项目。工作的目标是忠实完成预注册验证协议，而不是获得预期的阳性结论。

核心科学问题是：

> SAEPS 的局部 neural-state elimination，是否比 raw fixed-network sensitivity 更准确地预测物理参数受到固定扰动、神经网络状态重新优化后形成的 nonlinear reduced objective 局部几何？

科学结论只能是 `SUPPORTED`、`PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED`。只要协议被正确执行，阴性科学结果同样属于项目成功完成。

## 2. 权威文件与优先级

执行前必须阅读并遵循以下文件：

1. `docs/EXECUTION_CONTRACT.md`：v2.0 任务书的最高优先级可执行协议；
2. `AGENTS.md`：执行纪律、权限和禁止行为；
3. `GOAL.md`：顶层目标与完成定义；
4. `docs/EXPERIMENT_SPEC.md`：实验设计与锁定配置；
5. `docs/ACCEPTANCE_CRITERIA.md`：工程与科学验收标准；
6. `docs/SCIENTIFIC_GATES.md`：科学判据；
7. `TASKS.md`：阶段状态与下一项工作；
8. `docs/LOCKED_PROTOCOL.md`：LOCK 后不可变的 confirmation 协议；
9. `docs/DECISIONS.md`、`docs/ISSUES.md`、`docs/PROVENANCE.md`：决策、异常与来源记录。

`docs/EXECUTION_CONTRACT.md` 已裁决的差异按其执行。其他文件冲突时，先停止相关实验，将冲突写入 `docs/ISSUES.md`，不得自行选择更容易产生理想结果的解释。

## 3. 阶段执行纪律

- 严格按 `P0 → P1 → P2 → P3 → P4 → LOCK → P5 → P6 → P7 → P8 → P9` 推进。
- 只有当前阶段的 engineering gate 为 `PASSED` 后，才能开始下一阶段。
- 每次工作先检查仓库与 `TASKS.md`，只推进最早的未完成阶段。
- 每完成一个可验证增量，运行对应测试并更新 `TASKS.md`。
- 每个通过验收的阶段必须形成独立、可追溯的 Git commit。
- 状态只能使用 `NOT_STARTED`、`IN_PROGRESS`、`BLOCKED`、`PASSED`、`FAILED`。
- engineering gate 失败时诊断并修复工程问题；scientific gate 失败时如实记录并按协议继续，不得调参迫使其通过。
- 若 P5 为 `NOT_SUPPORTED`，按 v2.0 停止大规模 P7 robustness 并记录 `PROTOCOL_STOP`；这不是工程失败。

## 4. Development 与 Confirmation 隔离

- Development 只允许使用协议指定的 development seeds 和候选集合。
- 核心 confirmation 固定使用 10 个 seeds `[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]`；robustness cells 使用 5 个预注册 seeds。
- Development 阶段只可在任务书明确允许的范围内调试、筛选和确定阈值。
- Confirmation 前必须把配置写入 `configs/locked/`，生成并记录 SHA256 hash。
- LOCK 同时生成 `docs/LOCKED_PROTOCOL.md`，记录 hash、git commit、日期和 decision reason。
- 锁定配置视为不可变；confirmation 运行后不得修改阈值、seed、benchmark、source、loss weights、网络结构、profile 区间、gamma 选择规则或其他科学设计。
- Confirmation 数据不得反馈到 development 决策中。
- 如锁定配置确需修改，停止 confirmation，保存现有结果，在 `docs/ISSUES.md` 记录原因和影响；未经明确的新协议授权不得继续。

## 5. 允许的自主操作

在不改变科学协议的前提下，可以：

- 创建和修改仓库内文件；
- 安装项目已声明的 Python 依赖；
- 编写并运行测试、训练、数值实验和聚合流程；
- 修复实现错误和合理的数值稳定性问题；
- 优化不改变数学定义与实验设计的工程性能；
- 生成日志、manifest、图表、表格和报告；
- 修改尚未锁定的 development 配置；
- 按预注册 screening rule 选择 benchmark。

## 6. 绝对禁止行为

不得：

- 删除、隐藏或静默排除不利或失败的 seed/run；
- 只报告最佳 seed，或不报告 aggregation denominator；
- 根据 confirmation 结果重新选择 PDE、source 或 benchmark；
- 根据 confirmation 结果改变 loss weights、网络结构、训练协议、profile 区间、阈值或 gamma；
- 为获得特定 \(\eta^{se}\) 或更美观结果而调参；
- 修改已锁定配置而不触发正式偏差记录；
- 手工填写或修改 paper-facing 数值；
- 在 LaTeX/Markdown 中硬编码实验结果；
- 将 failed run 从聚合中静默排除；
- 将 synthetic reference truth 用作真实部署指标；
- 将未通过 stationarity gate 的 checkpoint 描述为有效 SAEPS 验证；
- 把相关性表述为因果性；
- 把局部参数可靠性表述为全局可辨识性；
- 因科学结果为阴性而把工程任务标为失败或未完成。

## 7. 强制停止与记录

出现以下情况时，保存全部现有产物并写入 `docs/ISSUES.md`：

- 理论公式与实现无法对应；
- explicit 与 matrix-free 实现持续不一致；
- SAEPS 不优于 raw baseline；
- nonlinear profile 不支持局部二次近似；
- benchmark 无法达到 stationarity；
- 数值不稳定无法通过不改变协议的合理方法解决；
- confirmation 与预期结论相反；
- confirmation 配置需要修改。

问题必须分类为 `implementation failure`、`numerical failure`、`benchmark failure` 或 `scientific failure`。科学失败不得通过继续调参“修复”。

## 8. 数据、来源与聚合纪律

- 每个 run 必须生成机器可读 manifest，并包含 `docs/ACCEPTANCE_CRITERIA.md` 要求的 provenance 字段。
- 所有预注册 run 必须有最终状态；失败状态必须包含 `failure_reason`。
- Run 最终状态只能是 `PASS`、`CHECKPOINT_INVALID`、`PROFILE_FAILURE`、`SOLVER_FAILURE` 或 `NUMERICAL_FAILURE`。
- 所有聚合必须从 `outputs/runs/` 的 manifest/raw results 读取。
- Figures、tables 和 summary 必须来自同一份自动聚合数据源。
- Scalar 主比较必须在同一 seed/checkpoint 内成对计算 \(D_i=E_{raw}^{(i)}-E_{SAEPS}^{(i)}\)，不得拆散配对后比较两个独立样本组。
- 自动检查 paper-facing median 与 seed-level 源数据 median 在浮点容差内一致。
- 最终主张必须可追溯到机器可读原始实验输出、锁定配置 hash 和 git commit。
- 所有核心 run 必须记录 hardware、dtype、timing、CG iterations 和 JVP/VJP counts，以支持 P8 成本审计。

## 9. 测试与完成规则

- Mock 仅限范围明确的单元测试；阶段验收必须使用实际数值数据或真实流程。
- P0 smoke test 必须实际完成训练、保存、重载和一致性验证。
- P1 必须以实际 tiny network 同时验证 explicit 与 matrix-free SAEPS。
- PDE 阶段验收必须执行真实训练、stationarity、SAEPS 和 state-reoptimized profile 流程。
- 最终以 `python scripts/validate_repository.py` 的实际执行为统一工程验收入口。
- scientific gate 为 `FAIL` 不得导致仓库验证返回工程失败。
- 只有满足 `GOAL.md` 的全部完成条件，生成 `FINAL_VALIDATION_REPORT.md`，且工作树干净、测试通过、commit 可追溯，才可宣布项目完成。
