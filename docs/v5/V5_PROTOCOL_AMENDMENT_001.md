# V5 Protocol Amendment 001 — Pre-execution adjudications

**日期：** 2026-08-23

**阶段：** V5.0 governance；任何 V5 科学实验之前

**parent protocol commit：** `126f125a91b4e0df654e8aa7dacb68fded68c3a8`

**parent protocol repository SHA-256：** `6abb0864cddb40fd63f29a24d97004c539727744d35b2ac9821888d0a90d0f12`

**parent source pre-normalization SHA-256：** `274b1179ace363cdd61897c05c43001a9435cbbf2f8d0caa58ef09a7dd796b52`

## 1. 修订性质与优先级

本修订只裁决启动审计发现的三个执行前问题，不改变 V5 的四个科学问题、confirmation cohorts、planned denominators、primary endpoints或数值阈值。有效 V5 协议是上述 parent protocol 与本修订的有序组合；冲突时本修订优先。

修订时 `outputs/runs/v5/` 不存在，seeds `200--204`、`210--224` 均无 V5 输出；没有 V5 scientific development、held-out、confirmation、gamma audit、profile或production scalability结果可供观察。因此三项裁决均不由结果驱动。

## 2. Decision 1 — V5 engineering reconstruction

历史 V4 JSON 没有保存可重载模型参数。现授权从冻结的历史 source seed、config与training semantics进行确定性重建，但不得称为“复用历史 checkpoint”或声称与历史tensor数值相同。

绑定规则：

1. 只写 V5-controlled paths；绝不修改 V2--V4 outputs。
2. artifact role固定为 `V5_RECONSTRUCTED_ENGINEERING_CHECKPOINT`。
3. 每个固定source seed最多重建一次；失败不重试、不换seed。
4. acceptance/retry/replacement/tuning不得读取任何V5科学结果。
5. Burgers固定重建`45,46,47`；Allen固定重建`70,71,72,73,74`。
6. Allen `70--72`可由V5.1和V5.2A共同读取同一V5 artifact；这不是历史V4 tensor reuse。
7. V5.4若需独立base，只允许重建一个。确定性规则固定为V4.7登记表中最小checkpoint ID `120`，即沿用`configs/v4_7/scalability.yaml`的source config与source seed `120`；选择不读取runtime、iteration、solver或科学结果。
8. 所有新训练或重建checkpoint必须保存可重载model state及SHA-256。
9. checkpoint manifest必须包含：`artifact_role`、`source_protocol`、`source_config_hash`、`source_seed`、`reconstruction_commit`、`model_state_hash`、`diagnostic_set_hash`、`dtype`、`device`与完整environment provenance。
10. 下游所需checkpoint缺少artifact、hash不符或不能reload时，V5 validator必须失败。

全V5保守训练/重建授权上限为`29`：9个engineering reconstructions（Burgers 3 + Allen 5 + scalability base 1）、V5.2B新训练5个、V5.3最多15个。29是ceiling，不是target；不需要的重建禁止执行。

**非结果驱动理由：** 裁决恢复协议所要求的可执行输入与provenance，不依据任何V5 curvature、error、profile或solver performance选择模型。

## 3. Decision 2 — profile two-level adjudication

对planned cohort `200--204`，定义：

`PROFILE_EVALUABLE = true` 当且仅当：center validity PASS；exact finite-gamma reference PASS；8个独立profile point全部满足冻结optimization gates；两个最小radius curvature有限。

`PROFILE_VALID = true` 当且仅当 `PROFILE_EVALUABLE = true`，且：finest-radius profile-vs-exact relative error `<=10%`；last-two-radius relative curvature change `<=5%`。

固定planned denominator为5：

- `n_evaluable < 4` → `INCONCLUSIVE`；
- `n_evaluable >= 4`且`n_profile_valid >= 4` → `SUPPORTED`；
- 其他情况 → `NOT_SUPPORTED`。

失败seed不得替换；不得创建V5.2C或rescue cohort。

**非结果驱动理由：** 该分类在任何V5 profile运行前解决numerical availability与scientific nonconvergence的逻辑分界，未改变10%、5%、4/5或planned denominator。

## 4. Decision 3 — non-binding generalized eigenvectors

V5.3 primary仍为预注册的`B`-whitened full-matrix errors与`D^(2)`。generalized eigen quantities全部secondary。

必须计算并保存generalized eigenvalues、eigenvectors、沿所得vectors的exact directional curvatures，以及维度无关relative eigengap：对升序二元eigenvalues `eta_1,eta_2`，定义

`relative_eigengap = |eta_2-eta_1| / max(|eta_1|, |eta_2|, 1e-30)`。

该量没有pass/fail threshold；eigenvector orientation不进入任何scientific adjudication；禁止跨seed声称稳定retained/absorbed directions。vectors只能连同eigengap描述，near-degenerate vectors不得作实质物理解释。generalized eigenvalues仍可作为secondary retained-geometry diagnostics报告。

**非结果驱动理由：** 删除任意post-hoc gap threshold，并明确把方向解释排除在primary与secondary gate之外。

## 5. Confirmation

本修订产生时没有任何V5 scientific output；它不授权V5.1或之后的任何科学阶段。V5.0全部governance artifacts与validators通过后，须另行报告`READY_FOR_V5_EXECUTION`，正式科学执行仍需用户后续指令。
