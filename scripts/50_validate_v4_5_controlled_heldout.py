"""Validate frozen v4.5 held-out development without mechanism outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    base = root / "outputs/runs/v4_5_controlled_mechanism/heldout"
    rows = []
    for seed in (88, 89):
        result_path = base / f"seed_{seed}/result.json"
        manifest = _read(base / f"seed_{seed}/manifest.json")
        record = _read(result_path)
        digest = hashlib.sha256(result_path.read_bytes()).hexdigest()
        rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "center_gate": record["center"]["final"]["local_minimum_gate"],
                "alpha_passes": sum(item["status"] == "PASS" for item in record["alpha_evaluations"]),
                "maximum_solver_residual": max(item["solver_verified_relative_residual"] for item in record["alpha_evaluations"]),
                "maximum_explicit_error": max(item["explicit_mf_relative_error"] for item in record["alpha_evaluations"]),
                "result_sha256": digest,
                "manifest_hash_matches": manifest["result_sha256"] == digest,
            }
        )
    checks = {
        "exact_heldout_seeds": [row["seed"] for row in rows] == [88, 89],
        "binding_centers_2_of_2": sum(row["binding_valid"] for row in rows) == 2,
        "alpha_evaluations_10_of_10": sum(row["alpha_passes"] for row in rows) == 10,
        "raw_hashes_match": all(row["manifest_hash_matches"] for row in rows),
        "solver_residual_gate": max(row["maximum_solver_residual"] for row in rows) <= 1.0e-8,
        "explicit_agreement_gate": max(row["maximum_explicit_error"] for row in rows) < 1.0e-6,
    }
    audit = {
        "schema_version": 1,
        "phase": "V4_5_CONTROLLED_MECHANISM_HELDOUT",
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "rows": rows,
        "selection_metrics_excluded": ["eta", "monotonicity", "spearman", "figure_appearance"],
        "confirmation_authorized": False,
    }
    path = root / "docs/evidence/v4_5_controlled_heldout.json"
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
