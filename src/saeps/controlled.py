"""Controlled manufactured parabolic-PINN geometry for protocol phase P2."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import yaml

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import (
    MatrixFreeEliminator,
    compute_matrix_free_saeps,
    exact_svd_complement_projector,
    explicit_tikhonov_operator,
)
from saeps.provenance import environment_provenance, make_run_id
from saeps.residual import stack_weighted_residuals
from saeps.seed import set_deterministic_seed
from saeps.solvers import conjugate_gradient


FINAL_STATUSES = {
    "PASS",
    "CHECKPOINT_INVALID",
    "PROFILE_FAILURE",
    "SOLVER_FAILURE",
    "NUMERICAL_FAILURE",
}


@dataclass(frozen=True)
class PointSet:
    pde_x: torch.Tensor
    pde_t: torch.Tensor
    data_x: torch.Tensor
    data_t: torch.Tensor
    initial_x: torch.Tensor
    boundary_t: torch.Tensor


@dataclass(frozen=True)
class TrainedCheckpoint:
    seed: int
    theta: torch.Tensor
    training_loss: float
    stop_reason: str
    adam_epochs: int
    lbfgs_closure_calls: int
    normalized_gradient: float
    state_rmse: float
    elapsed_seconds: float


def truth_state(x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    return torch.sin(torch.pi * x) * torch.exp(-t) + 0.2 * torch.sin(
        3.0 * torch.pi * x
    ) * torch.sin(2.0 * torch.pi * t)


def truth_operator(x: torch.Tensor, t: torch.Tensor, diffusion: float, reaction: float) -> torch.Tensor:
    state = truth_state(x, t)
    time_derivative = -torch.sin(torch.pi * x) * torch.exp(-t) + 0.4 * torch.pi * torch.sin(
        3.0 * torch.pi * x
    ) * torch.cos(2.0 * torch.pi * t)
    space_second = -torch.pi**2 * torch.sin(torch.pi * x) * torch.exp(-t) - 1.8 * torch.pi**2 * torch.sin(
        3.0 * torch.pi * x
    ) * torch.sin(2.0 * torch.pi * t)
    return time_derivative - diffusion * space_second + reaction * state


def _unpack(theta: torch.Tensor, width: int) -> tuple[torch.Tensor, ...]:
    expected = 4 * width + 1
    if theta.ndim != 1 or theta.numel() != expected:
        raise ValueError(f"theta must have shape ({expected},)")
    return (
        theta[:width],
        theta[width : 2 * width],
        theta[2 * width : 3 * width],
        theta[3 * width : 4 * width],
        theta[-1],
    )


def network_state_and_derivatives(
    theta: torch.Tensor, x: torch.Tensor, t: torch.Tensor, width: int
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    weight_x, weight_t, bias, output_weight, output_bias = _unpack(theta, width)
    activation = torch.tanh(
        x[:, None] * weight_x[None, :]
        + t[:, None] * weight_t[None, :]
        + bias[None, :]
    )
    first = 1.0 - activation.square()
    state = activation @ output_weight + output_bias
    time_derivative = (first * weight_t[None, :] * output_weight[None, :]).sum(dim=1)
    space_second = (
        -2.0
        * activation
        * first
        * weight_x[None, :].square()
        * output_weight[None, :]
    ).sum(dim=1)
    return state, time_derivative, space_second


def make_training_points(config: dict[str, Any], seed: int) -> PointSet:
    training = config["training"]
    dtype = getattr(torch, config["dtype"])
    generator = torch.Generator(device="cpu").manual_seed(seed + 20_000)

    def uniform(count: int) -> torch.Tensor:
        return torch.rand(count, dtype=dtype, generator=generator)

    pde_count = int(training["pde_points"])
    data_count = int(training["data_points"])
    return PointSet(
        pde_x=uniform(pde_count),
        pde_t=uniform(pde_count),
        data_x=uniform(data_count),
        data_t=uniform(data_count),
        initial_x=uniform(int(training["initial_points"])),
        boundary_t=uniform(int(training["boundary_points_per_side"])),
    )


def make_diagnostic_points(config: dict[str, Any]) -> PointSet:
    diagnostic = config["diagnostic"]
    dtype = getattr(torch, config["dtype"])
    nx, nt = (int(value) for value in diagnostic["pde_grid"])
    x = torch.linspace(0.0, 1.0, nx + 2, dtype=dtype)[1:-1]
    t = torch.linspace(0.0, 1.0, nt + 2, dtype=dtype)[1:-1]
    mesh_x, mesh_t = torch.meshgrid(x, t, indexing="ij")
    data_nx, data_nt = (int(value) for value in diagnostic["data_grid"])
    data_x = torch.linspace(0.0, 1.0, data_nx, dtype=dtype)
    data_t = torch.linspace(0.0, 1.0, data_nt, dtype=dtype)
    data_mesh_x, data_mesh_t = torch.meshgrid(data_x, data_t, indexing="ij")
    return PointSet(
        pde_x=mesh_x.reshape(-1),
        pde_t=mesh_t.reshape(-1),
        data_x=data_mesh_x.reshape(-1),
        data_t=data_mesh_t.reshape(-1),
        initial_x=torch.linspace(0.0, 1.0, int(diagnostic["initial_points"]), dtype=dtype),
        boundary_t=torch.linspace(
            0.0, 1.0, int(diagnostic["boundary_points_per_side"]), dtype=dtype
        ),
    )


def base_residual(
    theta: torch.Tensor, points: PointSet, config: dict[str, Any]
) -> torch.Tensor:
    width = int(config["network"]["hidden_width"])
    diffusion = float(config["pde"]["diffusion"])
    reaction = float(config["pde"]["reaction"])
    weights = config["training"]["loss_weights"]
    pde_state, pde_time, pde_space_second = network_state_and_derivatives(
        theta, points.pde_x, points.pde_t, width
    )
    predicted_operator = pde_time - diffusion * pde_space_second + reaction * pde_state
    data_state = network_state_and_derivatives(theta, points.data_x, points.data_t, width)[0]
    initial_t = torch.zeros_like(points.initial_x)
    initial_state = network_state_and_derivatives(theta, points.initial_x, initial_t, width)[0]
    left_x = torch.zeros_like(points.boundary_t)
    right_x = torch.ones_like(points.boundary_t)
    boundary_state = torch.cat(
        [
            network_state_and_derivatives(theta, left_x, points.boundary_t, width)[0],
            network_state_and_derivatives(theta, right_x, points.boundary_t, width)[0],
        ]
    )
    boundary_truth = torch.cat(
        [truth_state(left_x, points.boundary_t), truth_state(right_x, points.boundary_t)]
    )
    return stack_weighted_residuals(
        {
            "pde": predicted_operator
            - truth_operator(points.pde_x, points.pde_t, diffusion, reaction),
            "data": data_state - truth_state(points.data_x, points.data_t),
            "initial": initial_state - truth_state(points.initial_x, initial_t),
            "boundary": boundary_state - boundary_truth,
        },
        weights,
    )


def _normalized_gradient(theta: torch.Tensor, residual: torch.Tensor) -> float:
    loss = 0.5 * torch.dot(residual, residual) / residual.numel()
    gradient = torch.autograd.grad(loss, theta)[0]
    denominator = max(float(torch.linalg.vector_norm(theta).item()), 1.0)
    return float(torch.linalg.vector_norm(gradient).item()) / denominator


def train_checkpoint(config: dict[str, Any], seed: int) -> TrainedCheckpoint:
    started = time.perf_counter()
    set_deterministic_seed(seed)
    dtype = getattr(torch, config["dtype"])
    width = int(config["network"]["hidden_width"])
    theta = torch.nn.Parameter(0.4 * torch.randn(4 * width + 1, dtype=dtype))
    points = make_training_points(config, seed)
    training = config["training"]
    adam = torch.optim.Adam([theta], lr=float(training["adam_learning_rate"]))
    for _ in range(int(training["adam_epochs"])):
        adam.zero_grad(set_to_none=True)
        residual = base_residual(theta, points, config)
        loss = 0.5 * torch.dot(residual, residual) / residual.numel()
        loss.backward()
        adam.step()

    closure_calls = 0
    optimizer = torch.optim.LBFGS(
        [theta],
        max_iter=int(training["lbfgs_max_iterations"]),
        tolerance_grad=float(training["lbfgs_tolerance_grad"]),
        tolerance_change=float(training["lbfgs_tolerance_change"]),
        line_search_fn="strong_wolfe",
    )

    def closure() -> torch.Tensor:
        nonlocal closure_calls
        closure_calls += 1
        optimizer.zero_grad(set_to_none=True)
        current = base_residual(theta, points, config)
        objective = 0.5 * torch.dot(current, current) / current.numel()
        objective.backward()
        return objective

    optimizer.step(closure)
    optimizer_state = optimizer.state[theta]
    lbfgs_iterations = int(optimizer_state.get("n_iter", 0))
    final_residual = base_residual(theta, points, config)
    final_loss = float((0.5 * torch.dot(final_residual, final_residual) / final_residual.numel()).item())
    gradient = _normalized_gradient(theta, final_residual)
    diagnostic = make_diagnostic_points(config)
    prediction = network_state_and_derivatives(
        theta, diagnostic.data_x, diagnostic.data_t, width
    )[0]
    state_rmse = float(
        torch.sqrt(
            torch.mean((prediction - truth_state(diagnostic.data_x, diagnostic.data_t)).square())
        ).item()
    )
    return TrainedCheckpoint(
        seed=seed,
        theta=theta.detach().clone(),
        training_loss=final_loss,
        stop_reason=(
            "ADAM_COMPLETED_THEN_LBFGS_MAX_ITERATIONS"
            if lbfgs_iterations >= int(training["lbfgs_max_iterations"])
            else "ADAM_COMPLETED_THEN_LBFGS_TERMINATED"
        ),
        adam_epochs=int(training["adam_epochs"]),
        lbfgs_closure_calls=closure_calls,
        normalized_gradient=gradient,
        state_rmse=state_rmse,
        elapsed_seconds=time.perf_counter() - started,
    )


def fourier_library(config: dict[str, Any], points: PointSet) -> dict[str, torch.Tensor]:
    library: dict[str, torch.Tensor] = {}
    temporal_modes = config["fourier_library"]["temporal_modes"]
    for spatial_frequency in config["fourier_library"]["spatial_frequencies"]:
        spatial = torch.sin(float(spatial_frequency) * torch.pi * points.pde_x)
        for temporal_mode in temporal_modes:
            if temporal_mode == "constant":
                temporal = torch.ones_like(points.pde_t)
            elif temporal_mode.startswith("sin"):
                frequency = int(temporal_mode[3:])
                temporal = torch.sin(float(frequency) * torch.pi * points.pde_t)
            elif temporal_mode.startswith("cos"):
                frequency = int(temporal_mode[3:])
                temporal = torch.cos(float(frequency) * torch.pi * points.pde_t)
            else:
                raise ValueError(f"unknown temporal mode: {temporal_mode}")
            value = spatial * temporal
            library[f"sin{spatial_frequency}x_{temporal_mode}t"] = value / torch.linalg.vector_norm(value)
    return library


def embedded_source(source: torch.Tensor, points: PointSet, config: dict[str, Any]) -> torch.Tensor:
    total = (
        points.pde_x.numel()
        + points.data_x.numel()
        + points.initial_x.numel()
        + 2 * points.boundary_t.numel()
    )
    result = torch.zeros(total, dtype=source.dtype, device=source.device)
    result[: source.numel()] = source * math.sqrt(float(config["training"]["loss_weights"]["pde"]))
    return result


def tangent_overlaps(
    jacobian_theta: torch.Tensor,
    library: dict[str, torch.Tensor],
    points: PointSet,
    config: dict[str, Any],
) -> tuple[dict[str, float], int]:
    complement, rank = exact_svd_complement_projector(
        jacobian_theta, float(config["fourier_library"]["svd_relative_tolerance"])
    )
    tangent_projector = torch.eye(
        complement.shape[0], dtype=complement.dtype, device=complement.device
    ) - complement
    overlaps: dict[str, float] = {}
    for name, source in library.items():
        vector = embedded_source(source, points, config)
        overlaps[name] = float((torch.dot(vector, tangent_projector @ vector) / torch.dot(vector, vector)).item())
    return overlaps, rank


def select_directions(
    per_seed_overlaps: dict[int, dict[str, float]],
    library: dict[str, torch.Tensor],
    orthogonality_tolerance: float,
) -> tuple[str, str, dict[str, float], float]:
    names = sorted(library)
    medians = {
        name: float(
            torch.median(
                torch.tensor(
                    [per_seed_overlaps[seed][name] for seed in sorted(per_seed_overlaps)],
                    dtype=torch.float64,
                )
            ).item()
        )
        for name in names
    }
    parallel = sorted(names, key=lambda name: (-medians[name], name))[0]
    orthogonal = [
        name
        for name in names
        if name != parallel
        and abs(float(torch.dot(library[parallel], library[name]).item())) <= orthogonality_tolerance
    ]
    if not orthogonal:
        raise RuntimeError("no Fourier candidate is orthogonal to q_parallel")
    perpendicular = sorted(orthogonal, key=lambda name: (medians[name], name))[0]
    inner_product = float(torch.dot(library[parallel], library[perpendicular]).item())
    return parallel, perpendicular, medians, inner_product


def _gamma_sweep_for_seed(
    theta: torch.Tensor,
    points: PointSet,
    q_parallel: torch.Tensor,
    q_perpendicular: torch.Tensor,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], float]:
    dummy_parameter = torch.zeros(1, dtype=theta.dtype)
    linearization = ResidualLinearization(
        lambda state, _: base_residual(state, points, config), theta, dummy_parameter
    )
    jacobian_theta, _ = linearization.explicit_jacobians()
    lambda_max = float(torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item())
    result: list[dict[str, Any]] = []
    for gamma_alpha in config["gamma"]["alpha_grid"]:
        gamma = float(gamma_alpha) * lambda_max
        eliminator = MatrixFreeEliminator(
            linearization,
            gamma,
            float(config["gamma"]["cg_tolerance"]),
            int(config["gamma"]["cg_max_iterations"]),
        )
        explicit_operator = explicit_tikhonov_operator(jacobian_theta, gamma)
        rows: list[dict[str, float]] = []
        for alpha in (0.0, 0.5, 1.0):
            source = math.sqrt(1.0 - alpha) * q_parallel + math.sqrt(alpha) * q_perpendicular
            vector = embedded_source(source, points, config)
            right_hand_side = linearization.vjp_theta(vector)
            solve = conjugate_gradient(
                eliminator.normal_operator,
                right_hand_side,
                float(config["gamma"]["cg_tolerance"]),
                int(config["gamma"]["cg_max_iterations"]),
            )
            matrix_free_value = vector - linearization.jvp_theta(solve.solution)
            explicit_value = explicit_operator @ vector
            eta = float((torch.dot(vector, matrix_free_value) / torch.dot(vector, vector)).item())
            operator_relative_error = float(
                (
                    torch.linalg.vector_norm(matrix_free_value - explicit_value)
                    / (torch.linalg.vector_norm(explicit_value) + torch.finfo(vector.dtype).eps)
                ).item()
            )
            rows.append(
                {
                    "alpha": alpha,
                    "eta": eta,
                    "cg_converged": solve.converged,
                    "cg_relative_residual": solve.relative_residual,
                    "cg_iterations": solve.iterations,
                    "explicit_mf_relative_error": operator_relative_error,
                }
            )
        result.append({"gamma_alpha": float(gamma_alpha), "gamma": gamma, "values": rows})
    return result, lambda_max


def select_nominal_gamma(
    sweeps: dict[int, list[dict[str, Any]]], config: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    grid = [float(value) for value in config["gamma"]["alpha_grid"]]
    cg_gate = float(config["gamma"]["cg_acceptance"])
    comparison_gate = float(config["gamma"]["explicit_mf_relative_tolerance"])
    plateau_gate = float(config["gamma"]["plateau_relative_tolerance"])
    eligible: list[bool] = []
    median_vectors: list[torch.Tensor] = []
    for index, _ in enumerate(grid):
        rows = [sweeps[seed][index]["values"] for seed in sorted(sweeps)]
        eligible.append(
            all(
                value["cg_converged"]
                and value["cg_relative_residual"] <= cg_gate
                and value["explicit_mf_relative_error"] < comparison_gate
                for seed_rows in rows
                for value in seed_rows
            )
        )
        median_vectors.append(
            torch.tensor(
                [
                    torch.median(
                        torch.tensor(
                            [seed_rows[alpha_index]["eta"] for seed_rows in rows],
                            dtype=torch.float64,
                        )
                    ).item()
                    for alpha_index in range(3)
                ],
                dtype=torch.float64,
            )
        )
    adjacent_changes: list[float] = []
    for index in range(len(grid) - 1):
        denominator = torch.linalg.vector_norm(median_vectors[index]) + torch.finfo(torch.float64).eps
        adjacent_changes.append(
            float((torch.linalg.vector_norm(median_vectors[index + 1] - median_vectors[index]) / denominator).item())
        )
    candidates = [
        index
        for index, change in enumerate(adjacent_changes)
        if eligible[index] and eligible[index + 1] and change <= plateau_gate
    ]
    if not candidates:
        raise RuntimeError(
            f"no eligible adjacent gamma plateau pair; eligible={eligible}, changes={adjacent_changes}"
        )
    selected_index = candidates[0]
    return grid[selected_index], {
        "eligible": eligible,
        "median_eta_vectors_alpha_0_0.5_1": [vector.tolist() for vector in median_vectors],
        "adjacent_relative_changes": adjacent_changes,
        "selected_lower_index": selected_index,
    }


def run_controlled_development(
    config_path: str | Path, output_root: str | Path, repo_root: str | Path
) -> dict[str, Any]:
    started = time.perf_counter()
    config = load_config(config_path)
    if config.get("phase") != "P2_DEVELOPMENT":
        raise ValueError("development config phase must be P2_DEVELOPMENT")
    if config["development_seeds"] != [0, 1, 2]:
        raise ValueError("development seeds must be exactly [0, 1, 2]")
    points = make_diagnostic_points(config)
    library = fourier_library(config, points)
    checkpoints: dict[int, TrainedCheckpoint] = {}
    overlaps: dict[int, dict[str, float]] = {}
    ranks: dict[int, int] = {}
    diagnostic_stationarity: dict[int, float] = {}
    for seed in config["development_seeds"]:
        checkpoint = train_checkpoint(config, int(seed))
        checkpoints[int(seed)] = checkpoint
        jacobian = torch.func.jacrev(lambda state: base_residual(state, points, config))(
            checkpoint.theta
        )
        diagnostic_stationarity[int(seed)] = _stationarity(
            jacobian, base_residual(checkpoint.theta, points, config)
        )
        overlaps[int(seed)], ranks[int(seed)] = tangent_overlaps(jacobian, library, points, config)
    parallel, perpendicular, medians, inner_product = select_directions(
        overlaps,
        library,
        float(config["fourier_library"]["orthogonality_tolerance"]),
    )
    sweeps: dict[int, list[dict[str, Any]]] = {}
    lambda_max: dict[int, float] = {}
    for seed, checkpoint in checkpoints.items():
        sweeps[seed], lambda_max[seed] = _gamma_sweep_for_seed(
            checkpoint.theta, points, library[parallel], library[perpendicular], config
        )
    nominal_gamma_alpha, selector_evidence = select_nominal_gamma(sweeps, config)

    provenance = environment_provenance(repo_root, config["dtype"], config["device"])
    digest = config_hash(config)
    run_id = make_run_id("P2-development", 0, digest, provenance["timestamp"])
    result = {
        "schema_version": 1,
        "phase": "P2_DEVELOPMENT",
        "run_id": run_id,
        "status": "PASS",
        "config_hash": digest,
        "development_seeds": config["development_seeds"],
        "checkpoints": {
            str(seed): {
                "training_loss": checkpoint.training_loss,
                "normalized_gradient": checkpoint.normalized_gradient,
                "diagnostic_theta_stationarity": diagnostic_stationarity[seed],
                "state_rmse_validation_only": checkpoint.state_rmse,
                "training_seconds": checkpoint.elapsed_seconds,
                "stop_reason": checkpoint.stop_reason,
                "lbfgs_closure_calls": checkpoint.lbfgs_closure_calls,
                "svd_rank": ranks[seed],
            }
            for seed, checkpoint in checkpoints.items()
        },
        "candidate_overlaps": {str(seed): value for seed, value in overlaps.items()},
        "median_candidate_overlaps": medians,
        "selected": {
            "q_parallel": parallel,
            "q_perpendicular": perpendicular,
            "empirical_inner_product": inner_product,
            "q_parallel_median_tangent_overlap": medians[parallel],
            "q_perpendicular_median_tangent_overlap": medians[perpendicular],
            "nominal_gamma_alpha": nominal_gamma_alpha,
        },
        "gamma_sweeps": {str(seed): value for seed, value in sweeps.items()},
        "lambda_max_by_seed": {str(seed): value for seed, value in lambda_max.items()},
        "gamma_selector_evidence": selector_evidence,
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "development.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        stream.write("\n")

    locked_config = {
        "schema_version": 1,
        "phase": "P2_CONFIRMATION",
        "contract_id": "SAEPS-JCP-EXEC-v2.0",
        "development_config_hash": digest,
        "development_run_id": run_id,
        "development_seeds": config["development_seeds"],
        "confirmation_seeds": config["confirmation_seeds"],
        "dtype": config["dtype"],
        "device": config["device"],
        "pde": config["pde"],
        "network": config["network"],
        "training": config["training"],
        "diagnostic": config["diagnostic"],
        "fourier_library": config["fourier_library"],
        "selected_sources": {
            "q_parallel": parallel,
            "q_perpendicular": perpendicular,
            "normalization": "unit discrete L2 norm on locked diagnostic PDE grid",
            "empirical_inner_product": inner_product,
        },
        "alpha_values": config["alpha_values"],
        "gamma": {**config["gamma"], "nominal_alpha": nominal_gamma_alpha},
        "confirmation_rules": config["confirmation_rules"],
    }
    locked_path = Path(repo_root) / "configs" / "locked" / "controlled_geometry.yaml"
    locked_path.parent.mkdir(parents=True, exist_ok=True)
    with locked_path.open("w", encoding="utf-8", newline="\n") as stream:
        yaml.safe_dump(locked_config, stream, sort_keys=False, allow_unicode=True)
    locked_bytes = locked_path.read_bytes()
    locked_hash = hashlib.sha256(locked_bytes).hexdigest()
    locked_path.with_suffix(".sha256").write_text(
        f"{locked_hash}  controlled_geometry.yaml\n", encoding="utf-8", newline="\n"
    )
    result["locked_config_path"] = str(locked_path.relative_to(repo_root))
    result["locked_config_sha256"] = locked_hash
    with (destination / "lock_manifest.json").open("w", encoding="utf-8") as stream:
        json.dump(
            {
                "locked_config_path": result["locked_config_path"],
                "locked_config_sha256": locked_hash,
                "development_run_id": run_id,
            },
            stream,
            indent=2,
            sort_keys=True,
        )
        stream.write("\n")
    return result


def verify_phase_lock(repo_root: str | Path) -> tuple[dict[str, Any], str, str]:
    root = Path(repo_root)
    locked_path = root / "configs" / "locked" / "controlled_geometry.yaml"
    hash_path = locked_path.with_suffix(".sha256")
    if not locked_path.is_file() or not hash_path.is_file():
        raise RuntimeError("P2 controlled-geometry lock files are missing")
    actual_hash = hashlib.sha256(locked_path.read_bytes()).hexdigest()
    declared_hash = hash_path.read_text(encoding="utf-8").split()[0]
    if actual_hash != declared_hash:
        raise RuntimeError("P2 controlled-geometry config hash mismatch")
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", str(locked_path), str(hash_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(f"P2 lock files are not clean and committed: {status}")
    commit = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%H", "--", str(locked_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not commit:
        raise RuntimeError("P2 lock config has no Git commit")
    config = load_config(locked_path)
    return config, actual_hash, commit


def _controlled_residual_function(
    points: PointSet, source: torch.Tensor, config: dict[str, Any]
) -> Any:
    pde_count = points.pde_x.numel()
    pde_scale = math.sqrt(float(config["training"]["loss_weights"]["pde"]))
    lambda_star = float(config["pde"]["lambda_star"])

    def residual(theta: torch.Tensor, log_lambda: torch.Tensor) -> torch.Tensor:
        value = base_residual(theta, points, config).clone()
        value[:pde_count] = value[:pde_count] - pde_scale * (
            torch.exp(log_lambda[0]) - lambda_star
        ) * source
        return value

    return residual


def _stationarity(jacobian: torch.Tensor, residual: torch.Tensor) -> float:
    numerator = torch.linalg.vector_norm(jacobian.T @ residual)
    denominator = (
        torch.linalg.matrix_norm(jacobian) * torch.linalg.vector_norm(residual)
        + torch.finfo(residual.dtype).eps
    )
    return float((numerator / denominator).item())


def _residual_summary(residual: torch.Tensor, points: PointSet) -> dict[str, float]:
    counts = [
        points.pde_x.numel(),
        points.data_x.numel(),
        points.initial_x.numel(),
        2 * points.boundary_t.numel(),
    ]
    names = ["pde", "observation", "initial", "boundary"]
    summary: dict[str, float] = {}
    offset = 0
    for name, count in zip(names, counts, strict=True):
        block = residual[offset : offset + count]
        summary[f"{name}_weighted_rms"] = float(torch.sqrt(torch.mean(block.square())).item())
        offset += count
    summary["total_weighted_rms"] = float(torch.sqrt(torch.mean(residual.square())).item())
    return summary


def _rankdata(values: list[float]) -> torch.Tensor:
    result = torch.empty(len(values), dtype=torch.float64)
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average_rank = 0.5 * (start + 1 + end)
        for position in range(start, end):
            result[ordered[position]] = average_rank
        start = end
    return result


def spearman(values_x: list[float], values_y: list[float]) -> float:
    if len(values_x) != len(values_y) or len(values_x) < 2:
        raise ValueError("Spearman inputs must have equal length >= 2")
    rank_x = _rankdata(values_x)
    rank_y = _rankdata(values_y)
    centered_x = rank_x - rank_x.mean()
    centered_y = rank_y - rank_y.mean()
    denominator = torch.linalg.vector_norm(centered_x) * torch.linalg.vector_norm(centered_y)
    if float(denominator.item()) == 0.0:
        return float("nan")
    return float((torch.dot(centered_x, centered_y) / denominator).item())


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    tensor = torch.tensor(values, dtype=torch.float64)
    quantiles = torch.quantile(tensor, torch.tensor([0.25, 0.5, 0.75], dtype=torch.float64))
    return tuple(float(value.item()) for value in quantiles)  # type: ignore[return-value]


def _write_controlled_svg(
    path: Path, alphas: list[float], seed_values: dict[int, list[float]]
) -> None:
    width, height = 760, 520
    left, right, top, bottom = 85, 30, 40, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    all_values = [value for values in seed_values.values() for value in values]
    y_min = min(0.0, min(all_values, default=0.0))
    y_max = max(1.0, max(all_values, default=1.0))

    def px(alpha: float) -> float:
        return left + alpha * plot_width

    def py(value: float) -> float:
        return top + (y_max - value) / max(y_max - y_min, 1.0e-12) * plot_height

    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="black"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="black"/>',
    ]
    for tick in alphas:
        lines.append(
            f'<text x="{px(tick):.2f}" y="{top + plot_height + 28}" text-anchor="middle" font-size="14">{tick:g}</text>'
        )
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        lines.append(
            f'<text x="{left - 12}" y="{py(tick) + 5:.2f}" text-anchor="end" font-size="14">{tick:g}</text>'
        )
        lines.append(
            f'<line x1="{left}" y1="{py(tick):.2f}" x2="{left + plot_width}" y2="{py(tick):.2f}" stroke="#dddddd"/>'
        )
    for index, (seed, values) in enumerate(sorted(seed_values.items())):
        points = " ".join(f"{px(alpha):.2f},{py(value):.2f}" for alpha, value in zip(alphas, values, strict=True))
        color = colors[index % len(colors)]
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.65"/>'
        )
        for alpha, value in zip(alphas, values, strict=True):
            lines.append(f'<circle cx="{px(alpha):.2f}" cy="{py(value):.2f}" r="2.5" fill="{color}"/>')
    if seed_values:
        medians = [
            float(torch.median(torch.tensor([values[index] for values in seed_values.values()], dtype=torch.float64)).item())
            for index in range(len(alphas))
        ]
        points = " ".join(f"{px(alpha):.2f},{py(value):.2f}" for alpha, value in zip(alphas, medians, strict=True))
        lines.append(f'<polyline points="{points}" fill="none" stroke="black" stroke-width="4"/>')
    lines.extend(
        [
            f'<text x="{left + plot_width / 2:.2f}" y="{height - 20}" text-anchor="middle" font-size="17">transverse fraction alpha</text>',
            f'<text x="22" y="{top + plot_height / 2:.2f}" text-anchor="middle" font-size="17" transform="rotate(-90 22 {top + plot_height / 2:.2f})">retained sensitivity eta</text>',
            '<text x="380" y="25" text-anchor="middle" font-size="18" font-weight="bold">Controlled tangent geometry</text>',
            '</svg>',
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_controlled_confirmation(output_root: str | Path, repo_root: str | Path) -> dict[str, Any]:
    started = time.perf_counter()
    config, lock_hash, lock_commit = verify_phase_lock(repo_root)
    expected_seeds = list(range(10, 20))
    if config["confirmation_seeds"] != expected_seeds:
        raise ValueError("P2 confirmation seeds must be exactly [10, ..., 19]")
    alphas = [float(value) for value in config["alpha_values"]]
    if alphas != [0.0, 0.25, 0.5, 0.75, 1.0]:
        raise ValueError("P2 alpha values do not match the v2.0 contract")
    digest = config_hash(config)
    provenance = environment_provenance(repo_root, config["dtype"], config["device"])
    aggregate_run_id = make_run_id("P2-confirmation", 10, digest, provenance["timestamp"])
    destination = Path(output_root) / aggregate_run_id
    records_dir = destination / "records"
    records_dir.mkdir(parents=True, exist_ok=False)
    points = make_diagnostic_points(config)
    library = fourier_library(config, points)
    parallel = library[config["selected_sources"]["q_parallel"]]
    perpendicular = library[config["selected_sources"]["q_perpendicular"]]
    log_lambda = torch.tensor([math.log(float(config["pde"]["lambda_star"]))], dtype=getattr(torch, config["dtype"]))
    records: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []

    for seed in expected_seeds:
        checkpoint = train_checkpoint(config, seed)
        base = base_residual(checkpoint.theta, points, config)
        jacobian_theta = torch.func.jacrev(lambda state: base_residual(state, points, config))(
            checkpoint.theta
        )
        theta_stationarity = _stationarity(jacobian_theta, base)
        checkpoint_valid = (
            checkpoint.training_loss <= float(config["confirmation_rules"]["checkpoint_training_loss_max"])
            and theta_stationarity
            <= float(config["confirmation_rules"]["checkpoint_theta_stationarity_max"])
        )
        lambda_max = float(torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item())
        gamma_alpha = float(config["gamma"]["nominal_alpha"])
        gamma = gamma_alpha * lambda_max
        for alpha in alphas:
            source = math.sqrt(1.0 - alpha) * parallel + math.sqrt(alpha) * perpendicular
            run_started = time.perf_counter()
            residual_function = _controlled_residual_function(points, source, config)
            status = "PASS" if checkpoint_valid else "CHECKPOINT_INVALID"
            failure_reason = None if checkpoint_valid else "locked checkpoint validity threshold failed"
            metrics: dict[str, Any] = {
                "Fraw": None,
                "Fse": None,
                "gse": None,
                "eta": None,
                "CG_iterations": None,
                "CG_relative_residual": None,
                "JVP_count": 0,
                "VJP_count": 0,
                "lambda_stationarity": None,
                "explicit_mf_relative_error": None,
            }
            if checkpoint_valid:
                try:
                    linearization = ResidualLinearization(
                        residual_function, checkpoint.theta, log_lambda
                    )
                    matrix_free = compute_matrix_free_saeps(
                        linearization,
                        gamma,
                        float(config["gamma"]["cg_tolerance"]),
                        int(config["gamma"]["cg_max_iterations"]),
                    )
                    explicit_operator = explicit_tikhonov_operator(jacobian_theta, gamma)
                    explicit_curvature = (
                        matrix_free.jacobian_parameter.T
                        @ explicit_operator
                        @ matrix_free.jacobian_parameter
                    )
                    comparison = float(
                        (
                            torch.linalg.matrix_norm(
                                matrix_free.eliminated_curvature - explicit_curvature
                            )
                            / (
                                torch.linalg.matrix_norm(explicit_curvature)
                                + torch.finfo(checkpoint.theta.dtype).eps
                            )
                        ).item()
                    )
                    max_cg = max(solve.relative_residual for solve in matrix_free.solves)
                    if max_cg > float(config["gamma"]["cg_acceptance"]):
                        status = "SOLVER_FAILURE"
                        failure_reason = f"CG relative residual {max_cg} exceeded locked threshold"
                    elif comparison >= float(config["gamma"]["explicit_mf_relative_tolerance"]):
                        status = "NUMERICAL_FAILURE"
                        failure_reason = f"explicit/MF error {comparison} exceeded locked threshold"
                    metrics = {
                        "Fraw": matrix_free.raw_curvature.tolist(),
                        "Fse": matrix_free.eliminated_curvature.tolist(),
                        "gse": matrix_free.eliminated_score.tolist(),
                        "eta": float(matrix_free.eta[0].item()),
                        "CG_iterations": [solve.iterations for solve in matrix_free.solves],
                        "CG_relative_residual": [solve.relative_residual for solve in matrix_free.solves],
                        "JVP_count": linearization.operation_counts.get("jvp_theta", 0)
                        + linearization.operation_counts.get("jvp_parameter", 0),
                        "VJP_count": linearization.operation_counts.get("vjp_theta", 0)
                        + linearization.operation_counts.get("vjp_parameter", 0),
                        "lambda_stationarity": _stationarity(
                            matrix_free.jacobian_parameter, matrix_free.residual
                        ),
                        "explicit_mf_relative_error": comparison,
                    }
                except Exception as error:
                    status = "SOLVER_FAILURE"
                    failure_reason = f"{type(error).__name__}: {error}"
            if status not in FINAL_STATUSES:
                raise RuntimeError(f"illegal final status: {status}")
            run_id = f"{aggregate_run_id}-seed{seed}-alpha{alpha:.2f}"
            record = {
                "schema_version": 1,
                "run_id": run_id,
                "timestamp": provenance["timestamp"],
                "git_commit": provenance["git_commit"],
                "config_path": "configs/locked/controlled_geometry.yaml",
                "config_hash": digest,
                "phase_lock_sha256": lock_hash,
                "phase_lock_commit": lock_commit,
                "seed": seed,
                "split": "confirmation",
                "benchmark": "controlled_manufactured_parabolic",
                "alpha": alpha,
                "source_parallel": config["selected_sources"]["q_parallel"],
                "source_perpendicular": config["selected_sources"]["q_perpendicular"],
                "architecture": config["network"]["architecture"],
                "dtype": config["dtype"],
                "hardware": provenance["processor"] or provenance["machine"],
                "parameter_coordinates": ["log_lambda"],
                "training_points": {
                    key: config["training"][key]
                    for key in ["pde_points", "data_points", "initial_points", "boundary_points_per_side"]
                },
                "diagnostic_points": config["diagnostic"],
                "sensor_layout": "seeded_uniform_training_and_locked_tensor_grid_diagnostic",
                "loss_weights": config["training"]["loss_weights"],
                "optimizer": "Adam_then_LBFGS_strong_wolfe",
                "learning_rate": config["training"]["adam_learning_rate"],
                "training_stop_reason": checkpoint.stop_reason,
                "checkpoint_epoch": checkpoint.adam_epochs,
                "lbfgs_closure_calls": checkpoint.lbfgs_closure_calls,
                "theta_stationarity": theta_stationarity,
                "lambda_stationarity": metrics["lambda_stationarity"],
                "residuals": _residual_summary(base, points),
                "state_error": {"value": checkpoint.state_rmse, "validation_only": True},
                "parameter_error": {"value": 0.0, "validation_only": True},
                "gamma_alpha": gamma_alpha,
                "gamma": gamma,
                "CG_iterations": metrics["CG_iterations"],
                "CG_relative_residual": metrics["CG_relative_residual"],
                "JVP_count": metrics["JVP_count"],
                "VJP_count": metrics["VJP_count"],
                "Fraw": metrics["Fraw"],
                "Fse": metrics["Fse"],
                "gse": metrics["gse"],
                "eta": metrics["eta"],
                "explicit_mf_relative_error": metrics["explicit_mf_relative_error"],
                "profile_points": None,
                "profile_curvature": None,
                "profile_fit_quality": None,
                "E_saeps": None,
                "E_raw": None,
                "D_paired": None,
                "training_time": checkpoint.elapsed_seconds,
                "saeps_time": time.perf_counter() - run_started,
                "frozen_profile_time": None,
                "reoptimized_profile_time": None,
                "peak_memory": None,
                "status": status,
                "failure_reason": failure_reason,
            }
            record_path = records_dir / f"seed_{seed}_alpha_{alpha:.2f}.json"
            with record_path.open("w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
                stream.write("\n")
            record_hash = hashlib.sha256(record_path.read_bytes()).hexdigest()
            manifest_rows.append(
                {
                    "run_id": run_id,
                    "seed": seed,
                    "alpha": alpha,
                    "status": status,
                    "path": str(record_path.relative_to(destination)),
                    "sha256": record_hash,
                }
            )
            records.append(record)

    status_counts = {status: sum(record["status"] == status for record in records) for status in sorted(FINAL_STATUSES)}
    seed_values: dict[int, list[float]] = {}
    per_seed: dict[str, Any] = {}
    for seed in expected_seeds:
        selected = [record for record in records if record["seed"] == seed]
        if all(record["status"] == "PASS" and record["eta"] is not None for record in selected):
            eta_values = [float(record["eta"]) for record in selected]
            correlation = spearman(alphas, eta_values)
            monotonic = all(
                eta_values[index + 1]
                >= eta_values[index] - float(config["confirmation_rules"]["monotonic_absolute_tolerance"])
                for index in range(len(eta_values) - 1)
            )
            seed_values[seed] = eta_values
            per_seed[str(seed)] = {
                "eta": eta_values,
                "spearman": correlation,
                "monotonic": monotonic,
                "status": "VALID",
            }
        else:
            per_seed[str(seed)] = {
                "eta": [record["eta"] for record in selected],
                "spearman": None,
                "monotonic": False,
                "status": "INVALID",
            }
    valid_correlations = [value["spearman"] for value in per_seed.values() if value["spearman"] is not None]
    valid_seed_count = len(valid_correlations)
    monotonic_count = sum(bool(value["monotonic"]) for value in per_seed.values())
    if valid_correlations:
        rho_q1, rho_median, rho_q3 = _quantiles([float(value) for value in valid_correlations])
    else:
        rho_q1 = rho_median = rho_q3 = None
    scientific_pass = (
        valid_seed_count == len(expected_seeds)
        and rho_median is not None
        and rho_median >= float(config["confirmation_rules"]["spearman_median_gate"])
        and monotonic_count >= int(config["confirmation_rules"]["monotonic_seed_gate"])
    )
    alpha_summary: dict[str, Any] = {}
    for index, alpha in enumerate(alphas):
        values = [seed_values[seed][index] for seed in sorted(seed_values)]
        if values:
            q1, median, q3 = _quantiles(values)
            alpha_summary[str(alpha)] = {"all_valid_seed_values": values, "q1": q1, "median": median, "q3": q3}
        else:
            alpha_summary[str(alpha)] = {"all_valid_seed_values": [], "q1": None, "median": None, "q3": None}
    summary = {
        "schema_version": 1,
        "phase": "P2_CONFIRMATION",
        "run_id": aggregate_run_id,
        "engineering_gate": "PASSED" if len(records) == 50 else "FAILED",
        "scientific_gate_sg1": "PASS" if scientific_pass else "FAIL",
        "planned_evaluations": 50,
        "completed_evaluations": len(records),
        "status_counts": status_counts,
        "planned_seeds": 10,
        "valid_seeds": valid_seed_count,
        "invalid_seeds": len(expected_seeds) - valid_seed_count,
        "alphas": alphas,
        "per_seed": per_seed,
        "spearman": {"q1": rho_q1, "median": rho_median, "q3": rho_q3},
        "monotonic_seed_count": monotonic_count,
        "alpha_summary": alpha_summary,
        "phase_lock_sha256": lock_hash,
        "phase_lock_commit": lock_commit,
        "config_hash": digest,
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    with (destination / "manifest.json").open("w", encoding="utf-8") as stream:
        json.dump({"schema_version": 1, "planned": 50, "records": manifest_rows}, stream, indent=2, sort_keys=True)
        stream.write("\n")
    with (destination / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        stream.write("\n")
    _write_controlled_svg(destination / "figure2_controlled_geometry.svg", alphas, seed_values)
    return summary
