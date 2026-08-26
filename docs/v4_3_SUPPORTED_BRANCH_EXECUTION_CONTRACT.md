# v4.3 — Supported-Branch Execution Contract

> **HISTORICAL v4 PROTOCOL — not the current paper-facing evidence state.** See [`../V5_FINAL_JCP_AUDIT_REPORT.md`](../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

## 1. Current adjudicated state

- v2 remains a completed historical protocol with final status `PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS`.
- v3.6 remains permanently `NOT_SUPPORTED`; its comparative hypothesis was not tested because of the recorded implementation defect.
- v4.1 remains passed engineering development.
- v4.2 remains permanently `SUPPORTED`: 12/15 planned strict wins, 12 valid pairs, median `D=27.636319042759617`, exact one-sided sign-test `p=0.000244140625`.
- V4.2 supports only Burgers scalar curvature relative to the exact finite-`gamma` reduced Hessian. It does not establish cross-PDE, multi-parameter, nonlinear-profile or practical-scale validity.

No historical lock, result or raw record may be changed by v4.3.

## 2. Claim hierarchy

1. **Confirmed:** on the locked Burgers small-network problem, SAEPS-GN is closer than raw fixed-state curvature to exact finite-`gamma` reduced curvature.
2. **Secondary limitation:** median absolute SAEPS error is about 7.50%, and only 3/12 valid v4.2 seeds are within 5%; SAEPS is not a uniformly exact Hessian surrogate.
3. **Unconfirmed:** external scalar replication, nonlinear-profile agreement, controlled-mechanism planned-denominator success, two-parameter geometry and scalability.
4. **Nonbinding diagnostic:** the frozen first-order GN adequacy indicator; v4.2 accuracy 0.75 and Spearman 0.622 do not support a strong self-certification claim.

## 3. Ordered program

The authorized order is:

```text
V4.3 governance freeze
  -> Allen--Cahn development (70--74)
  -> Allen--Cahn executable/protocol lock
  -> Allen--Cahn one-shot confirmation (75--84)
  -> controlled-mechanism closure (85--99)
  -> two-parameter exact geometry (100--114)
  -> practical scalability (120--124)
  -> noise/sparsity and architecture robustness (130--139)
  -> final evidence audit
```

Only the first two nodes are currently authorized. Seeds `75--139` are reserved and must not be run until their own preceding gates pass.

## 4. Allen--Cahn development contract

### 4.1 Isolation

- benchmark is fixed to the previously retained `Allen-Cahn` candidate; no PDE screening is permitted;
- development seeds are exactly `[70,71,72,73,74]`;
- confirmation seeds `[75,76,77,78,79,80,81,82,83,84]` remain inactive;
- Burgers v4.2 thresholds are hypotheses to audit, not automatically valid Allen--Cahn thresholds;
- no configuration choice may use `D`, `E_SAEPS`, raw advantage, eta or visual appeal.

### 4.2 Development objectives

Development may select engineering settings only from:

- finite and stable conventional forward solution;
- common-center first- and second-order validity;
- parameter-only explicit curvature reference;
- exact finite-`gamma` reduced Hessian availability;
- matrix-free curvature-solver residual/agreement and cost;
- gamma-matched nonlinear-profile branch and optimization-accuracy diagnostics;
- explicit-versus-directional-HVP second-order correction agreement;
- complete fail-soft records and raw-schema/aggregator integration.

### 4.3 Required outputs

Every seed must retain independent statuses for center, parameter reference, curvature solver, exact reference, score diagnostic and nonlinear profile. Score remains nonbinding. Earlier computable quantities must survive later failures.

The development acceptance report must state all five terminal results and must not make a confirmation claim. A future confirmation lock may be drafted only after the frozen engineering chain is demonstrated on all center-valid seeds and the runner-to-aggregator schema integration test passes.

## 5. Proposed Allen--Cahn confirmation rule

The following is a preregistration candidate, not yet a lock:

- primary estimand: paired `D=E_raw-E_SAEPS` against exact finite-`gamma` reduced curvature;
- planned denominator: 10;
- minimum valid pairs: 8;
- planned strict wins required: 8/10;
- median valid-pair `D` must be positive;
- one-sided exact paired sign test must satisfy `p<=0.05`;
- all conditions are jointly required for `SUPPORTED`;
- invalid planned seeds are planned non-wins and cannot be replaced;
- gamma-matched nonlinear profile and the unchanged 5% GN indicator are secondary, independently statused endpoints.

These rules must be reviewed and frozen before any seed `75--84` is run. They cannot be revised from confirmation outcomes.

## 6. Stop rules

- Adequate Allen--Cahn valid coverage with comparative failure: do not add a third scalar PDE; report Burgers-specific support.
- Numerical-availability failure: preserve the one-shot cohort and open only a new named development version with new seeds.
- Profile failure with valid exact curvature: restrict the claim to exact local reduced geometry.
- Indicator failure: remove the self-diagnostic claim without changing the comparative endpoint.
- Two-parameter failure: restrict the method claim to scalar geometry; do not manufacture coupling.
- Scalability failure: explicitly restrict the implementation to small-network diagnostics.
