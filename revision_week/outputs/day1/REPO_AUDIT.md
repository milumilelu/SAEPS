# Repository audit — actual local evidence

Source workspace: `C:\Users\RZF\Desktop\博士课题资料\SAEPS`; base `cd01a26072f8d87c09efef4be217eff17373e39a`.
Separate clean worktree: `C:\Users\RZF\Desktop\博士课题资料\SAEPS-so-week1`, branch `codex/saeps-so-week1`.
Original user deletions/untracked files preserved in `initial_workspace.json`.
User's explicit no-push instruction overrides historical AGENTS auto-sync.
This is a newly authorized retrospective development extension; historical locks
and terminal V2/V4/V5 decisions remain closed. No new confirmation or training.

All 16 locally visible references were inspected by `git ls-tree`;
see `branch_inventory.json` for exact commits and protocol/checkpoint paths.
No network fetch was performed; remote-only changes are outside this audit.
Historical short hashes were resolved in `historical_refs.json`; the named tag
and release branch must not be conflated with the manuscript's report commit.

## Reusable evidence

The v3 archive contains 25 planned scalar records (Burgers 55–69, Allen–Cahn
75–84), including 21 complete valid matrix centers and four historical failures.
Their frozen source records are binding; the reconstruction/decomposition is
post-hoc nonbinding. Every record and hash is in `artifact_manifest.csv`.
The V2 exact decomposition was aborted; it is not substituted for V3.
V5 has 29 reloadable model files on main (including failed coupled attempts),
but none is the original E0 scalar seed/center. Scanning every visible reference
finds no tensor checkpoint for these 21 original E0 centers. V3 runner reconstructs
theta/data in memory then serializes blocks and normalized diagnostics, not
theta, raw residual, or full gradients. Thus E0 matrix audit is possible; original
center HVP, absolute gradient and T3 replay remain unavailable without a separate
costed reconstruction. The residual/data recipe is recoverable; exact tensor
identity is not claimed. No reconstruction was started.

## Objective and variables, checked in code

`src/saeps/scalar.py::scalar_network`: theta packs wx, wt, bias, output weights,
then output bias; n=4*width+1 (archived Burgers n=65, Allen n=33).
Joint derivatives pack [theta, log_parameter]. Burgers parameter is viscosity;
Allen–Cahn parameter is reaction rate, diffusion fixed. `scalar_residual` has
the form a(theta)+exp(lambda)b(theta), with no parameter regularizer.
`residual.py::stack_weighted_residuals` multiplies each block by sqrt(weight),
no block-size normalization; weights are fixed configuration values.
Training/center objective uses 0.5*mean(rbar²), archived derivatives use
0.5*sum(rbar²) (`posthoc_exact_fixed_state_v1.py::curvature_blocks`).
Gamma is saved alpha*lambda_max(Gtt), added once to state block, fixed in E0.
Do not mix mean-objective derivatives or recompute gamma inside perturbations.

Coupled source: `src/saeps/multi.py::multi_residual`, manufactured reaction-diffusion
u_t-du*u_xx+a*u-b*v-source_u and v_t-dv*v_xx-a*u+b*v-source_v;
coordinates [log a,log b], separate u/v tanh state blocks. V5 width6 => n=50.
`v5/two_parameter_frozen.py::_primary_metrics` defines B2=sym(Fraw)+tau I,
tau=tau_relative*max(trace(Fraw)/2,1), L=chol(B2), Fhat=L^-1 F L^-T.
Use D L^-T for the corresponding bound. Historical scalar denominator floor
is 1e-8 (`configs/posthoc_exact_fixed_state_v3.yaml`).

Validity: `v31/local_minimum.py::exact_state_diagnostics` uses mean-objective
gradient norm/max(||theta||,1), and lambda_min(Hmean)>=-max(atol,rtol*spectral_scale).
`posthoc_exact_fixed_state_v1.py::_center_valid` also requires G_theta and S_theta
below inherited center thresholds; S=||J^T r||/(||J|| ||r||+epsilon) in
`p4_screening.py::_stationarity`. `v41/numerics.py` verifies original normal
residuals for scaled LSQR refinement. Frozen configuration defines all numerical
thresholds; E0 does not relax them. Historical local numerical validity is retained
separately from algebraic Schur validity. It is not exact mathematical stationarity.

## V6 overlap and negative evidence

`codex/v6-phase15-protocol` is 71b84e3ca28b00bac5a0d9924213415ad66954cd.
Its `curvature.py` has scalar complete quadratic, `operators.py` explicitly uses
dense matrices; HVP_actual=0. `stopping.py` uses an indicator, not a relative bound.
Its RESULT_VALIDATION_V2 reports numerical validation PASSED but development
gate NOT_SUPPORTED. Findings retain worsening seeds59/67 and no scalable
candidate selected. These are inspected historical reports, not rerun results.
Reuse the existing quadratic/archived loader pattern; add multi-column and
inexact identities plus bound classification in revision_week/core.py.

## Resource and evidence limits

Python/NumPy/Torch CPU versions and hardware in environment.json. CPU-only,
approximately 31.8 GiB RAM. No GPU available in installed Torch.
Historical reconstruction wall time is summed separately from E0; missing original
training totals are explicitly unknown. Seed inventories remain attached to each
branch/protocol; future independent seed collision scan/freeze is not performed
in this first-stage request. No new seeds, protocol.frozen.yaml, E1–E5 outcomes,
or background execution are claimed.
