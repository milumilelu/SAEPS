"""V5.4 real-residual-dimension matrix-free cost audit."""

from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.controlled import base_residual, fourier_library, make_diagnostic_points
from saeps.core import MatrixFreeEliminator
from saeps.io_utils import write_json_atomic
from saeps.provenance import environment_provenance
from saeps.v48.pipeline import _widen
from saeps.v5.governance import sha256_file, validate_checkpoint_manifest


STATE_COUNTS = [1001, 10001, 100001]
RESIDUAL_COUNTS = [213, 853, 3413]
REPEATS = [1, 2, 3]


def _verify(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    freeze = json.loads(
        (root / "configs/v5/RESIDUAL_SCALABILITY_EXECUTABLE_FREEZE.json").read_text(
            encoding="utf-8"
        )
    )
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5.4 executable is not authorized")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.4 frozen file mismatch: {relative}")
    return (
        load_config(root / "configs/v5/residual_scalability_execution.yaml"),
        load_config(root / "configs/v5/residual_scalability.yaml"),
    )


def _load_base(root: Path) -> tuple[torch.Tensor, dict[str, Any]]:
    manifest_path = root / "outputs/runs/v5/checkpoints/scalability_base/seed_120/checkpoint_manifest.json"
    manifest = validate_checkpoint_manifest(root, manifest_path)
    if manifest["status"] != "PASS" or int(manifest["source_seed"]) != 120:
        raise RuntimeError("V5.4 base reconstruction is not valid")
    payload = torch.load(root / manifest["model_state_path"], map_location="cpu", weights_only=True)
    return payload["theta"], manifest


def _runtime_for_condition(
    root: Path,
    execution: dict[str, Any],
    state_count: int,
    residual_count: int,
) -> dict[str, Any]:
    runtime = copy.deepcopy(load_config(root / "configs/locked/controlled_geometry.yaml"))
    width = int(execution["state_parameter_counts"][state_count]["target_width"])
    runtime["network"]["hidden_width"] = width
    runtime["network"]["architecture"] = f"tanh_mlp_2x{width}x1"
    construction = execution["residual_constructions"][residual_count]
    runtime["diagnostic"] = copy.deepcopy(construction)
    return runtime


