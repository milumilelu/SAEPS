# SAEPS V5 JCP Gap-Closure Execution Plan

**状态：** `PLANNING_ONLY / NOT_AUTHORIZED_FOR_SCIENTIFIC_EXECUTION`

**权威科学协议：** `V5_JCP_MINIMAL_PROTOCOL.md`

**协议 SHA-256：** `274b1179ace363cdd61897c05c43001a9435cbbf2f8d0caa58ef09a7dd796b52`

**制定日期：** 2026-08-23

## 1. 目标、边界与当前判断

V5 只关闭四个 JCP 证据缺口：有限 `gamma`/有效秩依赖、exact reduced Hessian 与 nonlinear profile 的桥接、耦合双参数比较优势、残差维数 `m` 的 matrix-free 成本。V5 不重做已经关闭的 scalar efficacy，不救 controlled mechanism，不扩展第三 PDE、真实数据、宽网络或额外 confirmation。

科学状态只允许 `SUPPORTED`、`PARTIALLY_SUPPORTED`、`NOT_SUPPORTED`、`INCONCLUSIVE`；工程状态单独使用 `PASSED`、`FAILED`、`BLOCKED`。正确执行的阴性科学结果属于实验完成。

当前仓库**尚未准备好运行 V5 科学 seed**，原因见第 11 节。本文档只规定实现链与授权条件，不授权任何 V5 development、held-out、confirmation 或 production-scale run。

## 2. 历史证据与不可变边界

| 范围 | 状态 | V5 使用方式 |
|---|---|---|
| v3.6 seeds `30--44` | 永久关闭，历史 `NOT_SUPPORTED`（execution-semantics failure） | 只读；不重跑、不修正聚合 |
| v4.2 Burgers `55--69` | `SUPPORTED`，12/15 valid/wins | 继承 scalar 主证据；不得用于 V5 checkpoint 选择 |
| v4.3 Allen development `70--74` | development | 只允许协议规定的 V5.1/V5.2 工程复用 |
| v4.4 Allen confirmation `75--84` | `SUPPORTED`，9/10 valid/wins | 只读继承；禁止 V5 重跑或 profile 调试 |
| v4.5 controlled `85--99`，尤其 `90--99` | `NOT_SUPPORTED` | 历史阴性证据必须保留；不再 rescue |
| v4.6 two-parameter `100--116` | engineering `100--102` 3/3；held-out `115--116` 1/2；`105--114` 永久未授权 | 只读背景；禁止重新激活旧 confirmation |
| v4.7 scalability `120--124` | cost-only `PASSED` | V5.4 可复用数值构造，但不能冒充科学 checkpoint |
| v4.8 robustness `130--139` | 已关闭；wide architecture 暴露 center failure | 只读继承 |

保护实现：V5 validator 必须递归计算历史 raw/manifest 哈希清单；所有 V5 写入仅允许 `outputs/runs/v5/`、`docs/evidence/v5/`、`paper_artifacts/v5/`。任何历史路径变化立即 `BLOCKED`。

## 3. 总体执行顺序与授权图

```text
V5.0 governance freeze
  ├─> V5.1 finite-gamma descriptive audit
  ├─> V5.2A profile engineering (70--74)
  │     └─ freeze ─> V5.2B held-out (200--204) ─> profile adjudication
  ├─> V5.3A center-only development (210--212)
  │     └─ 3/3 ─> freeze ─> V5.3B held-out (213--214)
  │                       └─ 2/2 ─> one-shot V5.3C (215--224)
  ├─> V5.4 residual-dimension cost audit
  └─> V5.5 baseline consolidation
              └─ all terminal records ─> V5.6 final audit
```

V5.1、V5.2、V5.3、V5.4 在科学问题上相互独立，但每条链必须先经过 V5.0；计算可串行安排，避免资源竞争与证据混淆。V5.5 等待 V5.2B；V5.6 等待所有已授权分支达到终态，包括停止或阴性终态。

## 4. V5.0 — Governance Freeze

