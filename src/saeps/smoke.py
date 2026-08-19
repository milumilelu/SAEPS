"""Real tiny-PINN training and checkpoint round-trip for P0 acceptance."""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn

from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.logging_utils import configure_logger, log_event
from saeps.provenance import environment_provenance, make_run_id
from saeps.seed import set_deterministic_seed


@dataclass(frozen=True)
class SmokeSettings:
    seed: int
    hidden_width: int
    adam_steps: int
    learning_rate: float
    collocation_points: int
    initial_condition_weight: float
    max_state_rmse: float
    max_roundtrip_abs_error: float

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "SmokeSettings":
        settings = cls(
            seed=int(values["seed"]),
            hidden_width=int(values["hidden_width"]),
            adam_steps=int(values["adam_steps"]),
            learning_rate=float(values["learning_rate"]),
            collocation_points=int(values["collocation_points"]),
            initial_condition_weight=float(values["initial_condition_weight"]),
            max_state_rmse=float(values["max_state_rmse"]),
            max_roundtrip_abs_error=float(values["max_roundtrip_abs_error"]),
        )
        if settings.hidden_width < 1 or settings.adam_steps < 1:
            raise ValueError("hidden_width and adam_steps must be positive")
        if settings.collocation_points < 3:
            raise ValueError("collocation_points must be at least 3")
        if settings.learning_rate <= 0 or settings.initial_condition_weight <= 0:
            raise ValueError("learning rate and IC weight must be positive")
        return settings


class TinyPINN(nn.Module):
    def __init__(self, hidden_width: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(1, hidden_width),
            nn.Tanh(),
            nn.Linear(hidden_width, hidden_width),
            nn.Tanh(),
            nn.Linear(hidden_width, 1),
        )

    def forward(self, time_coordinate: torch.Tensor) -> torch.Tensor:
        return self.layers(time_coordinate)


def _time_grid(count: int) -> torch.Tensor:
    return torch.linspace(0.0, 1.0, count, dtype=torch.float64).reshape(-1, 1)


def _residual(model: nn.Module, times: torch.Tensor, create_graph: bool) -> torch.Tensor:
    differentiable_times = times.detach().clone().requires_grad_(True)
    state = model(differentiable_times)
    derivative = torch.autograd.grad(
        state,
        differentiable_times,
        grad_outputs=torch.ones_like(state),
        create_graph=create_graph,
    )[0]
    return derivative + state


def _loss(model: nn.Module, times: torch.Tensor, ic_weight: float) -> torch.Tensor:
    residual = _residual(model, times, create_graph=True)
    initial_time = torch.zeros((1, 1), dtype=torch.float64)
    initial_error = model(initial_time) - 1.0
    return residual.square().mean() + ic_weight * initial_error.square().mean()


def _evaluate(model: nn.Module, times: torch.Tensor, ic_weight: float) -> dict[str, Any]:
    residual = _residual(model, times, create_graph=False).detach()
    with torch.no_grad():
        prediction = model(times).detach()
        truth = torch.exp(-times)
        state_rmse = torch.sqrt(torch.mean((prediction - truth).square()))
        initial_error = model(torch.zeros((1, 1), dtype=torch.float64)) - 1.0
        loss = residual.square().mean() + ic_weight * initial_error.square().mean()
    return {
        "prediction": prediction.reshape(-1).cpu(),
        "residual": residual.reshape(-1).cpu(),
        "loss": float(loss.item()),
        "state_rmse": float(state_rmse.item()),
        "pde_mse": float(residual.square().mean().item()),
        "ic_abs_error": float(initial_error.abs().item()),
    }


