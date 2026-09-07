# 第一层：历史矩阵开发试验

仅复用归档矩阵；不训练、不改变历史确认配置与结论。本文数值由 audit_pilot.py 从 outputs/runs/v5/upgrade_pilot 自动生成。

工程核验：PASSED。历史计划 25 条，有效 21 条，原有无效 4 条；两组使用完全相同检查点。

误差定义：相对同一 gamma 下精确 Schur 的 Frobenius 误差，分母为 ||H*||+1e-8。预算0为已有 K(Z0) 二阶投影修正；预算k是最多k次共同子空间扩展，并非完整算法迭代成本。

|预处理|问题|扩展预算|有效数|原SAEPS中位误差|修正中位误差|最差误差|改善数|
|---|---|---:|---:|---:|---:|---:|---:|
|gn-diagonal|ALL|0|21|0.100541|0.0129427|0.0820674|19|
|gn-diagonal|ALL|1|21|0.100541|0.0128327|0.081149|19|
|gn-diagonal|ALL|3|21|0.100541|0.0119778|0.0800702|19|
|gn-diagonal|ALL|5|21|0.100541|0.010988|0.0784418|19|
|gn-diagonal|ALL|10|21|0.100541|0.00872509|0.0769249|19|
|gn-diagonal|Allen-Cahn|0|9|0.278567|0.0070305|0.0541164|9|
|gn-diagonal|Allen-Cahn|1|9|0.278567|0.00694223|0.0540465|9|
|gn-diagonal|Allen-Cahn|3|9|0.278567|0.00676762|0.0539968|9|
|gn-diagonal|Allen-Cahn|5|9|0.278567|0.00660464|0.053943|9|
|gn-diagonal|Allen-Cahn|10|9|0.278567|0.00622892|0.0521408|9|
|gn-diagonal|Burgers|0|12|0.0750323|0.0197357|0.0820674|10|
|gn-diagonal|Burgers|1|12|0.0750323|0.0192376|0.081149|10|
|gn-diagonal|Burgers|3|12|0.0750323|0.0185878|0.0800702|10|
|gn-diagonal|Burgers|5|12|0.0750323|0.0180256|0.0784418|10|
|gn-diagonal|Burgers|10|12|0.0750323|0.0160737|0.0769249|10|
|gn-exact|ALL|0|21|0.100541|0.0129427|0.0820674|19|
|gn-exact|ALL|1|21|0.100541|0.000858833|0.0218409|21|
|gn-exact|ALL|3|21|0.100541|5.58502e-07|0.000586312|21|
|gn-exact|ALL|5|21|0.100541|4.2679e-10|4.10755e-06|21|
|gn-exact|ALL|10|21|0.100541|3.38631e-12|1.56106e-11|21|
|gn-exact|Allen-Cahn|0|9|0.278567|0.0070305|0.0541164|9|
|gn-exact|Allen-Cahn|1|9|0.278567|0.000150802|0.0218409|9|
|gn-exact|Allen-Cahn|3|9|0.278567|7.14748e-08|7.67736e-05|9|
|gn-exact|Allen-Cahn|5|9|0.278567|1.50265e-11|1.36299e-07|9|
|gn-exact|Allen-Cahn|10|9|0.278567|1.42397e-12|8.28849e-12|9|
|gn-exact|Burgers|0|12|0.0750323|0.0197357|0.0820674|10|
|gn-exact|Burgers|1|12|0.0750323|0.000993656|0.0170779|12|
|gn-exact|Burgers|3|12|0.0750323|1.80957e-06|0.000586312|12|
|gn-exact|Burgers|5|12|0.0750323|7.5006e-10|4.10755e-06|12|
|gn-exact|Burgers|10|12|0.0750323|4.99291e-12|1.56106e-11|12|

## 核验

归档SAEPS最大相对复核差：3.19693e-11；归档精确Schur最大相对复核差：1.90585e-11。
配方恒等式最大相对残差：1.9116e-11。正半定间隙、嵌套单调性和已有修正公式在1e-8尺度容差内通过。基线复核容差1e-6。
16组随机SPD、仿射退化、非正定拒绝、原无效保留与实际CLI覆盖保护均通过。以上容差用于工程核验，不是新增科学支持阈值。

## 变差记录