- **类型：** governance / engineering。
- **目的：** 将协议、seed、gate、schema、可执行代码和历史保护边界冻结为机器可核验对象。
- **输入：** 本协议、现有 governance、V4 final audit、历史 manifests；不读科学结果来改变 V5 阈值。
- **新增文件：**
  - `docs/v5/V5_JCP_MINIMAL_PROTOCOL.md`：根协议的 byte-identical 受控副本；
  - `docs/v5/V5_PROTOCOL_FREEZE.md`、`V5_SCIENTIFIC_GATES.md`、`V5_SEED_REGISTRY.md`、`V5_SEMANTIC_GATE_GRAPH.md`；
  - `configs/v5/*.yaml` 与随后生成的 `configs/v5/locked/*.yaml`；
  - `src/saeps/v5/{governance,schemas,validation,provenance}.py`；
  - `scripts/60_validate_v5_governance.py`、对应 tests。
- **seed registry：** 明确 historical/protected、development、held-out、confirmation、cost-checkpoint 五类；禁止命名空间重叠。
- **raw schema 公共字段：** schema/phase/role/seed-or-checkpoint/config hash/source hashes/git commit/dirty state/hardware/device/dtype/package versions/timestamps/timing/status/failure stage/failure reason/binding validity；每个 numerical object 独立 status。
- **gate：** byte/hash、seed disjointness、output path allowlist、planned denominator、confirmation prior-output absence、excluded-outcome access lint、raw→aggregate lineage 全部 `PASSED`。
- **失败行为：** 任一 governance check 失败即 `BLOCKED`，不得进入 V5.1--V5.5。
- **验收：** 冻结 commit 必须干净、tests 与 repository validator 通过；confirmation 必须另有 clean preflight 与一次性 authorization record。
- **计算：** 无训练；秒至分钟级静态验证。

## 5. V5.1 — Finite-gamma / Effective-Rank Audit

- **问题：** SAEPS 的 state absorption 与 GN error 如何随有限 `gamma` 及 `J_theta` 有效秩变化；高 `gamma` 是否回到 raw 极限。
- **类型：** descriptive sensitivity audit；无“SAEPS 必须赢”的 gate。
- **依赖：** V5.0 `PASSED`；checkpoint 可实际加载；第 11.1 阻断已解决。
- **输入选择：**
  - Burgers：仅按既有 binding status 与 seed 顺序，从 v4.1 engineering pool 取首 3 个，即拟定 `45,46,47`；
  - Allen--Cahn：仅按既有 binding status 与 seed 顺序从 `70--74` 取首 3 个，即 `70,71,72`；
  - 选择过程禁止读取 `eta`、`D`、误差或图。
- **配置：** `configs/v5/finite_gamma_audit.yaml`，锁定 `alpha=[1e-10,1e-8,1e-6,1e-4,1e-2,1,1e2]`，`gamma=alpha*lambda_max(J_theta^T J_theta)`，记录 power/eigendecomposition 方法与 tolerance。
- **复用：** PDE residual builders、V4.1/V4.3 center objects、explicit Jacobian、`full_hessian_references`、scaled LSQR/LSMR、provenance/hash utilities。
- **新增：** `src/saeps/v5/finite_gamma.py`、runner、validator、aggregator；小系统优先 explicit/direct，matrix-free 只作一致性检查。
- **每 checkpoint × alpha raw record：** `F_raw`、`F_se_GN`、exact finite-gamma `H_red`、`E_raw`、`E_SAEPS`、`eta`、`J_theta` singular spectrum、`lambda_max`、`m`、`n_theta`、effective-rank definition/value、solve residuals/statuses。
- **数值 gate：** finite values；matrix symmetry；direct residual；explicit/matrix-free 相对误差；gamma 使用同一 `lambda_max`；7/7 alpha 有终态。失败项保留，不替换 checkpoint。
- **端点：** alpha 曲线、high-gamma `F_se_GN→F_raw` relative gap、low-gamma absorption trend、effective-rank association；只描述，不以结果校准 nominal gamma。
- **聚合/报告：** `outputs/runs/v5/finite_gamma/...` → `docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.{md,json}`；图表自动读取同一 aggregate。
- **失败/停止：** checkpoint 不可加载则 `BLOCKED`；数值项失败为 terminal record，不允许换 checkpoint。
- **测试：** gamma formula、direct Schur identity、high-gamma synthetic limit、selection blindness、7-level completeness、raw-to-summary reproduction。
- **计算：** 0 次训练，6 checkpoints × 7 alpha = 42 小型分解/求解；预计 CPU 分钟级。若被迫重建 checkpoint，则不再满足“0 training”，必须先修订执行授权而非静默执行。

