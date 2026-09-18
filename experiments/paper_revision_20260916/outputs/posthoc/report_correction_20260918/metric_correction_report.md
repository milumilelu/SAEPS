# 指标定义更正报告

日期：2026-09-18。分类：**事后只读重算**，非预注册实验。
不重新训练，不覆盖历史输出，不修改冻结脚本。

## 问题

`E_GN_fix` 的计算与论文定义不符。

论文定义（`paper/manuscript.tex`，Eq. `fixed_state_exact_error`）：

```
Delta_GN,fix = F_raw - H_fix_exact
E_GN,fix     = |F_raw - H_fix_exact| / (|H_red_exact| + 1e-8)
```

运行脚本实际输出的是：

```
|F_se - F_raw| / (|H_fix| + 1e-8)
```

分子是松弛校正而非固定状态截断，分母用了固定状态块而非约化参照。**分子与分母都不对。**

## 真实回归例（来自本命名空间归档记录）

来源：`outputs/heldout/e3/e3_all_fits.csv`，data=916101，init=926001，noise=0。

| 量 | 值 |
|---|---|
| F_raw | 31.691529364882115 |
| F_se_GN | 1.6381987355663945 |
| H_fix_exact | 31.694172677784533 |
| H_red_exact | 1.6410548213691847 |
| 旧 E_GN_fix（错误） | 0.9482289039492354 |
| **新 E_GN_fix（论文定义）** | **0.0016107401482815197** |

回归校验通过：`True`。

## 未受影响的量

`E_raw`、`E_SAEPS`、`E_fix`、`E_relax` 的定义与实现一致，未变。
其中 `E_relax` 之所以不受影响，是因为它与代码所用的符号约定同时反号，差值绝对值不变。

校验 `E_raw`/`E_SAEPS` 未被更动：`True`。

## 代数恒等式

```
F_se - H_red = (F_raw - H_fix) - (C_GN - C_exact)
C_exact = H_fix - H_red,   C_GN = F_raw - F_se
```

全部 48 行核验通过：`True`，
最大残差 0.000e+00。

退化校验（`F_raw = H_fix` 时 `E_GN_fix` 必须为 0，即使存在状态松弛）：`True`。

## 汇总影响

| 口径 | 中位 E_GN,fix |
|---|---|
| 旧（错误字段） | 0.943847 |
| 新（论文定义） | 0.00113169 |

## 对论文的含义

- 这个错误**不推翻** `E_raw`/`E_SAEPS` 的排序：两者独立计算，未使用该字段。
- **但所有"固定状态 GN 截断约为 0.94"的机制叙述必须撤回重算。**
- 修正后真正的固定状态截断误差比原报小数个量级，且与该中心的 `E_SAEPS` 接近——
  这才是值得继续核验的机制关系，不能用错误字段替代。

## 产出

- `metric_definition_audit.csv`：逐行旧值、新值与差值，含源路径与源哈希。
- `e3_metrics_corrected.csv`：修正后的 E3 指标表。
- `e6_metric_dependency_audit.csv`：E6 同名字段的依赖审查。
- `metric_correction_summary.json`：机器可读汇总与校验结果。

旧列保留为 `E_GN_fix_reported`，新列为 `E_GN_fix_recomputed`，没有静默覆盖。
