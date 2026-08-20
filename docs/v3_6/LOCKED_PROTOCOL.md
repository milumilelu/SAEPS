# v3.6 Scalar Confirmation — Locked Protocol

**State:** `LOCKED_NOT_EXECUTED`  
**Lock date:** 2026-08-20  
**Execution authorization:** `false`

This document freezes the untouched scalar-curvature confirmation before any seed in `[30,44]` is run or inspected. Locking does not authorize execution. A later explicit authorization may only start the frozen one-shot run; it may not modify this protocol.

## 1. Scientific question and scope

The primary question is whether neural-state elimination improves scalar curvature relative to a frozen neural state. The scope is curvature only. Score, parameter update, multi-parameter inference and nonlinear profiling are excluded.

The finite-\(\gamma\) exact reduced Hessian is the gold standard:

\[
H_{\mathrm{red}}^{\mathrm{exact},\gamma}
=H_{\lambda\lambda}
-H_{\lambda\theta}(H_{\theta\theta}+\gamma I)^{-1}H_{\theta\lambda}.
\]

For every valid paired seed,

\[
E_{\mathrm{raw}}=
\frac{|F_{\mathrm{raw}}-H_{\mathrm{red}}^{\mathrm{exact},\gamma}|}
{|H_{\mathrm{red}}^{\mathrm{exact},\gamma}|+10^{-8}},\qquad
E_{\mathrm{SAEPS}}=
\frac{|F_{\mathrm{se}}^{\mathrm{GN}}-H_{\mathrm{red}}^{\mathrm{exact},\gamma}|}
{|H_{\mathrm{red}}^{\mathrm{exact},\gamma}|+10^{-8}},
\]

\[
D_i=E_{\mathrm{raw},i}-E_{\mathrm{SAEPS},i}.
\]

No universal \(E_{\mathrm{SAEPS}}\le5\%\) accuracy gate is used. The historical development finding that SAEPS is not uniformly accurate within 5% remains unchanged.

## 2. Frozen cohort and one-shot rule

- Planned seeds are exactly `30,31,...,44`, giving a planned denominator of 15.
- No seed may be replaced, rerun with changed settings, or removed from the planned denominator.
- Confirmation may be executed only once after explicit authorization.
- Confirmation results may not be fed back into center, solver, gamma, indicator, threshold or endpoint choices.
- Every planned seed must receive a terminal machine-readable status and failure reason where applicable.

## 3. Frozen numerical chain

The center policy is baseline v3.4 exact-trust optimization followed, only after baseline failure, by the v3.5 frozen enhanced rescue. All first- and second-order tolerances and the maximum 40 rescue steps are copied without alteration from the frozen v3.5 selection.

The curvature solver is augmented least-squares scaled LSQR with two iterative-refinement passes. Each pass has at most 500 iterations; the full maximum is 1500. Scaling uses the exact diagonal of \(J_\theta^T J_\theta+\gamma I\) obtained through basis JVPs. A solver pass requires verified original normal residual at most \(10^{-8}\) and relative agreement with the explicit direct GN reference at most \(10^{-6}\).

The damping is fixed as

\[
\gamma=10^{-8}\lambda_{\max}(J_\theta^T J_\theta)
\]

at the accepted common center. The exact finite-\(\gamma\) Hessian reduction uses the full loss Hessian and is not replaced by an unregularized or profile curvature.

## 4. Validity and planned denominator

A numerical primary pair exists only when the center, exact gold-standard reduction and selected solver pass and all primary quantities are finite. An invalid seed is excluded only from calculations that mathematically require a numeric pair. It remains one of the 15 planned seeds and counts as a non-win under the planned-seed win rule. Invalid and failed results must be displayed individually.

## 5. Primary decision rule

A strict win is \(D_i>10^{-12}\). A value with \(|D_i|\le10^{-12}\) is a tie: it is a planned non-win and is excluded from the sign-test denominator.

`SUPPORTED` requires all of the following:

1. at least 12 valid numerical pairs;
2. at least 12 strict wins among all 15 planned seeds;
3. positive median \(D_i\) among valid numerical pairs;
4. one-sided exact paired sign-test \(p\le0.05\), using only non-tied valid pairs, null success probability 0.5, alternative \(D_i>0\), and no continuity correction.

The `12/15` threshold is locked because 12 wins is the smallest all-valid count yielding a one-sided exact binomial tail below 0.05: \(P[X\ge12;X\sim\mathrm{Binomial}(15,0.5)]\approx0.0176\), whereas 11 wins gives approximately 0.0592. The planned-denominator condition remains stricter when seeds are invalid.

If any primary condition fails, the result is `NOT_SUPPORTED`. Fewer than 12 valid pairs is recorded as `NOT_SUPPORTED` with reason `insufficient_valid_pairs`; invalid seeds remain visible and cannot create an inconclusive-denominator escape. `PARTIALLY_SUPPORTED` is reserved for the prespecified case in which the comparative primary result is supported but a secondary scientific claim fails; it cannot be used to relax the four primary conditions.

## 6. Secondary absolute accuracy

Report all valid seed-level \(E_{\mathrm{SAEPS}}\) values and their median, IQR and range. Median uses the average of the two middle order statistics for an even denominator. Quartiles use NumPy's `linear` quantile convention and IQR is \(Q_{0.75}-Q_{0.25}\); range is `[minimum, maximum]`. Also report \(E_{\mathrm{raw}}\), planned/valid/invalid counts, and the number and fraction with \(E_{\mathrm{SAEPS}}\le5\%\). The 5% count is descriptive and cannot override the primary result.

## 7. Frozen GN indicator

Let

\[
x=(J_\theta^T J_\theta+\gamma I)^{-1}J_\theta^T J_\lambda,
\]

\[
\Delta H_{\mathrm{first}}
=S_{\lambda\lambda}-2x^T S_{\theta\lambda}+x^T S_{\theta\theta}x,
\qquad
I_{\mathrm{GN}}=
\frac{|\Delta H_{\mathrm{first}}|}{\max(|F_{\mathrm{se}}^{\mathrm{GN}}|,10^{-8})}.
\]

The predicted class is `within 5%` exactly when \(I_{\mathrm{GN}}\le0.05\); the observed class is `within 5%` exactly when \(E_{\mathrm{SAEPS}}\le0.05\). Confirmation reports the confusion matrix, accuracy, Spearman association, median absolute calibration error and all seed values. This indicator is a secondary nonbinding diagnostic: its definition, threshold and role cannot be recalibrated or promoted after seeing confirmation.

## 8. Audit and immutability

The authoritative machine-readable protocol is `configs/v3_6/locked_scalar_confirmation.yaml`. Its raw SHA-256 and the Git commit containing the first locked bytes are recorded separately in `configs/v3_6/LOCK_RECORD.json`; this prevents the act of recording the commit from changing the locked file. Static validation must pass without creating any v3.6 run directory. Any future protocol change requires a new version and explicit deviation record; v3.6 results may not be continued under a modified lock.
