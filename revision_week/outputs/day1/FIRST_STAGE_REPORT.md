# 第一阶段实际交付

工作树：C:\Users\RZF\Desktop\博士课题资料\SAEPS-so-week1；实现提交：da5e67bc43ce47c0a79b666fa46dc982d14d3f1f。
本地分支 codex/saeps-so-week1；没有 push。原工作区状态与输入矩阵 hash 检查通过。

27 个数学/算子测试通过；E0 保存 25/25 历史计划记录，21/21 可用矩阵通过复现。
最大历史曲率相对复现误差 3.21878e-11，最大归一化缺陷恒等式误差 1.67897e-11。
19/21 中心改善，逐中心 GN/SO 误差倍数中位数 7.83917。
GN 相对误差中位数 0.100541；SO 0.0129427。
四个旧无效种子 Burgers57/61/63、Allen81 保留；Burgers59/67 的 SO 变差保留。

21 条为数值误差界估计，严格验证型 0；初始有限相对界 0/21。
界/实际误差倍数中位数 227002，界很松。
有限对角 PCG 修正 9/21 达到数值估计 10% 容差，
其余保留超预算状态。SO-ADAPT 的总成本优势尚未建立。

按任务书规则，**值得继续有预算限制的 SO 开发 E1**；不能直接冻结独立验证。
SO-ADAPT 仅值得作为有限开发诊断，不宜据此推广；V6 的可扩展候选阴性结论不变。
局部代数曲率结果不是 profile 精度或反演参数精度的证明。

本轮可计量累计计算 43.548 秒；
E0 本身 1.481 秒；历史归档重构耗时
3801.892 秒单列，未重复训练。
详细口径见 COMPUTE_BUDGET_REPORT.md；真实 HVP=0，原始训练总成本不可完整恢复。

统一 validator 最终退出码 0。初次检查发现新 worktree
LF 检出与历史 CRLF 字节库存不一致；只对新 worktree 恢复85个已核验历史文件的
字节表示，未改变数值、锁定库存或原工作区。首次失败日志和修复 hash 均保存。

缺口：21个原始中心的 theta/data/绝对梯度张量未归档。其他29个检查点不能替代它们。
因此未完成这些历史中心的真实 HVP/T3 重放；没有新队列、宽度实验、profile 或一步更新。
本次仅完成用户要求的第一阶段，不声称整个七天任务完成，也没有后台继续运行。

入口与路径：REPO_AUDIT.md、artifact_manifest.csv、ALL_RUNS.csv、METHOD_SUMMARY.csv、
raw/、TEST_REPORT.md、STAGE_VALIDATION.json；代码在 revision_week/core.py 和 run.py。
恢复命令见 RESUME_COMMANDS.md；数学说明见 ../../METHOD_MATH_NOTE.md。
