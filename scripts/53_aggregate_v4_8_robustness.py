from __future__ import annotations

import json
from pathlib import Path

from saeps.v49.aggregation import aggregate_v4_8


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = aggregate_v4_8(root)
    destination = root / "docs/evidence/v4_8_robustness.json"
    destination.write_text(json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
