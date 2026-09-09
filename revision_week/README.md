# SAEPS SO first-stage development

Isolated extension for the user's 2026-09-09 request. Historical locks remain
closed. No push, training, replacement seeds or new confirmation. Inputs are
read-only from the original workspace; outputs: revision_week/outputs/day1.

PowerShell from this worktree:

```powershell
$py = 'C:/Users/RZF/Desktop/博士课题资料/SAEPS/.venv/Scripts/python.exe'
& $py revision_week/run.py audit --repo 'C:/Users/RZF/Desktop/博士课题资料/SAEPS'
& $py revision_week/run.py self-test
& $py revision_week/run.py run --experiment E0 --config revision_week/config/protocol.template.yaml
& $py revision_week/run.py report --run-id day1
```

E0 writes each terminal record atomically. Repeat the run command to resume;
input/config/code hashes must match, and failed records are also reused.
Changed inputs/code require a new output root, never replacement of failed runs.
Freeze and E1–E5 are not implemented or claimed. The original E0 tensors are not
archived; the JVP/HVP adapter is validated only on a tiny actual scalar network.
Dense diagonal-PCG is a bounded E0 diagnostic, not production efficiency evidence.
ALL_RUNS.csv, METHOD_SUMMARY.csv and raw/ drive all generated result reports.
