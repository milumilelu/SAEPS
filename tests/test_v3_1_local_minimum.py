from __future__ import annotations

import torch

from saeps.v31.local_minimum import (
    exact_state_diagnostics,
    optimize_state_local_minimum,
)


def _specification() -> dict[str, object]:
    return {
        "normalized_gradient_tolerance": 1.0e-8,
        "hessian_absolute_tolerance": 1.0e-10,
        "hessian_relative_tolerance": 1.0e-12,
        "maximum_escape_cycles": 5,
        "negative_probe_relative_radii": [0.01, 0.03, 0.1, 0.3, 1.0],
        "trust_initial_relative_radius": 0.3,
        "trust_minimum_relative_radius": 1.0e-8,
        "trust_maximum_relative_radius": 1.0,
        "trust_backtracking_factors": [1.0, 0.5, 0.25],
        "minimum_actual_decrease": 1.0e-14,
        "optimizer": {
            "adam_warmup_epochs": 0,
            "adam_learning_rate": 1.0e-3,
            "outer_steps_max": 4,
            "inner_iterations": 30,
            "history_size": 10,
            "line_search": "strong_wolfe",
            "tolerance_grad": 1.0e-13,
            "tolerance_change": 1.0e-15,
        },
        "polish_optimizer": {
            "adam_warmup_epochs": 0,
            "adam_learning_rate": 1.0e-3,
            "outer_steps_max": 4,
            "inner_iterations": 30,
            "history_size": 10,
            "line_search": "strong_wolfe",
            "tolerance_grad": 1.0e-13,
            "tolerance_change": 1.0e-15,
        },
        "stopping": {
            "minimum_outer_steps": 2,
            "plateau_window": 2,
            "relative_loss_change": 1.0e-12,
            "normalized_gradient": 1.0e-8,
        },
    }


def test_exact_gate_rejects_stationary_saddle_and_records_negative_curvature() -> None:
    objective = lambda theta: (theta[0].square() - 1.0).square() + theta[1].square()
    diagnostics, _, _, _ = exact_state_diagnostics(
        objective, torch.zeros(2, dtype=torch.float64), _specification()
    )
    assert diagnostics["gradient_pass"]
    assert not diagnostics["hessian_pass"]
    assert diagnostics["minimum_state_eigenvalue_mean_objective"] == -4.0


def test_exact_hessian_escape_reaches_actual_local_minimum() -> None:
    objective = lambda theta: (theta[0].square() - 1.0).square() + theta[1].square()
    state, result = optimize_state_local_minimum(
        objective, torch.zeros(2, dtype=torch.float64), _specification()
    )
    assert result["status"] == "PASS"
    assert state is not None
    assert abs(abs(float(state[0])) - 1.0) <= 1.0e-7
    assert abs(float(state[1])) <= 1.0e-7
    assert result["negative_direction_probes"]
    assert result["negative_direction_probes"][0]["descent_found"]
    assert result["final"]["local_minimum_gate"] == "PASS"
