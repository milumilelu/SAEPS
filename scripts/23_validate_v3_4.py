"""Validate and aggregate v3.4 development evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v34.validation import validate_v3_4


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = validate_v3_4(root)
    if arguments.write_evidence:
        (root / "docs/evidence/v3_4_validation.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)

