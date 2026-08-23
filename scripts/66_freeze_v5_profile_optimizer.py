"""Apply the frozen V5.2A selection rule and write the optimizer lock."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_selection import write_profile_optimizer_lock


if __name__ == "__main__":
    lock = write_profile_optimizer_lock(Path(__file__).resolve().parents[1])
    print(json.dumps({"selected_candidate": lock["selected_candidate"], "forbidden_metrics_read": lock["forbidden_metrics_read"]}, indent=2))