def _save_checkpoint_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".pt", delete=False) as stream:
            temporary_name = stream.name
        torch.save(payload, temporary_name)
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def run_smoke(
    settings: SmokeSettings,
    output_root: str | Path,
    repo_root: str | Path,
    full_config: dict[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    digest = config_hash(full_config)
    set_deterministic_seed(settings.seed)
    torch.set_default_dtype(torch.float64)

    provenance = environment_provenance(root, dtype="float64", device="cpu")
    run_id = make_run_id("P0-smoke", settings.seed, digest, provenance["timestamp"])
    run_directory = Path(output_root).resolve() / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    logger = configure_logger("saeps.smoke", run_directory / "run.jsonl")

    model = TinyPINN(settings.hidden_width).to(dtype=torch.float64)
    times = _time_grid(settings.collocation_points)
    initial_metrics = _evaluate(model, times, settings.initial_condition_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings.learning_rate)

    log_event(logger, "training_started", run_id=run_id, seed=settings.seed)
    started = time.perf_counter()
    for _ in range(settings.adam_steps):
        optimizer.zero_grad(set_to_none=True)
        loss = _loss(model, times, settings.initial_condition_weight)
        loss.backward()
        optimizer.step()
    training_seconds = time.perf_counter() - started
    trained_metrics = _evaluate(model, times, settings.initial_condition_weight)

    checkpoint_path = run_directory / "checkpoint.pt"
    _save_checkpoint_atomic(
        checkpoint_path,
        {
            "schema_version": 1,
            "model_state": model.state_dict(),
            "hidden_width": settings.hidden_width,
            "seed": settings.seed,
            "config_hash": digest,
        },
    )

    reloaded = TinyPINN(settings.hidden_width).to(dtype=torch.float64)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint["config_hash"] != digest or checkpoint["seed"] != settings.seed:
        raise RuntimeError("Checkpoint provenance does not match the active run")
    reloaded.load_state_dict(checkpoint["model_state"])
    reloaded_metrics = _evaluate(reloaded, times, settings.initial_condition_weight)

    prediction_error = float(
        torch.max(torch.abs(trained_metrics["prediction"] - reloaded_metrics["prediction"])).item()
    )
    residual_error = float(
        torch.max(torch.abs(trained_metrics["residual"] - reloaded_metrics["residual"])).item()
    )
    roundtrip_error = max(prediction_error, residual_error)
    trained_enough = trained_metrics["state_rmse"] <= settings.max_state_rmse
    roundtrip_pass = roundtrip_error <= settings.max_roundtrip_abs_error
    loss_decreased = trained_metrics["loss"] < initial_metrics["loss"]
    status = "PASS" if trained_enough and roundtrip_pass and loss_decreased else "NUMERICAL_FAILURE"

    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "phase": "P0",
        "benchmark": "tiny_ode_u_t_plus_u",
        "split": "engineering_smoke",
        "seed": settings.seed,
        "config_hash": digest,
        "config": full_config,
        "settings": asdict(settings),
        "provenance": provenance,
        "training_time_seconds": training_seconds,
        "training_stop_reason": "configured_adam_steps_completed",
        "initial_metrics": {
            key: value for key, value in initial_metrics.items() if not isinstance(value, torch.Tensor)
        },
        "trained_metrics": {
            key: value for key, value in trained_metrics.items() if not isinstance(value, torch.Tensor)
        },
        "roundtrip": {
            "prediction_max_abs_error": prediction_error,
            "residual_max_abs_error": residual_error,
            "max_abs_error": roundtrip_error,
        },
        "status": status,
        "failure_reason": None if status == "PASS" else "smoke quality or round-trip gate failed",
    }
    write_json_atomic(run_directory / "metadata.json", metadata)
    write_json_atomic(
        run_directory / "validation.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "status": status,
            "state_rmse": trained_metrics["state_rmse"],
            "max_state_rmse": settings.max_state_rmse,
            "roundtrip_max_abs_error": roundtrip_error,
            "max_roundtrip_abs_error": settings.max_roundtrip_abs_error,
            "loss_decreased": loss_decreased,
        },
    )
    log_event(
        logger,
        "smoke_completed",
        run_id=run_id,
        status=status,
        state_rmse=trained_metrics["state_rmse"],
        roundtrip_max_abs_error=roundtrip_error,
    )
    if status != "PASS":
        raise RuntimeError(f"P0 smoke validation failed; see {run_directory / 'validation.json'}")
    return metadata


def run_smoke_from_config(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    config = load_config(config_path)
    smoke_mapping = config.get("smoke")
    if not isinstance(smoke_mapping, dict):
        raise ValueError("Configuration must contain a smoke mapping")
    return run_smoke(
        SmokeSettings.from_mapping(smoke_mapping),
        output_root=output_root,
        repo_root=repo_root,
        full_config=config,
    )

