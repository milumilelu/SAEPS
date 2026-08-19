# V3.2 Seed-20 Gamma-Primary Acceptance

## 结论

v3.2 工程执行 `PASSED`，gamma-matched primary chain `FAIL`。这不是 unregularized profile 导致的阻断：gamma profile 自身未通过最细尺度 convergence 与 optimization-accuracy convergence，同时 standard CG 和 Jacobi-PCG 也未通过 solver gate。exact gamma-matched Hessian reduction 单独 `PASS`。seeds 21–24 与 confirmation 均未授权。

## Common center

- normalized objective gradient: `5.65188e-7`;
- residual stationarity `S_theta=2.00458e-6`;
- recorded `S_lambda=0.0971141`;
- exact numerical-minimum candidate: `PASS`;
- mean-objective `lambda_min=-7.26699e-7`, registered `tau=2.05042e-6`.

## Gamma-matched primary profile

Nominal 与 strict accuracy levels 均为 8/8 numerical local-minimum candidates，全部 gamma-state Hessian 最小特征值约为 `2.02e-4` 至 `2.05e-4`，明确为正。

| h | nominal curvature | strict curvature |
|---:|---:|---:|
| 0.05 | 36.0839 | 35.8240 |
| 0.025 | 36.1329 | 35.7741 |
| 0.0125 | 36.2106 | 35.4660 |
| 0.00625 | 40.6946 | 33.4943 |

- strict `0.025 -> 0.0125` change: `0.8687%`, PASS;
- strict `0.0125 -> 0.00625` change: `5.8868%`, FAIL against 5%;
- nominal/strict accuracy difference at `h=0.0125`: `2.0996%`, PASS;
- nominal/strict accuracy difference at `h=0.00625`: `21.4971%`, FAIL.

因此当前不能把 `H_profile^gamma` 视为收敛值。它比 unregularized 明显稳定，但尚未形成完整闭环。

## Solver and exact Hessian

- standard CG: `SOLVER_FAILURE`; 500 iterations 后至少一个 verified residual 为约 `1.20e-7`，高于 gate；
- Jacobi-PCG: `SOLVER_FAILURE`; 两个 residual 分别约 `1.40e-5` 与 `0.2905`；
- exact gamma state block: minimum eigenvalue `0.0752908`, condition number约 `1.002e8`；
- exact gamma reduction: `H_red_exact_gamma=35.8538460`, solve residual `2.28e-14`, PASS；
- unregularized exact block仍非正定，作为非阻断诊断保留。

因为 primary profile 与 solver gate 均失败，协议禁止生成正式四量 comparison。不能从 coarse/中间尺度的数值接近关系宣称 SAEPS 已获支持。
