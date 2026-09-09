# Resume / reproduce saved stage

```powershell
Set-Location 'C:\Users\RZF\Desktop\博士课题资料\SAEPS-so-week1'
$py = 'C:\Users\RZF\Desktop\博士课题资料\SAEPS\.venv\Scripts\python.exe'
& $py revision_week/run.py run --experiment E0 --config revision_week/config/protocol.template.yaml
& $py revision_week/run.py report --run-id day1
```

The first command was actually rerun and left all terminal raw hashes unchanged.
No seed replacements or automatic background continuation. The raw results,
source commit and input hashes remain the authoritative numerical evidence.
Do not rerun audit against this changed branch inventory and call it the old audit.
New E1 needs explicit historical tensor recovery/provenance work before use.
