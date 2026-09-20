# Q2 补强 Reviewer Risk Matrix

**Namespace:** `paper_strengthening_v1`
**阶段:** `S0 PASSED / DEVELOPMENT_ONLY`
**日期:** 2026-09-20

| ID | 审稿人可能的质疑 | 当前证据 | 风险级别 | 补强动作 | 关闭条件 |
|---|---|---|---|---|---|
| R1 | 方法只是经典 Schur/variable projection 的重新命名 | 稿件已承认经典来源，但缺少统一替代基线 | HIGH | 建立 raw、fixed exact、SAEPS、VP0/SVD、profile/FIM registry | 主表明确显示新增诊断价值；不宣称新代数定理 |
| R2 | exact-Hessian Schur 不等于 nonlinear reoptimized profile | 历史 profile 仅 1/5 valid；0/21 达到最严格 stationarity | CRITICAL | S1 dry-run；S2 冻结 profile 规则；S3 独立 profile validation | profile stationarity、fit-quality 和分母全部预先冻结且可审计 |
| R3 | 一维合成问题不足以支持泛化 | 主要结果来自 Burgers/Allen–Cahn；two-parameter 8/10 | HIGH | 完成两参数协议或加入预先指定的二维/非合成 benchmark | 独立问题结果或明确 LIMITED_CLAIMS |
| R4 | gamma、坐标、权重变化会改变结论 | 已有 gamma sweep、coordinate identity 和部分 architecture audit | MEDIUM | 统一 gamma/coordinate/weight sensitivity table | 排序稳定性与翻转区域全部报告 |
| R5 | 只保留有利 seed 或把相关 fit 当独立样本 | 当前记录保留失败分母；E3 使用 seed 作为统计单位 | MEDIUM | 每张表报告 planned/valid/failed；seed-level paired aggregation | raw-to-aggregate 自动校验通过 |
| R6 | 大规模实验只是成本演示，不代表精度或 speedup | 当前稿件已限定 stronger damping 与 function-preserving expansion | MEDIUM | 把 operator feasibility 与 end-to-end cost 分开 | 不再使用 large-network accuracy/production speedup 措辞 |
| R7 | profile 失败被隐藏在 supplement | 当前正文已写 unsupported，但需要紧邻正面结果呈现 | HIGH | 在主结果段加入 failure table 和 gate explanation | 正文与 supplement denominator 一致 |
| R8 | 论文数字和代码结果无法复现 | provenance、hash、manifest 已较完整 | LOW | S5 重新生成所有 paper-facing artifacts | validator 或既有失败均有可追溯解释 |
| R9 | 期刊定位不匹配或按错误分区投稿 | 尚未固定目标期刊、类别和年份 | MEDIUM | 投稿前重新核验 scope、JCR/Scopus category 和模板 | cover letter 给出具体 scope fit |

## 处理优先级

`R2 > R1 > R3 > R7 > R4 > R5 > R6 > R8 > R9`。

若 R2 无法关闭，不得通过扩大实验数量掩盖 profile stationarity 缺口；论文应采用 Claim Ledger 的收缩版本。
