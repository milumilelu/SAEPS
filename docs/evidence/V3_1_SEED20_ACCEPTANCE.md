# V3.1 Seed-20 Development Acceptance

## 结论

v3.1 工程执行 `PASSED`，严格全链条 `FAIL`。seed 20 已找到满足一阶与 exact-Hessian 二阶 gate 的 center，unregularized profile 的 8/8 点也全部达到相同局部极小标准；但四尺度曲率不收敛，因此流程在 unregularized profile 阶段合规停止。seeds 21–24 与 confirmation 均未授权。

## Center

- mean loss: `0.0366474069 -> 0.00389160203`;
- exact-Hessian saddle escape cycles: `13`;
- normalized objective gradient: `7.55298e-6 <= 1e-4`;
- residual stationarity `S_theta=3.23403e-5 <= 1e-4`;
- minimum mean-objective state-Hessian eigenvalue: `-8.53524e-9`;
- registered `tau=7.91289e-7`; second-order gate `PASS`.

## Unregularized profile

所有 8 个 profile points 的统一 gradient gate 与 exact state-Hessian gate 均为 `PASS`。未归一化对称曲率为：

| h | curvature |
|---:|---:|
| 0.05 | 19.2297181 |
| 0.025 | 16.0247230 |
| 0.0125 | 8.71030515 |
| 0.00625 | -1.45181518 |

最细两个相邻变化分别为 `0.839743` 与 `6.999596`，均高于 `0.05` gate。该结果排除了“profile point 仍停在明显 saddle”这一解释，但不支持稳定的局部二阶 reduced curvature。

## 串行停止

由于 unregularized multiscale convergence 为 `FAIL`，程序没有运行 gamma-matched profile、standard-CG/PCG gate、exact reduced-Hessian comparison，也没有查看 seeds 21–24 或 30–44。这是协议要求，不是工程遗漏。
