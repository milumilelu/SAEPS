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
| E3 开发队列 | `PASSED`（8/8 通过精确约化；SAEPS 8/8 胜出） |
| E3 预算收敛 | `PASSED`（中位变化 7.7% → 2.2%；最终预算 1e5） |
| E3 协议冻结 | 已冻结（`reports/E3_FROZEN_PROTOCOL.json`，失败关闭） |
| E3 留出队列 | `PASSED`（24/24 有效、6/6 数据种子完整、SAEPS 24/24 胜出） |
| E4 坐标与度量 | `PASSED`（80/80 必需检查） |
| E5 弱方向诊断 | `PASSED`（8/8 方向可分辨） |
| E8 同阻尼成本 | `PASSED`（72 次运行全部 PASS） |
| E6 中型网络 | `PASSED`（三架构 18/18 中心可用，SAEPS 18/18 胜出） |
| E7 局部 profile | `PASSED`（20/21 步通过参照核验） |

详见 `reports/E0_E3_REPORT.md` 与 `reports/experiment_status.json`。

## 关键约束

- 历史证据固定在标签 `jcp-submission-v1` = `d5a231d857e410b96ae66174fb98fec9c8b9b34a`。
- 所有历史输入通过 `git show` 只读读取，不检出、不写入。
- 未重跑或替换任何历史种子。**新训练仅限本命名空间的新基准**（E3/E6），不涉及任何历史 PINN；历史 `jcp-submission-v1` 结果保持只读。
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
outputs/heldout/       E3 留出队列与 E7 profile 核验产出
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

## 尚未实现

- 论文正文回填（E0–E8 结果尚未整合进稿件）。
- E2 指定的标量队列仍为 `NOT_AVAILABLE`（原始状态张量未存档）。

## 更正记录（2026-09-18）

两处实质性错误已修正，细节见 `outputs/posthoc/report_correction_20260918/`：

1. **`E_GN_fix` 定义用错**：运行脚本输出的是 `|F_se - F_raw|/(|H_fix|+eps)`，
   论文定义是 `|F_raw - H_fix|/(|H_red|+eps)`。留出队列中位值由 0.943847 更正为 **0.00118074**。
   `E_raw`/`E_SAEPS`/`E_fix`/`E_relax` 未受影响。冻结脚本未改动。
2. **符号检验单位用错**：`p = 5.96e-08` 等于 `2^-24`，把 24 个相关拟合当成独立单位。
   主推断应回到数据种子级：**`p = 2^-6 = 0.015625`**。

## 证据提交区分

- `evidence_ref` / `evidence_commit`：历史证据固定标签 `jcp-submission-v1`。
- 新实验的执行提交见各commit信息；`jcp-submission-v1` 是历史标签，**不是**新实验的执行提交。

## 开发阶段变更记录

`protocol.yaml` 的 `development_change_log` 记录 E3 状态精修预算两次调整
（1000 → 30000 → 100000）。1000 次迭代后状态远未驻点（归一化梯度 2.1e-4），
精确状态 Hessian 块非正定，8/8 开发拟合的约化失败。
选择规则只看驻点性与预算收敛趋势，不看曲率胜负。
**α=1e-8 无需改动，它不是失败原因。**

**收敛情况**：中位 \(E_{SAEPS}\) 逐级变化 7.7% → 2.2%；3e4→1e5 时 8 点中 5 点变化 < 1%，
最差单点 14.2%。队列级统计量接近收敛，**单点绝对值仍带敏感性，必须披露**。

## 冻结与留出

`reports/E3_FROZEN_PROTOCOL.json` 记录 `protocol.yaml` 与 `src/e3_saturation.py` 的
SHA256。留出运行器在快照缺失、哈希不符或未授权时**直接拒绝运行**：

```bash
python src/freeze_protocol.py --reason "..." --development-summary <json>
python src/e3_saturation.py --heldout --out <dir>   # 校验冻结快照后才开始
```

## 记录规则

- 结果表必须由 `outputs/` 中的记录自动生成，不得手工填写。
- 失败、超时、缺失均须保留在分母中。
- 相对误差必须声明分母（标量 `|H_red|+1e-8`，矩阵 `||W(H_red)||_F+1e-30`）。
- 事后分析不得改称预注册。
