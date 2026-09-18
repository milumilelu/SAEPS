"""Shared, deterministic centre cache for E6 and E7.

E3's runs never saved model states, so E6 and E7 must retrain the centres they need.
This module trains them once, caches to disk, and hands the same centre to both
experiments.  The frozen E3 files are imported read-only and are not modified: the
single-hidden-layer path calls straight into ``e3_saturation``, so the base structure is
the same code that produced the frozen result rather than a reimplementation of it.

Architectures are given as a list.  ``[2, 16, 1]`` and ``[2, 32, 1]`` are the frozen
single-hidden-layer family (4*width+1 states).  ``[2, 16, 16, 1]`` is implemented here
with hand-derived derivatives that pass through the same softplus output transform; the
derivation is checked against autograd before any training is trusted.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import e3_saturation as E3  # noqa: E402
import repo_adapter as A  # noqa: E402


def state_count(architecture: list[int]) -> int:
    """Number of trainable state parameters for the given architecture."""
    total = 0
    for fan_in, fan_out in zip(architecture[:-1], architecture[1:]):
        total += fan_in * fan_out + fan_out
    return total


def _deep(theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor):
    """u, u_t, u_x, u_xx for the two-hidden-layer tanh net, differentiated by hand."""
    width = 16
    i1 = width * 2
    i2 = i1 + width
    i3 = i2 + width * width
    i4 = i3 + width
    i5 = i4 + width
    w1 = theta[:i1].reshape(width, 2)
    b1 = theta[i1:i2]
    w2 = theta[i2:i3].reshape(width, width)
    b2 = theta[i3:i4]
    w3 = theta[i4:i5]
    b3 = theta[i5]

    c1 = x[:, None] * w1[:, 0] + t[:, None] * w1[:, 1] + b1
    z1 = torch.tanh(c1)
    d1 = 1.0 - z1.square()
    c2 = z1 @ w2.T + b2
    z2 = torch.tanh(c2)
    d2 = 1.0 - z2.square()

    v = z2 @ w3 + b3
    s = torch.sigmoid(v)
    u = torch.nn.functional.softplus(v) + E3.OUTPUT_SHIFT

    dc2_dx = (d1 * w1[:, 0]) @ w2.T
    dc2_dt = (d1 * w1[:, 1]) @ w2.T
    v_x = (d2 * dc2_dx) @ w3
    v_t = (d2 * dc2_dt) @ w3
    u_x = s * v_x
    u_t = s * v_t

    d1d = -2.0 * z1 * d1
    d2d = -2.0 * z2 * d2
    ddc2_dx = (d1d * w1[:, 0].square()) @ w2.T
    v_xx = (d2d * dc2_dx.square()) @ w3 + (d2 * ddc2_dx) @ w3
    u_xx = s * (1.0 - s) * v_x.square() + s * v_xx
    return u, u_t, u_x, u_xx


def field(theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, architecture: list[int]):
    """Dispatch on depth so the single-hidden path stays the frozen implementation."""
    if len(architecture) == 3:
        return E3.evaluate(theta, x, t, int(architecture[1]))
    if len(architecture) == 4:
        return _deep(theta, x, t)
    raise ValueError(f"unsupported architecture {architecture}")


def field_autograd(theta, x, t, architecture):
    """Independent autograd evaluation, for the derivative preflight."""
    if len(architecture) == 3:
        return E3.evaluate_autograd(theta, x, t, int(architecture[1]))

    width = 16
    w1 = theta[: 2 * width].reshape(width, 2)
    b1 = theta[2 * width : 3 * width]
    w2 = theta[3 * width : 3 * width + width * width].reshape(width, width)
    b2 = theta[3 * width + width * width : 4 * width + width * width]
    w3 = theta[4 * width + width * width : 5 * width + width * width]
    b3 = theta[-1]

    def value(xx, tt):
        c1 = torch.tanh(xx[:, None] * w1[:, 0] + tt[:, None] * w1[:, 1] + b1)
        c2 = torch.tanh(c1 @ w2.T + b2)
        v = c2 @ w3 + b3
        return torch.nn.functional.softplus(v) + E3.OUTPUT_SHIFT

    xx = x.detach().clone().requires_grad_(True)
    tt = t.detach().clone().requires_grad_(True)
    u = value(xx, tt)
    u_x, u_t = torch.autograd.grad(u.sum(), [xx, tt], create_graph=True)
    u_xx = torch.autograd.grad(u_x.sum(), xx, create_graph=True)[0]
    return u.detach(), u_t.detach(), u_x.detach(), u_xx.detach()


def unweighted_blocks(
    theta, lam, points, local, architecture: list[int]
) -> dict[str, torch.Tensor]:
    """Same residual block structure as E3, with the field supplied by the architecture."""
    diffusion = float(local["diffusion"])
    rho = float(local["rho_known"])
    kappa = torch.exp(lam.reshape(()))

    u, u_t, _, u_xx = field(theta, points.pde_x, points.pde_t, architecture)
    forcing = E3.source(
        points.pde_x, points.pde_t, diffusion, rho, float(local["kappa_truth"])
    )
    pde = u_t - diffusion * u_xx - rho * u / (1.0 + kappa * u) - forcing

    # every block must use the same architecture's field, not the frozen single-hidden one
    data = field(theta, points.data_x, points.data_t, architecture)[0] - local["_observed_data"]
    zeros = torch.zeros_like(points.initial_x)
    initial = field(theta, points.initial_x, zeros, architecture)[0] - E3.truth(
        points.initial_x, zeros
    )
    left = torch.zeros_like(points.boundary_t)
    right = torch.ones_like(points.boundary_t)
    u_left, _, ux_left, _ = field(theta, left, points.boundary_t, architecture)
    u_right, _, ux_right, _ = field(theta, right, points.boundary_t, architecture)
    return {
        "pde": pde,
        "data": data,
        "initial": initial,
        "boundary_value": u_left - u_right,
        "boundary_slope": ux_left - ux_right,
    }


def weighted_residual(theta, lam, points, local, architecture) -> torch.Tensor:
    parts = unweighted_blocks(theta, lam, points, local, architecture)
    weights = E3.block_weights(local)
    return torch.cat([parts[name] * weights[name] for name in weights])


def objective(theta, lam, points, local, architecture) -> torch.Tensor:
    r = weighted_residual(theta, lam, points, local, architecture)
    return 0.5 * (r * r).sum()


def train(
    base_config: dict[str, Any],
    architecture: list[int],
    data_seed: int,
    init_seed: int,
    noise_level: float,
    budget: int,
) -> dict[str, Any]:
    """Adam then L-BFGS jointly, then freeze the parameter and polish the state."""
    local = E3.prepare(base_config, data_seed, noise_level)
    points = local["_points"]
    count = state_count(architecture)
    spec = base_config["optimizer"]
    m = E3.residual_count(base_config)

    generator = torch.Generator(device="cpu").manual_seed(init_seed)
    theta = (
        0.3 * torch.randn(count, dtype=torch.float64, generator=generator)
    ).requires_grad_(True)
    lam = torch.log(
        torch.tensor([base_config["kappa_initial"]], dtype=torch.float64)
    ).requires_grad_(True)

    started = time.perf_counter()
    adam = torch.optim.Adam([theta, lam], lr=float(spec["adam_learning_rate"]))
    for _ in range(int(spec["adam_steps"])):
        adam.zero_grad(set_to_none=True)
        objective(theta, lam, points, local, architecture).backward()
        adam.step()

    lbfgs = torch.optim.LBFGS(
        [theta, lam],
        max_iter=int(spec["lbfgs_max_iterations"]),
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def closure():
        lbfgs.zero_grad(set_to_none=True)
        value = objective(theta, lam, points, local, architecture)
        value.backward()
        return value

    lbfgs.step(closure)
    lam_fixed = lam.detach().clone()

    polish = torch.optim.LBFGS(
        [theta],
        max_iter=budget,
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def polish_closure():
        polish.zero_grad(set_to_none=True)
        value = objective(theta, lam_fixed, points, local, architecture)
        value.backward()
        return value

    polish.step(polish_closure)
    final = objective(theta, lam_fixed, points, local, architecture)
    gradient = torch.autograd.grad(final, theta)[0]
    normalized = float(torch.linalg.vector_norm(gradient).item()) / (
        m * max(float(torch.linalg.vector_norm(theta.detach()).item()), 1.0)
    )
    return {
        "theta": theta.detach().clone(),
        "lam": lam_fixed.detach().clone(),
        "points": points,
        "local": local,
        "architecture": architecture,
        "state_parameters": count,
        "residuals": m,
        "data_seed": data_seed,
        "initialization_seed": init_seed,
        "noise_level": noise_level,
        "objective": float(final.item()),
        "normalized_state_gradient": normalized,
        "polish_iterations": int(polish.state[theta].get("n_iter", 0)),
        "seconds": time.perf_counter() - started,
    }


def cache_path(cache: Path, architecture: list[int], data_seed: int, init_seed: int, noise: float) -> Path:
    tag = "_".join(str(v) for v in architecture)
    return cache / f"arch{tag}_data{data_seed}_init{init_seed}_noise{noise:g}.pt"


def load_or_train(
    cache: Path,
    base_config: dict[str, Any],
    architecture: list[int],
    data_seed: int,
    init_seed: int,
    noise: float,
    budget: int,
) -> dict[str, Any]:
    """Deterministic: retraining the same key reproduces the same centre."""
    path = cache_path(cache, architecture, data_seed, init_seed, noise)
    if path.is_file():
        payload = torch.load(path, map_location="cpu", weights_only=False)
        payload["local"] = E3.prepare(base_config, data_seed, noise)
        payload["points"] = payload["local"]["_points"]
        payload["architecture"] = list(architecture)
        return payload
    result = train(base_config, architecture, data_seed, init_seed, noise, budget)
    cache.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "theta": result["theta"],
            "lam": result["lam"],
            "state_parameters": result["state_parameters"],
            "residuals": result["residuals"],
            "data_seed": data_seed,
            "initialization_seed": init_seed,
            "noise_level": noise,
            "objective": result["objective"],
            "normalized_state_gradient": result["normalized_state_gradient"],
            "polish_iterations": result["polish_iterations"],
            "seconds": result["seconds"],
        },
        path,
    )
    return result
