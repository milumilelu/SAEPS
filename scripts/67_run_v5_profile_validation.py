"""Run frozen V5.2A optimizer validation seeds 73--74."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_validation import run_profile_validation


if __name__ == "__main__":
    rows = run_profile_validation(Path(__file__).resolve().parents[1])
    print(json.dumps({"terminal_records": len(rows), "pass_records": sum(row["status"] == "PASS" for row in rows), "heldout_authorized": all(row["binding_valid"] for row in rows)}, indent=2))
