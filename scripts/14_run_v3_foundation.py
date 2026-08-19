"""Run the isolated v3 foundation development workflow."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v3.foundation import run_foundation_development


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_foundation_development(
        root / "configs/v3/foundation_development.yaml",
        root / "outputs/runs/v3_foundation",
        root,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "status": result["status"],
                "engineering_gate": result["engineering_gate"],
                "common_base_status": result["common_base_refinement"]["status"],
                "profile_statuses": {
                    key: value["status"]
                    for key, value in (result.get("profiles") or {}).items()
                },
                "full_hessian_status": (result.get("full_hessian") or {}).get("status"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result["engineering_gate"] == "PASSED" else 1)
