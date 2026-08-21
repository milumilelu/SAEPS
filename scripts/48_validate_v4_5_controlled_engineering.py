"""Validate v4.5 engineering using binding numerical objects only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    base = root / "outputs/runs/v4_5_controlled_mechanism/engineering_v2"
    rows = []
    for seed in (85, 86, 87):
        directory = base / f"seed_{seed}"
        result_path = directory / "result.json"
        manifest = _read(directory / "manifest.json")
        record = _read(result_path)
        actual_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
        rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "center_method": record["center_method"],
                "center_gate": record["center"]["final"]["local_minimum_gate"],
                "theta_stationarity": record["center"]["theta_stationarity"],
                "alpha_passes": sum(row["status"] == "PASS" for row in record["alpha_evaluations"]),
                "maximum_solver_residual": max(row["solver_verified_relative_residual"] for row in record["alpha_evaluations"]),
                "maximum_explicit_error": max(row["explicit_mf_relative_error"] for row in record["alpha_evaluations"]),
                "result_sha256": actual_hash,
                "manifest_hash_matches": manifest["result_sha256"] == actual_hash,
            }
        )
    checks = {
        "exact_engineering_seeds": [row["seed"] for row in rows] == [85, 86, 87],
        "binding_centers_3_of_3": sum(row["binding_valid"] for row in rows) == 3,
        "alpha_evaluations_15_of_15": sum(row["alpha_passes"] for row in rows) == 15,
        "raw_hashes_match": all(row["manifest_hash_matches"] for row in rows),
        "solver_residual_gate": max(row["maximum_solver_residual"] for row in rows) <= 1.0e-8,
        "explicit_agreement_gate": max(row["maximum_explicit_error"] for row in rows) < 1.0e-6,
    }
    audit = {
        "schema_version": 1,
        "phase": "V4_5_CONTROLLED_MECHANISM_ENGINEERING_V2",
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "rows": rows,
        "selection_metrics_excluded": ["eta", "monotonicity", "spearman", "figure_appearance"],
    }
    evidence = root / "docs/evidence/v4_5_controlled_engineering.json"
    evidence.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
