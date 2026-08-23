import json
from pathlib import Path

from saeps.v5.baseline_consolidation import build_baseline_consolidation


ROOT = Path(__file__).resolve().parents[1]


def test_v5_baseline_consolidation_is_source_derived_and_preserves_failure() -> None:
    aggregate = build_baseline_consolidation(ROOT)
    assert aggregate["training_runs"] == 0
    assert aggregate["profile_valid_count"] == 1
    assert aggregate["scientific_status_inherited"] == "NOT_SUPPORTED"
    source = json.loads((ROOT / "outputs/runs/v5/profile_bridge/seed_200/result.json").read_text(encoding="utf-8"))
    row = aggregate["seed_rows"][0]
    assert row["curvature"]["F_raw"] == source["F_raw"]
    assert row["curvature"]["F_se_GN"] == source["F_se_GN_explicit"]
    assert row["curvature"]["H_red_exact_gamma"] == source["H_red_exact_gamma"]
    center = next(point for point in row["objective_rows"] if point["offset"] == 0.0)
    assert center["Phi_reopt_gamma"] == source["m"] * source["profile"]["center_loss_mean"]
    assert center["Phi_frozen"] == center["Phi_SAEPS_quadratic"] == center["Phi_reopt_gamma"]
