"""Scalar inverse-PINN benchmarks used by P4 screening and P5 confirmation."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import torch

from saeps.forward import ForwardSolution, interpolate_solution, solve_periodic_scalar
from saeps.residual import stack_weighted_residuals
from saeps.seed import set_deterministic_seed


@dataclass(frozen=True)
class ScalarPoints:
    pde_x: torch.Tensor
    pde_t: torch.Tensor
    data_x: torch.Tensor
    data_t: torch.Tensor
    initial_x: torch.Tensor
    boundary_t: torch.Tensor


@dataclass(frozen=True)
class ScalarCheckpoint:
    benchmark: str
    seed: int
    theta: torch.Tensor
    log_parameter: torch.Tensor
    training_loss: float
    state_rmse: float
    parameter_relative_error: float
    adam_epochs: int
    lbfgs_iterations: int
    lbfgs_closure_calls: int
    stop_reason: str
    elapsed_seconds: float


def scalar_network(
    theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    expected = 4 * width + 1
    if theta.ndim != 1 or theta.numel() != expected:
        raise ValueError(f"theta must have {expected} elements")
    wx = theta[:width]
    wt = theta[width : 2 * width]
    bias = theta[2 * width : 3 * width]
    output = theta[3 * width : 4 * width]
    output_bias = theta[-1]
    activation = torch.tanh(x[:, None] * wx + t[:, None] * wt + bias)
    first = 1.0 - activation.square()
    state = activation @ output + output_bias
    state_t = (first * wt * output).sum(dim=1)
    state_x = (first * wx * output).sum(dim=1)
    state_xx = (-2.0 * activation * first * wx.square() * output).sum(dim=1)
    return state, state_t, state_x, state_xx


def make_scalar_points(config: dict[str, Any], seed: int) -> ScalarPoints:
    dtype = getattr(torch, config["dtype"])
    counts = config["points"]
    final_time = float(config["domain"]["t"][1])
    generator = torch.Generator(device="cpu").manual_seed(seed + 40_000)

    def random(count: int) -> torch.Tensor:
        return torch.rand(count, dtype=dtype, generator=generator)

    return ScalarPoints(
        pde_x=random(int(counts["pde"])),
        pde_t=final_time * random(int(counts["pde"])),
        data_x=random(int(counts["data"])),
        data_t=final_time * random(int(counts["data"])),
        initial_x=random(int(counts["initial"])),
        boundary_t=final_time * random(int(counts["boundary_times"])),
    )


def initial_state(benchmark: str, x: torch.Tensor) -> torch.Tensor:
    amplitude = 1.0 if benchmark == "Burgers" else 0.5
    return amplitude * torch.sin(2.0 * torch.pi * x)


def scalar_residual(
    theta: torch.Tensor,
    log_parameter: torch.Tensor,
    benchmark: str,
    points: ScalarPoints,
    reference: ForwardSolution,
    config: dict[str, Any],
) -> torch.Tensor:
    width = int(config["network"]["hidden_width"])
    physical = torch.exp(log_parameter[0])
    state, state_t, state_x, state_xx = scalar_network(
        theta, points.pde_x, points.pde_t, width
    )
    if benchmark == "Burgers":
        pde = state_t + state * state_x - physical * state_xx
    elif benchmark == "Allen-Cahn":
        diffusion = float(config["benchmarks"][benchmark]["fixed_diffusion"])
        pde = state_t - diffusion * state_xx - physical * (state - state**3)
    else:
        raise ValueError(f"unknown benchmark: {benchmark}")
    data = scalar_network(theta, points.data_x, points.data_t, width)[0] - interpolate_solution(
        reference, points.data_x, points.data_t
    )
    zero_t = torch.zeros_like(points.initial_x)
    initial = scalar_network(theta, points.initial_x, zero_t, width)[0] - initial_state(
        benchmark, points.initial_x
    )
    left = torch.zeros_like(points.boundary_t)
    right = torch.ones_like(points.boundary_t)
    left_values = scalar_network(theta, left, points.boundary_t, width)
    right_values = scalar_network(theta, right, points.boundary_t, width)
    boundary = torch.cat([left_values[0] - right_values[0], left_values[2] - right_values[2]])
    return stack_weighted_residuals(
        {"pde": pde, "data": data, "initial": initial, "boundary": boundary},
        config["loss_weights"],
    )


def solve_truth(config: dict[str, Any], benchmark: str, parameter: float | None = None) -> ForwardSolution:
    specification = config["benchmarks"][benchmark]
    value = float(specification["truth_parameter"] if parameter is None else parameter)
    solver = config["forward_solver"]
    return solve_periodic_scalar(
        benchmark,
        value,
        spatial_points=int(solver["spatial_points"]),
        time_steps=int(solver["time_steps"]),
        final_time=float(config["domain"]["t"][1]),
        dtype=getattr(torch, config["dtype"]),
        allen_cahn_diffusion=float(specification.get("fixed_diffusion", 0.01)),
    )


def train_scalar_checkpoint(
    config: dict[str, Any], benchmark: str, seed: int, reference: ForwardSolution
) -> tuple[ScalarCheckpoint, ScalarPoints]:
    started = time.perf_counter()
    set_deterministic_seed(seed)
    dtype = getattr(torch, config["dtype"])
    width = int(config["network"]["hidden_width"])
    theta = torch.nn.Parameter(0.3 * torch.randn(4 * width + 1, dtype=dtype))
    initial_parameter = float(config["benchmarks"][benchmark]["initial_parameter"])
    log_parameter = torch.nn.Parameter(torch.tensor([math.log(initial_parameter)], dtype=dtype))
    points = make_scalar_points(config, seed)
    settings = config["optimizer"]
    adam = torch.optim.Adam(
        [theta, log_parameter], lr=float(settings["adam_learning_rate"])
    )
    for _ in range(int(settings["adam_epochs"])):
        adam.zero_grad(set_to_none=True)
        residual = scalar_residual(theta, log_parameter, benchmark, points, reference, config)
        loss = 0.5 * torch.mean(residual.square())
        loss.backward()
        adam.step()
    closure_calls = 0
    lbfgs = torch.optim.LBFGS(
        [theta, log_parameter],
        max_iter=int(settings["lbfgs_max_iterations"]),
        tolerance_grad=float(settings["lbfgs_tolerance_grad"]),
        tolerance_change=float(settings["lbfgs_tolerance_change"]),
        history_size=100,
        line_search_fn="strong_wolfe",
    )

    def closure() -> torch.Tensor:
        nonlocal closure_calls
        closure_calls += 1
        lbfgs.zero_grad(set_to_none=True)
        residual = scalar_residual(theta, log_parameter, benchmark, points, reference, config)
        objective = 0.5 * torch.mean(residual.square())
        objective.backward()
        return objective

    lbfgs.step(closure)
    iterations = int(lbfgs.state[theta].get("n_iter", 0))
    final_residual = scalar_residual(theta, log_parameter, benchmark, points, reference, config)
    final_loss = float((0.5 * torch.mean(final_residual.square())).item())
    prediction = scalar_network(theta, points.data_x, points.data_t, width)[0]
    truth = interpolate_solution(reference, points.data_x, points.data_t)
    state_rmse = float(torch.sqrt(torch.mean((prediction - truth).square())).item())
    truth_parameter = float(config["benchmarks"][benchmark]["truth_parameter"])
    learned = float(torch.exp(log_parameter.detach())[0].item())
    checkpoint = ScalarCheckpoint(
        benchmark=benchmark,
        seed=seed,
        theta=theta.detach().clone(),
        log_parameter=log_parameter.detach().clone(),
        training_loss=final_loss,
        state_rmse=state_rmse,
        parameter_relative_error=abs(learned - truth_parameter) / truth_parameter,
        adam_epochs=int(settings["adam_epochs"]),
        lbfgs_iterations=iterations,
        lbfgs_closure_calls=closure_calls,
        stop_reason=(
            "ADAM_COMPLETED_THEN_LBFGS_MAX_ITERATIONS"
            if iterations >= int(settings["lbfgs_max_iterations"])
            else "ADAM_COMPLETED_THEN_LBFGS_TERMINATED"
        ),
        elapsed_seconds=time.perf_counter() - started,
    )
    return checkpoint, points


def refine_scalar_checkpoint(
    config: dict[str, Any],
    checkpoint: ScalarCheckpoint,
    points: ScalarPoints,
    reference: ForwardSolution,
    settings: dict[str, Any],
) -> ScalarCheckpoint:
    """Apply the single locked, uniform checkpoint-refinement retry."""
    started = time.perf_counter()
    theta = torch.nn.Parameter(checkpoint.theta.detach().clone())
    log_parameter = torch.nn.Parameter(checkpoint.log_parameter.detach().clone())
    adam = torch.optim.Adam(
        [theta, log_parameter], lr=float(settings["adam_learning_rate"])
    )
    for _ in range(int(settings["adam_epochs"])):
        adam.zero_grad(set_to_none=True)
        residual = scalar_residual(
            theta, log_parameter, checkpoint.benchmark, points, reference, config
        )
        loss = 0.5 * torch.mean(residual.square())
        loss.backward()
        adam.step()
    calls = 0
    lbfgs = torch.optim.LBFGS(
        [theta, log_parameter],
        max_iter=int(settings["lbfgs_max_iterations"]),
        tolerance_grad=float(config["optimizer"]["lbfgs_tolerance_grad"]),
        tolerance_change=float(config["optimizer"]["lbfgs_tolerance_change"]),
        history_size=100,
        line_search_fn="strong_wolfe",
    )

    def closure() -> torch.Tensor:
        nonlocal calls
        calls += 1
        lbfgs.zero_grad(set_to_none=True)
        residual = scalar_residual(
            theta, log_parameter, checkpoint.benchmark, points, reference, config
        )
        value = 0.5 * torch.mean(residual.square())
        value.backward()
        return value

    lbfgs.step(closure)
    residual = scalar_residual(
        theta, log_parameter, checkpoint.benchmark, points, reference, config
    )
    loss = float((0.5 * torch.mean(residual.square())).item())
    width = int(config["network"]["hidden_width"])
    prediction = scalar_network(theta, points.data_x, points.data_t, width)[0]
    truth = interpolate_solution(reference, points.data_x, points.data_t)
    state_rmse = float(torch.sqrt(torch.mean((prediction - truth).square())).item())
    truth_parameter = float(config["benchmarks"][checkpoint.benchmark]["truth_parameter"])
    learned = float(torch.exp(log_parameter.detach())[0].item())
    iterations = int(lbfgs.state[theta].get("n_iter", 0))
    return ScalarCheckpoint(
        benchmark=checkpoint.benchmark,
        seed=checkpoint.seed,
        theta=theta.detach().clone(),
        log_parameter=log_parameter.detach().clone(),
        training_loss=loss,
        state_rmse=state_rmse,
        parameter_relative_error=abs(learned - truth_parameter) / truth_parameter,
        adam_epochs=checkpoint.adam_epochs + int(settings["adam_epochs"]),
        lbfgs_iterations=checkpoint.lbfgs_iterations + iterations,
        lbfgs_closure_calls=checkpoint.lbfgs_closure_calls + calls,
        stop_reason="LOCKED_UNIFORM_RETRY_COMPLETED",
        elapsed_seconds=checkpoint.elapsed_seconds + (time.perf_counter() - started),
    )


def classical_observation_loss(
    config: dict[str, Any],
    benchmark: str,
    parameter: float,
    points: ScalarPoints,
    truth: ForwardSolution,
) -> float:
    candidate = solve_truth(config, benchmark, parameter)
    difference = interpolate_solution(candidate, points.data_x, points.data_t) - interpolate_solution(
        truth, points.data_x, points.data_t
    )
    return float((0.5 * torch.mean(difference.square())).item())
