from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.residual_scalability import run_residual_scalability


if __name__ == "__main__":
    rows = run_residual_scalability(Path(__file__).resolve().parents[1])
    print(json.dumps({"terminal_records": len(rows), "pass_records": sum(row["status"] == "PASS" for row in rows)}, indent=2))
