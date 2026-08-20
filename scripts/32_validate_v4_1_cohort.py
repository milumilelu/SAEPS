"""Validate one v4.1 development cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v41.validation import validate_v41_cohort


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["ENGINEERING_INTEGRATION", "HELDOUT_DEVELOPMENT"])
    parser.add_argument("--write-evidence", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = validate_v41_cohort(root, arguments.role)
    if arguments.write_evidence:
        suffix = arguments.role.lower()
        (root / f"docs/evidence/v4_1_{suffix}_validation.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
