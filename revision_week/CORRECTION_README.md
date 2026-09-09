# Phase 1B corrective development

User authorization: after the code review, “交给你了”. This repair preserves all
day1/day2 data and records previous repeat attempts as protocol deviations.
It does not retrospectively change any historical protocol or label it compliant.

No more training is permitted. The old five entry points now reject execution,
preventing silent overwrite/replay. Their original source remains in commit
0c91c4f; historical code-hash manifests refer to that version, not the repaired code.

New protocol: config/phase1b_correction.json. Supplemental validation has four
real HVP workers and at most 24 profile solves on saved states (4 original starts,
8 distinct saved candidates, and one fixed precision refinement of each). These
are corrective validation costs, not replacements for old runs or new candidates.
The original process did not save its start/candidate tensors, requiring numerical
replay for precision analysis. Extra validation is separately scoped and accounted.
No increase of original training/ADAPT iterations or tuning of trial coordinates.

Worker process deadlines include startup, with aggregate charged wall time and
immutable attempt claims. A worker timeout/failure cannot trigger a retry.
The shared solver also checks time in its closure; timeout cannot be accepted.
Resuming the same code/config reuses completed tasks. Parent interruption leaves
an incomplete claim requiring explicit audit, not an automatic restart.

From this worktree, use the existing SAEPS venv Python:

```powershell
$py = 'C:/Users/RZF/Desktop/博士课题资料/SAEPS/.venv/Scripts/python.exe'
& $py -m pytest -q revision_week/test_p1b_correction.py revision_week/test_core.py
& $py revision_week/p1b_correct.py run
& $py revision_week/p1b_correct.py report
& $py revision_week/p1b_closeout.py
```

The first run requires committed code and a clean worktree, then records source,
configuration and all historical output hashes before any new measurement.
Reports derive counters and metrics from worker records; historical estimated
failure costs remain labelled estimates. Independent confirmation remains closed.

Final authority for the corrective run: outputs/phase1b_correction_v1/FINAL_CORRECTION_REPORT.md
and FINAL_REVIEW_VALIDATION.json. They separately report objective precision margin,
strict state stationarity, and historical compliance; none implies the others.
The report's historical artifacts remain exactly as they were at execution time.
