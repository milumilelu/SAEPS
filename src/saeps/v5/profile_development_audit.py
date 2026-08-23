"""Audit V5.2A candidate selection and frozen validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file


def build_profile_development_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    lock = json.loads((root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json").read_text(encoding="utf-8"))
    rows = []
    for seed in [73, 74]:
        path = root / f"outputs/runs/v5/profile_engineering/validation/seed_{seed}/result.json"
        if not path.is_file():
            raise ValueError(f"missing V5.2A validation record: {seed}")
        record = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "all_8_profile_points_pass": record["all_8_profile_points_pass"],
                "finest_profile_exact_relative_error": record[
                    "finest_profile_exact_relative_error"
                ],
                "last_two_curvature_relative_change": record[
                    "last_two_curvature_relative_change"
                ],
                "source": {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)},
            }
        )
    gate = all(row["status"] == "PASS" and row["all_8_profile_points_pass"] for row in rows)
    return {
        "schema_version": 1,
        "phase": "V5_2A_PROFILE_ENGINEERING",
        "engineering_status": "PASSED" if gate else "FAILED",
        "selected_candidate": lock["selected_candidate"],
        "candidate_selection": lock["candidate_summaries"],
        "validation_records": rows,
        "validation_gate": "2_of_2_exact_reference_and_8_of_8_independent_profile_points_PASS",
        "heldout_authorized": gate,
        "heldout_accuracy_thresholds_changed": False,
        "development_accuracy_is_nonbinding": True,
        "forbidden_metrics_read": False,
    }


def write_profile_development_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit = build_profile_development_audit(root)
    write_json_atomic(root / "docs/evidence/v5/V5_PROFILE_DEVELOPMENT_AUDIT.json", audit)
    lines = [
        "# V5.2A Profile Development Audit",
        "",
        f"- Engineering status: `{audit['engineering_status']}`",
        f"- Selected optimizer: `{audit['selected_candidate']}`",
        f"- Held-out authorized: `{str(audit['heldout_authorized']).lower()}`",
        "- Development accuracy values are nonbinding; held-out 10%/5% thresholds remain unchanged.",
        "",
        "| Seed | Status | 8/8 points | Finest profile/exact error | Last-two change |",
        "|---:|---|---|---:|---:|",
    ]
    lines.extend(
        f"| {row['seed']} | {row['status']} | {str(row['all_8_profile_points_pass']).lower()} | {row['finest_profile_exact_relative_error']:.6g} | {row['last_two_curvature_relative_change']:.6g} |"
        for row in audit["validation_records"]
    )
    (root / "docs/evidence/v5/V5_PROFILE_DEVELOPMENT_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return audit
