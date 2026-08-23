"""Freeze the V5.2A optimizer selection from the preregistered candidate rule."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.profile_engineering import CANDIDATE_SEEDS, select_profile_candidate


def write_profile_optimizer_lock(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selection = select_profile_candidate(root)
    sources = []
    for summary in selection["candidate_summaries"]:
        candidate = summary["candidate"]
        for seed in CANDIDATE_SEEDS:
            path = (
                root
                / "outputs/runs/v5/profile_engineering/candidates"
                / candidate
                / f"seed_{seed}/result.json"
            )
            sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    lock = {
        **selection,
        "contract_id": "SAEPS-V5.2A-FROZEN-PROFILE-OPTIMIZER",
        "freeze_date": "2026-08-23",
        "selected_settings": {
            "kind": "optimize_state_local_minimum",
            "normalized_gradient_tolerance": 1.0e-6,
            "h_values": [0.04, 0.02, 0.01, 0.005],
            "independent_start_from_common_theta0": True,
            "continuation_forbidden": True,
        },
        "validation_seeds": [73, 74],
        "heldout_scientific_seeds": [200, 201, 202, 203, 204],
        "source_records": sources,
    }
    write_json_atomic(root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json", lock)
    write_json_atomic(root / "docs/evidence/v5/V5_PROFILE_OPTIMIZER_SELECTION.json", lock)
    lines = [
        "# V5.2A Profile Optimizer Selection",
        "",
        f"Selected: `{lock['selected_candidate']}`",
        "",
        "Selection used only the frozen numerical/profile criteria. D, E_raw, E_SAEPS, eta, F_raw and F_se_GN were neither computed nor read.",
        "",
        "| Candidate | Complete seeds | Passing points | Median finest exact error | Median last-two change |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in lock["candidate_summaries"]:
        lines.append(
            f"| {row['candidate']} | {row['complete_seed_count']}/3 | {row['passing_point_count']}/24 | "
            f"{row['median_finest_profile_exact_relative_error']:.6g} | {row['median_last_two_curvature_relative_change']:.6g} |"
        )
    (root / "docs/evidence/v5/V5_PROFILE_OPTIMIZER_SELECTION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return lock
