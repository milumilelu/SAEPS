# V5 Execution Plan Audit

**审计对象：** `docs/v5/V5_EXECUTION_PLAN.md`

**权威协议：** `V5_JCP_MINIMAL_PROTOCOL.md`，SHA-256 `274b1179ace363cdd61897c05c43001a9435cbbf2f8d0caa58ef09a7dd796b52`

**审计范围：** 规划一致性与非科学预检；未运行任何 V5 seed

**结论：** `CONDITIONALLY_SATISFIED / NOT READY FOR EXECUTION`

## 1. 审计方法

逐节检查协议中的 scientific question、scope、cohort、gate、stop rule、claim与交付物，并检查现有代码/证据是否支持计划中的复用。分类只使用 `SATISFIED`、`NOT_APPLICABLE`、`BLOCKED`、`AMBIGUOUS`。`SATISFIED` 表示计划忠实覆盖，不代表代码已实现或实验已通过。

## 2. Binding requirement audit

### V5 总体与 V5.0

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| V5 仅关闭四个指定 gap | SATISFIED | Plan §§1,3；无第三 PDE、真实数据或额外 rescue |
| 科学与工程状态分离 | SATISFIED | Plan §§1,4,10；两套状态空间 |
| 阴性结果不等于工程失败 | SATISFIED | Plan §§1,10 |
| 创建 V5 protocol/gates/seed registry/gate graph/config/output/evidence结构 | SATISFIED | Plan §4列出具体路径与freeze流程 |
| v2--v4.8 原始证据不可变 | SATISFIED | Plan §2与V5 output allowlist/hash inventory |
| historical negative/inconclusive evidence可见 | SATISFIED | Plan §§2,9,10 |
| paper-facing值不能手填 | SATISFIED | Plan §§4,9,10规定raw→aggregate单源 |
| 本启动任务不运行科学seed | SATISFIED | 仅执行read-only检查/tests；无`outputs/runs/v5` |

### V5.1 finite-gamma/effective-rank

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| 0 new training、existing development checkpoints only | BLOCKED | Plan §11.1；仓库无可加载theta checkpoint，不能虚构reuse |
| Burgers/Allen各首3个binding-valid，按seed且盲于结果 | SATISFIED | 拟定45--47与70--72；选择依据仅历史status |
| 不读取scalar confirmation选择checkpoint | SATISFIED | Plan §5明令禁止55--69/75--84作为选择源 |
| alpha 7-level family与gamma定义 | SATISFIED | 精确列出7 levels及`alpha*lambda_max` |
| 保存四曲率/误差/eta/spectrum/dim/rank | SATISFIED | Plan §5 raw schema完整覆盖 |
| 验证high-gamma raw limit与low-gamma absorption | SATISFIED | 定义连续diagnostics；不增加有利阈值 |
| 不以“必须赢”为gate，不重校nominal gamma | SATISFIED | descriptive-only adjudication |

### V5.2 nonlinear profile

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| V5.2A仅用Allen 70--74；不读75--84 | SATISFIED | Plan §6.1 |
| finite-gamma profile objective与sum scaling | SATISFIED | 明确公式及mean-to-sum乘m；代码检查确认V3/V3.4已有相同换算 |
| h固定为.04,.02,.01,.005 | SATISFIED | Plan §6.1 |
| 每点从同一theta0独立启动 | SATISFIED | primary independent runner；continuation仅非绑定diagnostic |
| optimizer选择仅依据允许数值量 | SATISFIED | exclusion list及两阶段选择流程 |
| held-out seeds 200--204，5个不可替换 | SATISFIED | Plan §6.2，planned denominator=5 |
| 每seed训练center并保存 frozen/reoptimized/exact/SAEPS/raw | SATISFIED | raw schema与execution chain覆盖 |
| PROFILE_VALID全部条件 | SATISFIED | 六项条件及10%/5%阈值逐项保留 |
| >=4/5 PROFILE_VALID为supported | SATISFIED | proposed adjudication保留该条件 |
| <4 valid为INCONCLUSIVE vs systematic nonconvergence为NOT_SUPPORTED | AMBIGUOUS | 协议两条在单一valid定义下冲突；Plan §11.2要求裁决evaluable层 |
| 禁止V5.2C rescue | SATISFIED | 明确停止 |

