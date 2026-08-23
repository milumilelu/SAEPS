"""One-shot V5 engineering reconstruction of fixed historical source seeds."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from dataclasses import fields
from pathlib import Path
from typing import Any

import torch

from saeps.config import config_hash, load_config
from saeps.controlled import base_residual, make_diagnostic_points, train_checkpoint
from saeps.io_utils import write_json_atomic
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v35.engineering import center_with_registered_rescue
from saeps.v36.pipeline import _center_specs
from saeps.v41.pipeline import _protected_v36
from saeps.v43.center import allen_center_candidates
from saeps.v43.pipeline import _protected_config
from saeps.v5.governance import RECONSTRUCTED_ROLE, sha256_file


def _tensor_digest(named_tensors: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(named_tensors.items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(list(value.shape)).encode("ascii"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def _point_tensors(points: Any) -> dict[str, torch.Tensor]:
    return {
        field.name: getattr(points, field.name).detach().cpu().clone()
        for field in fields(points)
        if isinstance(getattr(points, field.name), torch.Tensor)
    }


def _git_commit(root: Path) -> str:
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5 reconstruction requires a clean committed executable")
    commit = provenance["git_commit"]
    if not isinstance(commit, str):
        raise RuntimeError("V5 reconstruction requires a git commit")
    return commit


def _historical_evidence(root: Path, benchmark: str, seed: int) -> tuple[str, str]:
    if benchmark == "burgers":
        relative = f"outputs/runs/v4_1_post_confirmation_development/engineering_integration/records/seed_{seed}.json"
    elif seed <= 72:
        relative = f"outputs/runs/v4_3_allen_cahn_development/architecture_w8/seed_{seed}/result.json"
    else:
        relative = f"outputs/runs/v4_3_allen_cahn_development/heldout/seed_{seed}/result.json"
    path = root / relative
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("binding_valid") is not True:
        raise RuntimeError(f"fixed historical source seed was not binding-valid: {seed}")
    return relative, sha256_file(path)


def _save_checkpoint(
    *,
    root: Path,
    destination: Path,
    source_protocol: str,
    source_seed: int,
    benchmark: str,
    theta: torch.Tensor,
    coordinate: torch.Tensor,
    point_tensors: dict[str, torch.Tensor],
    model_metadata: dict[str, Any],
    reconstruction_status: str,
    center_record: dict[str, Any] | None,
    center_stationarity: dict[str, float] | None,
    training_record: dict[str, Any],
    source_hashes: dict[str, str],
    historical_evidence: dict[str, str] | None,
    elapsed_seconds: float,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    artifact = destination / "model_state.pt"
    payload = {
        "theta": theta.detach().cpu().clone(),
        "coordinate": coordinate.detach().cpu().clone(),
        "source_seed": source_seed,
        "benchmark": benchmark,
        "points": point_tensors,
        "model_metadata": model_metadata,
    }
    torch.save(payload, artifact)
    model_hash = sha256_file(artifact)
    diagnostic_hash = _tensor_digest(point_tensors)
    source_path = root / source_protocol
    manifest = {
        "schema_version": 1,
        "phase": "V5_ENGINEERING_RECONSTRUCTION",
        "artifact_role": RECONSTRUCTED_ROLE,
        "source_protocol": source_protocol,
        "source_config_hash": sha256_file(source_path),
        "source_seed": source_seed,
        "reconstruction_commit": provenance["git_commit"],
        "model_state_path": artifact.relative_to(root).as_posix(),
        "model_state_hash": model_hash,
        "diagnostic_set_hash": diagnostic_hash,
        "dtype": str(theta.dtype).removeprefix("torch."),
        "device": str(theta.device),
        "environment": provenance,
        "status": reconstruction_status,
        "attempt": 1,
        "retry_permitted": False,
        "replacement_permitted": False,
        "historical_tensor_identity_claimed": False,
    }
    write_json_atomic(destination / "checkpoint_manifest.json", manifest)
    record = {
        "schema_version": 1,
        "phase": "V5_ENGINEERING_RECONSTRUCTION",
        "role": "engineering_reconstruction",
        "benchmark": benchmark,
        "seed": source_seed,
        "status": reconstruction_status,
        "binding_valid": reconstruction_status == "PASS",
        "failure_stage": None if reconstruction_status == "PASS" else "center",
        "failure_reason": None if reconstruction_status == "PASS" else "fixed reconstructed center gate failed",
        "config_hash": config_hash(load_config(root / "configs/v5/reconstruction.yaml")),
        "source_hashes": source_hashes,
        "provenance": provenance,
        "artifact_manifest_path": (destination / "checkpoint_manifest.json").relative_to(root).as_posix(),
        "model_state_hash": model_hash,
        "diagnostic_set_hash": diagnostic_hash,
        "training": training_record,
        "center": center_record,
        "center_stationarity": center_stationarity,
        "historical_binding_evidence": historical_evidence,
        "elapsed_seconds": elapsed_seconds,
    }
    write_json_atomic(destination / "result.json", record)
    return record


def _reconstruct_scalar(
    root: Path,
    benchmark: str,
    seed: int,
    destination: Path,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    if benchmark == "burgers":
        source_protocol = "configs/v4_1/post_confirmation_development.yaml"
        development = load_config(root / source_protocol)
        curvature = _protected_v36(root, development)
        scalar_locked = load_config(root / curvature["source_files"]["scalar_config"]["path"])
        runtime = _runtime_config(scalar_locked)
        benchmark_name = "Burgers"
        center_kind = "burgers_registered_rescue"
    else:
        source_protocol = "configs/v4_3/allen_cahn_development.yaml"
        development = load_config(root / source_protocol)
        sources = development["protected_sources"]
        runtime = copy.deepcopy(_protected_config(root, sources["scalar_runtime"]))
        curvature = _protected_config(root, sources["curvature_protocol"])
        runtime["network"]["hidden_width"] = int(development["architecture_engineering"]["selected_width"])
        benchmark_name = "Allen-Cahn"
        center_kind = "allen_deterministic_candidates"
    truth = solve_truth(runtime, benchmark_name)
    checkpoint, points = train_scalar_checkpoint(runtime, benchmark_name, seed, truth)
    residual_function = lambda state, coordinate: scalar_residual(
        state, coordinate, benchmark_name, points, truth, runtime
    )
    parameter = checkpoint.log_parameter.detach().clone()
    objective = _mean_residual_objective(
        residual_function, parameter, checkpoint.theta, 0.0, False
    )
    local, enhanced = _center_specs(curvature)
    if benchmark == "burgers":
        selected, center = center_with_registered_rescue(
            objective, checkpoint.theta, local, enhanced
        )
        selected_diagnostics = None
        if selected is not None:
            selected_diagnostics = (
                center["baseline"]
                if center["selected_method"] == "baseline_v3_4_exact_trust"
                else center["enhanced"]
            )
            gradient = float(selected_diagnostics["final"]["normalized_objective_gradient"])
    else:
        selected, center = allen_center_candidates(
            lambda state: residual_function(state, parameter),
            objective,
            checkpoint.theta,
            seed,
            local,
            development["center_engineering"],
        )
        selected_diagnostics = None
        if selected is not None:
            selected_diagnostics = center["candidates"][int(center["selected_candidate"])]
            gradient = float(
                selected_diagnostics["final_exact_diagnostics"]["normalized_objective_gradient"]
            )
    stationarity = None
    center_pass = False
    if selected is not None:
        residual = residual_function(selected, parameter)
        jacobian_theta = torch.func.jacrev(lambda state: residual_function(state, parameter))(selected)
        jacobian_parameter = torch.func.jacrev(lambda value: residual_function(selected, value))(parameter)
        s_theta = _stationarity(jacobian_theta, residual)
        s_lambda = _stationarity(jacobian_parameter, residual)
        stationarity = {"G_theta": gradient, "S_theta": s_theta, "S_lambda": s_lambda}
        center_pass = (
            gradient < float(curvature["center"]["required_objective_gradient_tolerance"])
            and s_theta < float(curvature["center"]["residual_stationarity_tolerance"])
        )
    saved_theta = selected if selected is not None else checkpoint.theta
    historical_path, historical_hash = _historical_evidence(root, benchmark, seed)
    return _save_checkpoint(
        root=root,
        destination=destination,
        source_protocol=source_protocol,
        source_seed=seed,
        benchmark=benchmark_name,
        theta=saved_theta,
        coordinate=parameter,
        point_tensors=_point_tensors(points),
        model_metadata={
            "hidden_width": int(runtime["network"]["hidden_width"]),
            "center_method_family": center_kind,
            "selected_center_available": selected is not None,
        },
        reconstruction_status="PASS" if center_pass else "CHECKPOINT_INVALID",
        center_record=center,
        center_stationarity=stationarity,
        training_record={
            "loss_mean": checkpoint.training_loss,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "parameter_relative_error_validation_only": checkpoint.parameter_relative_error,
            "stop_reason": checkpoint.stop_reason,
            "seconds": checkpoint.elapsed_seconds,
        },
        source_hashes={
            source_protocol: sha256_file(root / source_protocol),
            "runtime_config": hashlib.sha256(json.dumps(runtime, sort_keys=True, default=str).encode()).hexdigest(),
        },
        historical_evidence={"path": historical_path, "sha256": historical_hash},
        elapsed_seconds=time.perf_counter() - started,
        provenance=provenance,
    )


def _reconstruct_scalability_base(
    root: Path,
    seed: int,
    destination: Path,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    source_protocol = "configs/v4_7/scalability.yaml"
    specification = load_config(root / source_protocol)
    if seed != min(int(value) for value in specification["checkpoints"]):
        raise ValueError("V5 scalability base must use the minimum registered V4.7 checkpoint ID")
    runtime = load_config(root / specification["source_config"])
    runtime["network"]["hidden_width"] = int(specification["base_width"])
    runtime["network"]["architecture"] = "tanh_mlp_2x25x1"
    checkpoint = train_checkpoint(runtime, seed)
    points = make_diagnostic_points(runtime)
    residual = base_residual(checkpoint.theta, points, runtime)
    finite = bool(torch.all(torch.isfinite(checkpoint.theta)).item()) and bool(
        torch.all(torch.isfinite(residual)).item()
    )
    return _save_checkpoint(
        root=root,
        destination=destination,
        source_protocol=source_protocol,
        source_seed=seed,
        benchmark="controlled_parabolic_scalability_base",
        theta=checkpoint.theta,
        coordinate=torch.tensor([0.0], dtype=checkpoint.theta.dtype),
        point_tensors=_point_tensors(points),
        model_metadata={
            "hidden_width": int(specification["base_width"]),
            "deterministic_source_rule": "minimum_registered_v4_7_checkpoint_id",
        },
        reconstruction_status="PASS" if finite else "NUMERICAL_FAILURE",
        center_record=None,
        center_stationarity={"normalized_gradient_training": checkpoint.normalized_gradient},
        training_record={
            "loss_mean": checkpoint.training_loss,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "stop_reason": checkpoint.stop_reason,
            "seconds": checkpoint.elapsed_seconds,
        },
        source_hashes={
            source_protocol: sha256_file(root / source_protocol),
            specification["source_config"]: sha256_file(root / specification["source_config"]),
        },
        historical_evidence=None,
        elapsed_seconds=time.perf_counter() - started,
        provenance=provenance,
    )


def _load_frozen_specification(root: Path) -> dict[str, Any]:
    specification = load_config(root / "configs/v5/reconstruction.yaml")
    freeze_path = root / "configs/v5/RECONSTRUCTION_EXECUTABLE_FREEZE.json"
    if not freeze_path.is_file():
        raise RuntimeError("V5 reconstruction executable freeze is missing")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5 reconstruction freeze does not authorize execution")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5 reconstruction frozen file mismatch: {relative}")
    if specification["execution_authorized"] is not True:
        raise RuntimeError("V5 reconstruction is not authorized")
    return specification


def _clean_source_provenance(root: Path) -> dict[str, Any]:
    provenance = environment_provenance(root, "float64", "cpu")
    _git_commit(root)
    return provenance


def _reconstruct_registered(
    root: Path,
    specification: dict[str, Any],
    provenance: dict[str, Any],
    family: str,
    seed: int,
) -> dict[str, Any]:
    if family not in specification["sources"]:
        raise ValueError("unknown V5 reconstruction family")
    family_spec = specification["sources"][family]
    if seed not in [int(value) for value in family_spec["seeds"]]:
        raise ValueError("source seed is outside the fixed reconstruction registry")
    destination = root / specification["output_root"] / family / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("reconstruction source already has a terminal artifact; rerun forbidden")
    if family == "burgers":
        return _reconstruct_scalar(root, "burgers", seed, destination, provenance)
    if family == "allen_cahn":
        return _reconstruct_scalar(root, "allen_cahn", seed, destination, provenance)
    return _reconstruct_scalability_base(root, seed, destination, provenance)


def reconstruct_checkpoint(repo_root: str | Path, family: str, seed: int) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    specification = _load_frozen_specification(root)
    if family not in specification["sources"]:
        raise ValueError("unknown V5 reconstruction family")
    if seed not in [int(value) for value in specification["sources"][family]["seeds"]]:
        raise ValueError("source seed is outside the fixed reconstruction registry")
    provenance = _clean_source_provenance(root)
    return _reconstruct_registered(root, specification, provenance, family, seed)


def reconstruct_all_checkpoints(repo_root: str | Path) -> list[dict[str, Any]]:
    """Reconstruct the complete fixed registry from one clean source snapshot."""

    root = Path(repo_root).resolve()
    specification = _load_frozen_specification(root)
    provenance = _clean_source_provenance(root)
    planned = [
        (family, int(seed))
        for family, family_spec in specification["sources"].items()
        for seed in family_spec["seeds"]
    ]
    for family, seed in planned:
        destination = root / specification["output_root"] / family / f"seed_{seed}"
        if destination.exists():
            raise RuntimeError(
                f"reconstruction source already has a terminal artifact; batch start forbidden: {family}/{seed}"
            )
    return [
        _reconstruct_registered(root, specification, provenance, family, seed)
        for family, seed in planned
    ]
