# S2 center-refinement analysis

本文件是对已关闭的 S2 development failure 的数值诊断，不是新的 confirmation 结果。它复用 `coarse_grid_tol_1e-7` 的 24 个 profile points/seed；只重新计算有限 γ profile 在 λ₀ 处的 center loss，并据此重算对称二阶差分。

## 诊断结果

| seed | 初始 center normalized gradient | refinement 后 gradient | center loss 改变量 | exact (H_{red}^{γ}) | refined-center curvature ([h=0.08,0.04,0.02,0.01]) |
|---:|---:|---:|---:|---:|---|
| 70 | (4.10\times10^{-8}) | (3.10\times10^{-8}) | (+3.65\times10^{-9}) | 5.48879 | 5.51037, 5.49402, 5.51324, 5.48949 |
| 71 | (3.16\times10^{-8}) | (9.94\times10^{-8}) | (-4.05\times10^{-10}) | 5.40164 | 5.43590, 5.42523, 5.40321, 5.29902 |
| 72 | (6.54\times10^{-7}) | (9.58\times10^{-8}) | (+6.44\times10^{-7}) | 4.26324 | 4.27116, 4.26183, 4.34580, 4.08006 |

S2 原始 profile 将未优化的 `theta0` loss 当作中心 loss。seed 72 的中心误差与 (h=0.01) 的二阶差分信号同量级，因此原始曲率为 `[4.197, 3.965, 3.160, -0.662]`；更换为 center-refined loss 后负曲率消失。这个结果支持“中心定义不一致 + 小步长误差放大”是主要数值原因。

但 center refinement 单独不能通过原有 fit-quality gate。三尺度、两尺度和全四尺度拟合仍分别为 `0/3` 全记录通过；因此不能把这次诊断写成 nonlinear-profile scientific support。

## 原因分解

1. **中心不一致。** profile points 已经重新优化，中心却没有按同一个有限 γ 目标求最小值，二阶差分因此混入中心优化误差。
2. **状态问题病态。** 原始 profile points 的 state-Hessian condition estimate 约为 (1.0\times10^8)（seed 70–72 的最大值约为 (1.03\times10^8)、(1.06\times10^8)、(1.22\times10^8)）。normalized gradient (10^{-7}) 并不能保证 soft direction 的 state error 足够小。
3. **小步长放大优化误差。** 曲率使用 (m[Φ(h)-2Φ(0)+Φ(-h)]/h^2)。当 (h=0.01) 时，任何 profile loss 误差都会被 (1/h^2=10^4) 放大。
4. **拟合门槛与 real profile 不匹配。** P3 的 (R^2\ge0.999999)、normalized RMSE (le10^{-6}) 在已知二次 synthetic objective 上成立，但当前 nonlinear PDE profile 存在高阶项和优化误差。直接放宽它会变成结果驱动的修复。
5. **中心优化还缺少下降保护。** seed 71 的 refinement loss 比原始 loss 高 (4.05\times10^{-10})。新的实现必须要求 refined objective 不高于 start，或将该点标为失败。

## 合规的下一版优化路线

若要继续，必须建立新版本 development 协议并在 confirmation 前锁定，不能修改已失败的 S2 记录：

1. 先对每个 checkpoint 做有限 γ center refinement；重新计算 (J_\theta)、γ、exact Schur reference 和 profile regularizer 的 reference state，保证中心、gamma、profile points 使用同一个 checkpoint 定义。
2. 对 state solve 使用预声明的 tighter gradient candidates（例如 (10^{-8})、(10^{-9})），并增加 objective non-increase、重复独立启动和 soft-direction displacement/error estimate。不能只增加最大迭代次数。
3. 用 loss-error budget 选择 (h_{min})：要求 profile loss 数值误差相对 (mHh_{min}^2) 足够小；若 (h=0.01) 不满足，就统一移除该尺度并保留所有失败记录。
4. 将 profile 拟合改为偶函数曲率随 (h^2) 的多尺度 extrapolation，或预先注册包含 quartic remainder 的模型；至少保留三个尺度，禁止使用只有一对点的恰合拟合。
5. 以重复启动差异、曲率随 (h) 的稳定性和预先锁定的 error budget 作为 fit gate。若新协议仍失败，科学结论必须保持 `NOT_SUPPORTED`，而不是继续调参。

机器可读诊断：`outputs/runs/paper_strengthening_v1/s2_center_refinement_diagnostic/`；运行配置：`configs/paper_strengthening/center_refinement_development.yaml`。
