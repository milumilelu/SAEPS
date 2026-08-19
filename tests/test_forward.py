from __future__ import annotations

import torch

from saeps.forward import interpolate_solution, solve_periodic_scalar


def test_forward_solvers_are_finite_and_deterministic() -> None:
    for benchmark, parameter in [("Burgers", 0.05), ("Allen-Cahn", 2.0)]:
        first = solve_periodic_scalar(benchmark, parameter, spatial_points=32, time_steps=200)
        second = solve_periodic_scalar(benchmark, parameter, spatial_points=32, time_steps=200)
        assert torch.all(torch.isfinite(first.values))
        assert torch.equal(first.values, second.values)


def test_periodic_interpolation_matches_saved_nodes() -> None:
    solution = solve_periodic_scalar("Burgers", 0.05, spatial_points=32, time_steps=200)
    indices = torch.tensor([0, 7, 31], dtype=torch.long)
    times = torch.tensor([0, 50, 200], dtype=torch.long)
    x = indices.to(torch.float64) / 32.0
    t = times.to(torch.float64) / 200.0 * 0.4
    actual = interpolate_solution(solution, x, t)
    assert torch.equal(actual, solution.values[times, indices])

