import numpy as np

from saeps.reliability_audit_v1.reliability import (
    GAMMA_ALPHA_GRID,
    classify_record,
    gamma_path_from_jacobians,
    selective_metrics,
    target_log_error,
)


def test_gamma_path_matches_scalar_finite_damping_and_zero_limit():
    result = gamma_path_from_jacobians(np.array([[1.0]]), np.array([[1.0]]))
    assert result["gamma_alpha_grid"] == list(GAMMA_ALPHA_GRID)
    assert result["state_rank"] == 1
    assert result["F0_rank"] == 0
    for row in result["gamma_path"]:
        gamma = row["gamma"]
        expected = gamma / (1.0 + gamma)
        assert np.isclose(row["F_gamma"][0][0], expected, rtol=1e-10, atol=1e-14)
        assert row["rank"] == 1


def test_full_rank_decision_uses_fim_and_never_truth():
    path = gamma_path_from_jacobians(np.zeros((3, 0)), np.eye(3, 1))
    manifest = {
        "execution_status": "PASS",
        "fit_status": "PASS",
        "unknown_parameters": ["k"],
        "_I_obs_matrix": np.array([[10.0]]),
    }
    decision = classify_record(manifest, path)
    assert decision["decision"] == "SUPPORTED_COMBINATION"
    assert decision["accepted"] is True
    assert decision["confidence_score"] == 1.0


def test_rank_deficiency_abstains_even_when_finite_gamma_is_positive():
    path = gamma_path_from_jacobians(np.array([[1.0]]), np.array([[1.0, 1.0]]))
    manifest = {
        "execution_status": "PASS",
        "fit_status": "PASS",
        "benchmark": "B3",
        "unknown_parameters": ["k", "C"],
        "_I_obs_matrix": np.array([[1.0, 1.0], [1.0, 1.0]]),
    }
    decision = classify_record(manifest, path)
    assert decision["decision"] == "WEAK_OR_CONFOUNDED"
    assert decision["accepted"] is False
    assert decision["reason"] == "independent_observation_rank_deficient"
    assert decision["identified_subspace"]["named_combinations"]["identifiable"] == ["log(k)-log(C)"]


def test_target_error_and_denominator_preserving_selective_curve():
    good = {
        "run_id": "good",
        "benchmark": "B1",
        "parameter_estimates": {"k": 0.6},
        "physical_truth": {"k": 0.6, "C": 1.2, "a": 1.0},
        "decision_record": {"accepted": True, "confidence_score": 1.0},
    }
    bad = {
        "run_id": "bad",
        "benchmark": "B1",
        "parameter_estimates": {"k": 0.3},
        "physical_truth": {"k": 0.6, "C": 1.2, "a": 1.0},
        "decision_record": {"accepted": True, "confidence_score": 0.1},
    }
    abstain = {"run_id": "abstain", "benchmark": "B2", "decision_record": {"accepted": False, "confidence_score": 0.0}}
    assert target_log_error(good) == 0.0
    assert target_log_error(bad) > np.log(1.1)
    metrics = selective_metrics([good, bad, abstain], thresholds=(0.0, 0.5))
    assert metrics["planned_denominator"] == 3
    assert metrics["risk_coverage"][0]["accepted"] == 2
    assert metrics["risk_coverage"][0]["coverage"] == 2 / 3
    assert metrics["risk_coverage"][0]["false_reliable_count"] == 1
    assert metrics["risk_coverage"][1]["accepted"] == 1
    assert metrics["risk_coverage"][1]["risk"] == 0.0
