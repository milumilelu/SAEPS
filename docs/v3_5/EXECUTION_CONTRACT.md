# SAEPS v3.5 Second-Order Diagnostic and Engineering Contract

**Contract ID:** `SAEPS-SECOND-ORDER-ENGINEERING-v3.5-development`  
**Status:** `DEVELOPMENT_ONLY / TWO-STAGE FREEZE / NO CONFIRMATION`

## 1. Scope and isolation

V3.4 remains immutable, including every 5% failure. V3.5 has three disjoint development roles:

- retrospective diagnostic seeds `20,22,23,24`, used only to explain the already observed GN-error variation;
- new engineering seeds `25,26,27`, used to select center and scalable-solver engineering;
- held-out development validation seeds `28,29`, forbidden until the engineering selection is committed.

Seed 21 is not rerun because v3.4 did not establish a valid center/reference. Confirmation seeds 30--44 remain unseen and forbidden.

## 2. Exact residual second-order decomposition

For the unnormalized residual objective, decompose

\[
H_{\theta\theta}=J_\theta^TJ_\theta+S_{\theta\theta},\quad
H_{\theta\lambda}=J_\theta^TJ_\lambda+S_{\theta\lambda},\quad
H_{\lambda\lambda}=J_\lambda^TJ_\lambda+S_{\lambda\lambda}.
\]

Compute all eight Schur reductions obtained by including/excluding the three S blocks. Attribute the exact-minus-GN curvature difference to the three blocks with the unique three-player Shapley decomposition. Require the Shapley sum to reproduce the exact difference to relative error `<=1e-10`.

Pre-register the following diagnostic indicators, without selecting based on future seeds:

1. spectral `S_theta_theta / GN_theta_theta` ratio;
2. Frobenius `S_theta_lambda / GN_theta_lambda` ratio;
3. scalar `S_lambda_lambda / GN_lambda_lambda` ratio;
4. maximum of the three block ratios;
5. absolute first-order reduced correction divided by `|Fse_GN|`;
6. absolute Shapley contribution sum divided by `|Fse_GN|`.

Report their association with the actual GN-to-exact error descriptively. No four-seed correlation is a confirmation claim.

## 3. Center and scalable-solver engineering

Center thresholds are unchanged. On seeds 25--27 compare:

- baseline v3.4 exact-Hessian trust/escape center;
- enhanced exact trust-region rescue, applied only after baseline failure, using negative-curvature escape or eigenvalue-clipped Newton steps with Armijo backtracking. Maximum work may change; stationarity/Hessian thresholds may not.

For curvature solves compare standard CG, augmented LSQR, column-scaled augmented LSQR, and two-pass scaled-LSQR iterative refinement. The explicit direct curvature is diagnostic reference only. Parameter residual `<=1e-8` and curvature relative error `<1e-6` remain unchanged.

The engineering selection rule on seeds 25--27 is lexicographic: maximize valid-center count or solver pass count, then minimize median verified residual, then minimize median iterations. Selection and config hash must be committed before seeds 28--29.

## 4. Future comparative estimand

For every valid development seed record

\[
E_{SAEPS}=\frac{|F_{se}^{GN}-H_{red}^{exact}|}{|H_{red}^{exact}|+10^{-8}},\quad
E_{raw}=\frac{|F_{raw}-H_{red}^{exact}|}{|H_{red}^{exact}|+10^{-8}},
\]

and paired `D=E_raw-E_SAEPS`. The future untouched-confirmation primary hypothesis is `D>0`, with all planned seeds retained in the denominator. V3.5 may define and test the pipeline but cannot authorize or run confirmation.

## 5. Decision

Only after seeds 28--29 complete under the frozen engineering choice may v3.5 recommend a future confirmation lock. No development result directly activates seeds 30--44.

