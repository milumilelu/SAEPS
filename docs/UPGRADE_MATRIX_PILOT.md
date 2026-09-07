# Historical matrix development pilot

Date: 2026-09-07. Status: PASSED (bounded engineering audit).

Authorization is the user's request to perform only the first-layer historical
matrix development experiment. The attached research proposal and starter are
reference material, not authorization for subsequent training, new confirmation,
publication, or changes to existing locks. V2 through V5 remain closed and unchanged.

Storage note: the pilot lives in `outputs/runs/v5/upgrade_pilot` solely because
the historical V5 inventory freezes the entire `outputs/runs` tree except its
`v5` subtree. This is not a reopening of V5 scientific execution. Existing V5
run/config files and its inventory validator remain unchanged. The first pilot
directories were moved intact from `outputs/runs/upgrade_pilot` after the full
validator exposed that storage collision; no numerical run was repeated.

This is a separate exploratory upgrade namespace, not feedback into historical
development or confirmation. All 25 archived records under
`outputs/posthoc/exact_fixed_state_v3/*/seed_*.json` are included, including four
originally invalid records. The 21 valid records are historical development data
for this new pilot only. No new seeds are run.

Use the supplied starter unchanged, with budgets 0,1,3,5,10, diagonal GN and exact
GN preconditioning, and its default positive-definiteness, rank and response
tolerances. Preserve checkpoint, residual scale, physical coordinates and gamma.
No outcome-driven adjustments were made. Exact GN is an optimistic dense control.
Both candidate construction and reference evaluation are matrix-only; neither
establishes production cost or nonlinear profile accuracy.

Reproduction (output directories must not already exist):

```powershell
.venv/Scripts/python.exe scripts/upgrade_pilot/pilot_curvature_correction.py --self-test
.venv/Scripts/python.exe scripts/upgrade_pilot/pilot_curvature_correction.py --repo . --output outputs/runs/v5/upgrade_pilot/gn_diagonal_01 --steps 0,1,3,5,10 --preconditioner gn-diagonal
.venv/Scripts/python.exe scripts/upgrade_pilot/pilot_curvature_correction.py --repo . --output outputs/runs/v5/upgrade_pilot/gn_exact_01 --steps 0,1,3,5,10 --preconditioner gn-exact
.venv/Scripts/python.exe scripts/upgrade_pilot/audit_pilot.py
```

The audit rebuilds its derived JSON/report from raw pilot records; checks source
and script hashes, denominator completeness, archived GN/Schur reproduction,
second-order correction identity, PSD gap and nested monotonicity; and tests CLI
overwrite protection. Engineering tolerances are 1e-6 for archived reproduction
and 1e-8 for scale-relative algebra checks, not scientific acceptance thresholds.
The supplied script's descriptive statuses are preserved; the audit maps terminal
records to PASS, CHECKPOINT_INVALID or NUMERICAL_FAILURE without overwriting them.

Generated report: `outputs/runs/v5/upgrade_pilot/audit/REPORT.md`.
Machine-readable evidence: `outputs/runs/v5/upgrade_pilot/audit/audit.json`.
Per-budget data: each method's `metrics.csv` and `records.json`.
Input hashes, starter/script hashes, environment and base Git commit are recorded.
Component timing and peak memory are unavailable in this starter; no speedup is
claimed. JVP/VJP/HVP and CG counts are zero because this is dense archived algebra.

The initial worktree contained unrelated deletions and untracked user material.
These were preserved. Automatic remote synchronization is withheld under AGENTS.md
section 10; only this task's explicit files may be committed locally.
