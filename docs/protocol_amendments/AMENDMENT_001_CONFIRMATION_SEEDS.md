# Protocol Amendment 001 — Confirmation 重复数与成对统计

**状态:** `ADOPTED`  
**生效日期:** 2026-08-19  
**适用契约:** `SAEPS-MVP-EXEC-v1.1`  
**来源附件 SHA256:** `402FD0B411CE115975AE50A62554FBB85B26A56405A64901721A523E974F9FF9`

## 变更原因

原协议的 5 个 confirmation seeds 和 `4/5` 胜出规则足以作最小工程验证，但不足以单独支撑较强的 across-seed superiority claim。在每个 seed 胜出概率为 0.5 的简单零假设下，至少 4/5 胜出的单侧概率为 0.1875；至少 9/10 胜出的单侧概率约为 0.0107。

本修订提高核心 confirmation 的重复数，并把 scalar 主判据改为同一 checkpoint 内的 paired comparison。它增强的是 across-seed reproducibility，不扩张 across-problem generality。

## 已采纳变更

1. Development seeds 保持 `[0, 1, 2]`；
2. 所有核心 confirmation 统一为 `[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]`；
3. Controlled geometry 从 25 增至 50 个 evaluations；
4. Controlled scientific gate 改为 median seed-level Spearman \(\ge0.9\)，且至少 8/10 seeds 满足锁定的单调/近单调规则；
5. Scalar comparison 定义配对差值
   \[
   D_i=E_{raw}^{(i)}-E_{SAEPS}^{(i)};
   \]
6. Scalar 强 gate 要求：至少 9/10 seeds 有 \(D_i>0\)、\(median(D)>0\)、paired bootstrap 95% CI 下界 \(>0\)；
7. 若前两条成立但 bootstrap CI 跨 0，最终结论不得高于 `PARTIALLY_SUPPORTED`；
8. Two-parameter benchmark 使用相同 10 个核心 seeds；原 80% ordering 门槛按比例落实为至少 8/10；
9. Robustness 使用 5 seeds/cell，定位为 stress test；
10. Architecture transfer 如执行，nominal architecture 使用核心 10 seeds，narrow/wide 各使用 5 seeds。

## 统计实现锁定要求

Bootstrap 的重采样单位必须是 paired \(D_i\)，不得拆散配对。CI 类型、重采样次数、bootstrap RNG seed、缺失/invalid pair 处理和百分比 effect-size 定义必须在首次 confirmation 前写入 `docs/EXPERIMENT_SPEC.md` 并锁定。本修订不擅自指定这些尚未给出的实现参数。

## 不变条款

- 不得因 10 seeds 的结果修改 benchmark、网络、loss、profile、gamma 或阈值；
- 无效 checkpoint 和失败 run 必须保留并计入 denominator 报告；
- 10 seeds 只支持训练随机性层面的可复现性，不证明跨所有 inverse PINNs 的普适性；
- scientific failure 仍然是合格的工程完成结果。

