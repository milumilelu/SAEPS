# Protocol Amendment 002 — v2.0 JCP 级实验协议

**状态:** `ADOPTED`  
**生效日期:** 2026-08-19  
**替代契约:** `SAEPS-MVP-EXEC-v1.1`  
**新契约:** `SAEPS-JCP-EXEC-v2.0`  
**来源文件:** `SAEPS 新仓库实验任务书 v2.0.md`  
**来源 SHA256:** `FD7F2675719F98997236D735CED8181D631A939835DF6A08A9192FBE6266B07C`

## 覆盖项

1. 阶段改为 P0 Repository、P1 Numerical core、P2 Controlled、P3 Profile、P4 Screening、LOCK、P5 Scalar、P6 Multi-parameter、P7 Robustness、P8 Cost、P9 Audit；
2. Amendment 001 的 3 development + 10 confirmation seed 设计继续有效；
3. Controlled gate 保持 median seed-level Spearman \(\ge0.9\) 且至少 8/10 单调；
4. Scalar paired gate细分为 `STRONGLY_SUPPORTED`、`SUPPORTED_WITH_UNCERTAINTY`、`PARTIALLY_SUPPORTED`、`NOT_SUPPORTED`；
5. Multi-parameter ordering gate 从此前裁决的 8/10 提高到 v2.0 明确规定的 9/10；
6. Multi-parameter mandatory directions 限定为 \(v_{max},v_{min}\)，不再强制 \(d_{error}\)；
7. Representative 2D seed 固定按“升序第一个 valid confirmation seed”自动选择；
8. P7 robustness 为 scalar benchmark 的 9 conditions × 5 seeds，最大 45 runs；
9. Architecture transfer 为 scalar-only：nominal 10，narrow 5，wide 5；
10. 新增 P8 computational-cost 硬性交付；
11. 若 P5 核心结果失败，按协议停止大规模 P7 robustness，不将该停止视为工程失败；
12. 新增 `docs/LOCKED_PROTOCOL.md`、Figure 6、Table 3、精确 run-status 枚举和 phase-level commit 要求。

## 解释原则

v2.0 是当前最高优先级实验设计。旧文件中与 v2.0 不冲突且更严格的数值正确性、provenance、自动聚合和失败保留要求继续有效；冲突条款由本修订明确覆盖。

