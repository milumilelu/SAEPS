from __future__ import annotations

from pathlib import Path

import torch
import pytest

from saeps.config import load_config
from saeps.controlled import (
    fourier_library,
    make_diagnostic_points,
    network_state_and_derivatives,
    select_directions,
    select_nominal_gamma,
    spearman,
    truth_operator,
    truth_state,
)


ROOT = Path(__file__).resolve().parents[1]


def test_truth_operator_matches_autodiff() -> None:
    dtype = torch.float64
    x = torch.tensor([0.17, 0.43, 0.81], dtype=dtype, requires_grad=True)
    t = torch.tensor([0.13, 0.57, 0.76], dtype=dtype, requires_grad=True)
    state = truth_state(x, t)
    time_derivative = torch.autograd.grad(state.sum(), t, create_graph=True)[0]
    space_first = torch.autograd.grad(state.sum(), x, create_graph=True)[0]
    space_second = torch.autograd.grad(space_first.sum(), x)[0]
    actual = time_derivative - 0.05 * space_second + state
    assert torch.allclose(actual, truth_operator(x, t, 0.05, 1.0), atol=1.0e-12, rtol=1.0e-12)


def test_network_analytic_derivatives_match_autodiff() -> None:
    dtype = torch.float64
    width = 3
    theta = torch.linspace(-0.4, 0.6, 4 * width + 1, dtype=dtype)
    x = torch.tensor([0.2, 0.7], dtype=dtype, requires_grad=True)
    t = torch.tensor([0.3, 0.8], dtype=dtype, requires_grad=True)
    state, analytic_t, analytic_xx = network_state_and_derivatives(theta, x, t, width)
    auto_t = torch.autograd.grad(state.sum(), t, create_graph=True)[0]
    auto_x = torch.autograd.grad(state.sum(), x, create_graph=True)[0]
    auto_xx = torch.autograd.grad(auto_x.sum(), x)[0]
    assert torch.allclose(analytic_t, auto_t, atol=1.0e-13, rtol=1.0e-13)
    assert torch.allclose(analytic_xx, auto_xx, atol=1.0e-13, rtol=1.0e-13)


def test_direction_selection_is_deterministic_and_orthogonal() -> None:
    config = load_config(ROOT / "configs/p2_development.yaml")
    points = make_diagnostic_points(config)
    library = fourier_library(config, points)
    overlaps = {
        seed: {name: float(index) + 0.01 * seed for index, name in enumerate(sorted(library))}
        for seed in [0, 1, 2]
    }
    parallel, perpendicular, _, inner_product = select_directions(
        overlaps, library, float(config["fourier_library"]["orthogonality_tolerance"])
    )
    assert parallel == sorted(library)[-1]
    assert perpendicular != parallel
    assert abs(inner_product) <= float(config["fourier_library"]["orthogonality_tolerance"])


def test_spearman_handles_monotone_and_ties() -> None:
    assert spearman(
        [0.0, 0.25, 0.5, 0.75, 1.0], [1.0, 2.0, 3.0, 4.0, 5.0]
    ) == pytest.approx(1.0, abs=1.0e-15)
    tied = spearman([0.0, 0.25, 0.5, 0.75, 1.0], [1.0, 1.0, 2.0, 3.0, 3.0])
    assert 0.9 < tied < 1.0


def test_gamma_selector_separates_explicit_plateau_from_cg_eligibility() -> None:
    config = load_config(ROOT / "configs/p2_development.yaml")
    config["gamma"]["alpha_grid"] = [1.0e-12, 1.0e-10, 1.0e-8]
    sweeps = {}
    for seed in [0, 1, 2]:
        sweeps[seed] = []
        for index, gamma_alpha in enumerate(config["gamma"]["alpha_grid"]):
            rows = []
            for eta in [0.1, 0.3, 0.6]:
                rows.append(
                    {
                        "explicit_eta": eta * (1.0 + 0.01 * index),
                        "cg_converged": index > 0,
                        "cg_relative_residual": 1.0e-12 if index > 0 else 1.0e-3,
                        "explicit_mf_relative_error": 1.0e-12 if index > 0 else 1.0e-2,
                    }
                )
            sweeps[seed].append({"gamma_alpha": gamma_alpha, "values": rows})
    selected, evidence = select_nominal_gamma(sweeps, config)
    assert selected == 1.0e-10
    assert evidence["eligible"] == [False, True, True]
