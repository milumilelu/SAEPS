from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.final_validation import validate_v5_repository


if __name__ == "__main__":
    result = validate_v5_repository(Path(__file__).resolve().parents[1], require_final=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