### V5.3 coupled two-parameter

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| 完全复用V4.6 benchmark/parameterization/residual/width6 | SATISFIED | Plan §7.1；不改科学对象 |
| 210--212 center-only development | SATISFIED | 精确seed及允许调项 |
| development禁止D/E/eigen/plot选择 | SATISFIED | schema级隔离，selection record不含comparative fields |
| 3/3 complete chain才held-out | SATISFIED | dependency gate与stop行为明确 |
| 213--214 byte-frozen held-out，2/2才confirmation | SATISFIED | 1/2即BLOCKED，不调后重跑 |
| confirmation 215--224 untouched | SATISFIED | zero-output preflight+one-shot授权 |
| Fraw/Fse/exact 2×2 primary | SATISFIED | raw矩阵及numerical statuses完整 |
| B-whitened Frobenius errors及D2 | SATISFIED | Plan §7.1明确公式；修复原markdown排版但不改含义 |
| tau/epsilon numerical convention | SATISFIED | 采用既有V4.6 tau与repository floor，要求V5.0明锁 |
| generalized eigen secondary及gap约束 | AMBIGUOUS | 协议无“足够eigengap”阈值；Plan §11.3不猜测 |
| valid>=9、wins>=9/10、medianD2>0、exact p<=.05 | SATISFIED | 四项AND gate逐项保留 |
| invalid planned seed为nonwin且不替换 | SATISFIED | planned denominator固定10 |
| valid<9为INCONCLUSIVE；coverage足但比较失败为NOT_SUPPORTED | SATISFIED | Plan §7.4 |
| 禁止第三PDE rescue | SATISFIED | terminal stop明确 |

### V5.4 residual-dimension scalability

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| 0 training，复用checkpoint | BLOCKED | V4.7 theta未保存；Plan §11.1要求提供或授权重建 |
| ntheta约1e3/1e4/1e5 × m=213/853/3413 | SATISFIED | 精确ntheta候选与3×3 grid |
| 每condition 3 repeats，共27 | SATISFIED | completeness validator预注册 |
| 保存time/iterations/JVP/VJP/residual/memory/status | SATISFIED | raw schema覆盖；memory仅可靠时 |
| cost-only，不拟合过度解释的指数 | SATISFIED | descriptive endpoint |
| 真实residual，不用synthetic padding冒充m | SATISFIED | config显式真实grid并断言count |

### V5.5/V5.6与投稿决策

| 要求 | 状态 | 计划中的落实/证据 |
|---|---|---|
| V5.5无新训练 | SATISFIED | 只读V4与V5.2 raw |
| 200--204生成frozen/SAEPS quadratic/reoptimized比较 | SATISFIED | Plan §9 |
| curvature raw/SAEPS/exact/profile全部报告 | SATISFIED | 同一machine aggregate驱动 |
| V5 final report/audit/validation与paper artifacts | SATISFIED | Plan §10逐项列出 |
| inherited与V5状态同表并保留历史negative | SATISFIED | final claim-to-evidence map |
| 情形A--D不因偏好修改结果 | SATISFIED | protocol-driven final adjudication |

### Explicit prohibitions

| 禁止项 | 状态 | 保障 |
|---|---|---|
| 删除不利seed、缩分母、替换invalid confirmation seed | SATISFIED | registries、planned denominator tests、failed-seed table |
| 重跑closed cohort或改historical raw | SATISFIED | protected hashes与path allowlist |
| confirmation后改threshold/gamma/config | SATISFIED | byte freeze、one-shot authorization、prior-output check |
| 用D/E/有利eigen/plots做被禁止的development选择 | SATISFIED | selection-stage schema不生成这些字段 |
| 失败后换PDE/建rescue confirmation | SATISFIED | terminal stop graph |
| 扩controlled、architecture、real-data或optimizer benchmark | SATISFIED | scope allowlist |
| 手工录paper数值 | SATISFIED | raw→aggregate→artifact validators |

