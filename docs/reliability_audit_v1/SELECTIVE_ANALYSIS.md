# RI-2 Gamma-Path and Selective Analysis

This is a development-only diagnostic pass over immutable RI-2 checkpoints. It does not authorize confirmation or support a general reliability claim.

## Reproducible commands

```text
.venv\Scripts\python.exe scripts\reliability_audit_v1\analyze_ri2_reliability.py --runs-dir outputs\reliability_audit_v1\pilot\ri2_full_v6 --output-dir outputs\reliability_audit_v1\pilot\ri2_full_v6\reliability_analysis
.venv\Scripts\python.exe scripts\reliability_audit_v1\summarize_pilot.py --runs-dir outputs\reliability_audit_v1\pilot\ri2_full_v6 --analysis outputs\reliability_audit_v1\pilot\ri2_full_v6\reliability_analysis\RI2_RELIABILITY_ANALYSIS.json --output outputs\reliability_audit_v1\pilot\ri2_full_v6\PILOT_RESULTS.json
```

The analyzer reconstructs `J_state` and `J_parameter` from each checkpoint and stores derived arrays under a separate `reliability_analysis/derived_jacobians/` namespace. The fixed path uses `gamma_alpha = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]` and reports `F_raw`, exact SVD zero-damping `F0`, all six `F_gamma` matrices, eigenvalues, ranks, projector distances and stability.

The truth-independent decision rule requires execution and fit gates, independent observation-FIM rank, the fixed information floor 1.0 and full zero-damping rank. It returns `SUPPORTED_COMBINATION`, `WEAK_OR_CONFOUNDED`, `UNRESOLVED_NUMERICAL` or `INVALID_CHECKPOINT`; weak candidates remain on risk/coverage curves.

## Corrected v6 result

The source is [`RI2_RELIABILITY_ANALYSIS.json`](../../outputs/reliability_audit_v1/pilot/ri2_full_v6/reliability_analysis/RI2_RELIABILITY_ANALYSIS.json). It contains all 24 planned records: B1 has 5 weak/confounded and 1 invalid checkpoint; B2, B3 and B4 each have 6 weak/confounded decisions. At score threshold 0, 17/24 candidates have target-error evaluations and false-reliable risk is 11/17; at thresholds 0.25–1.0, coverage is 5/24 and false-reliable risk is 1.0. These are descriptive development metrics and show that the current rule does not demonstrate incremental reliability value.

The legacy v3 analysis remains under `outputs/reliability_audit_v1/pilot/ri2_full_v3/reliability_analysis/` for provenance.

