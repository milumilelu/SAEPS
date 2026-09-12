# Cost audit

The corrected RI-2 development pilot (`outputs/reliability_audit_v1/pilot/ri2_full_v6`; v3/v5 retained) executed 24 cases once. Per-run manifests record training wall time, dtype, hardware, Adam/L-BFGS iteration budgets, Jacobian dimensions, gamma scale and raw matrix paths. Derived gamma-path analysis records its source checkpoints and cached Jacobians under the versioned `reliability_analysis/derived_jacobians/` directory.

The pilot has no PINN-reoptimised profile, bootstrap or independent finite-difference solve cost per run; those fields remain unavailable rather than being inferred. The independent physical-reference refinement report is `outputs/reliability_audit_v1/pilot/ri1/PHYSICAL_REFERENCE_REPORT.json`. Historical SAEPS cost evidence is retained in `docs/evidence/P8_ACCEPTANCE.md` and is not relabeled as identifiability-pilot cost.