## 6. V5.2 — Nonlinear Profile Bridge Resolution

### 6.1 V5.2A Profile engineering

- **问题：** 有限 `gamma` exact reduced Hessian 是否等于独立重优化后的 nonlinear profile 局部曲率。
- **类型：** engineering/development。
- **依赖：** V5.0 `PASSED`；Allen old-development seeds only。
- **seeds：** `70--74`；严禁读取 `75--84`。
- **目标函数：** `Phi_gamma(s)=min_theta[0.5||r(theta,q0+s)||² + gamma/2||theta-theta0||²]`。复用代码时保持 residual-sum scaling；现有 mean-scaled optimizer 的 profile curvature 必须乘 `m`，已有 V3/V3.4 实现与此一致。
- **radius：** `h=[0.04,0.02,0.01,0.005]`；每个 `+/-h` 从同一 `theta0` 独立启动。continuation 可另存为非绑定 diagnostic，不能替代 primary independent starts。
- **可选 optimizer：** L-BFGS 与 Newton-CG/trust-region；选择只能依据 stationarity、optimization residual、symmetry、h-convergence、exact consistency，禁止使用 `D`、`E_raw`、`E_SAEPS` 或图形美观度。
- **复用/新增：** 复用 Allen residual/center、V3.1 exact state diagnostics、V3.4 profile accuracy audit与exact Hessian；新增 independent-start runner、optimizer comparison log、profile-specific schema与validator。
- **raw quantities：** center gates；每个点初值 hash、loss、gradient、state Hessian minimum eigenvalue、iterations、termination、wall time；每个 h 的 frozen/reoptimized objective、profile curvature；exact `H_red`、SAEPS、raw；smallest-two finite/convergence/error。
- **engineering freeze：** 选择 optimizer/config 后，冻结 config+runner+validators+tests；不得把 70--74 的 comparative outcomes写入选择器。

### 6.2 V5.2B Fresh held-out bridge

- **类型：** held-out scientific bridge。
- **seeds：** `200--204`，固定 5 个，无替换；每 seed 新训练中心。
- **执行：** center → exact finite-gamma → SAEPS/raw → 8 independent profile points → validation；fail-soft 保存此前可计算对象。
- **原协议 seed-level `PROFILE_VALID`：** center valid；8/8 point optimization；exact valid；smallest two finite；finest-h profile-vs-exact error `<=10%`；last-two relative change `<=5%`。
- **待裁决的 adjudication：** 见第 11.2。建议引入不改变数值阈值的 `PROFILE_EVALUABLE`：center、8/8 optimization、exact、smallest-two finite。随后：
  - evaluable `<4/5` → `INCONCLUSIVE`；
  - evaluable `>=4/5` 且 `PROFILE_VALID>=4/5` → `SUPPORTED`；
  - evaluable `>=4/5` 但 `PROFILE_VALID<4/5` → `NOT_SUPPORTED`，删除 nonlinear-profile-equivalence claim。
  在用户裁决前不得锁定或运行。
- **聚合/报告：** planned denominator 始终为 5；输出 seed table、失败阶段、profile/exact差、两最细尺度变化；`V5_PROFILE_BRIDGE_REPORT.{md,json}`。
- **停止：** 无 V5.2C rescue；阴性或 inconclusive 均终止此链。
- **测试：** independent initialization、objective scaling、8-point completeness、threshold boundaries、planned-denominator、三种 adjudication path、raw→plot lineage。
- **计算：** protocol nominal 为 5 次新训练 + 40 个 held-out reoptimizations；另有 70--74 engineering 的 optimizer trials。由于旧 theta 未保存，engineering 若需重训会额外增加最多 5 次训练，必须先获授权。

