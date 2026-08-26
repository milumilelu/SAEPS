# SAEPS v3.4 Curvature-Validation Development Contract

> **HISTORICAL v3 PROTOCOL — not the current paper-facing evidence state.** See [`../../V5_FINAL_JCP_AUDIT_REPORT.md`](../../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

**Contract ID:** `SAEPS-CURVATURE-VALIDATION-v3.4-development`  
**Status:** `DEVELOPMENT_ONLY / FROZEN_BEFORE SEEDS 21-24 / NO CONFIRMATION`

## 1. Scope and ordering

V3.4 changes classification, not historical outcomes. V3.2 and v3.3 failures remain immutable. Seed 20 verifies the implementation of this contract. If and only if its readiness gate passes, run seeds 21--24 without changing this contract or configuration. Seeds 30--44 remain forbidden.

## 2. Solver hierarchy

Three solver objects are reported separately.

1. `CURVATURE_SOLVER_GATE` is binding. Explicit augmented SVD is the direct reference. Standard matrix-free CG and augmented matrix-free LSQR are scalable candidates. A candidate passes only when its parameter-column residual is at most `1e-8` and its curvature differs from explicit direct by less than `1e-6`. At least one candidate must pass.
2. `SCORE_SOLVER_GATE` audits the residual RHS required by the state-eliminated score. It is nonbinding for the curvature study.
3. `PRECONDITIONER_DIAGNOSTIC` records Jacobi-PCG and is nonbinding.

No failed v3.3 status is relabeled; v3.4 computes new, mathematically separated gates.

## 3. Local gold standard

For this 65-state-parameter network, the exact gamma-matched full-Hessian Schur complement is the binding local gold standard. It requires a valid common state minimum, positive definite gamma state block, and direct solve residual at most `1e-8`.

The explicit GN curvature is locally supported when its relative error to the exact reduction is at most 5%. This threshold is frozen before seeds 21--24.

## 4. Finite-radius profile and resolution certificate

The nonlinear gamma-matched profile is an independent `FINITE_RADIUS_VALIDATION`, not the definition of the local Hessian. Nominal and strict center-outward branches use the unchanged v3.2 offsets and optimizers.

At every optimized point, compute the local quadratic suboptimality estimate

\[
\delta L=\tfrac12 g_\theta^T(H_{\theta\theta}^{\gamma})^{-1}g_\theta.
\]

For a symmetric scale \(h\), propagate the estimate to

\[
\Delta H_{opt}(h)=\frac{m}{h^2}
[\delta L(+h)+2\delta L(0)+\delta L(-h)].
\]

A scale is `CERTIFIED` only if both strict endpoints are numerical local-minimum candidates, the relative optimization-error budget is at most 5%, and nominal/strict curvature discrepancy is at most 5%. A locally valid scale that exceeds either numerical budget is `RESOLUTION_LIMIT`, not scientific failure. No rule requires the smallest h to be certified. The finite-radius numerical gate requires at least two adjacent certified scales; exact-reference agreement is reported separately and passes at 5% on every certified scale.

## 5. Branch audit

Every point records parent-relative weight distance and function-space distance on a fixed `33 x 17` diagnostic grid. Nominal/strict function-space distance is also recorded at each offset. Completeness and finiteness are binding engineering checks; magnitudes and the preregistered 25% function-distance alert are descriptive and do not select or discard scales.

## 6. Development decision

Seed-20 readiness requires common-center, curvature-solver, exact-local-reference, local-GN, certified-window, and branch-audit engineering gates. Score and Jacobi-PCG remain nonbinding. Passing readiness activates only seeds 21--24 under these frozen rules. It never authorizes confirmation.
