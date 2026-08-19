"""Run the v3.1 development-only seed-20 serial gate."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v31.pipeline import run_seed20_development


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_seed20_development(
        root / "configs/v3_1/seed20_development.yaml",
        root / "outputs/runs/v3_1_state_minimum",
        root,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "engineering_gate": result["engineering_gate"],
                "full_chain_gate": result["full_chain_gate"],
                "serial_stop_stage": result["serial_stop_stage"],
                "eligible_to_request_activation_of_seeds_21_24": result[
                    "eligible_to_request_activation_of_seeds_21_24"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result["engineering_gate"] == "PASSED" else 1)
