import torch

from saeps.v43.center import exact_gauss_newton_refine, multidirection_saddle_escape


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


def test_multidirection_escape_retains_failed_candidate_and_finds_descent() -> None:
    theta = torch.tensor([0.05, 0.05], dtype=torch.float64)

    def objective(state: torch.Tensor) -> torch.Tensor:
        return (state[0] ** 2 - 1.0) ** 2 + 0.5 * (state[1] ** 2 - 0.25) ** 2

    local = {
        "normalized_gradient_tolerance": 1.0e-6,
        "hessian_absolute_tolerance": 1.0e-10,
        "hessian_relative_tolerance": 1.0e-10,
        "optimizer": {
            "adam_warmup_epochs": 0,
            "adam_learning_rate": 1.0e-3,
            "outer_steps_max": 8,
            "inner_iterations": 50,
            "history_size": 20,
            "line_search": "strong_wolfe",
            "tolerance_grad": 1.0e-12,
            "tolerance_change": 1.0e-14,
        },
        "polish_optimizer": {
            "adam_warmup_epochs": 0,
            "adam_learning_rate": 1.0e-3,
            "outer_steps_max": 8,
            "inner_iterations": 50,
            "history_size": 20,
            "line_search": "strong_wolfe",
            "tolerance_grad": 1.0e-12,
            "tolerance_change": 1.0e-14,
        },
        "stopping": {
            "minimum_outer_steps": 1,
            "plateau_window": 2,
            "relative_loss_change": 1.0e-6,
            "normalized_gradient": 1.0e-6,
        },
    }
    state, audit = multidirection_saddle_escape(
        objective,
        theta,
        local,
        {
            "maximum_cycles": 8,
            "maximum_negative_directions": 2,
            "relative_radii": [0.1, 0.3, 1.0],
            "minimum_actual_decrease": 1.0e-12,
        },
    )
    assert objective(state) < objective(theta)
    assert audit["status"] == "PASS"
