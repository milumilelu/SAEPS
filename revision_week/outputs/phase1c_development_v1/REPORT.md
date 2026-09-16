# Phase 1C 开发试验实测报告



本轮为用户授权的补充开发，旧协议与失败结果保持不变。



驻点校正：6/12 达到原定 1e-8 门槛。

新一步比较：8/16 状态有效；8/16 接受。

合成真值参数误差改善：8/8，与目标下降独立报告。



SO 与 GN 的逐分支实际下降差及误差分辨率：

```json

[
  {
    "root": "burgers_55",
    "offset": 0.05,
    "SO_minus_GN_actual": 0.006043261403963385,
    "comparison_error_estimate": 4.2645953244087754e-14,
    "resolved": true,
    "SO_better": true,
    "distinct_steps": true
  },
  {
    "root": "burgers_55",
    "offset": -0.05,
    "SO_minus_GN_actual": 0.012356072394489104,
    "comparison_error_estimate": 6.126010806453477e-14,
    "resolved": true,
    "SO_better": true,
    "distinct_steps": true
  }
]

```

SO-ADAPT 终点固定，旧估计通过 9/21；新估计通过 1/21。

四格表：{'Q1': 1, 'Q2': 20, 'Q3': 0, 'Q4': 0}；新界有效度中位数 516.81721917494。



新增 worker 活动墙钟 17.931 秒（含进程启动）；工程检查另列。历史 235 文件哈希不变。



驻点修复使用稠密精确 Hessian Newton，仅证明小网络上的数值可行性；不建立大规模求解效率。

新步长为运行前固定的统一 0.1 倍原始步，再应用 0.1 安全半径；只覆盖两个标量根中心，不是多参数独立验证。

新估计利用固定 8 步对角 PCG 和已有数值谱下界；原 SO-ADAPT 迭代终点不变。这不是严格证书，也不是端到端 matrix-free 优势。

历史重复恢复和原协议冻结时序偏差保留；本轮不启动独立确认或下游实验。