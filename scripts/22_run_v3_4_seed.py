"""Run one authorized v3.4 development seed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v34.pipeline import run_curvature_validation_seed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_curvature_validation_seed(
        arguments.seed,
        root / "configs/v3_4/curvature_validation.yaml",
        root / "outputs/runs/v3_4_curvature_validation",
        root,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "seed": result["seed"],
                "readiness_gate": result["readiness_gate"],
                "curvature_solver": (result["solver_hierarchy"] or {})
                .get("CURVATURE_SOLVER_GATE", {})
                .get("status"),
                "score_solver": (result["solver_hierarchy"] or {})
                .get("SCORE_SOLVER_GATE", {})
                .get("status"),
                "local_GN": (result["local_GN_validation"] or {}).get("status"),
                "finite_radius": (result["finite_radius_validation"] or {}).get(
                    "status"
                ),
                "certified_h": (result["finite_radius_validation"] or {}).get(
                    "certified_h_values"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
