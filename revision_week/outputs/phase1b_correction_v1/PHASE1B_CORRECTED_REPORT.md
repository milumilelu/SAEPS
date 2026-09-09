# Phase 1B 审查修复报告

本目录是新的补充开发验证；day1/day2 原始产物逐文件 SHA256 保持不变。
没有新增训练、替换种子、调 gamma 或重新选择候选步。来源提交 1d528afba6ffb3bd2b7c307eb67c4ddf78b5cf7f。

机器验收结果：

```json
{
  "historical_outputs_unchanged": true,
  "recovery_blocks_pass": true,
  "hvp_pass": 4,
  "hvp_attempted": 4,
  "quadrants": {
    "Q1": 9,
    "Q2": 12,
    "Q3": 0,
    "Q4": 0
  },
  "profile_rows": 16,
  "profile_numerically_resolved": 0,
  "process_failures": 0,
  "original_protocol_compliance": "NOT_ESTABLISHED_WITH_RETAINED_DEVIATIONS",
  "independent_freeze_readiness": "DEFER: new protocol must explicitly acknowledge historical deviations and supplemental development scope",
  "terminal_median_effectivity": 196.43960479884183,
  "initial_median_effectivity": 227002.19937534767,
  "source_commit": "1d528afba6ffb3bd2b7c307eb67c4ddf78b5cf7f"
}
```

## 修复与可保留结论

恢复检查现在比较全部六个G/H块和保存数据生成的残差；不再只比较曲率标量。
HVP路径从保存的真实状态/数据构建，完整收费：加载、显式GN Jacobian/求解、冷HVP、
独立预热、三次稳态HVP、验证Hessian和谱分解。该路线明确为dense-assisted，未声称全流程矩阵无关。
每条HVP结果检查全部算子/二次型/伴随/梯度恒等式，而非只检查H@v。

ADAPT保留原算法停止点与100次迭代预算，只重放矩阵算法以恢复最终Z，核对保存终点。
初始与最终缺陷的谱机制分开保存于ADAPT_TERMINAL_ANALYSIS.csv，不再混用。

一步补验只重放原保存的候选坐标，完全相同坐标去重。共同起点和候选均做一次固定精化，
保存状态、带锚定目标、梯度、状态块SPD和精化前后目标变化。数值可分辨要求下降与接受余量
超过10倍精化变化和剩余局部梯度能量估计；这仍是数值精度审计，不是严格全局误差界。
GN/SO/ORACLE原候选被信赖半径截到同一点，所以不能推导SO相对GN的实际一步增益。

## 不可被事后修复的历史偏差

历史多次重放与导出失败确实发生，违反每中心一次流程限制；计入失败计算估计，不能称421秒为总用量。
历史失败的精确计时和尝试原始日志未完整保存，只有原台账估计，本轮无法追溯补造。
历史协议与结果同提交，缺少可独立验证的运行前冻结证据，不反向认证原冻结。
新的24次上限精度补验是本次修复授权下的补充验证，不并入原16次试验或称原预算执行完全合规。

已测历史成功活动 442.608485 秒；原HVP实测 2.226525 秒。
新工作进程墙钟合计 114.793204 秒，矩阵复核 0.230151 秒。
完整失败估计、第一阶段历史成本与新成本分别见COST_LEDGER.json；未知总量不伪造单一精确值。

结论：保留有证据的局部代数、恢复、HVP和精度审计结果；撤回原报告“全部合规、冻结条件全部满足”。
可以据本轮证据讨论新的独立协议，但不自动冻结或启动。所有输出由机器结果生成；未使用硬编码成功数。