## 3. Repository implementation audit

| 检查 | 状态 | 发现 |
|---|---|---|
| V4 final evidence可读且状态一致 | SATISFIED | V4 final为`PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS / NOT_READY_FOR_FULL_JCP` |
| scalar closed evidence可继承 | SATISFIED | Burgers 12/15、Allen 9/10；计划不重跑 |
| controlled negative可追溯 | SATISFIED | 6/10 valid/monotonic；计划不rescue |
| two-param kernels可复用 | SATISFIED | V4.6已有explicit/MF/exact/coupling/generalized geometry |
| profile sum scaling可复用 | SATISFIED | current profile code以mean优化并乘m输出curvature |
| solver engineering可复用 | SATISFIED | augmented scaled LSQR/LSMR、CG、JVP/VJP、exact refs已有测试 |
| scalability construction可复用 | SATISFIED | function-preserving widths与cost counters已通过V4.7 |
| historical checkpoint tensors可加载 | BLOCKED | 除P0 smoke外未发现`.pt/.pth/.npy/.npz`；V4.6/V4.7写`theta=None` |
| 既有tests覆盖V5所有新语义 | NOT_APPLICABLE | 既有tests覆盖基础numerics/gate semantics；V5 cohort、profile adjudication、whitening、m-grid、freeze仍需新tests |
| 当前V5 output为空 | SATISFIED | `outputs/runs/v5`不存在；未发现200--204、210--224 V5 records |

## 4. New tests required before execution

1. V5 seed registry disjointness、protected hash inventory与output allowlist。
2. Blind checkpoint selection与development excluded-field schema。
3. 7-level gamma completeness、direct Schur identity与high-gamma numerical limit。
4. independent profile start、sum scaling、8-point completeness、10%/5% boundaries及裁决分支。
5. B-whitened matrix error、coordinate rescaling、D2、sign-test ties、invalid planned nonwin。
6. 3/3→2/2→one-shot confirmation authorization graph。
7. exact residual counts、3×3×3 timing completeness、fresh initial guess、counter/timer semantics。
8. raw→aggregate→figure/table reproduction与paper-facing median consistency。

这些 unit tests 不能替代真实 PDE E2E phase validation。

## 5. Non-scientific preflight record

本启动任务允许且只执行以下操作：完整读取协议/治理/代码/历史evidence；检查seed/output路径；检查checkpoint文件；计算协议hash；运行repository tests与validator。未创建或运行任何V5 scientific seed，未修改历史output。

最终tests/validator结果在提交前写入本节：

- full test suite：`PASSED` — 80 tests passed（18条来自TorchScript弃用的非阻断warning）
- repository validator：`PASSED` — P9全部checks通过
- historical output mutation：`NONE_OBSERVED`
- V5 scientific output：`NONE`

## 6. Audit disposition

- `SATISFIED`：计划覆盖所有可明确解释的binding requirements。
- `BLOCKED`：V5.1/V5.4缺少可加载checkpoint tensors。
- `AMBIGUOUS`：V5.2的`INCONCLUSIVE`与`NOT_SUPPORTED`分界；V5.3 secondary eigengap解释阈值。
- `NOT_APPLICABLE`：现有tests不可能覆盖尚未实现的V5特有语义，因此已列出新增tests，而非宣称已覆盖。

`V5_EXECUTION_PLAN.md` 对协议的规划审计结果为 **CONDITIONALLY SATISFIED**；只有上述BLOCKED/AMBIGUOUS项被裁决且V5.0实现/验证通过后，才能升级为 `PASSED`。

**READY_FOR_V5_EXECUTION: NO**
