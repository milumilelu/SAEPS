# RI-2 Gamma-Path and Selective Analysis

This artifact is a development-only diagnostic pass over the immutable RI-2 pilot checkpoints. It does not authorize confirmation or support a general reliability claim.

## Reproducible command

```text
.venv\Scripts\python.exe scripts\reliability_audit_v1\analyze_ri2_reliability.py --runs-dir outputs\reliability_audit_v1\pilot\ri2_full_v3 --output-dir outputs\reliability_audit_v1\pilot\ri2_full_v3\reliability_analysis
```

The script reconstructs `J_state` and `J_parameter` from each checkpoint when the pilot manifest has no retained Jacobian arrays. Derived arrays are kept in a separate `reliability_analysis/derived_jacobians/` namespace; the pilot directories are not modified.

## Frozen diagnostics

The path is `gamma = gamma_alpha * lambda_max(J_state.T @ J_state)` for `gamma_alpha = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]`. Each record contains full `F_raw`, exact SVD zero-damping `F0`, all six `F_gamma` matrices, eigenvalues, effective ranks, positive-eigenspace projector distance to `F0`, and a gamma stability score.

The decision rule never reads physical truth. A record must pass execution and fit gates, have an independent observation-FIM rank covering all manifest unknowns, exceed the fixed information floor 1.0, and retain full zero-damping rank to receive `SUPPORTED_COMBINATION`. Otherwise it abstains as `WEAK_OR_CONFOUNDED`, `UNRESOLVED_NUMERICAL`, or `INVALID_CHECKPOINT`. Weak but rank-complete candidates remain on risk/coverage curves so abstention cannot masquerade as zero risk.

## Pilot result

The machine-readable source is [`RI2_RELIABILITY_ANALYSIS.json`](../../outputs/reliability_audit_v1/pilot/ri2_full_v3/reliability_analysis/RI2_RELIABILITY_ANALYSIS.json). It retains all 24 planned records. The observed labels are B1: 1 supported combination, 1 zero-damping rank abstention, and 4 invalid checkpoints; B2: 6 weak-information abstentions; B3: 6 confounded abstentions; B4: 6 confounded abstentions. The fixed score curve has 8 rank-complete candidates at threshold 0 (coverage 8/24, false-reliable risk 7/8) and 2 at thresholds 0.25 through 1.0 (coverage 2/24, false-reliable risk 1/2). Truth enters only in the post hoc identifiable-target error evaluation (`log k` for B1/B2, `log(k/C)` for B3, and the declared single-time B4 combination). These are pilot diagnostics, not confirmation estimates.
