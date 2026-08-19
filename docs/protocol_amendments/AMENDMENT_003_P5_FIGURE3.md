# Amendment 003 — P5 Figure 3 artifact completion

Date: 2026-08-19  
Scope: artifact-only, post-confirmation engineering correction

The locked P5 runner generated all raw profiles, Figure 4 and Table 2 but omitted the required Figure 3 overlay. `scripts/09_build_scalar_figure3.py` reads immutable record JSON and renders centered, independently normalized frozen/reoptimized/classical curves for the first valid seed selected in ascending order.

This amendment does not retrain, recompute profiles, change numerical values, alter inclusion, change a threshold, or change SG-2. It exists solely to complete the preregistered visual artifact and must be disclosed in the final audit.
