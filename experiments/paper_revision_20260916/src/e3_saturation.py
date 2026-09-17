"""E3: inverse saturation coefficient in a manufactured reaction-diffusion problem.

    u_t = D u_xx + rho * u / (1 + kappa u) + f(x, t)

D and rho are known, kappa is inverted, and the source f is frozen at the true kappa.
Unlike the benchmarks used elsewhere in this repository the physical coefficient enters
non-affinely, so the E1 parameter-block identity does not apply and the truncation the
curvature comparison relies on changes character.  The non-affine remainder is measured
directly from the fixed-state residual:

    H_ll - G_ll - g_l = kappa^2 * sum_i rbar_i * d2 rbar_i / dkappa2

with, at fixed state, d r / dkappa = rho u^2 / (1 + kappa u)^2 and
d2 r / dkappa2 = -2 rho u^3 / (1 + kappa u)^3.  Both sides are exported, so the term that
comes purely from the log coordinate can be separated from the genuinely non-affine term.

Objective convention: the sum objective 1/2 sum rbar_i^2 everywhere, so loss, gradient and
damping share one scale by construction.

Modes:
    --verify      analytic source, derivatives and the non-affine identity
    --develop     the 8 development fits listed in protocol.yaml
    --heldout     the 24 held-out fits (requires a frozen snapshot)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

OUTPUT_SHIFT = 0.05
EPS = 1.0e-30
NOISE_STREAM_OFFSET = 9_000_000


@dataclass(frozen=True)
class Points:
    pde_x: torch.Tensor
    pde_t: torch.Tensor
    data_x: torch.Tensor
    data_t: torch.Tensor
    initial_x: torch.Tensor
    boundary_t: torch.Tensor


def truth(x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    return (
        1.0
        + 0.2 * torch.exp(-t) * torch.cos(2.0 * math.pi * x)
        + 0.1 * torch.exp(-2.0 * t) * torch.sin(4.0 * math.pi * x)
    )


def truth_derivatives(x: torch.Tensor, t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    u_t = (
        -0.2 * torch.exp(-t) * torch.cos(2.0 * math.pi * x)
        - 0.2 * torch.exp(-2.0 * t) * torch.sin(4.0 * math.pi * x)
    )
    u_xx = (
        -0.2 * (2.0 * math.pi) ** 2 * torch.exp(-t) * torch.cos(2.0 * math.pi * x)
        - 0.1 * (4.0 * math.pi) ** 2 * torch.exp(-2.0 * t) * torch.sin(4.0 * math.pi * x)
    )
    return u_t, u_xx


def source(
    x: torch.Tensor,
    t: torch.Tensor,
    diffusion: float,
    rho: float,
    kappa: float,
) -> torch.Tensor:
    """Manufactured source frozen at the true kappa; never re-derived per iterate."""
    u = truth(x, t)
    u_t, u_xx = truth_derivatives(x, t)
    return u_t - diffusion * u_xx - rho * u / (1.0 + kappa * u)


def make_points(config: dict[str, Any], seed: int) -> Points:
    counts = config["points"]
    final_time = float(config["domain_t"][1])
    generator = torch.Generator(device="cpu").manual_seed(seed)

    def uniform(count: int) -> torch.Tensor:
        return torch.rand(count, dtype=torch.float64, generator=generator)

    return Points(
        uniform(int(counts["pde"])),
        final_time * uniform(int(counts["pde"])),
        uniform(int(counts["data"])),
        final_time * uniform(int(counts["data"])),
        uniform(int(counts["initial"])),
        final_time * uniform(int(counts["boundary_times"])),
    )


def observation_noise(points: Points, level: float, stream_seed: int) -> torch.Tensor:
    """Additive noise on observations only.

    The standard-normal draw depends on ``stream_seed`` alone, so the 0.0 and 0.02 levels
    form a paired experiment on identical draws and identical spatial points.
    """
    if level == 0.0:
        return torch.zeros_like(points.data_x)
    base = truth(points.data_x, points.data_t)
    generator = torch.Generator(device="cpu").manual_seed(stream_seed)
    z = torch.randn(base.shape, dtype=base.dtype, generator=generator)
    return level * float(base.std(unbiased=False).item()) * z


def raw_output(theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int) -> torch.Tensor:
    expected = 4 * width + 1
    if theta.numel() != expected:
        raise ValueError(f"theta must have {expected} elements")
    wx = theta[:width]
    wt = theta[width : 2 * width]
    bias = theta[2 * width : 3 * width]
    out = theta[3 * width : 4 * width]
    return torch.tanh(x[:, None] * wx + t[:, None] * wt + bias) @ out + theta[-1]


def field(theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int) -> torch.Tensor:
    """Positive output transform, so 1 + kappa*u stays away from zero."""
    return F.softplus(raw_output(theta, x, t, width)) + OUTPUT_SHIFT


def evaluate(
    theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int, second: bool = True
):
    """u, u_t, u_x, u_xx, differentiated analytically through the output transform.

    Hand-derived rather than autograd so the residual stays usable inside
    ``torch.func`` transforms, which reject ``requires_grad_()``.  The preflight check
    compares every branch against autograd before any training is trusted.

    With s = sigmoid(v), the chain rule through u = softplus(v) + 0.05 gives
        u_x  = s * v_x
        u_xx = s (1 - s) v_x^2 + s * v_xx
    """
    wx = theta[:width]
    wt = theta[width : 2 * width]
    bias = theta[2 * width : 3 * width]
    out = theta[3 * width : 4 * width]
    out_bias = theta[-1]

    activation = torch.tanh(x[:, None] * wx + t[:, None] * wt + bias)
    first = 1.0 - activation.square()
    v = activation @ out + out_bias
    s = torch.sigmoid(v)
    u = F.softplus(v) + OUTPUT_SHIFT

    v_x = (first * wx * out).sum(dim=1)
    v_t = (first * wt * out).sum(dim=1)
    u_x = s * v_x
    u_t = s * v_t
    if not second:
        return u, u_t, u_x, None
    v_xx = (-2.0 * activation * first * wx.square() * out).sum(dim=1)
    u_xx = s * (1.0 - s) * v_x.square() + s * v_xx
    return u, u_t, u_x, u_xx


def evaluate_autograd(theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int):
    """Independent autograd evaluation of the same branches, for the preflight check."""
    x = x.detach().clone().requires_grad_(True)
    t = t.detach().clone().requires_grad_(True)
    u = field(theta, x, t, width)
    u_x, u_t = torch.autograd.grad(u.sum(), [x, t], create_graph=True)
    u_xx = torch.autograd.grad(u_x.sum(), x, create_graph=True)[0]
    return u.detach(), u_t.detach(), u_x.detach(), u_xx.detach()


def prepare(config: dict[str, Any], data_seed: int, noise_level: float) -> dict[str, Any]:
    """Build the per-fit local config with points and noisy observations fixed up front.

    Sampling and the noise draw must happen exactly once, outside any differentiation.
    Redrawing inside the residual would both break the paired 0.0/0.02 design and put a
    random op inside ``torch.func`` transforms, which reject it.
    """
    local = dict(config)
    local["noise_level"] = float(noise_level)
    local["_data_seed"] = int(data_seed)
    points = make_points(config, data_seed)
    observed = truth(points.data_x, points.data_t) + observation_noise(
        points, float(noise_level), int(data_seed) + NOISE_STREAM_OFFSET
    )
    local["_points"] = points
    local["_observed_data"] = observed
    return local


def unweighted_blocks(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
) -> dict[str, torch.Tensor]:
    width = int(config["architecture"][1])
    diffusion = float(config["diffusion"])
    rho = float(config["rho_known"])
    kappa = torch.exp(lam.reshape(()))

    u, u_t, _, u_xx = evaluate(theta, points.pde_x, points.pde_t, width)
    forcing = source(points.pde_x, points.pde_t, diffusion, rho, float(config["kappa_truth"]))
    pde = u_t - diffusion * u_xx - rho * u / (1.0 + kappa * u) - forcing

    data = field(theta, points.data_x, points.data_t, width) - config["_observed_data"]

    zeros = torch.zeros_like(points.initial_x)
    initial = field(theta, points.initial_x, zeros, width) - truth(points.initial_x, zeros)

    left = torch.zeros_like(points.boundary_t)
    right = torch.ones_like(points.boundary_t)
    u_left, _, ux_left, _ = evaluate(theta, left, points.boundary_t, width, second=False)
    u_right, _, ux_right, _ = evaluate(theta, right, points.boundary_t, width, second=False)
    return {
        "pde": pde,
        "data": data,
        "initial": initial,
        "boundary_value": u_left - u_right,
        "boundary_slope": ux_left - ux_right,
    }


def block_weights(config: dict[str, Any]) -> dict[str, float]:
    w = config["block_weights"]
    root = math.sqrt
    return {
        "pde": root(float(w["pde"])),
        "data": root(float(w["data"])),
        "initial": root(float(w["initial"])),
        "boundary_value": root(float(w["boundary"])),
        "boundary_slope": root(float(w["boundary"])),
    }


def weighted_residual(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
) -> torch.Tensor:
    parts = unweighted_blocks(theta, lam, points, config)
    weights = block_weights(config)
    return torch.cat([parts[name] * weights[name] for name in weights])


def sum_objective(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
) -> torch.Tensor:
    r = weighted_residual(theta, lam, points, config)
    return 0.5 * (r * r).sum()


def residual_count(config: dict[str, Any]) -> int:
    counts = config["points"]
    return (
        int(counts["pde"])
        + int(counts["data"])
        + int(counts["initial"])
        + 2 * int(counts["boundary_times"])
    )


def kappa_derivatives(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
):
    """d r / dkappa and d2 r / dkappa2 of the weighted PDE residual, at fixed state."""
    width = int(config["architecture"][1])
    rho = float(config["rho_known"])
    weight = block_weights(config)["pde"]
    kappa = torch.exp(lam.reshape(()))
    u = field(theta, points.pde_x, points.pde_t, width)
    denominator = 1.0 + kappa * u
    first = weight * rho * u.square() / denominator.square()
    second = weight * (-2.0 * rho) * u.pow(3) / denominator.pow(3)
    return first, second


def parameter_blocks(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
) -> dict[str, torch.Tensor]:
    """g_l, G_ll and H_ll of the sum objective in log-coordinate, by autograd."""
    from torch.autograd.functional import hessian, jacobian

    lam_v = lam.detach().clone().reshape(1).requires_grad_(True)
    rfun = lambda v: weighted_residual(theta, v, points, config)  # noqa: E731
    J = jacobian(rfun, lam_v, strategy="forward-mode", vectorize=True)
    r = rfun(lam_v).detach()
    G = J.T @ J
    g = J.T @ r
    H = hessian(lambda v: 0.5 * (rfun(v) ** 2).sum(), lam_v)
    return {"J": J.detach(), "r": r, "G": G.detach(), "g": g.detach(), "H": H.detach()}


def nonaffine_identity(
    theta: torch.Tensor, lam: torch.Tensor, points: Points, config: dict[str, Any]
) -> dict[str, Any]:
    """Compare both sides of H_ll - G_ll - g_l = kappa^2 sum rbar_i d2 rbar_i / dkappa2.

    Only the PDE block depends on kappa, so the sum runs over that block; every other
    residual has a vanishing second kappa-derivative.
    """
    blocks = parameter_blocks(theta, lam, points, config)
    left = float((blocks["H"] - blocks["G"] - torch.diag(blocks["g"]))[0, 0].item())
    parts = unweighted_blocks(theta, lam, points, config)
    r_pde = (parts["pde"] * block_weights(config)["pde"]).detach()
    _, second = kappa_derivatives(theta, lam, points, config)
    kappa = torch.exp(lam.reshape(()))
    right = float((kappa.square() * (r_pde * second).sum()).item())
    scale = max(abs(left), abs(right), 1.0e-30)
    return {
        "affine_prediction_g_l": float(blocks["g"][0].item()),
        "log_identity_left_H_minus_G": float((blocks["H"] - blocks["G"])[0, 0].item()),
        "left_H_minus_G_minus_g": left,
        "right_kappa2_sum_r_d2r": right,
        "absolute_difference": abs(left - right),
        "relative_difference": abs(left - right) / scale,
        "kappa": float(kappa.item()),
    }


def verify(repo: Path, commit: str) -> dict[str, Any]:
    """Analytic source, derivative and non-affine checks before any training."""
    config = load_config(repo, commit)
    config = prepare(config, int(config["development_data_seeds"][0]), 0.0)
    points = config["_points"]
    width = int(config["architecture"][1])

    x = points.pde_x.detach().clone().requires_grad_(True)
    t = points.pde_t.detach().clone().requires_grad_(True)
    u = truth(x, t)
    u_x, u_t = torch.autograd.grad(u.sum(), [x, t], create_graph=True)
    u_xx = torch.autograd.grad(u_x.sum(), x, create_graph=True)[0]
    analytic_ut, analytic_uxx = truth_derivatives(points.pde_x, points.pde_t)
    forcing = source(
        points.pde_x, points.pde_t, float(config["diffusion"]), float(config["rho_known"]),
        float(config["kappa_truth"]),
    )
    residual_at_truth = (
        analytic_ut
        - float(config["diffusion"]) * analytic_uxx
        - float(config["rho_known"]) * truth(points.pde_x, points.pde_t)
        / (1.0 + float(config["kappa_truth"]) * truth(points.pde_x, points.pde_t))
        - forcing
    )

    # periodic boundary of the manufactured solution
    left = torch.zeros(8, dtype=torch.float64)
    right = torch.ones(8, dtype=torch.float64)
    tt = torch.linspace(0.0, 0.4, 8, dtype=torch.float64)
    periodicity_value = float((truth(left, tt) - truth(right, tt)).abs().max().item())
    lx = left.clone().requires_grad_(True)
    rx = right.clone().requires_grad_(True)
    slope_left = torch.autograd.grad(truth(lx, tt).sum(), lx)[0]
    slope_right = torch.autograd.grad(truth(rx, tt).sum(), rx)[0]
    periodicity_slope = float((slope_left - slope_right).abs().max().item())

    # non-affine identity at the true state and coefficient
    generator = torch.Generator(device="cpu").manual_seed(20260916)
    theta = 0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    lam = torch.log(torch.tensor([float(config["kappa_truth"])], dtype=torch.float64))
    identity = nonaffine_identity(theta, lam, points, config)

    # analytic network branches vs autograd on the same random state
    xb = points.pde_x[:64]
    tb = points.pde_t[:64]
    an_u, an_ut, an_ux, an_uxx = evaluate(theta, xb, tb, width)
    ag_u, ag_ut, ag_ux, ag_uxx = evaluate_autograd(theta, xb, tb, width)
    branch_gap = {
        "u": float((an_u - ag_u).abs().max().item()),
        "u_t": float((an_ut - ag_ut).abs().max().item()),
        "u_x": float((an_ux - ag_ux).abs().max().item()),
        "u_xx": float((an_uxx - ag_uxx).abs().max().item()),
    }

    # a truly affine control: hold the reaction term linear in kappa and the identity must collapse
    return {
        "classification": "NEW_EXPERIMENT_VERIFICATION",
        "task": "E3_preflight",
        "environment": A.frozen_environment(repo, "jcp-submission-v1"),
        "residual_count": residual_count(config),
        "state_parameter_count": 4 * width + 1,
        "checks": {
            "truth_u_t_autograd_vs_analytic": float(
                (u_t.detach() - analytic_ut).abs().max().item()
            ),
            "truth_u_xx_autograd_vs_analytic": float(
                (u_xx.detach() - analytic_uxx).abs().max().item()
            ),
            "source_satisfies_pde_at_truth": float(residual_at_truth.abs().max().item()),
            "periodic_boundary_value_gap": periodicity_value,
            "periodic_boundary_slope_gap": periodicity_slope,
            "network_branches_analytic_vs_autograd": branch_gap,
            "truth_minimum_value": float(truth(torch.linspace(0, 1, 257, dtype=torch.float64),
                                              torch.linspace(0, 0.4, 257, dtype=torch.float64)).min().item()),
        },
        "nonaffine_identity": identity,
    }


def load_config(repo: Path, commit: str) -> dict[str, Any]:
    """Read the frozen E3 protocol snapshot from this namespace."""
    import yaml

    raw = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "protocol.yaml").read_text(encoding="utf-8")
    )
    e3 = raw["E3"]
    return {
        "points": {k: int(v) for k, v in e3["points"].items()},
        "domain_t": [float(v) for v in e3["domain_t"]],
        "diffusion": float(e3["diffusion"]),
        "rho_known": float(e3["rho_known"]),
        "kappa_truth": float(e3["kappa_truth"]),
        "kappa_initial": float(e3["kappa_initial"]),
        "architecture": [int(v) for v in e3["architecture"]],
        "block_weights": {k: float(v) for k, v in e3["block_weights"].items()},
        "noise_levels": [float(v) for v in e3["noise_levels"]],
        "development_data_seeds": [int(v) for v in e3["development_data_seeds"]],
        "heldout_data_seeds": [int(v) for v in e3["heldout_data_seeds"]],
        "initialization_seeds": [int(v) for v in e3["initialization_seeds"]],
        "optimizer": e3["optimizer_proposal"],
        "gamma_alpha": float(raw["numerics"]["gamma_alpha_primary"]),
        "scalar_error_floor": float(raw["numerics"]["scalar_error_floor"]),
        "exact_hessian": {
            "symmetry_relative_tolerance": 1.0e-8,
            "positive_eigenvalue_relative_tolerance": 1.0e-10,
            "solve_relative_tolerance": 1.0e-8,
        },
    }


def train_fit(
    config: dict[str, Any], data_seed: int, init_seed: int, noise_level: float
) -> dict[str, Any]:
    """Adam then L-BFGS on the sum objective, then freeze the parameter and polish state."""
    local = prepare(config, data_seed, noise_level)
    points = local["_points"]
    width = int(config["architecture"][1])
    optimizer_spec = config["optimizer"]

    generator = torch.Generator(device="cpu").manual_seed(init_seed)
    theta = (
        0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    ).requires_grad_(True)
    lam = torch.log(
        torch.tensor([config["kappa_initial"]], dtype=torch.float64)
    ).requires_grad_(True)

    adam = torch.optim.Adam(
        [theta, lam], lr=float(optimizer_spec["adam_learning_rate"])
    )
    for _ in range(int(optimizer_spec["adam_steps"])):
        adam.zero_grad(set_to_none=True)
        value = sum_objective(theta, lam, points, local)
        value.backward()
        adam.step()

    lbfgs = torch.optim.LBFGS(
        [theta, lam],
        max_iter=int(optimizer_spec["lbfgs_max_iterations"]),
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def closure():
        lbfgs.zero_grad(set_to_none=True)
        value = sum_objective(theta, lam, points, local)
        value.backward()
        return value

    lbfgs.step(closure)
    joint_iterations = int(lbfgs.state[theta].get("n_iter", 0))
    joint_objective = float(sum_objective(theta, lam, points, local).item())

    # freeze the physical parameter, polish the state only
    lam_fixed = lam.detach().clone()
    polish = torch.optim.LBFGS(
        [theta],
        max_iter=int(optimizer_spec["fixed_parameter_state_polish_max_iterations"]),
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def polish_closure():
        polish.zero_grad(set_to_none=True)
        value = sum_objective(theta, lam_fixed, points, local)
        value.backward()
        return value

    polish.step(polish_closure)
    polish_iterations = int(polish.state[theta].get("n_iter", 0))
    final_value = sum_objective(theta, lam_fixed, points, local)
    gradient = torch.autograd.grad(final_value, theta)[0]
    m = residual_count(config)
    normalized_state_gradient = float(torch.linalg.vector_norm(gradient).item()) / (
        m * max(float(torch.linalg.vector_norm(theta.detach()).item()), 1.0)
    )

    kappa = float(torch.exp(lam_fixed.reshape(())).item())
    return {
        "theta": theta.detach().clone(),
        "lam": lam_fixed.detach().clone(),
        "points": points,
        "local": local,
        "data_seed": data_seed,
        "initialization_seed": init_seed,
        "noise_level": noise_level,
        "objective_after_joint": joint_objective,
        "objective_after_polish": float(final_value.item()),
        "joint_lbfgs_iterations": joint_iterations,
        "polish_lbfgs_iterations": polish_iterations,
        "normalized_state_gradient_after_polish": normalized_state_gradient,
        "kappa_estimate": kappa,
        "parameter_relative_error": abs(kappa - config["kappa_truth"]) / config["kappa_truth"],
    }


def center_curvature(fit: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """F_raw, F_se and the exact reduced reference, with the error decomposition."""
    from torch.autograd.functional import jacobian
    from saeps.v3.foundation import full_hessian_references

    theta = fit["theta"]
    lam = fit["lam"]
    points = fit["points"]
    local = fit["local"]

    rfun = lambda t, l: weighted_residual(t, l, points, local)  # noqa: E731
    theta_v = theta.detach().clone().requires_grad_(True)
    lam_v = lam.detach().clone().requires_grad_(True)
    J_theta = jacobian(lambda t: rfun(t, lam_v), theta_v, strategy="forward-mode", vectorize=True)
    J_lam = jacobian(lambda l: rfun(theta_v, l), lam_v, strategy="forward-mode", vectorize=True)

    G_tt = J_theta.T @ J_theta
    gamma = config["gamma_alpha"] * float(torch.linalg.eigvalsh(G_tt).max().item())
    F_raw = J_lam.T @ J_lam
    F_se = F_raw - J_lam.T @ J_theta @ torch.linalg.solve(
        G_tt + gamma * torch.eye(theta.numel(), dtype=theta.dtype), J_theta.T @ J_lam
    )

    exact = full_hessian_references(
        lambda t, l: rfun(t, l), theta, lam, gamma, config["exact_hessian"]
    )
    matched = exact["gamma_matched"]
    if matched["status"] != "PASS":
        return {
            "status": "REFERENCE_REDUCTION_FAILED",
            "failure_reason": matched.get("failure_reason"),
            "gamma": gamma,
        }
    H_red = float(matched["reduced_hessian"][0][0])
    H_fix = float(exact["exact_parameter_block"][0][0])
    f_raw = float(F_raw[0, 0].item())
    f_se = float(F_se[0, 0].item())

    floor = config["scalar_error_floor"]
    c_exact = H_red - H_fix
    c_gn = f_se - f_raw
    denom = abs(H_red) + floor
    identity = nonaffine_identity(theta, lam, points, local)
    return {
        "status": "PASS",
        "gamma": gamma,
        "F_raw": f_raw,
        "F_se_GN": f_se,
        "H_fix_exact": H_fix,
        "H_red_exact": H_red,
        "relaxation_exact": c_exact,
        "relaxation_GN": c_gn,
        "E_raw": abs(f_raw - H_red) / denom,
        "E_SAEPS": abs(f_se - H_red) / denom,
        "E_fix": abs(H_fix - H_red) / denom,
        "E_GN_fix": abs(c_gn) / (abs(H_fix) + floor),
        "E_relax": abs(c_gn - c_exact) / (abs(c_exact) + floor),
        "exact_parameter_block_nonaffine": H_fix,
        "nonaffine": identity,
    }


def run_cohort(
    config: dict[str, Any], seeds: list[int], out: Path, repo: Path, commit: str
) -> None:
    rows = []
    for data_seed in seeds:
        for noise_level in [float(v) for v in config["noise_levels"]]:
            for init_seed in config["initialization_seeds"]:
                fit = train_fit(config, data_seed, init_seed, noise_level)
                curvature = center_curvature(fit, config)
                row = {
                    "data_seed": data_seed,
                    "initialization_seed": init_seed,
                    "noise_level": noise_level,
                    **{
                        k: v
                        for k, v in fit.items()
                        if k not in ("theta", "lam", "points", "local")
                    },
                    **curvature,
                }
                row.pop("nonaffine", None)
                row.update(
                    {
                        f"nonaffine_{k}": v
                        for k, v in (curvature.get("nonaffine") or {}).items()
                    }
                )
                rows.append(row)
                print(f"  data={data_seed} init={init_seed} noise={noise_level} "
                      f"kappa={fit['kappa_estimate']:.6f} E_SAEPS={curvature.get('E_SAEPS')}")

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e3_all_fits.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    valid = [r for r in rows if r.get("status") == "PASS"]
    wins = [r for r in valid if r["E_SAEPS"] < r["E_raw"]]
    summary = {
        "classification": "NEW_EXPERIMENT",
        "task": "E3_saturation_inversion",
        "environment": A.frozen_environment(repo, "jcp-submission-v1"),
        "objective": "sum objective 1/2 sum rbar^2 (loss, gradient and damping share one scale)",
        "fits_planned": len(rows),
        "fits_valid": len(valid),
        "median_E_raw": _median([r["E_raw"] for r in valid]),
        "median_E_SAEPS": _median([r["E_SAEPS"] for r in valid]),
        "median_E_fix": _median([r["E_fix"] for r in valid]),
        "median_E_GN_fix": _median([r["E_GN_fix"] for r in valid]),
        "median_E_relax": _median([r["E_relax"] for r in valid]),
        "SAEPS_wins": len(wins),
        "median_kappa_relative_error": _median([r["parameter_relative_error"] for r in valid]),
        "nonaffine_term_median": _median([r["nonaffine_left_H_minus_G_minus_g"] for r in valid]),
        "nonaffine_identity_max_abs_difference": max(
            (r["nonaffine_absolute_difference"] for r in valid), default=None
        ),
    }
    with (out / "e3_cluster_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")


def _median(values: list[float]) -> float | None:
    import statistics

    clean = [v for v in values if v is not None and math.isfinite(v)]
    return statistics.median(clean) if clean else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--develop", action="store_true")
    mode.add_argument("--heldout", action="store_true")
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--polish-budget",
        type=int,
        default=None,
        help="override the state-polish budget; used to show the reported quantities "
        "stop moving as the budget grows",
    )
    args = parser.parse_args()
    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    commit = A.resolve_commit(repo)

    if args.verify:
        destination = args.out.resolve()
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = verify(repo, commit)
        with destination.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
        print(destination)
        return

    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)
    config = load_config(repo, commit)
    if args.polish_budget is not None:
        config["optimizer"] = dict(config["optimizer"])
        config["optimizer"]["fixed_parameter_state_polish_max_iterations"] = (
            args.polish_budget
        )
    seeds = (
        config["development_data_seeds"] if args.develop else config["heldout_data_seeds"]
    )
    run_cohort(config, seeds, out, repo, commit)
    print(out)


if __name__ == "__main__":
    main()

