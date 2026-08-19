from saeps.artifacts import _final_mapping


def test_numerically_limited_positive_scalar_pair_maps_to_partial_investigation() -> None:
    p2 = {"scientific_gate_sg1": "FAIL", "valid_seeds": 5}
    p5 = {
        "scientific_classification_sg2": "PARTIALLY_SUPPORTED",
        "median_D": 1.0,
        "valid": 1,
    }
    p6 = {"scientific_gate_sg3": "FAIL", "valid": 0}
    assert _final_mapping(p2, p5, p6) == (
        "PARTIALLY_SUPPORTED",
        "INVESTIGATE_NUMERICS",
    )
