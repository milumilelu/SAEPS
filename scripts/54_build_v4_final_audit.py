from __future__ import annotations

import json
from pathlib import Path

from saeps.v49.final_audit import audit_v4, render_report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    audit = audit_v4(root)
    (root / "docs/evidence/v4_final_audit.json").write_text(
        json.dumps(audit, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (root / "V4_FINAL_AUDIT_REPORT.md").write_text(render_report(audit), encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
