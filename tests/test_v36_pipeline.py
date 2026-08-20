from __future__ import annotations

from saeps.config import load_config
from saeps.v36.pipeline import _aggregate, _exact_sign_tail


def _record(seed: int, d_value: float, e_saeps: float = 0.1) -> dict:
    return {
        "seed": seed,
        "status": "PASS",
        "failure_stage": None,
        "D": d_value,
        "E_raw": e_saeps + d_value,
        "E_SAEPS": e_saeps,
        "I_GN": e_saeps,
    }


def test_exact_sign_threshold() -> None:
    assert _exact_sign_tail(12, 15) < 0.05
    assert _exact_sign_tail(11, 15) > 0.05


def test_planned_invalid_seed_is_nonwin() -> None:
    specification = load_config("configs/v3_6/locked_scalar_confirmation.yaml")
    records = [_record(seed, 1.0) for seed in range(30, 42)]
    records.extend(
        {
            "seed": seed,
            "status": "CHECKPOINT_INVALID",
            "failure_stage": "center",
            "D": None,
            "E_raw": None,
            "E_SAEPS": None,
            "I_GN": None,
        }
        for seed in range(42, 45)
    )
    result = _aggregate(records, specification)
    assert result["scientific_status"] == "SUPPORTED"
    assert result["strict_wins_out_of_planned_15"] == 12
    assert result["invalid"] == 3


def test_eleven_planned_wins_cannot_support() -> None:
    specification = load_config("configs/v3_6/locked_scalar_confirmation.yaml")
    records = [_record(seed, 1.0) for seed in range(30, 41)]
    records.extend(_record(seed, -1.0) for seed in range(41, 45))
    result = _aggregate(records, specification)
    assert result["scientific_status"] == "NOT_SUPPORTED"
    assert result["primary_conditions"]["planned_seed_wins"] is False
