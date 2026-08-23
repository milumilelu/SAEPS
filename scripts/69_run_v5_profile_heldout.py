"""Run the one-shot V5.2B held-out profile bridge cohort."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_heldout import run_profile_heldout


if __name__ == "__main__":
    rows = run_profile_heldout(Path(__file__).resolve().parents[1])
    print(json.dumps({"terminal_records": len(rows), "evaluable": sum(row["PROFILE_EVALUABLE"] for row in rows), "profile_valid": sum(row["PROFILE_VALID"] for row in rows)}, indent=2))
