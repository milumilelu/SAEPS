"""Run the one-shot V5.2A profile optimizer candidate cohort."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_engineering import run_profile_candidate_cohort, select_profile_candidate


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    rows = run_profile_candidate_cohort(root)
    selection = select_profile_candidate(root)
    print(json.dumps({"terminal_records": len(rows), "pass_records": sum(row["status"] == "PASS" for row in rows), "selected_candidate": selection["selected_candidate"], "candidate_summaries": selection["candidate_summaries"]}, indent=2))
