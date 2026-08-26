# SAEPS v3.3 Numerical-Decomposition Development Contract

> **HISTORICAL v3 PROTOCOL — not the current paper-facing evidence state.** See [`../../V5_FINAL_JCP_AUDIT_REPORT.md`](../../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

**Contract ID:** `SAEPS-NUMERICAL-DECOMPOSITION-v3.3-development`  
**Status:** `DEVELOPMENT_ONLY / NOT_LOCKED / NO_CONFIRMATION_AUTHORIZED`

## 1. Single objective and isolation

The only objective is to separate solver error, Gauss--Newton approximation error, and nonlinear-profile error. Only Burgers development seed 20 is active. Seeds 21--24 and 30--44 remain forbidden. No v2, v3.0, v3.1, or v3.2 configuration or result may be changed.

All four nodes use one newly reproduced v3.3 common center, one learned parameter coordinate, and the v3.2 gamma rule. The v3.2 common-center and gamma-profile gates are copied without relaxation.

## 2. Four registered nodes

The diagnostic chain is

\[
F_{se}^{GN,MF}\leftrightarrow F_{se}^{GN,explicit}
\leftrightarrow H_{red}^{exact,\gamma}\leftrightarrow H_{profile}^{\gamma}.
\]

1. `Fse_GN_explicit_direct` is the solver-independent GN reference. Construct explicit \(J_\theta,J_\lambda\), form the augmented matrix
   \[
   A_\gamma=\begin{bmatrix}J_\theta\\\sqrt{\gamma}I\end{bmatrix},
   \]
   and solve each augmented least-squares problem by direct SVD-based linear algebra. The reported curvature is the minimized augmented residual norm squared.
2. `Fse_GN_matrix_free_CG` is computed with JVP/VJP and standard CG. Its value is retained even when its registered residual gate fails.
3. Jacobi-PCG remains a separately reported matrix-free diagnostic.
4. `Fse_GN_augmented_LSQR` uses only augmented forward/adjoint operator applications and LSQR. It is a development cross-check that avoids explicitly forming normal equations.
5. `Hred_exact_gamma` is the exact full-Hessian Schur reduction.
6. `Hprofile_gamma` is the strict, finest-scale v3.2 nonlinear gamma-matched profile curvature, retained with its profile gate status.

## 3. Error decomposition

Always compute the following when both endpoints are finite:

- solver error: matrix-free CG versus explicit direct GN;
- preconditioner diagnostic: Jacobi-PCG versus explicit direct GN;
- augmented Krylov diagnostic: LSQR versus explicit direct GN;
- GN approximation error: explicit direct GN versus exact gamma-matched reduction;
- nonlinear/profile error: exact gamma-matched reduction versus gamma profile;
- total GN-to-profile discrepancy: explicit direct GN versus gamma profile.

The denominator is `max(abs(reference), 1e-8)`, where the right-hand node is the reference. No agreement threshold is introduced for the scientific decomposition.

## 4. Binding gates and reporting

The existing common-center, gamma-profile, exact-Hessian, CG, and PCG gates remain unchanged. Direct explicit and LSQR numerical audits use the preregistered tolerances in the v3.3 configuration. A failed gate must retain its value and failure status when finite.

The complete decomposition object is always labeled:

```text
NONBINDING_DIAGNOSTIC_ONLY
```

It is not paper-facing and cannot authorize seed expansion. A separate `paper_facing_comparison` may be populated only if every registered center, profile, explicit, CG, PCG, LSQR, and exact-Hessian gate passes. Seed 20 passing would still require a new user-authorized amendment before seeds 21--24; confirmation remains forbidden.
