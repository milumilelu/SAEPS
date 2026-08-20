from __future__ import annotations

from saeps.config import load_config
from saeps.v42.aggregation import aggregate_v42


def _row(seed: int, d_value: float) -> dict:
    return {
        "seed": seed,
        "status": "PASS",
        "failure_stage": None,
        "D": d_value,
        "E_raw": 2.0,
        "E_SAEPS": 2.0 - d_value,
        "I_GN": 0.04,
    }


def test_v42_preserves_twelve_of_fifteen_rule() -> None:
    v42 = load_config("configs/v4_2/locked_corrected_confirmation.yaml")
    v36 = load_config("configs/v3_6/locked_scalar_confirmation.yaml")
    result = aggregate_v42([_row(seed, 1.0) for seed in range(55, 70)], v42, v36)
    assert result["scientific_status"] == "SUPPORTED"
    assert result["strict_wins_out_of_planned_15"] == 15
    assert result["v3_6_result_modified"] is False
