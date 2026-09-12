"""Permanent, checkpoint-independent identifiability regression tests."""

from __future__ import annotations

import torch

from saeps.identifiability import (
    add_observation_noise,
    benchmark_observation_jacobian,
    benchmark_rank,
    counterexample_metadata,
    exact_zero_damping_curvature,
    finite_gamma_reduced_curvature,
    heat_flux,
    heat_flux_sensitivities,
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


def test_state_coordinate_rescaling_changes_fixed_anchor_metric() -> None:
    jp = torch.ones((1, 1), dtype=DTYPE)
    gamma = 0.01
    values = []
    for scale in (0.1, 1.0, 10.0):
        jw = torch.tensor([[scale]], dtype=DTYPE)
        fixed = finite_gamma_reduced_curvature(jw, jp, gamma)
        covariant = finite_gamma_reduced_curvature(jw, jp, gamma * scale**2)
        values.append(float(fixed.item()))
        assert torch.allclose(covariant, torch.tensor([[gamma / (1.0 + gamma)]], dtype=DTYPE), atol=1.0e-12)
    assert values[0] > values[1] > values[2]


def test_finite_damping_kernel_matches_physical_sensitivity_rank() -> None:
    generator = torch.Generator().manual_seed(20260912)
    jw = torch.randn((7, 3), dtype=DTYPE, generator=generator)
    coefficient = torch.randn((3, 2), dtype=DTYPE, generator=generator)
    jp = jw @ coefficient
    assert torch.linalg.norm(exact_zero_damping_curvature(jw, jp)) < 1.0e-10
    for gamma in (0.01, 1.0, 10.0):
        reduced = finite_gamma_reduced_curvature(jw, jp, gamma)
        eig = torch.linalg.eigvalsh(reduced)
        assert numerical_rank(reduced) == 2
        assert torch.min(eig).item() > 0.0


def test_normalized_collocation_duplication_preserves_curvature() -> None:
    generator = torch.Generator().manual_seed(7)
    jw = torch.randn((5, 2), dtype=DTYPE, generator=generator)
    jp = torch.randn((5, 2), dtype=DTYPE, generator=generator)
    baseline = finite_gamma_reduced_curvature(jw, jp, 0.1)
    duplicated = finite_gamma_reduced_curvature(
        torch.cat((jw, jw)) / torch.sqrt(torch.tensor(2.0, dtype=DTYPE)),
        torch.cat((jp, jp)) / torch.sqrt(torch.tensor(2.0, dtype=DTYPE)),
        0.1,
    )
    assert torch.allclose(duplicated, baseline, atol=1.0e-12, rtol=1.0e-12)


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


def test_heat_flux_observations_resolve_k_C_confounding() -> None:
    x, t = torch.meshgrid(
        torch.tensor([0.2, 0.4, 0.7], dtype=DTYPE),
        torch.tensor([0.02, 0.2, 0.5], dtype=DTYPE),
        indexing="xy",
    )
    x, t = x.reshape(-1), t.reshape(-1)
    k, C = 0.6, 1.2
    temperature_jacobian = heat_temperature_sensitivities(x, t, k, C)[:, :2] / 0.01
    flux_jacobian = heat_flux_sensitivities(x, t, k, C) / 0.05
    assert numerical_rank(temperature_jacobian) == 1
    assert numerical_rank(torch.cat((temperature_jacobian, flux_jacobian))) == 2
    # Validate the physical-coordinate flux derivative independently by centered
    # finite differences (the columns above are physical k,C derivatives).
    h = 1.0e-6
    finite_columns = []
    for index in range(2):
        params_plus = [k, C]
        params_minus = [k, C]
        params_plus[index] += h
        params_minus[index] -= h
        finite_columns.append(
            (heat_flux(x, t, *params_plus) - heat_flux(x, t, *params_minus)) / (2.0 * h) / 0.05
        )
    assert torch.allclose(torch.stack(finite_columns, dim=1), flux_jacobian, rtol=1.0e-7, atol=1.0e-7)


def test_unknown_amplitude_is_confounded_at_one_time_but_resolved_at_two() -> None:
    x = torch.tensor([0.1, 0.3, 0.5, 0.8], dtype=DTYPE)
    k, C, amplitude = 2.0, 5.0, 1.7
    one_time = heat_temperature_sensitivities(x, torch.full_like(x, 0.2), k, C, amplitude)
    assert numerical_rank(one_time) == 1

    x_two = x.repeat(2)
    t_two = torch.cat((torch.full_like(x, 0.1), torch.full_like(x, 0.7)))
    two_times = heat_temperature_sensitivities(x_two, t_two, k, C, amplitude)
    assert numerical_rank(two_times) == 2


def test_benchmark_observation_jacobians_match_expected_ranks() -> None:
    x = torch.tensor([0.2, 0.4, 0.7], dtype=DTYPE)
    full_times = torch.cat((torch.full_like(x, 0.02), torch.full_like(x, 0.5)))
    full_x = x.repeat(2)
    expected = {"B1": 1, "B2": 1, "B3": 1, "B4": 1, "B5": 2, "B6": 2}
    designs = {
        "B1": (x, torch.full_like(x, 0.2)),
        "B2": (x[:2], torch.full_like(x[:2], 1.0e-4)),
        "B3": (full_x, full_times),
        "B4": (x, torch.full_like(x, 0.2)),
        "B5": (full_x, full_times),
        "B6": (full_x, full_times),
    }
    for benchmark, rank in expected.items():
        actual = benchmark_rank(benchmark, *designs[benchmark])
        assert actual == rank
        assert benchmark_observation_jacobian(benchmark, *designs[benchmark]).ndim == 2


def test_observation_noise_generator_is_seeded_and_preserves_shape() -> None:
    values = torch.zeros(8, dtype=DTYPE)
    first = add_observation_noise(values, sigma=0.1, seed=10)
    repeat = add_observation_noise(values, sigma=0.1, seed=10)
    other = add_observation_noise(values, sigma=0.1, seed=11)
    assert first.shape == values.shape
    assert torch.equal(first, repeat)
    assert not torch.equal(first, other)


def test_counterexample_metadata_is_machine_readable() -> None:
    metadata = counterexample_metadata()
    assert metadata["state_parameter_compensation"]["zero_damping_rank"] == 0
    assert metadata["parameter_only_rank_deficiency"]["rank"] == 1
    assert metadata["heat_temperature_only_k_C"]["identifiable_combination"] == "k/C"


def test_local_curvature_does_not_rule_out_global_aliases() -> None:
    values = torch.tensor([2.0, -2.0], dtype=DTYPE)
    assert torch.equal(values.square(), torch.tensor([4.0, 4.0], dtype=DTYPE))
    local_gn = (2.0 * values).square()
    assert torch.all(local_gn > 0)
