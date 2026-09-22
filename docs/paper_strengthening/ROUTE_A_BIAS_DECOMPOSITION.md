# Route A 偏差–覆盖率分解

## 结论

现有 30 个 E3 replicate 支持“覆盖率缺口主要由参数偏差放大”的判断，但不能把条件 coverage 解释为无偏极限下的严格估计。按真实参数偏差分层后，SAEPS 在低偏差组达到 100% coverage，在中等偏差组仍为 100%，而高偏差组下降到 53.3%。

## 分层结果

真实参数为 \(\kappa^\star=1.2\)，定义 \(b_i=|\hat\kappa_i-\kappa^\star|\)。

| 偏差层 | replicate 数 | raw | SAEPS | parameter-block |
|---|---:|---:|---:|---:|
| \(b\le 0.02\) | 5 | 100% | 100% | 100% |
| \(0.02<b\le0.05\) | 10 | 0% | 100% | 0% |
| \(b>0.05\) | 15 | 0% | 53.3% | 0% |

总体 coverage 为 raw 16.7%、SAEPS 76.7%、parameter-block 16.7%。分层后可以看到，SAEPS 在偏差不大的 replicate 中能够覆盖真值；剩余失败主要集中在大偏差组。raw 和 parameter-block 即使在低偏差组以外也几乎完全欠覆盖，说明曲率高估仍是独立问题。

## 解释边界

该分层使用真实参数计算偏差，因此是诊断性 oracle 分析，不是可部署的 bias correction。不能把低偏差组的 100% 直接报告为总体 coverage，也不能把“将估计量强行移回真值”作为方法结果。它的用途是区分两种机制：

1. 当参数估计接近真值时，SAEPS 区间通常足以覆盖；
2. 当估计偏差超过约 0.05 时，即使 SAEPS 区间变宽，中心偏移仍会造成漏覆盖。

## 对 95% 目标的含义

95% 仍然是名义目标，但不是当前 development setup 下的唯一成功门槛。现有数据表明，SAEPS 已修正曲率高估；剩余缺口主要由偏差和表示/优化误差决定。若要声称接近无偏极限下的 95%，仍需：

- 增加 100–200 个 replicate；
- 通过独立重启、网络容量或偏差校正处理大偏差 replicate；
- 在 Burgers 或 Allen–Cahn 上复现同一分解；
- 报告分层 coverage 以及 binomial uncertainty，而不是只报告总体比例。

## 论文可用表述

> The undercoverage was not homogeneous across refits. After stratifying by the absolute parameter-estimation error, SAEPS covered the truth in 100% of the low- and intermediate-bias refits, while coverage decreased to 53.3% in the high-bias group. This pattern indicates that state elimination corrects the curvature component of undercoverage, whereas residual failures are dominated by estimator displacement and PINN approximation error.

该结果支持“曲率欠覆盖与参数偏差可分解”的叙事，但不构成无偏 coverage 定理。
