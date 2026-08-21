from __future__ import annotations

import json
from pathlib import Path

from saeps.v44.preflight import run_v44_preflight


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    result = run_v44_preflight(ROOT)
    (ROOT / "docs/evidence/V4_4_PRE_CONFIRMATION_AUDIT.json").write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)

