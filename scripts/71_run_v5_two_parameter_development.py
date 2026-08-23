from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.two_parameter_development import run_two_parameter_development


if __name__ == "__main__":
    rows = run_two_parameter_development(Path(__file__).resolve().parents[1])
    print(json.dumps({"terminal_records": len(rows), "binding_valid": sum(row["binding_valid"] for row in rows), "heldout_authorized": all(row["binding_valid"] for row in rows)}, indent=2))
