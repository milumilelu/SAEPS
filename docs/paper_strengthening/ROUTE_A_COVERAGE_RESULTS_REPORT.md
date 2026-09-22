# Route A：SAEPS coverage 修正路线结果报告

## 1. 结论先行

当前证据不支持把 SAEPS 描述为已经恢复名义 95% coverage 的最终方法，但支持一个有论文价值的中等强度结论：

> 在 E3 饱和反应扩散 inverse PINN 的 development 实验中，raw fixed-state curvature 产生严重过窄的 Wald 区间；经过 neural-state elimination 和联合 sandwich 方差校准后，SAEPS coverage 显著提高，但仍低于名义 95%，剩余误差主要来自参数估计偏差、PINN 表示误差和有限样本局部近似误差。

因此，95% 是名义校准目标，不是路线 A 是否具有论文价值的二元门槛。路线 A 的核心价值在于揭示并量化 fixed-state curvature 导致的欠覆盖风险，并给出一种低成本的局部修正。

## 2. 已完成证据链

### 2.1 局部 Gaussian surrogate

基于 exact reduced curvature 的预审 surrogate 在 95% 名义水平下得到：

| Benchmark | raw | SAEPS | parameter-block |
|---|---:|---:|---:|
| Allen–Cahn | 0.328 | 0.917 | 0.955 |
| Burgers | 0.285 | 0.946 | 0.958 |

该结果只证明局部曲率方向上的可行性，不能替代真实 noisy-data refitting。

### 2.2 第一轮 10 个 noisy-data replicate

初始 Wald 方差直接使用加权曲率和观测噪声换算，得到：

| Method | Coverage |
|---|---:|
| raw | 0/10 |
| SAEPS | 2/10 |
| parameter-block | 0/10 |

该轮暴露了统计实现问题：区间极窄，实际参数估计误差远大于观测噪声诱导的局部标准误。

### 2.3 联合 sandwich 校准后的 10 个 replicate

修正后的方差使用联合 parameter–state Jacobian，并仅将 observation data block 的噪声传播到 nuisance-state 和参数方向：

| Method | Coverage |
|---|---:|
| raw | 4/10 |
| SAEPS | 8/10 |
| parameter-block | 4/10 |

这表明 SAEPS 的改善不是由简单扩大所有区间造成，而是与状态消除后的有效曲率变化一致。

### 2.4 扩展 Monte Carlo：30 个 replicate

固定 E3 benchmark、网络结构、噪声水平和优化器，使用 30 个独立 data seeds：

| Method | Valid replicates | Covered | Empirical coverage |
|---|---:|---:|---:|
| raw | 30 | 5 | 16.7% |
| SAEPS | 30 | 23 | 76.7% |
| parameter-block | 30 | 5 | 16.7% |

所有 replicate 均保留，solver failure 为 0/30。SAEPS 相对 raw 提高了 60 个百分点，但距离 95% 名义目标仍有约 18 个百分点差距。

### 2.5 收敛分层审计

在固定 10 个 seeds 下改变 state-polish 预算：

| 层级 | Polish budget | raw | SAEPS | parameter-block |
|---|---:|---:|---:|---:|
| L1 | 1,500 | 40% | 70% | 40% |
| L2 | 5,000 | 40% | 70% | 40% |

增加 polish 预算后，部分状态梯度显著下降，但 coverage 比例没有变化。这说明当前欠覆盖不能主要归因于 1,500 次 state polish 不足。

## 3. 为什么 SAEPS 仍未达到 95%

30 个 replicate 的参数估计均值为 1.233，而真值为 1.2；参数估计相对误差均值为 6.34%。因此，剩余 coverage 损失主要不是观测噪声方差不足，而是估计偏差和 PINN 逼近误差。

同时，22/30 个扩展 Monte Carlo replicate 的归一化 state gradient 高于 (10^{-5})，说明部分拟合仍没有达到严格驻点。即使把 polish 预算从 1,500 增加到 5,000，coverage 也没有变化，表明需要进一步处理优化偏差、表示误差和有限样本 profile 非线性，而不是单纯增加迭代次数。

## 4. 路线 A 当前允许的论文主张

可以主张：

1. fixed-state curvature 在该 inverse PINN benchmark 中造成明显的区间欠覆盖；
2. SAEPS 在相同 noisy-data refitting 框架下显著扩大了区间并改善了 coverage；
3. SAEPS 的改善与 neural-state elimination 的局部曲率修正一致；
4. sandwich 校准后，SAEPS 在 development Monte Carlo 中达到 76.7% coverage，而 raw 仅为 16.7%；
5. 剩余欠覆盖揭示了局部曲率修正无法单独消除的参数偏差与 PINN 优化误差。

不应主张：

1. SAEPS 已恢复名义 95% coverage；
2. SAEPS 提供有限样本统计保证；
3. 该结果自动推广到其他 PDE、网络结构或噪声机制；
4. raw curvature 必然在所有 inverse PINN 中导致相同程度的欠覆盖。

## 5. 推荐的论文叙事

论文应把问题表述为“固定状态局部信息导致的系统性过度自信风险”，而不是把 coverage 结果写成一个已经完成的置信区间校准定理。主结果表应同时报告 coverage、区间宽度、参数估计偏差和失败分母；不能只报告 SAEPS 的 23/30。

最稳妥的摘要级表述是：

> Across a development Monte Carlo study, raw fixed-state curvature achieved 16.7% empirical coverage at the nominal 95% level, whereas the state-eliminated SAEPS correction increased coverage to 76.7%. The remaining undercoverage was associated with estimator bias and incomplete PINN state convergence, establishing SAEPS as a useful local correction rather than a complete finite-sample calibration.

## 6. 下一步

优先级应为：

1. 完成 15,000 次 polish 的 L3 收敛层，确认 L1/L2 结论不是预算偶然性；
2. 对 (hat\kappa>1.5) 的异常 replicate 做独立重启、目标函数和 profile 审计；
3. 将 30 个 replicate 扩展到 100–200 个，报告 coverage 的 binomial confidence interval；
4. 增加一个不同 PDE 或不同噪声水平，检验路线 A 是否具有跨问题稳定性；
5. 若 coverage 仍低于 95%，保留“显著改善但未完全校准”的主张，不通过调参强行达到 95%。

## 7. 机器可读证据

- [30-replicate Monte Carlo results](../../outputs/posthoc/paper_strengthening/coverage_refit_mc_v1/coverage_refit_pilot_results.json)
- [Convergence L1 results](../../outputs/posthoc/paper_strengthening/coverage_refit_conv_l1/coverage_refit_pilot_results.json)
- [Convergence L2 results](../../outputs/posthoc/paper_strengthening/coverage_refit_conv_l2/coverage_refit_pilot_results.json)
- [Monte Carlo configuration](../../configs/paper_strengthening/coverage_refit_mc_v1.yaml)
- [Coverage refitting implementation](../../experiments/paper_revision_20260916/src/coverage_refit_pilot.py)

本报告属于 development evidence，不改变 locked confirmation 协议，也不把 development coverage 结果转写为确认性结论。