|预处理|问题|seed|预算|原误差|修正误差|
|---|---|---:|---:|---:|---:|
|gn-diagonal|Burgers|59|0|0.021715|0.0599441|
|gn-diagonal|Burgers|59|1|0.021715|0.0582211|
|gn-diagonal|Burgers|59|3|0.021715|0.0576242|
|gn-diagonal|Burgers|59|5|0.021715|0.056677|
|gn-diagonal|Burgers|59|10|0.021715|0.0551962|
|gn-diagonal|Burgers|67|0|0.0420263|0.0820674|
|gn-diagonal|Burgers|67|1|0.0420263|0.081149|
|gn-diagonal|Burgers|67|3|0.0420263|0.0800702|
|gn-diagonal|Burgers|67|5|0.0420263|0.0784418|
|gn-diagonal|Burgers|67|10|0.0420263|0.0769249|
|gn-exact|Burgers|59|0|0.021715|0.0599441|
|gn-exact|Burgers|67|0|0.0420263|0.0820674|

K(Z0)高于精确Schur不代表它必然比原SAEPS更接近参考；这些变差样本保留，不调参消除。

## 保留的无效检查点

- Allen-Cahn seed 81: CHECKPOINT_INVALID — frozen center policy failed
- Burgers seed 57: CHECKPOINT_INVALID — frozen center policy failed
- Burgers seed 61: CHECKPOINT_INVALID — frozen center policy failed
- Burgers seed 63: CHECKPOINT_INVALID — frozen center policy failed

## 解释与下一步边界

结果支持继续研究二阶响应修正。对角预处理下增加少量方向收益有限，精确GN控制组收益显著；这提示预处理可能是主要瓶颈，但不是因果证明。
gn-exact每次使用稠密状态求解，只是乐观控制组；当前矩阵规模小，且初始GN响应与验证oracle均用稠密求解。没有独立组件计时、HVP成本或可扩展性证据，尚未满足“同等误差下成本更低”的进阶条件。
不自动启动第二层训练。下一步应先研究可扩展预处理与完整成本测量；新的确认评价必须冻结新配置并使用独立种子/观测。精确Schur代数的一致性不能替代nonlinear profile验证。

## 全部有效检查点逐预算数据

