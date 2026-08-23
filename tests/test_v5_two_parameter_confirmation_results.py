from pathlib import Path

from saeps.v5.two_parameter_aggregation import build_two_parameter_confirmation


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_two_parameter_confirmation_applies_planned_denominator() -> None:
    aggregate = build_two_parameter_confirmation(ROOT)
    assert aggregate["engineering_status"] == "PASSED"
    assert aggregate["terminal_count"] == 10
    assert aggregate["binding_valid_count"] == 8
    assert aggregate["planned_win_count"] == 8
    assert aggregate["scientific_status"] == "INCONCLUSIVE"
    assert aggregate["primary_gate"]["valid_gate_pass"] is False
    assert aggregate["primary_gate"]["planned_win_gate_pass"] is False


def test_actual_valid_two_parameter_pairs_are_directionally_consistent_but_nonbinding() -> None:
    aggregate = build_two_parameter_confirmation(ROOT)
    assert aggregate["valid_win_count"] == 8
    assert aggregate["valid_non_tied_count"] == 8
    assert aggregate["one_sided_exact_sign_test_p"] == 0.00390625
    assert aggregate["valid_median_D2"] > 0.0
    assert aggregate["generalized_geometry_role"] == (
        "secondary_nonbinding_no_orientation_claim"
    )
