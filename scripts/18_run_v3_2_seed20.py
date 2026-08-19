"""Run v3.2 seed-20 gamma-matched primary development."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v32.pipeline import run_seed20_gamma_primary


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_seed20_gamma_primary(
        root / "configs/v3_2/seed20_gamma_primary.yaml",
        root / "outputs/runs/v3_2_gamma_primary",
        root,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "engineering_gate": result["engineering_gate"],
                "primary_chain_gate": result["primary_chain_gate"],
                "gamma_profile_status": (
                    result["gamma_matched_primary"] or {}
                ).get("status"),
                "unregularized_status": (
                    result["unregularized_secondary"] or {}
                ).get("status"),
                "krylov_status": (result["krylov_gate"] or {}).get("status"),
                "gamma_exact_status": (
                    (result["full_hessian"] or {}).get("gamma_matched") or {}
                ).get("status"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result["engineering_gate"] == "PASSED" else 1)
