import torch

from saeps.v43.center import exact_gauss_newton_refine


def test_exact_gauss_newton_refine_reduces_real_nonlinear_least_squares() -> None:
    theta = torch.tensor([2.0, -1.0], dtype=torch.float64)

    def residual(state: torch.Tensor) -> torch.Tensor:
        return torch.stack([state[0] ** 2 - 1.0, state[1] - 0.5, state[0] + state[1] - 1.5])

    initial = float((0.5 * torch.mean(residual(theta).square())).item())
    refined, audit = exact_gauss_newton_refine(
        residual,
        theta,
        {
            "maximum_iterations": 30,
            "initial_damping": 1.0e-4,
            "minimum_damping": 1.0e-12,
            "maximum_damping": 1.0e4,
            "accepted_damping_factor": 0.3,
            "rejected_damping_factor": 10.0,
            "maximum_relative_step": 0.5,
            "backtracking_factors": [1.0, 0.5, 0.25, 0.125],
            "normalized_gradient_tolerance": 1.0e-10,
        },
    )
    final = float((0.5 * torch.mean(residual(refined).square())).item())
    assert final < initial * 1.0e-8
    assert audit["accepted_steps"] > 0
