# SAEPS V5 Final JCP Evidence Audit Report

- Audit status: `PASSED_WITH_SCIENTIFIC_LIMITATIONS`
- Scientific conclusion: `PARTIALLY_SUPPORTED`
- Paper readiness: `CLAIM_NARROWING_REQUIRED`
- Recommended scope: **scalar-focused finite-gamma local reduced-curvature methods paper**
- New training/reconstruction: `29/29`

## Final evidence table

| Evidence | Status | Result | Paper role |
|---|---|---|---|
| Burgers scalar comparative | `SUPPORTED` | 12/15 planned wins; 12/12 valid wins; median E_SAEPS=0.0750323; p=0.00024414062 | `PRIMARY_SUPPORTED` |
| Allen-Cahn scalar replication | `SUPPORTED` | 9/10 planned wins; 9/9 valid wins; median E_SAEPS=0.278567; p=0.001953125 | `INDEPENDENT_REPLICATION_SUPPORTED` |
| Noise/sparsity robustness | `DESCRIPTIVE_WITH_EXACT_ANCHOR_SUPPORT` | 52/60 binding-valid; 14/14 exact-anchor wins | `SECONDARY` |
| Controlled tangent-overlap mechanism | `NOT_SUPPORTED` | 6/10 planned monotonic; 6/10 valid; valid median Spearman=1 | `CONDITIONAL_ONLY` |
| Finite-gamma family | `DESCRIPTIVE_COMPLETE` | 42/42 terminal; 38/42 numerical PASS; no nominal-gamma recalibration | `SENSITIVITY_AUDIT_NONBINDING` |
| Nonlinear profile bridge | `NOT_SUPPORTED` | 5/5 evaluable; 1/5 PROFILE_VALID | `CLAIM_DELETED` |
| Two-parameter comparative geometry | `INCONCLUSIVE` | 8/10 valid; 8/10 planned wins; valid sign p=0.00390625 | `DIRECTIONAL_EVIDENCE_NONBINDING` |
| State-parameter scalability | `PASSED` | up to n_theta=100001; inherited function-preserving controlled checkpoint; cost-only | `ENGINEERING_COST` |
| Residual-dimension scalability | `PASSED` | 27/27 PASS; actual residuals m=213,853,3413; no exponent fit | `ENGINEERING_COST` |
| Wide architecture | `UNTESTED_DUE_INVALID_CENTERS` | 0/5 width32 center-valid in inherited V4.8 | `LIMITATION` |

## Final judgment

V5 closes the planned execution program but does not close every scientific gap. The two independently confirmed scalar PDE results support the comparative claim that local neural-state elimination is substantially closer than frozen-state curvature to exact finite-damping reduced curvature. This is the strongest paper-facing result.

The nonlinear profile bridge is not supported (1/5 valid). The coupled two-parameter result is inconclusive because only 8/10 planned seeds are valid, although all eight valid pairs favor SAEPS. Therefore the repository does not support claims of nonlinear-profile equivalence or empirically confirmed general multi-parameter geometry.

A JCP manuscript is defensible only after narrowing the title, abstract, and conclusions to scalar finite-gamma local reduced curvature, with the two-parameter experiment reported as nonbinding directional evidence and the profile failure as a limitation. The full general claim is not ready.

## Required claim edits

- Lead with paired scalar comparative efficacy against exact finite-gamma reduced curvature.
- Report Burgers and Allen-Cahn absolute SAEPS errors; do not claim exact Hessian recovery.
- Delete nonlinear-profile-equivalence language and report V5.2 as NOT_SUPPORTED.
- Present two-parameter results as availability-limited directional evidence, not confirmation.
- Keep controlled mechanism, gamma family, robustness and scalability explicitly secondary or descriptive.
- State that wide-architecture curvature remains untested because frozen centers were invalid.

## Deviations and retained failures

| Phase | Classification | Planned | Affected | Resolution |
|---|---|---:|---:|---|
| V5.1 | numerical | 42 | 4 | retained; descriptive audit complete |
| V5.2 | scientific | 5 | 4 | NOT_SUPPORTED; nonlinear-profile claim deleted |
| V5.3 | benchmark numerical availability | 10 | 2 | INCONCLUSIVE; no replacements or rescue |
| V5.4 | measurement limitation | 27 | 27 | peak CPU tensor memory unavailable; all timing solves retained |
