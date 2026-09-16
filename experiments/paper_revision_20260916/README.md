# SAEPS 论文修订实验工作区

服务于局部曲率论文的补实验（E0–E8）。本目录是**唯一**的新增输出命名空间。
本工作区不修改 v2/v4/v5 协议、锁定配置、历史输出或 `PROTOCOL_STOP`。

## 当前状态

| 任务 | 状态 |
|---|---|
| E0 数据与统计审计 | `PASSED` |
| E1 参数梯度恒等式 | `PASSED` |
| E2 固定锚点敏感性 | `PARTIAL`（标量指定队列 `NOT_AVAILABLE`） |
| E3–E8 | `NOT_STARTED` |

详见 `reports/E0_E1_E2_REPORT.md` 与 `reports/experiment_status.json`。

## 关键约束

- 历史证据固定在标签 `jcp-submission-v1` = `d5a231d857e410b96ae66174fb98fec9c8b9b34a`。
- 所有历史输入通过 `git show` 只读读取，不检出、不写入。
- 未训练任何 PINN；未重跑或替换任何历史种子。
- 缺失的原始张量记录为 `NOT_AVAILABLE`，不用重建数据冒充原始归档。
- 所有输出目录拒绝覆盖。

## 目录

```text
protocol.yaml          数值、种子与容差快照
configs/protocol.yaml  包自测使用的相对路径副本
src/repo_adapter.py    只读适配器（检查点、点位、配置、损失尺度）
src/e0_audit.py        E0 审计
src/e1_identity.py     E1 恒等式核验
src/e2_stationarity.py E2 固定锚点敏感性
src/audit_repository.py, audit_archive.py, numerics.py, plan_jobs.py,
                        benchmark_saturation.py 为包内独立检查器与排程器
tests/                 包合成测试 + 仓库适配器集成测试
outputs/posthoc/       E0/E1/E2 产出
reports/               报告、状态、输出清单
```

## 运行

```bash
cd experiments/paper_revision_20260916
export PYTHONPATH="../../src:$PWD/src"

python -m pytest -q tests                 # 28 项：20 项包合成 + 8 项适配器集成

python src/e0_audit.py        --out outputs/posthoc/e0   # 目录需不存在
python src/e1_identity.py     --out outputs/posthoc/e1
python src/e2_stationarity.py --out outputs/posthoc/e2
python src/manifest_outputs.py
```

`plan_jobs.py` 只输出排程，不执行训练。本工作区**没有**完整训练执行器（E3–E8 所需）。

## 尚未实现

- E3 饱和反应扩散训练模块（32 个拟合 + E6 扩展 12 个）。
- E4/E5/E7/E8 的复用型分析。
- 完整训练执行器与真实检查点导出器。

## 记录规则

- 结果表必须由 `outputs/` 中的记录自动生成，不得手工填写。
- 失败、超时、缺失均须保留在分母中。
- 相对误差必须声明分母（标量 `|H_red|+1e-8`，矩阵 `||W(H_red)||_F+1e-30`）。
- 事后分析不得改称预注册。
