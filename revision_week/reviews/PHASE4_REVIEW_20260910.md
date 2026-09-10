# Phase 4 实现审查（2026-09-10）

审查对象：a6000 `/mnt/sda/ubuntu/RZW/SAEPS/repo`，HEAD `78f2fd7`；任务书 SAEPS_PHASE4_SOLVER_REFINEMENT_EXECUTION_RULES.md。本次仅审查、只读核验与运行已有测试；未重新求解、未修改实验结果、未 push。

## 结论

请求修改，不能接受“工程闭环全部通过”。名义近端路线具有开发价值，但 alpha=1e-10 的合规选择依据尚未成立。历史失败不改写；不进入 confirmation。

## 独立核验结果

- 当前 Phase 4 单元测试重新执行：20 passed（1.37 秒测试时间）。不等于协议执行完整性通过。
- 当前 3598 项历史 SHA256 基线重新逐文件检查：无变化。
- 当前保存标签确为 Route R 0/6、名义 Route P 4/6；alpha 网格标签为 5/4/6/6/6。
- 名义 Route P 的 K8/K10 状态均不同；从已保存 F_reduced 独立计算，其 6 个中心的漂移约 3.63e-10 至 1.57e-8，属于有利的开发诊断。
- Route R allen_cahn_1016 的联合 Hessian 漂移报告约 0.957；保存的约化曲率漂移独立计算约 0.33497。两者应区分，不能据此证明此前优化器失败的因果机制。

## 发现

### P1：所选 alpha 的两个通过位置没有独立精修状态

`tasks_grid/multi_1026_a1e-10` 与 `multi_1027_a1e-10` 的 curvature_K8.json 和 curvature_K10.json 具有完全相同的 state_theta_sha256；对应 F_reduced 漂移均为零。K8 已到 1.21013e-12、1.93712e-13，说明按 500 nfev 分块观察时已越过两个目标。再次调用求解器但返回同一状态，不能作为任务书 §6.3 的实际继续精修稳定性证据，也不能强迫一个已收敛状态移动来制造证据。

因此 5/6 中有 2 项曲率稳定性证据不足，不能直接用现有标签宣布 alpha=1e-10 已按规则选定。需保留原结果，在新版本中解决里程碑捕捉或定义明确的、事先授权的超额收敛处置。不能事后改选另一 alpha。

定位：diagnostics.py:183、least_squares_solver.py:21、finalize.py:288。

### P1：attempt-2 产物被覆盖，复现与完整成本无法追溯

docs/ISSUES.md:738–745 明确记录 attempt-3 覆盖 attempt-2 任务目录，仅保留 ATTEMPT2_RUN_LOG.txt。该日志只有终态及原因，没有 theta、曲率、梯度、资源时间或 manifest，不能证明“所有绑定数值完全复现”。任务书 §19 要求版本变化保留旧结果。

当前 protocol.json 的 version 实际为 2，不是汇报中的 v3。RUN_MANIFEST 和 GRID_RUN_MANIFEST 的 head_commit 都是 ddb3778，最终诊断修改在 df7ca6b 才提交。两个提交间 protocol.json 没有变化，现有记录不足以证明最终代码在执行前已按所述 v3 冻结。应尝试从备份恢复；不能把重新运行当作恢复被覆盖证据。

### P1：RAW_LOCAL_MINIMUM 标签缺少原始梯度门槛

diagnostics.py:246 只检查 H_raw 的正定性，再在 Route P 通过时赋予 raw_local_minimum=True。近端驻点通常满足 raw_gradient + gamma*(theta-theta0)=0，并不是原始目标驻点。

实际 burgers_1006_proximal、burgers_1007_proximal 被标 True，但独立由保存梯度范数和 theta 计算的原始归一化梯度为 5.29466e-6、2.91290e-6，均大于 1e-8。名义 Route P 的 allen_cahn_1016、multi_1027 本来就标 False。因此“四个近端通过中心 raw 局部极小成立”也与文件不符。

应把 H_raw_SPD 单独作为诊断；原始局部最小标签还须要求原始目标驻点，不得用近端梯度替代。

### P1：VALIDATION.all_pass 是部分自我声明，不是独立验收

finalize.py:223 中多项 checklist 直接为 True。recompute_value（第84行）只重算 raw loss，不核验近端总目标、梯度、Hessian、K8/K10 的不同状态、协议源码哈希与进程退出状态。当前 12/12 复算最多证明保存终态的 raw loss 一致，不能称完整统一 Objective 复算通过。

应将检查改为读取证据的断言并添加负控制：同一 K8/K10、错误 raw-local-minimum、篡改 gamma/hash、缺失过程文件、失败进程但 PASS claim，都应使验收失败。

### P1：成本台账没有覆盖实际全部尝试

finalize.py:340 仅聚合当前 tasks 的12项。台账 1895.1403 秒不含网格 547.2818 秒，也不含 attempt-1 1861.8181 秒和 smoke。扫描所有尚存 process.json，已可追溯 56 项共 4375.7024 worker-wall 秒；这还不含被覆盖 attempt-2 的未知成本、测试和控制器成本。未知必须标记 unknown，不能作0。

### P2：阶段预算和硬上限未按声称严格执行

least_squares_solver.py:39 只在500 nfev分块前检查 wall_cap，没有把阶段剩余时间传入该块的 deadline；实际 raw multi_1027 K8 为325.541秒，超过300秒；burgers_1007 K10为209.971秒，超过200秒。run_development.py:217/273 设置硬上限为600+120=720秒，而细则要求每任务600秒。当前不等于有正式任务已超过600秒，但执行保护并不是声明的上限。

应在每次 residual/Jacobian 计算前后检查 task/stage deadline，硬上限与协议一致，清理成本单列。

### P2：曲率指标与结论需要准确命名

冻结协议明确把 K 定义为联合(theta,lambda) Hessian，F_star为非绑定诊断。因此联合 K 稳定并不能一般地保证 Schur约化参数曲率稳定（尤其 A 接近奇异时）。这不是可以事后换 gate 的理由，而是必须限制本轮结论；新增方法版本应把目标一致的约化曲率验证写清楚。

### 其他应补齐的保护

- run_development.py 无独占锁、无已有结果拒写保护，grid() 没有在入口读取并强制验证分支 B 的授权证据；重复调用可覆盖任务。
- physical_fit() 的分块+10%仅对 proximal绑定，对raw未执行同一分块门槛；任务书§6.4要求需明确且一致。
- K12被称为非绑定，但worker.py:148选最后达到的状态作最终稳定性和物理拟合判定，可能反过来影响已通过的K10结论。当前须增加专门回归测试。
- 分支 B 实现只检查通过数量与问题覆盖；未把位移异常、近端项主导的审查依据写入决策证据。不能事后新增有利阈值。

## 建议处置

1. 保留本轮所有文件和标签，追加审查更正，不重写原始结果。
2. 暂停 alpha 已冻结、原始局部最小、完整工程通过等声明。
3. 对全部既有中心做不重新优化的完整证据审计；恢复旧尝试备份并补全成本，恢复不了的明确标缺失。
4. 新协议版本修复验收、里程碑、资源上限和不可覆盖机制；先通过合成负控制。
5. 近端路线保留为有希望的开发分支，但只有修复后的限定验证通过，才讨论 holdout。不得自动启动 confirmation、替换中心或 push。