## 7. V5.3 — Coupled Two-Parameter Exact Geometry Confirmation

### 7.1 Common matrix semantics

- **benchmark：** 完全继承 V4.6 coupled PDE、双参数化、residual、loss、width 6、finite gamma gold standard与coupling gate。
- **矩阵：** `F_raw`、`F_se_GN`、exact finite-gamma `H_red`；均存完整 2×2 matrix、symmetry diagnostics、eigenvalues和solver statuses。
- **coordinate stabilization：** `B=F_raw+tau I`；沿用 V4.6 `tau=1e-10*max(trace(F_raw)/2,1)`，保存 `tau`。以 `B^{-1/2}` 双边白化，使用 Frobenius norm：`E_SAEPS^(2)=||B^-1/2(F_se-H_red)B^-1/2||_F/(||B^-1/2 H_red B^-1/2||_F+epsilon)`，raw 同理，`D^(2)=E_raw^(2)-E_SAEPS^(2)`；拟沿用 repository numerical floor `epsilon=1e-30`，须在 V5.0 明文锁定。
- **secondary：** generalized eigensystem、`B` normalization、exact directional curvature、eigengap和vectors。eigengap 解释阈值尚待第 11.3 裁决；不足时只报告特征值，不解释向量。

### 7.2 V5.3A Center-only development

- **类型/seeds：** development，`210--212`。
- **允许选择：** optimizer duration、deterministic L-BFGS、stationarity stopping、solver tolerances；只能看 center、solver residual、explicit/matrix-free一致性、exact validity与coupling，不得用 `D`、任一 E、favorable eigenvalues或plots。
- **防泄漏实现：** 两阶段 runner。阶段 A 只生成 center/numerical record，schema 不含 comparative fields；3/3 center candidate 后才用冻结候选运行非选择性完整链。
- **gate：** 3/3 complete binding chain；否则停止 V5.3，状态 `BLOCKED_BY_CENTER_AVAILABILITY`，不进入 held-out。

### 7.3 V5.3B Frozen executable held-out

- **类型/seeds：** held-out，`213--214`；byte-frozen executable。
- **gate：** 2/2 complete binding validity。1/2 或 0/2 即 `BLOCKED_BY_CENTER_AVAILABILITY`；不得修改后重跑，不得授权 confirmation。
- **artifact：** held-out raw/manifest、freeze verification、gate report与confirmation authorization decision。

### 7.4 V5.3C Untouched confirmation

- **类型/seeds：** one-shot confirmation，`215--224`，固定 planned denominator 10；仅在 A=3/3、B=2/2、clean preflight、zero prior output、独立 authorization 后运行。
- **primary：** 每 planned seed 的 `D^(2)`；invalid planned seeds 计为 planned non-win，不删除、不替换。
- **test：** valid non-tied paired directional exact sign test；同时报告 planned wins。ties 的 exact convention在 freeze 中复用 V4 aggregate convention并写入测试。
- **SUPPORTED：** valid `>=9/10`、planned wins `>=9/10`、valid median `D^(2)>0`、one-sided exact sign `p<=0.05` 全部满足。
- **INCONCLUSIVE：** valid `<9/10`。
- **NOT_SUPPORTED：** numerical coverage adequate（valid `>=9`）但任一 comparative requirement fail。
- **失败行为：** 所有 seed terminal；fail-soft；不重跑、不调阈值、不创建第三 PDE 或 rescue confirmation。
- **代码/产物：** `src/saeps/v5/two_parameter.py` 尽量封装 V4.6 kernels；独立 preflight/runner/aggregator/validator；`V5_TWO_PARAMETER_CONFIRMATION_REPORT.{md,json}` 与 failed-seed table。
- **测试：** whitened matrix calculation against direct NumPy/Torch reference、coordinate rescaling check、invalid-as-nonwin、sign test/ties、3/3→2/2→confirmation dependency、excluded-field absence、one-shot immutability。
- **计算：** 最多 15 次新训练（A 3 + B 2 + C 10）。confirmation 只在前两 gate 通过时发生。

