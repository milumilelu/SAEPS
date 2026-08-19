from __future__ import annotations

import torch

from saeps.autodiff import ResidualLinearization
from saeps.v3.foundation import (
    full_hessian_references,
    gauss_newton_references,
    refine_common_base,
    run_multiscale_profile,
)
from saeps.v3.validation import _hash_matches_with_portable_newlines


DTYPE = torch.float64


def _linear_residual(theta: torch.Tensor, parameter: torch.Tensor) -> torch.Tensor:
    return torch.stack(
        [
            theta[0] + parameter[0],
            2.0 * theta[0] - parameter[0],
            theta[0] - 0.5 * parameter[0],
        ]
    )


def _optimizer_specification() -> dict[str, object]:
    return {
        "h_values": [0.05, 0.025, 0.0125, 0.00625],
        "optimizer": {
            "adam_warmup_epochs": 0,
            "outer_steps_max": 6,
            "inner_iterations": 25,
            "history_size": 10,
            "line_search": "strong_wolfe",
            "tolerance_grad": 1.0e-13,
            "tolerance_change": 1.0e-15,
        },
        "stopping": {
            "minimum_outer_steps": 2,
            "plateau_window": 2,
            "relative_loss_change": 1.0e-12,
            "normalized_gradient": 1.0e-10,
        },
        "convergence": {
            "adjacent_pairs_required": 2,
            "relative_tolerance": 1.0e-8,
            "denominator_absolute_floor": 1.0e-10,
        },
    }


def test_common_base_refinement_uses_actual_objective() -> None:
    specification = _optimizer_specification()
    refined, record = refine_common_base(
        _linear_residual,
        torch.tensor([1.0], dtype=DTYPE),
        torch.tensor([0.0], dtype=DTYPE),
        {
            "optimizer": specification["optimizer"],
            "stopping": specification["stopping"],
        },
    )
    assert record["status"] == "PASS"
    assert refined is not None
    assert abs(float(refined[0])) <= 1.0e-10
    assert record["delta_loss_relative"] > 0.999999


def test_dual_multiscale_profiles_match_exact_linear_reductions() -> None:
    theta = torch.tensor([0.0], dtype=DTYPE)
    parameter = torch.tensor([0.0], dtype=DTYPE)
    gamma = 0.2
    specification = _optimizer_specification()
    unregularized = run_multiscale_profile(
        _linear_residual, theta, parameter, gamma, specification, matched=False
    )
    matched = run_multiscale_profile(
        _linear_residual, theta, parameter, gamma, specification, matched=True
    )
    expected_unregularized = 2.25 - 2.25 / 6.0
    expected_matched = 2.25 - 2.25 / (6.0 + gamma)
    assert unregularized["status"] == "PASS"
    assert matched["status"] == "PASS"
    assert abs(unregularized["finest_curvature"] - expected_unregularized) <= 1.0e-10
    assert abs(matched["finest_curvature"] - expected_matched) <= 1.0e-10
    assert matched["objective_scaling"] == (
        "0.5*mean(r^2) + gamma/(2*m)*||theta-theta_base||^2"
    )


def test_full_hessian_and_gauss_newton_agree_for_linear_residual() -> None:
    theta = torch.tensor([0.0], dtype=DTYPE)
    parameter = torch.tensor([0.0], dtype=DTYPE)
    gamma = 0.2
    hessian = full_hessian_references(
        _linear_residual,
        theta,
        parameter,
        gamma,
        {
            "symmetry_relative_tolerance": 1.0e-12,
            "positive_eigenvalue_relative_tolerance": 1.0e-12,
            "solve_relative_tolerance": 1.0e-12,
        },
    )
    gauss_newton = gauss_newton_references(
        ResidualLinearization(_linear_residual, theta, parameter),
        gamma,
        1.0e-12,
        10,
    )
    assert hessian["status"] == "PASS"
    assert hessian["unregularized"]["status"] == "PASS"
    assert hessian["gamma_matched"]["status"] == "PASS"
    assert gauss_newton["status"] == "PASS"
    assert torch.allclose(
        torch.tensor(hessian["gamma_matched"]["reduced_hessian"]),
        torch.tensor(gauss_newton["Fse_explicit"]),
        atol=1.0e-12,
        rtol=0.0,
    )


def test_manifest_hash_accepts_only_newline_equivalent_bytes(tmp_path) -> None:
    import hashlib

    path = tmp_path / "record.json"
    path.write_bytes(b'{\r\n  "status": "PASS"\r\n}\r\n')
    expected_lf = hashlib.sha256(b'{\n  "status": "PASS"\n}\n').hexdigest()
    assert _hash_matches_with_portable_newlines(path, expected_lf)
    path.write_bytes(b'{\r\n  "status": "FAILED"\r\n}\r\n')
    assert not _hash_matches_with_portable_newlines(path, expected_lf)
