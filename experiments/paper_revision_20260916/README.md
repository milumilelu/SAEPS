# SAEPS 论文修订实验工作区

服务于局部曲率论文的补实验（E0–E8）。本目录是**唯一**的新增输出命名空间。
本工作区不修改 v2/v4/v5 协议、锁定配置、历史输出或 `PROTOCOL_STOP`。

## 当前状态

| 任务 | 状态 |
|---|---|
| E0 数据与统计审计 | `PASSED` |
| E1 参数梯度恒等式 | `PASSED` |
| E2 固定锚点敏感性 | `PARTIAL`（标量指定队列 `NOT_AVAILABLE`） |
| E2 曲率漂移 | `PASSED` |
| E3 预检 | `PASSED` |
| E3 开发队列 | `BLOCKED`（α=1e-8 下状态块非正定，精确约化不可用） |
| E4–E8 | `NOT_STARTED` |

详见 `reports/E0_E3_REPORT.md` 与 `reports/experiment_status.json`。

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
src/e2_stationarity.py E2 固定锚点敏感性（预算/梯度级别）
src/e2_curvature_drift.py E2 参照漂移（3.1–3.4 节的关键表）
src/e3_saturation.py   E3 饱和反应扩散：预检、非仿射恒等式、开发队列
src/audit_repository.py, audit_archive.py, numerics.py, plan_jobs.py,
                        benchmark_saturation.py 为包内独立检查器与排程器
tests/                 包合成测试 + 仓库适配器集成测试
outputs/posthoc/       E0/E1/E2 产出
outputs/development/   E3 预检与开发队列产出
outputs/heldout/       预留（E3 留出队列尚未获准运行）
reports/               报告、状态、输出清单
```

## 运行

```bash
cd experiments/paper_revision_20260916
export PYTHONPATH="../../src:$PWD/src"

python -m pytest -q tests                 # 包合成 + 适配器集成测试

python src/e0_audit.py            --out outputs/posthoc/e0   # 目录需不存在
python src/e1_identity.py         --out outputs/posthoc/e1
python src/e2_stationarity.py     --out outputs/posthoc/e2
python src/e2_curvature_drift.py  --out outputs/posthoc/e2_curvature
python src/e3_saturation.py --verify  --out outputs/development/e3/e3_preflight.json
python src/e3_saturation.py --develop --out outputs/development/e3
python src/manifest_outputs.py
```

`plan_jobs.py` 只输出排程，不执行训练。

## 尚未实现 / 尚未获准

- E3 留出队列（24 个拟合）在开发阶段问题解决前不运行。
- E4/E5/E7/E8 的复用型分析；E6 中型网络扩展。
- **E3 当前阻断项**：α=1e-8 下状态块在全部 8 个开发拟合上非正定（最小特征值低至 −0.27），
  精确 Schur 参照不可得。按协议不得裁剪、不得以加大阻尼偷换目标。

## 记录规则

- 结果表必须由 `outputs/` 中的记录自动生成，不得手工填写。
- 失败、超时、缺失均须保留在分母中。
- 相对误差必须声明分母（标量 `|H_red|+1e-8`，矩阵 `||W(H_red)||_F+1e-30`）。
- 事后分析不得改称预注册。
