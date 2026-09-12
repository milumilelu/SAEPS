import pytest
import torch
import numpy as np

from saeps.reliability_audit_v1.corrections import (
    DecisionMode,
    SaepsOnlyInput,
    check_log_parameter_bounds,
    evaluate_refinement,
    make_side_effect_free_closure,
    normalized_heat_residual_from_parameters,
    normalized_quadrature_weights,
    weighted_residual_mean_square,
)
from saeps.reliability_audit_v1.reliability import classify_saeps_only, gamma_path_from_jacobians


def _saeps_values():
    return {
        "observation": [1.0],
        "known_constants": {"pi": 3.14159},
        "checkpoint": object(),
        "noise_sigma": 0.01,
        "residual_weights": {"data": 1.0},
        "numerical_config": {"dtype": "float64"},
    }


def test_saep_only_rejects_hidden_truth_and_fim() -> None:
    values = _saeps_values()
    values["physical_truth"] = {"k": 0.6}
    with pytest.raises(TypeError, match="rejects oracle"):
        SaepsOnlyInput.from_mapping(values)

    values = _saeps_values()
    values["numerical_config"] = {"reference": {"k_true": 0.6}}
    with pytest.raises(TypeError, match="rejects oracle"):
        SaepsOnlyInput.from_mapping(values)

    obj = SaepsOnlyInput.from_mapping(_saeps_values())
    assert obj.mode is DecisionMode.SAEPS_ONLY


def test_normalized_residual_is_invariant_to_common_parameter_scale() -> None:
    ut = torch.tensor([0.8, -0.3, 1.4], dtype=torch.float64)
    uxx = torch.tensor([-1.2, 0.9, -0.1], dtype=torch.float64)
    first = normalized_heat_residual_from_parameters(ut, uxx, 0.6, 1.2)
    second = normalized_heat_residual_from_parameters(ut, uxx, 0.006, 0.012)
    torch.testing.assert_close(first, second)


def test_closure_does_not_clamp_or_mutate_parameters() -> None:
    parameter = torch.nn.Parameter(torch.tensor(0.25, dtype=torch.float64))
    optimizer = torch.optim.LBFGS([parameter], max_iter=1)
    before = parameter.detach().clone()

    def objective():
        return (parameter - 1.0).square()

    closure = make_side_effect_free_closure(objective, optimizer, {"k": parameter}, lower=-1.0, upper=1.0)
    value = closure()
    assert value.ndim == 0
    torch.testing.assert_close(parameter.detach(), before)
    assert check_log_parameter_bounds({"k": parameter}, -1.0, 1.0)["within_bounds"]

    parameter.data.fill_(2.0)
    with pytest.raises(ValueError, match="outside bounds"):
        closure()


def test_refinement_uses_one_percent_noise_threshold() -> None:
    result = evaluate_refinement(0.1, 0.10015798093922381, noise_scale=0.01)
    assert result["threshold"] == pytest.approx(1.0e-4)
    assert result["pass"] is False
    assert result["noise_fraction"] == pytest.approx(0.01)


def test_gamma_report_separates_cross_scale_from_within_spectrum_score() -> None:
    result = gamma_path_from_jacobians(
        np.array([[1.0]]), np.array([[1.0]]),
        gamma_alpha_grid=(1.0e-4, 1.0e-2),
    )
    assert result["gamma_stability_score"] == pytest.approx(1.0)
    assert result["gamma_cross_scale_ratio"] > 50.0
    assert "within-spectrum" in result["gamma_stability_interpretation"]


def test_saeps_only_decision_does_not_require_observation_fim() -> None:
    path = gamma_path_from_jacobians(np.zeros((3, 0)), np.eye(3, 1))
    decision = classify_saeps_only(path, n_unknown=1)
    assert decision["accepted"] is True
    assert "I_obs" not in decision


def test_f0_is_norm_of_explicit_projected_columns() -> None:
    result = gamma_path_from_jacobians(np.eye(2), np.array([[1.0], [2.0]]))
    assert result["F0_projection_residual_norm"] == pytest.approx(0.0, abs=1e-12)
    assert result["F0"][0][0] == pytest.approx(0.0, abs=1e-12)


def test_quadrature_weights_keep_domain_mass_when_points_are_repeated() -> None:
    base = torch.tensor([1.0, 2.0], dtype=torch.float64)
    repeated = base.repeat_interleave(4)
    first = weighted_residual_mean_square(base, normalized_quadrature_weights(2))
    second = weighted_residual_mean_square(repeated, normalized_quadrature_weights(repeated.numel()))
    assert second == pytest.approx(first.item())
