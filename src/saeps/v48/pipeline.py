"""Matrix-free scaling on a real controlled-PINN residual."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.controlled import base_residual, fourier_library, make_diagnostic_points, train_checkpoint
from saeps.core import MatrixFreeEliminator, explicit_tikhonov_operator
from saeps.provenance import environment_provenance


def _widen(theta: torch.Tensor, base_width: int, target_width: int, seed: int) -> torch.Tensor:
    wx, wt, bias, out, output_bias = theta[:base_width], theta[base_width:2*base_width], theta[2*base_width:3*base_width], theta[3*base_width:4*base_width], theta[-1:]
    if target_width == base_width:
        return theta.clone()
    generator = torch.Generator(device="cpu").manual_seed(seed + 48_000)
    count = target_width - base_width
    extra = 0.3 * torch.randn(3, count, dtype=theta.dtype, generator=generator)
    return torch.cat([torch.cat([wx, extra[0]]), torch.cat([wt, extra[1]]), torch.cat([bias, extra[2]]), torch.cat([out, torch.zeros(count, dtype=theta.dtype)]), output_bias])


def run_scalability_checkpoint(root: Path, seed: int) -> dict:
    specification = load_config(root / "configs/v4_7/scalability.yaml")
    key = str(seed)
    if key not in specification["checkpoints"]:
        raise ValueError("unregistered scalability checkpoint")
    destination = root / f"outputs/runs/v4_7_scalability/checkpoint_{seed}"
    if destination.exists():
        raise RuntimeError("checkpoint output exists")
    runtime = load_config(root / specification["source_config"])
    runtime["network"]["hidden_width"] = int(specification["base_width"])
    runtime["network"]["architecture"] = "tanh_mlp_2x25x1"
    provenance = environment_provenance(root, runtime["dtype"], runtime["device"])
    started = time.perf_counter()
    checkpoint = train_checkpoint(runtime, seed)
    target_width = int(specification["checkpoints"][key]["target_width"])
    theta = _widen(checkpoint.theta, int(specification["base_width"]), target_width, seed)
    expanded = dict(runtime)
    expanded["network"] = dict(runtime["network"], hidden_width=target_width, architecture=f"tanh_mlp_2x{target_width}x1")
    points = make_diagnostic_points(expanded)
    library = fourier_library(expanded, points)
    source = library[expanded["selected_sources"]["q_parallel"]]
    pde_count = points.pde_x.numel()
    scale = math.sqrt(float(expanded["training"]["loss_weights"]["pde"]))
    parameter = torch.tensor([0.0], dtype=theta.dtype)

    def residual_function(state: torch.Tensor, coordinate: torch.Tensor) -> torch.Tensor:
        value = base_residual(state, points, expanded).clone()
        value[:pde_count] -= scale * coordinate[0] * source
        return value

    linearization = ResidualLinearization(residual_function, theta, parameter)
    _, jl = linearization.explicit_jacobians() if theta.numel() <= int(specification["explicit_audit_max_parameters"]) else (None, torch.func.jacrev(lambda q: residual_function(theta, q))(parameter))
    vector = torch.randn(theta.numel(), dtype=theta.dtype, generator=torch.Generator().manual_seed(seed + 49_000))
    vector /= torch.linalg.vector_norm(vector)
    for _ in range(int(specification["power_iterations"])):
        vector = linearization.vjp_theta(linearization.jvp_theta(vector))
        vector /= max(float(torch.linalg.vector_norm(vector).item()), 1.0e-30)
    normal_value = linearization.vjp_theta(linearization.jvp_theta(vector))
    lambda_estimate = float(torch.dot(vector, normal_value).item())
    gamma = float(specification["gamma_alpha"]) * max(lambda_estimate, 1.0e-12)
    solve_started = time.perf_counter()
    eliminator = MatrixFreeEliminator(linearization, gamma, float(specification["cg_tolerance"]), int(specification["cg_max_iterations"]))
    applied = eliminator.apply(jl[:, 0])
    solve_seconds = time.perf_counter() - solve_started
    fse = float(torch.dot(jl[:, 0], applied.value).item())
    explicit_error = None
    if theta.numel() <= int(specification["explicit_audit_max_parameters"]):
        jt, _ = linearization.explicit_jacobians()
        explicit = float((jl.T @ explicit_tikhonov_operator(jt, gamma) @ jl)[0, 0].item())
        explicit_error = abs(fse - explicit) / max(abs(explicit), 1.0e-30)
    passed = applied.solves[0].relative_residual <= float(specification["cg_acceptance"]) and (explicit_error is None or explicit_error <= float(specification["explicit_matrix_free_relative_tolerance"]))
    result = {"schema_version": 1, "phase": specification["phase"], "checkpoint": seed, "status": "PASS" if passed else "SOLVER_FAILURE", "scientific_claim_binding": False, "state_parameter_count": theta.numel(), "residual_count": jl.shape[0], "target_width": target_width, "function_preserving_padding": True, "gamma": gamma, "lambda_max_power_estimate": lambda_estimate, "cg_iterations": applied.solves[0].iterations, "verified_relative_residual": applied.solves[0].relative_residual, "explicit_relative_error": explicit_error, "JVP_count": dict(linearization.operation_counts).get("jvp_theta", 0), "VJP_count": dict(linearization.operation_counts).get("vjp_theta", 0), "training_seconds": checkpoint.elapsed_seconds, "solve_seconds": solve_seconds, "elapsed_seconds": time.perf_counter() - started, "provenance": provenance, "config_hash": config_hash(specification)}
    destination.mkdir(parents=True)
    path = destination / "result.json"
    path.write_text(json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (destination / "manifest.json").write_text(json.dumps({"schema_version": 1, "result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "status": result["status"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result
