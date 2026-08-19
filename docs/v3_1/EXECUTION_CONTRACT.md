# SAEPS v3.1 State-Minimum Development Contract

**Contract ID:** `SAEPS-STATE-MIN-v3.1-development`  
**Status:** `DEVELOPMENT_ONLY / NOT_LOCKED / NO_CONFIRMATION_AUTHORIZED`

## 1. Scope and isolation

v3.1 addresses only state-local-minimum validity and linear-solver robustness. It does not modify v2 or v3.0 raw evidence, does not authorize confirmation, and initially authorizes only Burgers development seed 20. Seeds 21–24 remain inactive until seed 20 completes the full chain. Seeds 30–44 remain unseen and forbidden.

## 2. Unified first-order gate

Center and every unregularized or gamma-matched profile point use the same optimizer, initialization policy and normalized objective-gradient tolerance `1e-4`:

\[
G(\theta)=\frac{\|\nabla_\theta L\|_2}{\max(\|\theta\|_2,1)}\le 10^{-4}.
\]

The center additionally reports the established residual stationarity statistic

\[
S_\theta=\frac{\|J_\theta^Tr\|_2}{\|J_\theta\|_F\|r\|_2}\le10^{-4}.
\]

Passing an L-BFGS termination flag alone is insufficient.

## 3. Exact second-order gate and saddle diagnosis

At the center and every profile point, compute the exact Hessian of the actual mean-scaled optimization objective. Define

\[
\tau=\max(10^{-8},10^{-10}\|H_{\theta\theta}\|_2).
\]

A state is a numerical local-minimum candidate only if

\[
\lambda_{\min}(H_{\theta\theta})\ge-\tau.
\]

If this fails, evaluate both signs of the most-negative unit eigenvector at every preregistered relative radius in `[1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]`, scaled by `max(||theta||,1)`. Record every loss. A lower-loss candidate may seed an exact-Hessian trust-region step and subsequent common L-BFGS polish. At most 12 saddle-escape cycles are allowed. Failure remains `NUMERICAL_FAILURE`; thresholds must not be relaxed.

The trust-region candidate set contains both signs of the negative-curvature direction, a spectrally shifted Newton step, and steepest descent, each with registered backtracking factors. The actually evaluated objective, not the quadratic model, selects acceptance.

## 4. Seed-20 serial gate

The workflow stops at the first failed stage:

1. center `G<=1e-4` and `S_theta<=1e-4`;
2. center exact second-order gate passes;
3. unregularized profile has 8/8 local-minimum points and both finest convergence comparisons pass;
4. gamma-matched profile has 8/8 local-minimum points and both finest convergence comparisons pass;
5. standard CG and Jacobi-PCG both satisfy the registered residual tolerance, with zero solver failures;
6. only then compare `Fse_GN`, `Hred_exact`, `Hprofile_gamma` and `Fraw`.

No partial chain may be described as a valid profile reference.

## 5. Krylov development gate

Use the same matrix-free normal operator as SAEPS. In addition to standard CG, run left Jacobi-PCG with the exact development-only diagonal `diag(Jtheta^T Jtheta + gamma I)`. All parameter and residual right-hand sides must converge with verified relative residual `<=1e-8` within 500 iterations. Preconditioner construction from explicit Jacobians is authorized only as a development diagnostic; a future scalable protocol must preregister a matrix-free approximation.

## 6. Expansion and future lock

Seed 20 passing does not authorize a lock. A later amendment may activate seeds 21–24. Confirmation may be locked only if at least 4/5 development seeds are full-chain valid and the numerical solver failure count is zero. Only after that lock may seeds 30–44 be used.
