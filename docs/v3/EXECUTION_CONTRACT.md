# SAEPS v3 Foundation Development Contract

**Contract ID:** `SAEPS-FOUNDATION-v3.0-development`  
**状态:** `DEVELOPMENT_ONLY / NOT_LOCKED / NO_CONFIRMATION_AUTHORIZED`  
**v2 preservation:** v2 remains immutable at lock commit `ad794ca2908c8935d0e21702fab7914ff944cce7`.

## 1. Scope

This contract authorizes only the five foundation corrections requested after the v2 negative audit:

1. version the complete v2 raw/artifact snapshot;
2. construct a common state-profiled base checkpoint;
3. compare unregularized and gamma-matched nonlinear profiles;
4. compute a full-Hessian reduced reference;
5. replace the seven-point quadratic-R2 primary gate with multiscale symmetric-curvature convergence.

No v3 confirmation run, scientific classification, benchmark screening or lock is authorized by this document.

## 2. Isolation

- v2 `configs/locked/*`, v2 raw results and v2 scientific conclusions are immutable.
- v3 code lives under `src/saeps/v3/`, configuration under `configs/v3/`, and raw runs under `outputs/runs/v3_foundation/`.
- v2 confirmation seeds `[10..19]` are forbidden in v3.
- Foundation validation uses development seed `20`. The reserved development pool is `[20..24]`; potential future confirmation seeds `[30..44]` remain inactive until a separate lock.
- Foundation results are diagnostic and must not enter v2 or future v3 confirmation statistics.

## 3. Common base state

After joint inverse training, hold the learned physical coordinate `lambda0` fixed and minimize the unregularized state objective to obtain `theta_hat(lambda0)`. SAEPS, full Hessians and both nonlinear profiles must use this identical `(theta_hat, lambda0)` base.

The run records

\[
\Delta_\theta^{base}=\frac{\|\theta_{hat}-\theta_0\|}{\|\theta_0\|+\epsilon},
\qquad
\Delta_L^{base}=\frac{L(\theta_0,\lambda_0)-L(\theta_{hat},\lambda_0)}{L(\theta_0,\lambda_0)+\epsilon},
\]

plus state-gradient stationarity before and after refinement. A failed refinement receives an explicit final status and cannot enter curvature comparison.

## 4. Matched objectives and scaling

Let `r` be the weighted residual vector of length `m`. SAEPS uses the unnormalized geometry

\[
\frac12\|r\|^2+\frac\gamma2\|\delta\theta\|^2.
\]

The code's mean-scaled nonlinear objectives therefore are

\[
L^0_{mean}=\frac{1}{2m}\|r\|^2,
\qquad
L^\gamma_{mean}=\frac{1}{2m}\left(\|r\|^2+\gamma\|\theta-\theta_{hat}\|^2\right).
\]

Profile curvatures are multiplied by `m` before comparison with `Fraw` or `Fse`. Adding `gamma/2` directly to the mean loss is forbidden because it would create an `m*gamma` mismatch.

## 5. Full-Hessian reference

For each objective, compute the exact Hessian blocks at the common base. A reduced Hessian is valid only when the state block is symmetric, finite and positive definite above the registered tolerance:

\[
H_{red}=H_{\lambda\lambda}-H_{\lambda\theta}H_{\theta\theta}^{-1}H_{\theta\lambda}.
\]

The gamma-matched exact state block is `H_theta_theta + gamma I`. Record state-block eigenvalue bounds, negative/nonpositive count, condition number, solve residual and Hessian symmetry. Never use an unchecked inverse or silently replace a nonpositive block.

## 6. Multiscale curvature

For `h in [0.05, 0.025, 0.0125, 0.00625]` in log-parameter coordinates, independently optimize the state at `+h` and `-h` from the common base and compute

\[
H(h)=m\frac{\Phi(h)-2\Phi(0)+\Phi(-h)}{h^2}.
\]

The primary convergence gate requires every point to pass the optimizer stopping rule and the two finest adjacent changes `(0.025 -> 0.0125)` and `(0.0125 -> 0.00625)` to be at most 5%, using denominator `max(abs(H_fine), 1e-8)`. Seven-point R2 may be retained only as a nonbinding diagnostic.

## 7. Foundation acceptance

Engineering acceptance requires:

- immutable v2 snapshot verification passes;
- all v2 locked file hashes remain unchanged;
- actual Burgers training and state-only refinement execute for seed 20;
- both profile objectives produce all planned final point statuses;
- exact full Hessian, Gauss-Newton SAEPS and multiscale estimates are machine-readable;
- any numerical/scientific failure is retained without threshold changes;
- unit tests and the v3 foundation validator pass.

Foundation acceptance does not imply v3 readiness for confirmation.
