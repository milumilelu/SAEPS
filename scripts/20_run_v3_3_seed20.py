"""Run v3.3 seed-20 numerical decomposition development."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v33.pipeline import run_seed20_numerical_decomposition


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_seed20_numerical_decomposition(
        root / "configs/v3_3/seed20_numerical_decomposition.yaml",
        root / "outputs/runs/v3_3_numerical_decomposition",
        root,
    )
    decomposition = result["development_decomposition"] or {}
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "engineering_gate": result["engineering_gate"],
                "registered_chain_gate": result["registered_chain_gate"],
                "diagnostic_reporting_scope": result["diagnostic_reporting_scope"],
                "nodes": decomposition.get("nodes"),
                "segment_relative_errors": decomposition.get(
                    "segment_relative_errors"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result["engineering_gate"] == "PASSED" else 1)