|预处理|问题|seed|预算|状态维数|子空间维数|原误差|修正误差|
|---|---|---:|---:|---:|---:|---:|---:|
|gn-diagonal|Allen-Cahn|75|0|33|0|0.244784|0.00164783|
|gn-diagonal|Allen-Cahn|75|1|33|1|0.244784|0.00160597|
|gn-diagonal|Allen-Cahn|75|3|33|3|0.244784|0.00151509|
|gn-diagonal|Allen-Cahn|75|5|33|5|0.244784|0.00148063|
|gn-diagonal|Allen-Cahn|75|10|33|10|0.244784|0.001345|
|gn-diagonal|Allen-Cahn|76|0|33|0|0.119892|0.00291128|
|gn-diagonal|Allen-Cahn|76|1|33|1|0.119892|0.00286625|
|gn-diagonal|Allen-Cahn|76|3|33|3|0.119892|0.00283667|
|gn-diagonal|Allen-Cahn|76|5|33|5|0.119892|0.00278353|
|gn-diagonal|Allen-Cahn|76|10|33|10|0.119892|0.00257333|
|gn-diagonal|Allen-Cahn|77|0|33|0|0.390497|0.00933295|
|gn-diagonal|Allen-Cahn|77|1|33|1|0.390497|0.00920473|
|gn-diagonal|Allen-Cahn|77|3|33|3|0.390497|0.00915951|
|gn-diagonal|Allen-Cahn|77|5|33|5|0.390497|0.00908873|
|gn-diagonal|Allen-Cahn|77|10|33|10|0.390497|0.00872509|
|gn-diagonal|Allen-Cahn|78|0|33|0|0.281678|0.00146566|
|gn-diagonal|Allen-Cahn|78|1|33|1|0.281678|0.00128644|
|gn-diagonal|Allen-Cahn|78|3|33|3|0.281678|0.00126688|
|gn-diagonal|Allen-Cahn|78|5|33|5|0.281678|0.00123801|
|gn-diagonal|Allen-Cahn|78|10|33|10|0.281678|0.00112572|
|gn-diagonal|Allen-Cahn|79|0|33|0|0.466723|0.00287442|
|gn-diagonal|Allen-Cahn|79|1|33|1|0.466723|0.0025827|
|gn-diagonal|Allen-Cahn|79|3|33|3|0.466723|0.00253984|
|gn-diagonal|Allen-Cahn|79|5|33|5|0.466723|0.00252032|
|gn-diagonal|Allen-Cahn|79|10|33|10|0.466723|0.00244906|
|gn-diagonal|Allen-Cahn|80|0|33|0|0.366263|0.0070305|
|gn-diagonal|Allen-Cahn|80|1|33|1|0.366263|0.00694223|
|gn-diagonal|Allen-Cahn|80|3|33|3|0.366263|0.00676762|
|gn-diagonal|Allen-Cahn|80|5|33|5|0.366263|0.00660464|
|gn-diagonal|Allen-Cahn|80|10|33|10|0.366263|0.00622892|
|gn-diagonal|Allen-Cahn|82|0|33|0|0.155524|0.0092228|
|gn-diagonal|Allen-Cahn|82|1|33|1|0.155524|0.00894858|
|gn-diagonal|Allen-Cahn|82|3|33|3|0.155524|0.00850482|
|gn-diagonal|Allen-Cahn|82|5|33|5|0.155524|0.00818908|
|gn-diagonal|Allen-Cahn|82|10|33|10|0.155524|0.00759196|
|gn-diagonal|Allen-Cahn|83|0|33|0|0.218192|0.0129427|
|gn-diagonal|Allen-Cahn|83|1|33|1|0.218192|0.0128327|
|gn-diagonal|Allen-Cahn|83|3|33|3|0.218192|0.0125849|
|gn-diagonal|Allen-Cahn|83|5|33|5|0.218192|0.0121367|
|gn-diagonal|Allen-Cahn|83|10|33|10|0.218192|0.0112659|
|gn-diagonal|Allen-Cahn|84|0|33|0|0.278567|0.0541164|
|gn-diagonal|Allen-Cahn|84|1|33|1|0.278567|0.0540465|
|gn-diagonal|Allen-Cahn|84|3|33|3|0.278567|0.0539968|
|gn-diagonal|Allen-Cahn|84|5|33|5|0.278567|0.053943|
|gn-diagonal|Allen-Cahn|84|10|33|10|0.278567|0.0521408|
|gn-diagonal|Burgers|55|0|65|0|0.0789617|0.0100727|
|gn-diagonal|Burgers|55|1|65|1|0.0789617|0.00926333|
|gn-diagonal|Burgers|55|3|65|3|0.0789617|0.00854488|
|gn-diagonal|Burgers|55|5|65|5|0.0789617|0.00742965|
|gn-diagonal|Burgers|55|10|65|10|0.0789617|0.00517759|
|gn-diagonal|Burgers|56|0|65|0|0.0922864|0.0321202|
|gn-diagonal|Burgers|56|1|65|1|0.0922864|0.031768|
|gn-diagonal|Burgers|56|3|65|3|0.0922864|0.0315171|
|gn-diagonal|Burgers|56|5|65|5|0.0922864|0.0309975|
|gn-diagonal|Burgers|56|10|65|10|0.0922864|0.0294444|
|gn-diagonal|Burgers|58|0|65|0|0.0142054|0.0105092|
|gn-diagonal|Burgers|58|1|65|1|0.0142054|0.010339|
|gn-diagonal|Burgers|58|3|65|3|0.0142054|0.00995766|
|gn-diagonal|Burgers|58|5|65|5|0.0142054|0.00957419|
|gn-diagonal|Burgers|58|10|65|10|0.0142054|0.00850524|
|gn-diagonal|Burgers|59|0|65|0|0.021715|0.0599441|
|gn-diagonal|Burgers|59|1|65|1|0.021715|0.0582211|
|gn-diagonal|Burgers|59|3|65|3|0.021715|0.0576242|
|gn-diagonal|Burgers|59|5|65|5|0.021715|0.056677|
|gn-diagonal|Burgers|59|10|65|10|0.021715|0.0551962|
|gn-diagonal|Burgers|60|0|65|0|0.0967368|0.00862663|
|gn-diagonal|Burgers|60|1|65|1|0.0967368|0.00824838|
|gn-diagonal|Burgers|60|3|65|3|0.0967368|0.00747886|
|gn-diagonal|Burgers|60|5|65|5|0.0967368|0.00706137|
|gn-diagonal|Burgers|60|10|65|10|0.0967368|0.00626344|
|gn-diagonal|Burgers|62|0|65|0|0.0711029|0.0199043|
|gn-diagonal|Burgers|62|1|65|1|0.0711029|0.0195011|
|gn-diagonal|Burgers|62|3|65|3|0.0711029|0.018905|
|gn-diagonal|Burgers|62|5|65|5|0.0711029|0.0180218|
|gn-diagonal|Burgers|62|10|65|10|0.0711029|0.0154731|
|gn-diagonal|Burgers|64|0|65|0|0.0699458|0.0478502|
|gn-diagonal|Burgers|64|1|65|1|0.0699458|0.0473341|
|gn-diagonal|Burgers|64|3|65|3|0.0699458|0.0461124|
|gn-diagonal|Burgers|64|5|65|5|0.0699458|0.0452543|
|gn-diagonal|Burgers|64|10|65|10|0.0699458|0.0411324|
|gn-diagonal|Burgers|65|0|65|0|0.100541|0.0188982|
|gn-diagonal|Burgers|65|1|65|1|0.100541|0.0181906|
|gn-diagonal|Burgers|65|3|65|3|0.100541|0.0173238|
|gn-diagonal|Burgers|65|5|65|5|0.100541|0.0168546|
|gn-diagonal|Burgers|65|10|65|10|0.100541|0.0150811|
|gn-diagonal|Burgers|66|0|65|0|0.0843159|0.0224363|
|gn-diagonal|Burgers|66|1|65|1|0.0843159|0.0221275|
|gn-diagonal|Burgers|66|3|65|3|0.0843159|0.0212987|
|gn-diagonal|Burgers|66|5|65|5|0.0843159|0.0208888|
|gn-diagonal|Burgers|66|10|65|10|0.0843159|0.0167104|
|gn-diagonal|Burgers|67|0|65|0|0.0420263|0.0820674|
|gn-diagonal|Burgers|67|1|65|1|0.0420263|0.081149|
|gn-diagonal|Burgers|67|3|65|3|0.0420263|0.0800702|
|gn-diagonal|Burgers|67|5|65|5|0.0420263|0.0784418|
|gn-diagonal|Burgers|67|10|65|10|0.0420263|0.0769249|
|gn-diagonal|Burgers|68|0|65|0|0.207051|0.0135873|
|gn-diagonal|Burgers|68|1|65|1|0.207051|0.0130003|
|gn-diagonal|Burgers|68|3|65|3|0.207051|0.0119778|
|gn-diagonal|Burgers|68|5|65|5|0.207051|0.010988|
|gn-diagonal|Burgers|68|10|65|10|0.207051|0.00684839|
|gn-diagonal|Burgers|69|0|65|0|0.0551079|0.0195671|
|gn-diagonal|Burgers|69|1|65|1|0.0551079|0.0189741|
|gn-diagonal|Burgers|69|3|65|3|0.0551079|0.0182707|
|gn-diagonal|Burgers|69|5|65|5|0.0551079|0.0180294|
|gn-diagonal|Burgers|69|10|65|10|0.0551079|0.0166743|
|gn-exact|Allen-Cahn|75|0|33|0|0.244784|0.00164783|
|gn-exact|Allen-Cahn|75|1|33|1|0.244784|6.29864e-05|
|gn-exact|Allen-Cahn|75|3|33|3|0.244784|2.47003e-08|
|gn-exact|Allen-Cahn|75|5|33|5|0.244784|5.0554e-13|
|gn-exact|Allen-Cahn|75|10|33|9|0.244784|3.61921e-13|
|gn-exact|Allen-Cahn|76|0|33|0|0.119892|0.00291128|
|gn-exact|Allen-Cahn|76|1|33|1|0.119892|5.87951e-05|
|gn-exact|Allen-Cahn|76|3|33|3|0.119892|6.14824e-08|
|gn-exact|Allen-Cahn|76|5|33|5|0.119892|1.50265e-11|
|gn-exact|Allen-Cahn|76|10|33|10|0.119892|1.42397e-12|
|gn-exact|Allen-Cahn|77|0|33|0|0.390497|0.00933295|
|gn-exact|Allen-Cahn|77|1|33|1|0.390497|0.000953039|
|gn-exact|Allen-Cahn|77|3|33|3|0.390497|5.58502e-07|
|gn-exact|Allen-Cahn|77|5|33|5|0.390497|1.07377e-09|
|gn-exact|Allen-Cahn|77|10|33|10|0.390497|1.84047e-12|
|gn-exact|Allen-Cahn|78|0|33|0|0.281678|0.00146566|
|gn-exact|Allen-Cahn|78|1|33|1|0.281678|2.0714e-05|
|gn-exact|Allen-Cahn|78|3|33|3|0.281678|5.35253e-09|
|gn-exact|Allen-Cahn|78|5|33|5|0.281678|9.0694e-13|
|gn-exact|Allen-Cahn|78|10|33|9|0.281678|2.93422e-13|
|gn-exact|Allen-Cahn|79|0|33|0|0.466723|0.00287442|
|gn-exact|Allen-Cahn|79|1|33|1|0.466723|0.000120957|
|gn-exact|Allen-Cahn|79|3|33|3|0.466723|1.45616e-08|
|gn-exact|Allen-Cahn|79|5|33|5|0.466723|1.18445e-12|
|gn-exact|Allen-Cahn|79|10|33|8|0.466723|2.03692e-12|
|gn-exact|Allen-Cahn|80|0|33|0|0.366263|0.0070305|
|gn-exact|Allen-Cahn|80|1|33|1|0.366263|0.000150802|
|gn-exact|Allen-Cahn|80|3|33|3|0.366263|7.14748e-08|
|gn-exact|Allen-Cahn|80|5|33|5|0.366263|2.00408e-12|
|gn-exact|Allen-Cahn|80|10|33|9|0.366263|8.01633e-13|
|gn-exact|Allen-Cahn|82|0|33|0|0.155524|0.0092228|
|gn-exact|Allen-Cahn|82|1|33|1|0.155524|0.00110159|
|gn-exact|Allen-Cahn|82|3|33|3|0.155524|7.42829e-06|
|gn-exact|Allen-Cahn|82|5|33|5|0.155524|1.20933e-08|
|gn-exact|Allen-Cahn|82|10|33|10|0.155524|3.18879e-13|
|gn-exact|Allen-Cahn|83|0|33|0|0.218192|0.0129427|
|gn-exact|Allen-Cahn|83|1|33|1|0.218192|0.00120758|
|gn-exact|Allen-Cahn|83|3|33|3|0.218192|7.85928e-07|
|gn-exact|Allen-Cahn|83|5|33|5|0.218192|7.34431e-10|
|gn-exact|Allen-Cahn|83|10|33|10|0.218192|8.28849e-12|
|gn-exact|Allen-Cahn|84|0|33|0|0.278567|0.0541164|
|gn-exact|Allen-Cahn|84|1|33|1|0.278567|0.0218409|
|gn-exact|Allen-Cahn|84|3|33|3|0.278567|7.67736e-05|
|gn-exact|Allen-Cahn|84|5|33|5|0.278567|1.36299e-07|
|gn-exact|Allen-Cahn|84|10|33|10|0.278567|5.92615e-12|
|gn-exact|Burgers|55|0|65|0|0.0789617|0.0100727|
|gn-exact|Burgers|55|1|65|1|0.0789617|0.00045798|
|gn-exact|Burgers|55|3|65|3|0.0789617|1.00725e-07|
|gn-exact|Burgers|55|5|65|5|0.0789617|4.01403e-11|
|gn-exact|Burgers|55|10|65|10|0.0789617|4.83486e-12|
|gn-exact|Burgers|56|0|65|0|0.0922864|0.0321202|
|gn-exact|Burgers|56|1|65|1|0.0922864|0.00443078|
|gn-exact|Burgers|56|3|65|3|0.0922864|2.8386e-05|
|gn-exact|Burgers|56|5|65|5|0.0922864|1.76359e-07|
|gn-exact|Burgers|56|10|65|10|0.0922864|1.11428e-11|
|gn-exact|Burgers|58|0|65|0|0.0142054|0.0105092|
|gn-exact|Burgers|58|1|65|1|0.0142054|0.000300939|
|gn-exact|Burgers|58|3|65|3|0.0142054|4.94441e-07|
|gn-exact|Burgers|58|5|65|5|0.0142054|2.14851e-10|
|gn-exact|Burgers|58|10|65|10|0.0142054|3.38631e-12|
|gn-exact|Burgers|59|0|65|0|0.021715|0.0599441|
|gn-exact|Burgers|59|1|65|1|0.021715|0.0169597|
|gn-exact|Burgers|59|3|65|3|0.021715|0.000586312|
|gn-exact|Burgers|59|5|65|5|0.021715|4.10755e-06|
|gn-exact|Burgers|59|10|65|10|0.021715|5.15096e-12|
|gn-exact|Burgers|60|0|65|0|0.0967368|0.00862663|
|gn-exact|Burgers|60|1|65|1|0.0967368|8.52641e-05|
|gn-exact|Burgers|60|3|65|3|0.0967368|4.13575e-08|
|gn-exact|Burgers|60|5|65|5|0.0967368|7.55319e-12|
|gn-exact|Burgers|60|10|65|9|0.0967368|1.95288e-12|
|gn-exact|Burgers|62|0|65|0|0.0711029|0.0199043|
|gn-exact|Burgers|62|1|65|1|0.0711029|0.000368887|
|gn-exact|Burgers|62|3|65|3|0.0711029|1.1666e-06|
|gn-exact|Burgers|62|5|65|5|0.0711029|2.57495e-10|
|gn-exact|Burgers|62|10|65|10|0.0711029|1.54061e-11|
|gn-exact|Burgers|64|0|65|0|0.0699458|0.0478502|
|gn-exact|Burgers|64|1|65|1|0.0699458|0.00520382|
|gn-exact|Burgers|64|3|65|3|0.0699458|3.60014e-05|
|gn-exact|Burgers|64|5|65|5|0.0699458|8.52219e-08|
|gn-exact|Burgers|64|10|65|10|0.0699458|5.04964e-13|
|gn-exact|Burgers|65|0|65|0|0.100541|0.0188982|
|gn-exact|Burgers|65|1|65|1|0.100541|0.00112848|
|gn-exact|Burgers|65|3|65|3|0.100541|2.45254e-06|
|gn-exact|Burgers|65|5|65|5|0.100541|1.07333e-09|
|gn-exact|Burgers|65|10|65|10|0.100541|1.56106e-11|
|gn-exact|Burgers|66|0|65|0|0.0843159|0.0224363|
|gn-exact|Burgers|66|1|65|1|0.0843159|0.000858833|
|gn-exact|Burgers|66|3|65|3|0.0843159|5.49086e-07|
|gn-exact|Burgers|66|5|65|5|0.0843159|4.2679e-10|
|gn-exact|Burgers|66|10|65|10|0.0843159|3.7054e-12|
|gn-exact|Burgers|67|0|65|0|0.0420263|0.0820674|
|gn-exact|Burgers|67|1|65|1|0.0420263|0.0170779|
|gn-exact|Burgers|67|3|65|3|0.0420263|0.000145451|
|gn-exact|Burgers|67|5|65|5|0.0420263|1.9659e-07|
|gn-exact|Burgers|67|10|65|10|0.0420263|7.00491e-13|
|gn-exact|Burgers|68|0|65|0|0.207051|0.0135873|
|gn-exact|Burgers|68|1|65|1|0.207051|0.000165446|
|gn-exact|Burgers|68|3|65|3|0.207051|2.58008e-08|
|gn-exact|Burgers|68|5|65|5|0.207051|6.66275e-13|
|gn-exact|Burgers|68|10|65|9|0.207051|1.1781e-11|
|gn-exact|Burgers|69|0|65|0|0.0551079|0.0195671|
|gn-exact|Burgers|69|1|65|1|0.0551079|0.00143823|
|gn-exact|Burgers|69|3|65|3|0.0551079|4.67154e-06|
|gn-exact|Burgers|69|5|65|5|0.0551079|7.42155e-09|
|gn-exact|Burgers|69|10|65|10|0.0551079|6.34295e-12|

## 全仓库验证

全仓库状态：FAILED。本试验独立审计状态与全仓库状态分别报告。
- scientific_gate_and_final_mapping: FAIL；详情见 repository_validation.json。
- unit_and_integration_tests: FAIL；详情见 repository_validation.json。
全仓库剩余失败源于任务开始前已删除的历史报告/协议文件；未替用户恢复这些文件，未推送远端。
