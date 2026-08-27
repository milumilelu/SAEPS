# Post-hoc exact fixed-state curvature decomposition v1 — aborted

**Status:** `ABORTED_RUNNER_BUG`

This analysis is post hoc and nonbinding. It does not alter any preregistered
confirmation result.

V1 was stopped after Burgers seeds 55 and 56. The runner mixed the historical
selected LSQR value of `F_SAEPS` with the explicit Schur value of
`C_relax_GN` in the exact-error identity. Although the direct LSQR-versus-
explicit consistency check passed for seed 56, cancellation made the mixed
identity residual fail and incorrectly changed `analysis_valid`.

The two completed raw records are retained unchanged under
`outputs/posthoc/exact_fixed_state_v1/burgers/`. No v1 seed may be resumed or
rerun. A corrected analysis requires a separately frozen and authorized v2
protocol. Original frozen Burgers and Allen--Cahn confirmation evidence and
all existing scientific adjudications remain unchanged.
