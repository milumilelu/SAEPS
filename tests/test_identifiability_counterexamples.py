"""Permanent, checkpoint-independent identifiability regression tests."""

from __future__ import annotations

import torch

from saeps.identifiability import (
    counterexample_metadata,
    exact_zero_damping_curvature,
    finite_gamma_reduced_curvature,
    heat_temperature,
    heat_temperature_sensitivities,
    numerical_rank,
)


DTYPE = torch.float64


def test_state_parameter_compensation_has_zero_unrestricted_curvature() -> None:
    # r(w,p)=w+p-y: every p has a compensating state w=y-p.
    jw = torch.tensor([[1.0]], dtype=DTYPE)
    jp = torch.tensor([[1.0]], dtype=DTYPE)
    raw = jp.T @ jp
    exact = exact_zero_damping_curvature(jw, jp)
    assert torch.allclose(raw, torch.ones((1, 1), dtype=DTYPE))
    assert torch.allclose(exact, torch.zeros((1, 1), dtype=DTYPE), atol=1.0e-14)

    for gamma in (1.0e-8, 1.0e-4, 1.0, 1.0e4):
        reduced = finite_gamma_reduced_curvature(jw, jp, gamma)
        expected = gamma / (1.0 + gamma)
        assert torch.allclose(reduced, torch.tensor([[expected]], dtype=DTYPE), atol=1.0e-12)


def test_finite_damping_curvature_is_regularization_dependent() -> None:
    jw = torch.tensor([[1.0]], dtype=DTYPE)
    jp = torch.tensor([[1.0]], dtype=DTYPE)
    values = [float(finite_gamma_reduced_curvature(jw, jp, g).item()) for g in (1.0e-8, 1.0e-4, 1.0, 1.0e4)]
    assert values == sorted(values)
    assert values[0] < 1.0e-6
    assert values[-1] > 0.999


def test_parameter_only_rank_deficiency_recovers_combination_not_individuals() -> None:
    jp = torch.tensor([[1.0, 1.0], [2.0, 2.0]], dtype=DTYPE)
    curvature = jp.T @ jp
    assert numerical_rank(jp) == 1
    eigenvalues, eigenvectors = torch.linalg.eigh(curvature)
    assert eigenvalues[0].item() <= 1.0e-12
    null_direction = eigenvectors[:, 0]
    expected = torch.tensor([1.0, -1.0], dtype=DTYPE) / torch.sqrt(torch.tensor(2.0, dtype=DTYPE))
    assert torch.allclose(null_direction.abs(), expected.abs(), atol=1.0e-12)


def test_parameter_coordinate_scaling_transforms_curvature_covariantly() -> None:
    jw = torch.tensor([[1.0, 0.2], [0.0, 2.0], [1.0, -1.0]], dtype=DTYPE)
    jp = torch.tensor([[1.0, 0.5], [0.0, 1.5], [2.0, -0.25]], dtype=DTYPE)
    scale = torch.diag(torch.tensor([3.0, 0.2], dtype=DTYPE))
    gamma = 0.3
    physical = finite_gamma_reduced_curvature(jw, jp, gamma)
    coordinate = finite_gamma_reduced_curvature(jw, jp @ scale, gamma)
    assert torch.allclose(coordinate, scale.T @ physical @ scale, atol=1.0e-12, rtol=1.0e-12)


def test_heat_temperature_solution_and_k_over_C_confounding() -> None:
    x = torch.tensor([0.1, 0.3, 0.7, 0.9], dtype=DTYPE)
    t = torch.tensor([0.1, 0.2, 0.4, 0.8], dtype=DTYPE)
    k, C, amplitude = 2.0, 5.0, 1.7
    values = heat_temperature(x, t, k, C, amplitude)
    expected = amplitude * torch.sin(torch.pi * x) * torch.exp(-torch.pi**2 * (k / C) * t)
    assert torch.allclose(values, expected, atol=1.0e-14, rtol=1.0e-14)

    sensitivities = heat_temperature_sensitivities(x, t, k, C, amplitude)
    assert numerical_rank(sensitivities[:, :2]) == 1
    # dT/dC = -(k/C) dT/dk, so the identifiable direction is k/C.
    assert torch.allclose(sensitivities[:, 1], -(k / C) * sensitivities[:, 0], atol=1.0e-13)


def test_unknown_amplitude_is_confounded_at_one_time_but_resolved_at_two() -> None:
    x = torch.tensor([0.1, 0.3, 0.5, 0.8], dtype=DTYPE)
    k, C, amplitude = 2.0, 5.0, 1.7
    one_time = heat_temperature_sensitivities(x, torch.full_like(x, 0.2), k, C, amplitude)
    assert numerical_rank(one_time) == 1

    x_two = x.repeat(2)
    t_two = torch.cat((torch.full_like(x, 0.1), torch.full_like(x, 0.7)))
    two_times = heat_temperature_sensitivities(x_two, t_two, k, C, amplitude)
    assert numerical_rank(two_times) == 2


def test_counterexample_metadata_is_machine_readable() -> None:
    metadata = counterexample_metadata()
    assert metadata["state_parameter_compensation"]["zero_damping_rank"] == 0
    assert metadata["parameter_only_rank_deficiency"]["rank"] == 1
    assert metadata["heat_temperature_only_k_C"]["identifiable_combination"] == "k/C"