## 8. V5.4 — Residual-Dimension Scalability Complement

- **问题：** matrix-free solve 在固定 `n_theta` 层级下随真实 residual count `m` 的成本与数值有效性如何变化。
- **类型：** cost-only engineering/descriptive audit；不产生 curvature efficacy claim。
- **依赖：** V5.0；可加载或可合法确定性重建 V4.7 function-preserving base checkpoint。
- **grid：** `n_theta≈[10^3,10^4,10^5]`（现有精确值 `1001,10001,100001`）× `m=[213,853,3413]`；每 condition 3 independent timing repeats，共 27。
- **建议固定 residual grids：** 复用 PDE residual定义并在 config 中显式列出 boundary/interior/initial grids，使总数精确为目标 `m`；freeze 前以真实 residual builder断言计数，不能靠padding synthetic rows。
- **复用：** V4.7 function-preserving width expansion、matrix-free normal operator、power gamma、CG/JVP/VJP计数、provenance。
- **计时语义：** 每 repeat 独立零初值；setup、power estimate、solve分开；允许未计入正式统计的固定次数 warm-up，但必须预注册且保存；不进行隐藏重试。
- **raw：** `n_theta,m,repeat`、wall/setup/solve、iterations、JVP/VJP、verified residual、status、peak memory（可靠时）、hardware/dtype/thread settings。
- **gate：** 27/27 terminal；operator finite；residual count exact；verified solver residual满足冻结 threshold。失败仍保留；不得因速度慢更换 condition。
- **端点：** 表格/曲线描述，不拟合或宣称过度解释的复杂度指数。
- **产物：** `V5_RESIDUAL_DIMENSION_SCALABILITY.{md,json}`。
- **测试：** 3×3×3 completeness、exact m counts、fresh initial guess、timer field separation、JVP/VJP accounting、small explicit cross-check。
- **计算：** 0 次训练、27 timings；按 V4.7 单次约秒级基线，增大 m 后预计 CPU 数分钟到数小时，必须在 dry-run 后给 wall-time 上界。checkpoint 缺失问题见第 11.1。

## 9. V5.5 — Baseline Consolidation

- **类型：** inherited evidence + descriptive visualization；0 新训练。
- **输入：** V4 closed aggregate与 V5.2 held-out `200--204` raw；不得手工录数。
- **每 profile-valid/evaluable seed 图层：** frozen `Phi`、SAEPS quadratic、gamma-reoptimized `Phi`；raw、SAEPS、exact、profile curvature；无效 seed 仍在表中显示失败原因。
- **实现：** 单一 machine-readable aggregate驱动 figures/tables；生成脚本禁止 literal paper-facing numerics；median与seed raw自动核对。
- **产物：** `paper_artifacts/v5/` 图表、baseline matrix、caption-ready scope statements；历史 controlled `NOT_SUPPORTED`、profile weakness、wide-center failure必须可见。
- **失败：** V5.2 `INCONCLUSIVE/NOT_SUPPORTED` 不阻止如实生成图表，只改变可用 claim。

## 10. V5.6 — Final JCP Evidence Audit

- **类型：** final read-only audit；无训练。
- **依赖：** 所有已授权分支均有 terminal report；未授权分支有 machine-readable stop record。
- **实现/产物：**
  - `V5_FINAL_JCP_AUDIT_REPORT.md`；
  - `docs/evidence/v5/v5_final_audit.json`；
  - `docs/evidence/v5/v5_final_validation.json`；
  - final paper-artifact manifest。
- **检查：** protocol/config/source/raw hashes；seed denominators；failed runs；raw→aggregate→table/figure reproduction；historical immutability；claim-to-evidence map；engineering/science status separation；repository validator；clean commit。
- **总体 adjudication：** 按协议情形 A--D与各 phase terminal state生成 `SUPPORTED/PARTIALLY_SUPPORTED/NOT_SUPPORTED/INCONCLUSIVE`，不能以投稿偏好覆盖 phase结果。
- **发布条件：** full tests + all V5 validators pass、无未解释 dirty files、commit可追溯。只有此时可宣布 V5完成。

