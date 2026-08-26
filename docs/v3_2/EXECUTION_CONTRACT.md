# SAEPS v3.2 Gamma-Matched Primary Development Contract

> **HISTORICAL v3 PROTOCOL — not the current paper-facing evidence state.** See [`../../V5_FINAL_JCP_AUDIT_REPORT.md`](../../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

**Contract ID:** `SAEPS-GAMMA-PRIMARY-v3.2-development`  
**Status:** `DEVELOPMENT_ONLY / NOT_LOCKED / NO_CONFIRMATION_AUTHORIZED`

## 1. Scope and isolation

Only Burgers development seed 20 is active. Seeds 21–24 and 30–44 are forbidden. v2, v3.0 and v3.1 configurations and raw evidence remain immutable. v3.2 corrects the v3.1 scientific ordering: gamma-matched profiling is primary; the unregularized profile is a nonbinding `gamma -> 0` stability diagnostic.

## 2. Common center

At the learned `lambda0`, optimize the unregularized state objective to a stricter internal objective-gradient tolerance `1e-6`, which implies the required

\[
G_\theta<10^{-4},\qquad S_\theta<10^{-4}.
\]

The exact state-Hessian numerical local-minimum gate from v3.1 remains binding. Record, but do not gate on,

\[
S_\lambda=\frac{\|J_\lambda^Tr\|_2}{\|J_\lambda\|_F\|r\|_2}.
\]

All curvature methods use this same center and learned parameter coordinate.

## 3. Local continuation branches

For each objective and optimization-accuracy level, solve offsets from the center outward independently on two branches:

- positive: `+0.00625 -> +0.0125 -> +0.025 -> +0.05`;
- negative: `-0.00625 -> -0.0125 -> -0.025 -> -0.05`.

Each point initializes from the immediately preceding, nearer-to-center state. Continuation across signs is forbidden. If a parent fails, descendants receive an explicit branch-dependency failure; restarting them from center is forbidden.

## 4. Optimization-accuracy convergence

Run every profile twice using identical objectives, offsets, continuation order and exact-Hessian gate:

- nominal: normalized objective-gradient tolerance `1e-4`;
- strict: normalized objective-gradient tolerance `1e-6`.

The strict run supplies paper-facing development curvature. For each of the two finest scales, require

\[
\frac{|H_{strict}(h)-H_{nominal}(h)|}
{\max(|H_{strict}(h)|,10^{-8})}\le0.05.
\]

This accuracy gate is separate from the strict profile's two-finest adjacent-scale convergence gate, also fixed at 5%.

## 5. Primary and secondary profiles

The gamma-matched objective is

\[
L^\gamma_{mean}=\frac{1}{2m}\left(\|r\|^2+\gamma\|\theta-\hat\theta\|^2\right).
\]

Its primary gate requires strict 8/8 numerical local-minimum candidates, multiscale convergence at the two finest adjacent pairs, and optimization-accuracy convergence at the two finest scales.

The unregularized objective undergoes the same audit, but its status is nonbinding for gamma-matched SAEPS validity. Its sole scientific role is diagnosing whether the `gamma -> 0` reduced geometry has a stable limit.

## 6. Solver and exact-Hessian gates

Run standard CG and development Jacobi-PCG on every seed-20 execution after profiling, regardless of profile outcome. Both must have zero failures and verified residual `<=1e-8`.

Compute the exact gamma-matched joint Hessian at the common center and its Schur reduction. The gamma-matched state block must pass symmetry, positive-definiteness and solve-residual gates. The unregularized exact reduction is diagnostic only.

## 7. Primary comparison and decision mapping

Only when the gamma-matched primary profile, solver gate and exact gamma reduction all pass, report

\[
F_{raw},\quad F_{se}^{GN}(\gamma),\quad
H_{red}^{exact,\gamma},\quad H_{profile}^{\gamma}.
\]

No binding agreement threshold is introduced in seed-20 development; report pairwise relative errors. Seed 20 passing does not activate seeds 21–24 automatically. A separate user-authorized amendment is required, and confirmation remains forbidden.
