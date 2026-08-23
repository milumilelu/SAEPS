from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.baseline_consolidation import (
    write_baseline_consolidation_figure,
    write_baseline_consolidation_report,
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    aggregate = write_baseline_consolidation_report(root)
    figure = write_baseline_consolidation_figure(root, aggregate)
    print(json.dumps({"engineering_status": aggregate["engineering_status"], "scientific_status": aggregate["scientific_status_inherited"], "profile_valid": aggregate["profile_valid_count"], "figure": figure.relative_to(root).as_posix()}, indent=2))
