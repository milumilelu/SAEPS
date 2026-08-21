from saeps.config import load_config
from saeps.v44.aggregation import aggregate_allen_confirmation


def _record(seed: int, valid: bool, difference: float | None) -> dict:
    return {
        "seed": seed,
        "status": "PASS" if valid else "CHECKPOINT_INVALID",
        "binding_valid": valid,
        "E_raw": 2.0 if valid else None,
        "E_SAEPS": 0.1 if valid else None,
        "D": difference,
        "I_GN": 0.08 if valid else None,
        "failure_reason": None if valid else "center failed",
        "statuses": {"profile_status": "PROFILE_FAILURE"},
    }


def test_v44_planned_denominator_and_exact_sign_rule() -> None:
    specification = load_config("configs/v4_4/locked_allen_cahn_confirmation.yaml")
    records = [_record(seed, seed < 83, 1.9 if seed < 83 else None) for seed in range(75, 85)]
    result = aggregate_allen_confirmation(records, specification)
    assert result["valid"] == 8
    assert result["strict_wins_out_of_planned"] == 8
    assert result["exact_one_sided_sign_p"] == 0.00390625
    assert result["scientific_status"] == "SUPPORTED"

