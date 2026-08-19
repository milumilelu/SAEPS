from __future__ import annotations

import torch

from saeps.v32.pipeline import run_accuracy_profile


def _residual(theta: torch.Tensor, parameter: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [
            theta[0] + parameter[0],
            2.0 * theta[0] - parameter[0],
            theta[0] - 0.5 * parameter[0],
        ]
    )


def _local_specification() -> dict[str, object]:
    optimizer = {
        "adam_warmup_epochs": 0,
        "adam_learning_rate": 1.0e-3,
        "outer_steps_max": 5,
        "inner_iterations": 30,
        "history_size": 10,
        "line_search": "strong_wolfe",
        "tolerance_grad": 1.0e-13,
        "tolerance_change": 1.0e-15,
    }
    return {
        "normalized_gradient_tolerance": 1.0e-10,
        "hessian_absolute_tolerance": 1.0e-12,
        "hessian_relative_tolerance": 1.0e-12,
        "maximum_escape_cycles": 3,
        "negative_probe_relative_radii": [0.01, 0.1],
        "trust_initial_relative_radius": 0.1,
        "trust_minimum_relative_radius": 1.0e-8,
        "trust_maximum_relative_radius": 1.0,
        "trust_backtracking_factors": [1.0, 0.5],
        "minimum_actual_decrease": 1.0e-14,
        "optimizer": optimizer,
        "polish_optimizer": optimizer,
        "stopping": {
            "minimum_outer_steps": 2,
            "plateau_window": 2,
            "relative_loss_change": 1.0e-12,
            "normalized_gradient": 1.0e-10,
        },
    }


def test_gamma_profile_uses_independent_center_outward_branches_and_accuracy_gate() -> None:
    result = run_accuracy_profile(
        _residual,
        torch.tensor([0.0], dtype=torch.float64),
        torch.tensor([0.0], dtype=torch.float64),
        0.2,
        _local_specification(),
        {
            "h_values": [0.05, 0.025, 0.0125, 0.00625],
            "accuracy_levels": {"nominal": 1.0e-8, "strict": 1.0e-10},
            "convergence": {
                "adjacent_pairs_required": 2,
                "relative_tolerance": 1.0e-7,
                "denominator_absolute_floor": 1.0e-10,
            },
            "accuracy_convergence": {
                "finest_scales_required": 2,
                "relative_tolerance": 1.0e-7,
                "denominator_absolute_floor": 1.0e-10,
            },
        },
        matched=True,
    )
    assert result["status"] == "PASS"
    assert result["optimization_accuracy_gate"] == "PASS"
    strict = result["accuracy_levels"]["strict"]
    assert strict["passed_points"] == 8
    positive = strict["branches"]["positive"]
    negative = strict["branches"]["negative"]
    assert [point["offset"] for point in positive] == [0.00625, 0.0125, 0.025, 0.05]
    assert [point["parent_offset"] for point in positive] == [0.0, 0.00625, 0.0125, 0.025]
    assert [point["offset"] for point in negative] == [-0.00625, -0.0125, -0.025, -0.05]
    assert [point["parent_offset"] for point in negative] == [0.0, -0.00625, -0.0125, -0.025]
