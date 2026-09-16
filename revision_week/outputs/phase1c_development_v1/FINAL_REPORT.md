# Phase 1C 审计结论



工程检查 PASSED：45 项测试、统一仓库 validator 和独立状态重载核验通过。科学结果有明确局限。



1. 驻点诊断：旧 LBFGS 终止证据为 {'max_eval_reached': 10, 'other_LBFGS_termination_not_logged': 1, 'max_iter_reached': 1}。函数评估上限早于迭代上限可以终止优化，不能据此宣称达到驻点；未保存原因的其他终止不作臆测。

Burgers 六个状态全部经两步 Newton 达标；Allen–Cahn 六个仍失败，其中 5 个在更新后的 Hessian 检查失去数值 SPD，另一个用完固定八步预算。

Newton 降低目标并不保证留在原局部正定区域。这个试验显示 Allen–Cahn 的障碍超出单纯放宽 LBFGS 预算；不继续救援或替换中心。

失败状态的最小特征值与位移范数：

```json

[
  {
    "task": "allen_cahn_84_plus_candidate0_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "state_not_SPD",
    "old_termination_evidence": "max_eval_reached",
    "old_gradient": 3.9019533004321444e-08,
    "new_gradient": 9.57164803980874e-05,
    "accepted_newton_steps": 1,
    "final_min_eigen": -0.0051193309687745485,
    "final_SPD_status": "not_SPD",
    "newton_step_norm": 0.04707857474269766,
    "objective_change": -2.801350523967683e-06
  },
  {
    "task": "allen_cahn_84_plus_candidate1_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "state_not_SPD",
    "old_termination_evidence": "max_eval_reached",
    "old_gradient": 6.806510814640921e-08,
    "new_gradient": 3.914654989925224e-05,
    "accepted_newton_steps": 1,
    "final_min_eigen": -0.006773621308162827,
    "final_SPD_status": "not_SPD",
    "newton_step_norm": 0.04773050023374211,
    "objective_change": -7.301611318288881e-06
  },
  {
    "task": "allen_cahn_84_plus_start_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "state_not_SPD",
    "old_termination_evidence": "max_eval_reached",
    "old_gradient": 3.750854784589344e-08,
    "new_gradient": 7.698096519937202e-05,
    "accepted_newton_steps": 1,
    "final_min_eigen": -0.005407611588145801,
    "final_SPD_status": "not_SPD",
    "newton_step_norm": 0.045906465419908574,
    "objective_change": -2.977261521486252e-06
  },
  {
    "task": "allen_cahn_84_minus_candidate0_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "iteration_limit",
    "old_termination_evidence": "max_eval_reached",
    "old_gradient": 3.131558303337841e-08,
    "new_gradient": 6.517883093329141e-06,
    "accepted_newton_steps": 8,
    "final_min_eigen": 0.001481379070047286,
    "final_SPD_status": "numerically_SPD",
    "newton_step_norm": 0.05531759304156768,
    "objective_change": -2.935941114334817e-06
  },
  {
    "task": "allen_cahn_84_minus_candidate1_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "state_not_SPD",
    "old_termination_evidence": "max_eval_reached",
    "old_gradient": 2.873896766910988e-08,
    "new_gradient": 4.566006250041529e-05,
    "accepted_newton_steps": 1,
    "final_min_eigen": -0.002242856585179023,
    "final_SPD_status": "not_SPD",
    "newton_step_norm": 0.024954415820006477,
    "objective_change": -1.1091204150937006e-06
  },
  {
    "task": "allen_cahn_84_minus_start_strict",
    "status": "PROFILE_FAILURE",
    "failure_reason": "state_not_SPD",
    "old_termination_evidence": "max_iter_reached",
    "old_gradient": 2.4118185018728604e-08,
    "new_gradient": 5.3424825643971386e-05,
    "accepted_newton_steps": 1,
    "final_min_eigen": -0.0007736256240023681,
    "final_SPD_status": "not_SPD",
    "newton_step_norm": 0.01922291733770476,
    "objective_change": -1.2099135021093055e-06
  }
]

```



2. 新一步试验：8/16 接受；Allen–Cahn 的八条由于公共起点失败而未执行候选求解，仍计入计划分母。

Burgers 两个偏移中 SO 实际下降均优于 GN，差值见 SUMMARY.json；三种曲率的候选不再因共同截断而相同。

这只是一个有效根中心上的两个关联观测，不支持跨 PDE 或独立统计结论。目标下降与合成真值误差改善分别报告。



3. 固定八步残差能量估计未成功：新界在 15/21 中更松，通过 1/21，原估计通过 9/21。

PCG 减少能量误差不保证欧氏残差范数下降，残差平方除以小 mu 的剩余项仍会膨胀。恒等式与参考包络核验通过，瓶颈是界的实用性，不是代数错误。

新旧界可在未来前瞻性协议中考虑组合，但本次没有事后更换估计器以提高通过数。停止这条固定八步方案；不宣称认证或效率提升。



本轮新增可核算 36.000 秒，其中实验 worker 17.931 秒；历史成本和估计失败账详见 COST_LEDGER/CLOSEOUT.json 引用。无新训练、无新种子。



结论：SO 局部一步用途为 PARTIALLY_SUPPORTED（仅 Burgers 开发中心）；SO-ADAPT 新估计方案 NOT_SUPPORTED。独立协议冻结继续暂缓，尤其不能绕过 Allen–Cahn 的局部有效性失败。

历史修正报告与全部失败保留，不把此次开发结果混入原 confirmation。