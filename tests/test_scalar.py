from __future__ import annotations

import torch

from saeps.p4_screening import _select_candidate
from saeps.scalar import scalar_network


def test_scalar_network_analytic_derivatives_match_autodiff() -> None:
    width = 4
    theta = torch.linspace(-0.5, 0.7, 4 * width + 1, dtype=torch.float64)
    x = torch.tensor([0.2, 0.6], dtype=torch.float64, requires_grad=True)
    t = torch.tensor([0.1, 0.3], dtype=torch.float64, requires_grad=True)
    state, analytic_t, analytic_x, analytic_xx = scalar_network(theta, x, t, width)
    auto_t = torch.autograd.grad(state.sum(), t, create_graph=True)[0]
    auto_x = torch.autograd.grad(state.sum(), x, create_graph=True)[0]
    auto_xx = torch.autograd.grad(auto_x.sum(), x)[0]
    assert torch.allclose(analytic_t, auto_t, atol=1.0e-13, rtol=1.0e-13)
    assert torch.allclose(analytic_x, auto_x, atol=1.0e-13, rtol=1.0e-13)
    assert torch.allclose(analytic_xx, auto_xx, atol=1.0e-13, rtol=1.0e-13)


def test_candidate_selection_uses_preregistered_order() -> None:
    summaries = {
        "Allen-Cahn": {
            "hard_gate_pass": True,
            "stationarity_passing_count": 3,
            "classical_clarity": 0.995,
            "profile_failure_fraction": 0.0,
        },
        "Burgers": {
            "hard_gate_pass": True,
            "stationarity_passing_count": 3,
            "classical_clarity": 0.999,
            "profile_failure_fraction": 0.0,
        },
    }
    selected, audit = _select_candidate(summaries)
    assert selected == "Burgers"
    assert [row["criterion"] for row in audit] == [
        "hard_numerical_gates",
        "stationarity_passing_count",
        "classical_curvature_clarity",
        "reoptimization_failure_rate",
        "alphabetical_name",
    ]

