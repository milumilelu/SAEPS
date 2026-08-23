# V5 Scientific Gates

## Status separation

- Engineering：`PASSED | FAILED | BLOCKED`。
- Scientific：`SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED | INCONCLUSIVE`。
- 阴性科学结果不构成engineering failure。

## V5.1 finite-gamma audit

Descriptive only。要求7个预注册alpha均有terminal numerical status；不设“SAEPS必须赢”gate，不重校nominal gamma。

## V5.2 profile bridge

- Planned seeds：`200--204`，denominator 5，无替换。
- `PROFILE_EVALUABLE`与`PROFILE_VALID`严格采用Amendment 001定义。
- `n_evaluable<4`：`INCONCLUSIVE`。
- `n_evaluable>=4 && n_profile_valid>=4`：`SUPPORTED`。
- 其他：`NOT_SUPPORTED`。
- 无V5.2C或rescue。

## V5.3 two-parameter matrix confirmation

- Development `210--212`：3/3 complete binding chain才授权held-out。
- Held-out `213--214`：2/2 complete binding chain才授权confirmation；否则`BLOCKED_BY_CENTER_AVAILABILITY`。
- Confirmation `215--224`：planned denominator 10，invalid planned seed为nonwin且不可替换。
- `SUPPORTED`要求：valid `>=9`；planned wins `>=9/10`；valid median `D^(2)>0`；valid non-tied paired one-sided exact sign test `p<=0.05`。
- valid `<9`：`INCONCLUSIVE`。
- valid `>=9`但比较条件未全过：`NOT_SUPPORTED`。
- generalized eigenvalues/vectors/eigengap全部non-binding；orientation不进入adjudication。

## V5.4/V5.5

Cost与baseline descriptive audits，不创建额外efficacy gate。