## 11. 执行前阻断与待裁决问题

### 11.1 `BLOCKED` — checkpoint 张量没有落盘

仓库搜索未发现 V4 scientific/scalability checkpoint 的 `.pt/.pth/.npy/.npz`；V4.6/V4.7 JSON明确将 `theta` 写为 `None`，其他结果也只保存指标。因此 V5.1/V5.4 的“0 new training、reuse checkpoint”当前不可执行。

必须在下列方案中裁决其一：

1. 提供原始 checkpoint tensor 及其 hash/provenance；或
2. 明确授权按历史 frozen config确定性重建到**新 V5 路径**，承认这属于额外训练/重建且不保证跨环境 bit identity；重建选择不得读取 V5结果。

不得把重训暗称为 checkpoint reuse，也不得写回 V4路径。

### 11.2 `AMBIGUOUS` — profile bridge 阴性与不可评估分界

协议把 convergence/accuracy写入 `PROFILE_VALID`，又同时规定 `<4 PROFILE_VALID → INCONCLUSIVE` 以及“足够 valid profiles但系统不收敛 → NOT_SUPPORTED”。按单一 `PROFILE_VALID` 定义，后者无法触发。第 6.2 的两层 `PROFILE_EVALUABLE/PROFILE_VALID` 是建议裁决，不在确认前自动生效。

### 11.3 `AMBIGUOUS` — generalized eigenvector eigengap threshold

协议要求 eigengap足够时才解释 vectors，但未给阈值。该阈值只影响 secondary claim，不影响 primary `D^(2)`；仍须在 seed `210` 前以与 outcome无关的规则锁定，或明确规定 vectors永远只作描述不作方向解释。

### 11.4 Engineering clarifications proposed for freeze

下列不改变科学端点，可按既有 convention 在 V5.0 固定：`epsilon=1e-30`；V4.6 `tau` formula；sign test在 valid non-tied pairs上；invalid/tied planned项不计 planned win；profile mean objective乘 `m`回到 residual-sum curvature；V5.1 high/low gamma只报告连续指标不设 post-hoc pass threshold。

## 12. 新增代码与验证清单

预计新增 `src/saeps/v5/` 六类模块：governance/schema、finite-gamma、independent profile、two-parameter wrappers/aggregation、m-scaling、final audit；新增编号 `60+` scripts、`tests/test_v5_*.py`、`configs/v5/`、`docs/v5/`、`docs/evidence/v5/`、`outputs/runs/v5/`。只在必要处修改 repository validator、TASKS/README/GOAL，且不得改变 V4 runtime或raw。

实际端到端验收使用真实 PDE residual与真实训练/重优化流程；synthetic checks只覆盖公式、边界条件和gate semantics，不能代替 phase验收。

## 13. 计算预算

| 阶段 | 新训练 | 主要额外计算 |
|---|---:|---|
| V5.0 | 0 | 静态检查/tests |
| V5.1 | 0（checkpoint存在时） | 42 gamma evaluations |
| V5.2A | 0--5（取决于checkpoint裁决） | optimizer工程、多尺度profiles |
| V5.2B | 5 | 40 primary point reoptimizations |
| V5.3A/B | 5 | 双参数完整numerics |
| V5.3C | 0或10 | 仅A/B全过后 |
| V5.4 | 0 | 27 solver timings |
| V5.5/V5.6 | 0 | aggregation/audit |

协议名义 worst case 为 20 次新训练；在当前 checkpoint 缺失下，若授权重建 V5.2A，实际 worst case 为 25 次，另加 optimizer engineering。任何新增量必须在执行授权中显式记录。

## 14. Formal execution authorization condition

只有以下条件全部满足，才可将 `READY_FOR_V5_EXECUTION` 设为 `YES`：

1. 第 11.1 checkpoint策略已裁决；
2. 第 11.2 profile adjudication已裁决；
3. 第 11.3 eigengap处理已冻结；
4. V5.0 governance artifacts、configs、schemas、tests与historical hash inventory完成并通过；
5. 用户审查本计划并明确授权正式执行。

当前：`READY_FOR_V5_EXECUTION = NO`。
