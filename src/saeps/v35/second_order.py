"""Residual-Hessian block and Shapley decomposition of reduced curvature."""

from __future__ import annotations

import itertools
import math
from typing import Any, Callable

import torch


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
BLOCKS = ("S_theta_theta", "S_theta_lambda", "S_lambda_lambda")


def _relative(left: float, right: float, floor: float) -> float:
    return abs(left - right) / max(abs(right), floor)


def second_order_reduced_decomposition(
    residual_function: ResidualFunction,
    theta: torch.Tensor,
    parameter: torch.Tensor,
    gamma: float,
    denominator_floor: float,
) -> dict[str, Any]:
    theta_size = theta.numel()
    joint = torch.cat([theta, parameter]).detach()

    def residual_joint(current: torch.Tensor) -> torch.Tensor:
        return residual_function(
            current[:theta_size], current[theta_size:]
        ).reshape(-1)

    def loss_joint(current: torch.Tensor) -> torch.Tensor:
        residual = residual_joint(current)
        return 0.5 * torch.sum(residual.square())

    jacobian = torch.func.jacrev(residual_joint)(joint)
    hessian = torch.func.hessian(loss_joint)(joint)
    gauss_newton = jacobian.T @ jacobian
    residual_second = 0.5 * ((hessian - gauss_newton) + (hessian - gauss_newton).T)
    g_tt = gauss_newton[:theta_size, :theta_size]
    g_tl = gauss_newton[:theta_size, theta_size:]
    g_ll = gauss_newton[theta_size:, theta_size:]
    s_tt = residual_second[:theta_size, :theta_size]
    s_tl = residual_second[:theta_size, theta_size:]
    s_ll = residual_second[theta_size:, theta_size:]
    identity = torch.eye(theta_size, dtype=theta.dtype, device=theta.device)
    base_state = g_tt + gamma * identity

    def reduce(included: frozenset[str]) -> float:
        state = base_state + (s_tt if "S_theta_theta" in included else 0.0)
        cross = g_tl + (s_tl if "S_theta_lambda" in included else 0.0)
        physical = g_ll + (s_ll if "S_lambda_lambda" in included else 0.0)
        value = physical - cross.T @ torch.linalg.solve(state, cross)
        return float(value[0, 0].item())

    subset_values: dict[frozenset[str], float] = {}
    for size in range(4):
        for subset in itertools.combinations(BLOCKS, size):
            subset_values[frozenset(subset)] = reduce(frozenset(subset))
    shapley: dict[str, float] = {}
    factorial = math.factorial
    for block in BLOCKS:
        contribution = 0.0
        others = [value for value in BLOCKS if value != block]
        for size in range(3):
            for subset_tuple in itertools.combinations(others, size):
                subset = frozenset(subset_tuple)
                weight = factorial(size) * factorial(2 - size) / factorial(3)
                contribution += weight * (
                    subset_values[subset | {block}] - subset_values[subset]
                )
        shapley[block] = contribution

    gn_reduced = subset_values[frozenset()]
    exact_reduced = subset_values[frozenset(BLOCKS)]
    exact_difference = exact_reduced - gn_reduced
    shapley_sum = sum(shapley.values())
    shapley_error = abs(shapley_sum - exact_difference) / max(
        abs(exact_difference), denominator_floor
    )
    state_solution = torch.linalg.solve(base_state, g_tl)
    first_order = float(
        (
            s_ll
            - 2.0 * state_solution.T @ s_tl
            + state_solution.T @ s_tt @ state_solution
        )[0, 0].item()
    )
    ratios = {
        "S_theta_theta_spectral_ratio": float(
            torch.linalg.matrix_norm(s_tt, ord=2).item()
        )
        / max(float(torch.linalg.matrix_norm(base_state, ord=2).item()), denominator_floor),
        "S_theta_lambda_frobenius_ratio": float(torch.linalg.matrix_norm(s_tl).item())
        / max(float(torch.linalg.matrix_norm(g_tl).item()), denominator_floor),
        "S_lambda_lambda_scalar_ratio": abs(float(s_ll[0, 0].item()))
        / max(abs(float(g_ll[0, 0].item())), denominator_floor),
    }
    ratios["maximum_block_ratio"] = max(ratios.values())
    ratios["first_order_correction_relative_to_GN"] = abs(first_order) / max(
        abs(gn_reduced), denominator_floor
    )
    ratios["absolute_shapley_sum_relative_to_GN"] = sum(
        abs(value) for value in shapley.values()
    ) / max(abs(gn_reduced), denominator_floor)
    raw = float(g_ll[0, 0].item())
    e_saeps = _relative(gn_reduced, exact_reduced, denominator_floor)
    e_raw = _relative(raw, exact_reduced, denominator_floor)
    subset_rows = {
        "+".join(sorted(subset)) if subset else "GN_NONE": value
        for subset, value in subset_values.items()
    }
    return {
        "Fraw": raw,
        "Fse_GN": gn_reduced,
        "Hred_exact_gamma": exact_reduced,
        "GN_to_exact_relative_error": e_saeps,
        "block_norms": {
            "GN_theta_theta_spectral": float(
                torch.linalg.matrix_norm(base_state, ord=2).item()
            ),
            "GN_theta_lambda_frobenius": float(torch.linalg.matrix_norm(g_tl).item()),
            "GN_lambda_lambda_scalar": float(g_ll[0, 0].item()),
            "S_theta_theta_spectral": float(torch.linalg.matrix_norm(s_tt, ord=2).item()),
            "S_theta_lambda_frobenius": float(torch.linalg.matrix_norm(s_tl).item()),
            "S_lambda_lambda_scalar": float(s_ll[0, 0].item()),
        },
        "block_ratios_and_indicators": ratios,
        "subset_reduced_curvatures": subset_rows,
        "shapley_contributions": shapley,
        "shapley_sum": shapley_sum,
        "exact_minus_GN": exact_difference,
        "shapley_reproduction_relative_error": shapley_error,
        "first_order_reduced_correction": first_order,
        "comparative_estimand": {
            "E_SAEPS": e_saeps,
            "E_raw": e_raw,
            "D_raw_minus_SAEPS": e_raw - e_saeps,
        },
    }

