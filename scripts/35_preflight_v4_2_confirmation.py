"""Run and optionally save v4.2 pre-confirmation audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v42.preflight import run_v42_preflight


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_v42_preflight(root)
    if arguments.write_evidence:
        (root / "docs/evidence/V4_2_PRE_CONFIRMATION_AUDIT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