def _condition(
    root: Path,
    execution: dict[str, Any],
    base_theta: torch.Tensor,
    manifest: dict[str, Any],
    provenance: dict[str, Any],
    state_count: int,
    residual_count: int,
) -> list[dict[str, Any]]:
    runtime = _runtime_for_condition(root, execution, state_count, residual_count)
    width = int(runtime["network"]["hidden_width"])
    theta = _widen(base_theta, 25, width, 120)
    if int(theta.numel()) != state_count:
        raise RuntimeError("V5.4 state count construction mismatch")
    points = make_diagnostic_points(runtime)
    actual_base = base_residual(theta, points, runtime)
    if int(actual_base.numel()) != residual_count:
        raise RuntimeError("V5.4 real residual construction count mismatch")
    library = fourier_library(runtime, points)
    source = library[runtime["selected_sources"]["q_parallel"]]
    pde_count = points.pde_x.numel()
    scale = math.sqrt(float(runtime["training"]["loss_weights"]["pde"]))
    parameter = torch.tensor([0.0], dtype=theta.dtype)

    def residual_function(state: torch.Tensor, coordinate: torch.Tensor) -> torch.Tensor:
        value = base_residual(state, points, runtime).clone()
        value[:pde_count] -= scale * coordinate[0] * source
        return value

    setup_started = time.perf_counter()
    setup_linearization = ResidualLinearization(residual_function, theta, parameter)
    parameter_column = torch.func.jacrev(lambda q: residual_function(theta, q))(parameter)[:, 0]
    vector = torch.randn(
        theta.numel(),
        dtype=theta.dtype,
        generator=torch.Generator().manual_seed(54_000 + state_count + residual_count),
    )
    vector /= torch.linalg.vector_norm(vector)
    for _ in range(int(execution["power_iterations"])):
        vector = setup_linearization.vjp_theta(setup_linearization.jvp_theta(vector))
        vector /= max(float(torch.linalg.vector_norm(vector).item()), 1.0e-30)
    normal_value = setup_linearization.vjp_theta(setup_linearization.jvp_theta(vector))
    lambda_estimate = float(torch.dot(vector, normal_value).item())
    gamma = float(execution["gamma_alpha"]) * max(lambda_estimate, 1.0e-12)
    setup_seconds = time.perf_counter() - setup_started
    rows = []
    for repeat in REPEATS:
        destination = (
            root
            / execution["output_root"]
            / f"n_{state_count}"
            / f"m_{residual_count}"
            / f"repeat_{repeat}"
        )
        if destination.exists():
            raise RuntimeError("V5.4 timing record already exists; rerun forbidden")
        destination.mkdir(parents=True, exist_ok=False)
        record: dict[str, Any] = {
            "schema_version": 1,
            "phase": "V5_4_RESIDUAL_SCALABILITY",
            "role": "cost_only_timing",
            "state_parameter_count": state_count,
            "residual_count": residual_count,
            "repeat": repeat,
            "status": "SOLVER_FAILURE",
            "binding_valid": False,
            "failure_stage": "solver",
            "failure_reason": None,
            "config_hash": config_hash(execution),
            "source_hashes": {
                "base_checkpoint_manifest": sha256_file(
                    root / "outputs/runs/v5/checkpoints/scalability_base/seed_120/checkpoint_manifest.json"
                ),
                "base_model_state": manifest["model_state_hash"],
                "runtime": sha256_file(root / "configs/locked/controlled_geometry.yaml"),
            },
            "provenance": provenance,
            "target_width": width,
            "real_residual_construction": True,
            "synthetic_residual_padding": False,
            "initial_guess": "zero",
            "gamma": gamma,
            "lambda_max_power_estimate": lambda_estimate,
            "power_iterations": int(execution["power_iterations"]),
            "shared_condition_setup_seconds": setup_seconds,
            "peak_memory_bytes": None,
            "peak_memory_unavailable_reason": execution["peak_memory_source"],
        }
        try:
            linearization = ResidualLinearization(residual_function, theta, parameter)
            before = dict(linearization.operation_counts)
            wall_started = time.perf_counter()
            solve_started = time.perf_counter()
            eliminator = MatrixFreeEliminator(
                linearization,
                gamma,
                float(execution["cg_tolerance"]),
                int(execution["cg_max_iterations"]),
            )
            applied = eliminator.apply(parameter_column)
            solve_seconds = time.perf_counter() - solve_started
            wall_seconds = time.perf_counter() - wall_started
            after = dict(linearization.operation_counts)
            relative_residual = float(applied.solve.relative_residual)
            passed = relative_residual <= float(execution["cg_acceptance"])
            record.update(
                {
                    "status": "PASS" if passed else "SOLVER_FAILURE",
                    "binding_valid": passed,
                    "failure_stage": None if passed else "solver",
                    "failure_reason": None
                    if passed
                    else "verified residual exceeds frozen acceptance",
                    "solve_seconds": solve_seconds,
                    "wall_seconds": wall_seconds,
                    "cg_iterations": int(applied.solve.iterations),
                    "verified_relative_residual": relative_residual,
                    "JVP_count": after.get("jvp_theta", 0) - before.get("jvp_theta", 0),
                    "VJP_count": after.get("vjp_theta", 0) - before.get("vjp_theta", 0),
                    "F_se_GN": float(torch.dot(parameter_column, applied.value).item()),
                }
            )
        except Exception as error:
            record["failure_reason"] = f"{type(error).__name__}: {error}"
        write_json_atomic(destination / "result.json", record)
        rows.append(record)
    return rows


def run_residual_scalability(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    execution, protocol = _verify(root)
    if protocol["total_timing_evaluations"] != 27:
        raise RuntimeError("V5.4 planned timing count changed")
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.4 requires a clean committed executable")
    base_theta, manifest = _load_base(root)
    for state_count in STATE_COUNTS:
        for residual_count in RESIDUAL_COUNTS:
            condition = root / execution["output_root"] / f"n_{state_count}" / f"m_{residual_count}"
            if condition.exists():
                raise RuntimeError("V5.4 has prior condition output; rerun forbidden")
    return [
        row
        for state_count in STATE_COUNTS
        for residual_count in RESIDUAL_COUNTS
        for row in _condition(
            root,
            execution,
            base_theta,
            manifest,
            provenance,
            state_count,
            residual_count,
        )
    ]
