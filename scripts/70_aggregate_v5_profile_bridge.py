from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_aggregation import write_profile_bridge_figure, write_profile_bridge_report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = write_profile_bridge_report(root)
    figure = write_profile_bridge_figure(root, result)
    print(json.dumps({"engineering_status": result["engineering_status"], "scientific_status": result["scientific_status"], "evaluable": result["evaluable_count"], "valid": result["profile_valid_count"], "figure": figure.relative_to(root).as_posix()}, indent=2))
