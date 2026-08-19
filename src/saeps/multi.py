"""Manufactured coupled reaction-diffusion inverse PINN for P6."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import torch

from saeps.residual import stack_weighted_residuals
from saeps.scalar import scalar_network
from saeps.seed import set_deterministic_seed


@dataclass(frozen=True)
class MultiPoints:
    pde_x: torch.Tensor
    pde_t: torch.Tensor
    data_x: torch.Tensor
    data_t: torch.Tensor
    initial_x: torch.Tensor
    boundary_t: torch.Tensor


@dataclass(frozen=True)
class MultiCheckpoint:
    seed: int
    theta: torch.Tensor
    coordinate: torch.Tensor
    training_loss: float
    state_rmse: float
    parameter_relative_errors: tuple[float, float]
    elapsed_seconds: float
    stop_reason: str
    adam_epochs: int
    lbfgs_iterations: int
    lbfgs_closure_calls: int


def truth_channels(x: torch.Tensor, t: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    u = torch.sin(torch.pi * x) * torch.exp(-t) + 0.1 * torch.sin(2.0 * torch.pi * x) * torch.sin(t)
    v = torch.cos(0.5 * torch.pi * x) * torch.exp(-0.5 * t) + 0.1 * torch.sin(3.0 * torch.pi * x) * torch.cos(t)
    return u, v


def truth_derivatives(x: torch.Tensor, t: torch.Tensor) -> tuple[torch.Tensor, ...]:
    u, v = truth_channels(x, t)
    ut = -torch.sin(torch.pi * x) * torch.exp(-t) + 0.1 * torch.sin(2.0 * torch.pi * x) * torch.cos(t)
    vt = -0.5 * torch.cos(0.5 * torch.pi * x) * torch.exp(-0.5 * t) - 0.1 * torch.sin(3.0 * torch.pi * x) * torch.sin(t)
    uxx = -torch.pi**2 * torch.sin(torch.pi * x) * torch.exp(-t) - 0.4 * torch.pi**2 * torch.sin(2.0 * torch.pi * x) * torch.sin(t)
    vxx = -0.25 * torch.pi**2 * torch.cos(0.5 * torch.pi * x) * torch.exp(-0.5 * t) - 0.9 * torch.pi**2 * torch.sin(3.0 * torch.pi * x) * torch.cos(t)
    return u, v, ut, vt, uxx, vxx


def make_multi_points(config: dict[str, Any], seed: int) -> MultiPoints:
    dtype = getattr(torch, config["dtype"])
    counts = config["points"]
    final_time = float(config["domain"]["t"][1])
    generator = torch.Generator(device="cpu").manual_seed(seed + 60_000)

    def random(count: int) -> torch.Tensor:
        return torch.rand(count, dtype=dtype, generator=generator)

    return MultiPoints(
        random(int(counts["pde"])), final_time * random(int(counts["pde"])),
        random(int(counts["data"])), final_time * random(int(counts["data"])),
        random(int(counts["initial"])), final_time * random(int(counts["boundary_times"])),
    )


def multi_residual(
    theta: torch.Tensor, coordinate: torch.Tensor, points: MultiPoints, config: dict[str, Any]
) -> torch.Tensor:
    width = int(config["network"]["hidden_width"])
    channel_size = 4 * width + 1
    if theta.numel() != 2 * channel_size or coordinate.shape != (2,):
        raise ValueError("multi state/coordinate shape mismatch")
    a, b = torch.exp(coordinate)
    u_values = scalar_network(theta[:channel_size], points.pde_x, points.pde_t, width)
    v_values = scalar_network(theta[channel_size:], points.pde_x, points.pde_t, width)
    u, v = u_values[0], v_values[0]
    truth_u, truth_v, truth_ut, truth_vt, truth_uxx, truth_vxx = truth_derivatives(points.pde_x, points.pde_t)
    specification = config["benchmark"]
    du, dv = float(specification["diffusion_u"]), float(specification["diffusion_v"])
    true_a, true_b = float(specification["truth_a"]), float(specification["truth_b"])
    source_u = truth_ut - du * truth_uxx + true_a * truth_u - true_b * truth_v
    source_v = truth_vt - dv * truth_vxx - true_a * truth_u + true_b * truth_v
    pde_u = u_values[1] - du * u_values[3] + a * u - b * v - source_u
    pde_v = v_values[1] - dv * v_values[3] - a * u + b * v - source_v
    data_truth_u, data_truth_v = truth_channels(points.data_x, points.data_t)
    data_u = scalar_network(theta[:channel_size], points.data_x, points.data_t, width)[0] - data_truth_u
    data_v = scalar_network(theta[channel_size:], points.data_x, points.data_t, width)[0] - data_truth_v
    zeros = torch.zeros_like(points.initial_x)
    initial_truth_u, initial_truth_v = truth_channels(points.initial_x, zeros)
    initial_u = scalar_network(theta[:channel_size], points.initial_x, zeros, width)[0] - initial_truth_u
    initial_v = scalar_network(theta[channel_size:], points.initial_x, zeros, width)[0] - initial_truth_v
    left = torch.zeros_like(points.boundary_t)
    right = torch.ones_like(points.boundary_t)
    truth_left = truth_channels(left, points.boundary_t)
    truth_right = truth_channels(right, points.boundary_t)
    boundary_u = torch.cat([
        scalar_network(theta[:channel_size], left, points.boundary_t, width)[0] - truth_left[0],
        scalar_network(theta[:channel_size], right, points.boundary_t, width)[0] - truth_right[0],
    ])
    boundary_v = torch.cat([
        scalar_network(theta[channel_size:], left, points.boundary_t, width)[0] - truth_left[1],
        scalar_network(theta[channel_size:], right, points.boundary_t, width)[0] - truth_right[1],
    ])
    return stack_weighted_residuals(
        {
            "pde_u": pde_u, "pde_v": pde_v, "data_u": data_u, "data_v": data_v,
            "initial_u": initial_u, "initial_v": initial_v,
            "boundary_u": boundary_u, "boundary_v": boundary_v,
        },
        config["loss_weights"],
    )


def train_multi_checkpoint(config: dict[str, Any], seed: int) -> tuple[MultiCheckpoint, MultiPoints]:
    started = time.perf_counter()
    set_deterministic_seed(seed)
    dtype = getattr(torch, config["dtype"])
    width = int(config["network"]["hidden_width"])
    theta = torch.nn.Parameter(0.3 * torch.randn(2 * (4 * width + 1), dtype=dtype))
    specification = config["benchmark"]
    coordinate = torch.nn.Parameter(torch.log(torch.tensor([specification["initial_a"], specification["initial_b"]], dtype=dtype)))
    points = make_multi_points(config, seed)
    settings = config["optimizer"]
    adam = torch.optim.Adam([theta, coordinate], lr=float(settings["adam_learning_rate"]))
    for _ in range(int(settings["adam_epochs"])):
        adam.zero_grad(set_to_none=True)
        residual = multi_residual(theta, coordinate, points, config)
        loss = 0.5 * torch.mean(residual.square())
        loss.backward(); adam.step()
    calls = 0
    lbfgs = torch.optim.LBFGS(
        [theta, coordinate], max_iter=int(settings["lbfgs_max_iterations"]), history_size=100,
        tolerance_grad=float(settings["lbfgs_tolerance_grad"]),
        tolerance_change=float(settings["lbfgs_tolerance_change"]), line_search_fn="strong_wolfe"
    )

    def closure() -> torch.Tensor:
        nonlocal calls
        calls += 1; lbfgs.zero_grad(set_to_none=True)
        residual = multi_residual(theta, coordinate, points, config)
        value = 0.5 * torch.mean(residual.square()); value.backward(); return value

    lbfgs.step(closure)
    iterations = int(lbfgs.state[theta].get("n_iter", 0))
    residual = multi_residual(theta, coordinate, points, config)
    loss = float((0.5 * torch.mean(residual.square())).item())
    channel_size = 4 * width + 1
    predicted_u = scalar_network(theta[:channel_size], points.data_x, points.data_t, width)[0]
    predicted_v = scalar_network(theta[channel_size:], points.data_x, points.data_t, width)[0]
    true_u, true_v = truth_channels(points.data_x, points.data_t)
    rmse = float(torch.sqrt(torch.mean(torch.cat([predicted_u-true_u, predicted_v-true_v]).square())).item())
    physical = torch.exp(coordinate.detach())
    errors = (
        abs(float(physical[0].item()) - float(specification["truth_a"])) / float(specification["truth_a"]),
        abs(float(physical[1].item()) - float(specification["truth_b"])) / float(specification["truth_b"]),
    )
    return MultiCheckpoint(
        seed, theta.detach().clone(), coordinate.detach().clone(), loss, rmse, errors,
        time.perf_counter()-started,
        "ADAM_COMPLETED_THEN_LBFGS_MAX_ITERATIONS" if iterations >= int(settings["lbfgs_max_iterations"]) else "ADAM_COMPLETED_THEN_LBFGS_TERMINATED",
        int(settings["adam_epochs"]), iterations, calls,
    ), points

