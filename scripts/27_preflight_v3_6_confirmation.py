"""Run and optionally save the v3.6 pre-confirmation audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v36.preflight import run_preconfirmation_audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_preconfirmation_audit(root)
    if arguments.write_evidence:
        (root / "docs/evidence/PRE_CONFIRMATION_AUDIT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)

