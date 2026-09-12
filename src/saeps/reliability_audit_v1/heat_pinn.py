"""Small, provenance-first heat-equation inverse PINN pilot (RI-2).

The implementation is intentionally self contained.  It uses the analytic
single-mode solution only to generate observations and the independent FIM;
the PINN is trained against the PDE, initial/boundary and observation residuals.
No test truth is consulted by the optimiser or by the fixed diagnostic rules.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from saeps.identifiability import (
    benchmark_observation_jacobian,
    finite_gamma_reduced_curvature,
    heat_temperature,
    observation_fim,
)
from saeps.residual import stack_weighted_residuals


BENCHMARKS = ("B1", "B2", "B3", "B4")
UNKNOWN_BY_BENCHMARK = {
    "B1": ("k",),
    "B2": ("k",),
    "B3": ("k", "C"),
    # The initial-condition amplitude is a nuisance coordinate in B4.  It is
    # optimized jointly but belongs to the eliminated state block.
    "B4": ("k",),
}
TRAINABLE_BY_BENCHMARK = {
    "B1": ("k",),
    "B2": ("k",),
    "B3": ("k", "C"),
    "B4": ("k", "a"),
}


@dataclass(frozen=True)
class HeatPINNConfig:
    """Frozen development defaults; confirmation must copy and hash this config."""

    benchmark: str = "B1"
    k_true: float = 0.6
    C_true: float = 1.2
    amplitude_true: float = 1.0
    noise_sigma: float = 0.01
    data_seed: int = 10
    # A separate RNG stream is required even when the pilot uses one noise
    # realisation per data case.  ``None`` preserves the legacy pilot files;
    # all new protocol runs set this explicitly.
    noise_seed: int | None = None
    optimizer_seed: int = 100
    dtype: str = "float64"
    width: int = 16
    depth: int = 2
    epochs: int = 100
    learning_rate: float = 1.0e-3
    n_collocation: int = 48
    n_data_x: int = 3
    n_data_times: int = 4
    n_ic: int = 16
    n_bc: int = 16
    weight_pde: float = 1.0
    weight_data: float = 10.0
    weight_ic: float = 10.0
    weight_bc: float = 2.0
    gamma_alpha: float = 1.0e-4
    # Declared pilot stationarity threshold for the mean weighted objective.
    # This is a training validity gate, not a test-truth-selected parameter.
    grad_tolerance: float = 5.0e-2
    loss_tolerance: float = 5.0e-3
    use_lbfgs: bool = True
    lbfgs_max_iter: int = 60
    lower_log_parameter: float = -4.0
    upper_log_parameter: float = 2.0
    output_dir: str | None = None

    def __post_init__(self) -> None:
        benchmark = self.benchmark.upper()
        object.__setattr__(self, "benchmark", benchmark)
        if benchmark not in BENCHMARKS:
            raise ValueError(f"benchmark must be one of {BENCHMARKS}")
        if self.k_true <= 0 or self.C_true <= 0 or self.amplitude_true == 0:
            raise ValueError("physical truth must be positive (except nonzero amplitude)")
        if self.noise_sigma < 0 or self.epochs < 1 or self.width < 1 or self.depth < 1:
            raise ValueError("invalid training configuration")
        if self.learning_rate <= 0 or self.gamma_alpha <= 0 or min(self.weight_pde, self.weight_data, self.weight_ic, self.weight_bc) <= 0:
            raise ValueError("learning rate and residual weights must be positive")
        if self.lbfgs_max_iter < 1:
            raise ValueError("lbfgs_max_iter must be positive")
        if self.lower_log_parameter >= self.upper_log_parameter:
            raise ValueError("log-parameter bounds must be ordered")

    @property
    def torch_dtype(self) -> torch.dtype:
        return torch.float32 if self.dtype in {"float32", "fp32"} else torch.float64

    @property
    def unknown_parameters(self) -> tuple[str, ...]:
        return UNKNOWN_BY_BENCHMARK[self.benchmark]

    @property
    def trainable_parameters(self) -> tuple[str, ...]:
        return TRAINABLE_BY_BENCHMARK[self.benchmark]

    @property
    def nuisance_parameter_names(self) -> tuple[str, ...]:
        return tuple(name for name in self.trainable_parameters if name not in self.unknown_parameters)

    @property
    def effective_noise_seed(self) -> int:
        return int(self.data_seed if self.noise_seed is None else self.noise_seed)

    def as_hash(self) -> str:
        # Artifact location is operational metadata, not part of the locked
        # scientific configuration; excluding it keeps hashes stable across
        # run directories.
        values = asdict(self)
        values.pop("output_dir", None)
        payload = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HeatObservation:
    benchmark: str
    x: torch.Tensor
    t: torch.Tensor
    values: torch.Tensor
    clean_values: torch.Tensor
    data_seed: int
    noise_sigma: float
    observation_type: str = "temperature"


def _observation_coordinates(config: HeatPINNConfig) -> tuple[torch.Tensor, torch.Tensor]:
    dtype = config.torch_dtype
    x_grid = torch.tensor([0.2, 0.4, 0.7], dtype=dtype)
    if config.benchmark == "B2":
        times = torch.tensor([1e-5, 4e-5, 7e-5, 1e-4], dtype=dtype)
        return x_grid.repeat_interleave(times.numel()), times.repeat(x_grid.numel())
    if config.benchmark == "B4":
        times = torch.full((1,), 0.2, dtype=dtype)
    else:
        times = torch.tensor([0.02, 0.08, 0.2, 0.4], dtype=dtype)
    return x_grid.repeat_interleave(times.numel()), times.repeat(x_grid.numel())


def generate_heat_observations(config: HeatPINNConfig) -> HeatObservation:
    """Generate deterministic temperature observations from the analytic solution."""
    x, t = _observation_coordinates(config)
    clean = heat_temperature(x, t, config.k_true, config.C_true, config.amplitude_true)
    generator = torch.Generator(device=x.device).manual_seed(config.effective_noise_seed)
    noise = torch.randn(clean.shape, dtype=clean.dtype, generator=generator) * config.noise_sigma
    return HeatObservation(config.benchmark, x, t, clean + noise, clean, config.data_seed, config.noise_sigma)


class _StateNet(nn.Module):
    def __init__(self, width: int, depth: int) -> None:
        super().__init__()
        layers: list[nn.Module] = [nn.Linear(2, width), nn.Tanh()]
        for _ in range(depth - 1):
            layers.extend((nn.Linear(width, width), nn.Tanh()))
        layers.append(nn.Linear(width, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, coordinates: torch.Tensor, amplitude: torch.Tensor | float = 0.0) -> torch.Tensor:
        # Exact homogeneous Dirichlet and single-mode initial-condition
        # embeddings.  The trainable amplitude is passed explicitly so B4 can
        # profile it as a nuisance parameter while B1--B3 hold it fixed.
        x = coordinates[:, :1]
        t = coordinates[:, 1:2]
        amplitude_value = torch.as_tensor(amplitude, dtype=coordinates.dtype, device=coordinates.device)
        baseline = amplitude_value * torch.sin(torch.pi * x)
        return baseline + t * x * (1.0 - x) * self.net(coordinates)


def _physical_values(config: HeatPINNConfig, log_parameters: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    result: dict[str, torch.Tensor] = {
        "k": torch.as_tensor(config.k_true, dtype=config.torch_dtype),
        "C": torch.as_tensor(config.C_true, dtype=config.torch_dtype),
        "a": torch.as_tensor(config.amplitude_true, dtype=config.torch_dtype),
    }
    for name, value in log_parameters.items():
        result[name] = torch.exp(value)
    return result


def _residual_blocks(
    model: _StateNet,
    config: HeatPINNConfig,
    observation: HeatObservation,
    log_parameters: dict[str, torch.Tensor],
    *,
    create_graph: bool,
) -> dict[str, torch.Tensor]:
    dtype = config.torch_dtype
    generator = torch.Generator().manual_seed(int(config.data_seed) + 7919)
    collocation = torch.rand((config.n_collocation, 2), dtype=dtype, generator=generator)
    collocation.requires_grad_(True)
    phys = _physical_values(config, log_parameters)
    u = model(collocation, phys["a"])
    grad_u = torch.autograd.grad(u, collocation, torch.ones_like(u), create_graph=True, retain_graph=True)[0]
    grad_x = grad_u[:, :1]
    grad_t = grad_u[:, 1:2]
    grad_xx = torch.autograd.grad(grad_x, collocation, torch.ones_like(grad_x), create_graph=create_graph, retain_graph=True)[0][:, :1]
    pde = phys["C"] * grad_t - phys["k"] * grad_xx

    data_coords = torch.stack((observation.x, observation.t), dim=1).detach().requires_grad_(True)
    data_pred = model(data_coords, phys["a"]).reshape(-1)
    data = data_pred - observation.values

    x_ic = torch.linspace(0.0, 1.0, config.n_ic, dtype=dtype)
    ic_coords = torch.stack((x_ic, torch.zeros_like(x_ic)), dim=1)
    ic_target = phys["a"] * torch.sin(torch.pi * x_ic)
    ic = model(ic_coords, phys["a"]).reshape(-1) - ic_target

    # The embedding already enforces BC; retaining an explicit block documents
    # the weighted residual and catches accidental changes to that embedding.
    x_bc = torch.tensor([0.0, 1.0], dtype=dtype).repeat(config.n_bc // 2 + 1)[: config.n_bc]
    t_bc = torch.linspace(0.0, 1.0, config.n_bc, dtype=dtype)
    bc_coords = torch.stack((x_bc, t_bc), dim=1)
    bc = model(bc_coords, phys["a"]).reshape(-1)
    return {"pde": pde.reshape(-1), "data": data, "ic": ic, "bc": bc}


def weighted_residual(
    model: nn.Module,
    config: HeatPINNConfig,
    observation: HeatObservation,
    log_parameters: dict[str, torch.Tensor],
    *,
    create_graph: bool = True,
) -> torch.Tensor:
    """Return the flattened weighted residual used by training and diagnostics."""
    blocks = _residual_blocks(model, config, observation, log_parameters, create_graph=create_graph)
    return stack_weighted_residuals(
        blocks,
        {"pde": config.weight_pde, "data": config.weight_data, "ic": config.weight_ic, "bc": config.weight_bc},
    )


@dataclass
class HeatPINNRun:
    config: HeatPINNConfig
    observation: HeatObservation
    model: _StateNet
    log_parameters: dict[str, nn.Parameter]
    residual: torch.Tensor
    jacobian_state: torch.Tensor | None
    jacobian_parameter: torch.Tensor | None
    F_raw: torch.Tensor | None
    F_gamma: torch.Tensor | None
    I_obs: torch.Tensor
    gamma: float | None
    train_loss: float
    gradient_norm: float
    compute_status: str
    fit_status: str
    profile_status: str
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def statuses(self) -> dict[str, str]:
        return {
            "COMPUTABLE": self.compute_status,
            "FIT_QUALIFIED": self.fit_status,
            "PROFILE_ELIGIBLE": self.profile_status,
        }

    @property
    def status_labels(self) -> dict[str, str]:
        """Protocol-facing labels, separate from the engineering PASS/FAIL fields."""
        return {
            "COMPUTABLE": "COMPUTABLE" if self.compute_status == "PASS" else "NOT_COMPUTABLE",
            "FIT_QUALIFIED": "FIT_QUALIFIED" if self.fit_status == "PASS" else "NOT_FIT_QUALIFIED",
            "PROFILE_ELIGIBLE": "PROFILE_ELIGIBLE" if self.profile_status == "PASS" else "NOT_PROFILE_ELIGIBLE",
        }

    @property
    def parameter_estimates(self) -> dict[str, float]:
        return {name: float(torch.exp(value).detach().cpu()) for name, value in self.log_parameters.items()}

    def to_manifest(self) -> dict[str, Any]:
        result = dict(self.manifest)
        result.update(
            {
                "run_id": f"ri2-{self.config.benchmark}-d{self.config.data_seed}-o{self.config.optimizer_seed}",
                "schema_version": 1,
                "protocol_id": "reliability_audit_v1",
                "benchmark": self.config.benchmark,
                "data_seed": self.config.data_seed,
                "noise_seed": self.config.effective_noise_seed,
                "optimizer_seed": self.config.optimizer_seed,
                "noise_sigma": self.config.noise_sigma,
                "unknown_parameters": list(self.config.unknown_parameters),
                "physical_parameters": [name for name in self.config.unknown_parameters if name in {"k", "C"}],
                "parameter_estimates": self.parameter_estimates,
                "statuses": self.statuses,
                "status_labels": self.status_labels,
                "execution_status": "PASS" if self.compute_status == "PASS" else "NUMERICAL_FAILURE",
                "fit_status": self.fit_status,
                "profile_status": self.profile_status,
                "numerical_status": "PASS" if self.compute_status == "PASS" else "FAIL",
                "fit_qualified": self.fit_status == "PASS",
                "profile_eligible": self.profile_status == "PASS",
                "failure_reason": (
                    None
                    if self.compute_status == "PASS" and self.fit_status == "PASS"
                    else ("FIT_QUALIFIED_GATE_FAILED" if self.compute_status == "PASS" else "DIAGNOSTIC_UNAVAILABLE")
                ),
                "physical_truth": {"k": self.config.k_true, "C": self.config.C_true, "a": self.config.amplitude_true},
                "nuisance_parameters": list(self.config.nuisance_parameter_names),
                "observation_type": self.observation.observation_type,
                "observation_covariance": {"kind": "homoscedastic", "sigma": self.config.noise_sigma},
                "residual_weights": {"pde": self.config.weight_pde, "data": self.config.weight_data, "ic": self.config.weight_ic, "bc": self.config.weight_bc},
                "gamma_scale_definition": "gamma_alpha * lambda_max(J_state.T @ J_state)",
                "rank_tolerance": 1.0e-10,
                "F_raw_rank": None if self.F_raw is None else int(torch.linalg.matrix_rank(self.F_raw, rtol=1.0e-10).item()),
                "F_gamma_rank": None if self.F_gamma is None else int(torch.linalg.matrix_rank(self.F_gamma, rtol=1.0e-10).item()),
                "train_loss": self.train_loss,
                "gradient_norm": self.gradient_norm,
                "gamma": self.gamma,
                "gamma_alpha": self.config.gamma_alpha,
                "F_raw_shape": None if self.F_raw is None else list(self.F_raw.shape),
                "F_gamma_shape": None if self.F_gamma is None else list(self.F_gamma.shape),
                "I_obs_shape": list(self.I_obs.shape),
                "jacobian_state_shape": None if self.jacobian_state is None else list(self.jacobian_state.shape),
                "jacobian_parameter_shape": None if self.jacobian_parameter is None else list(self.jacobian_parameter.shape),
                "hardware": platform.platform(),
                "dtype": self.config.dtype,
                "jvp_count": 0,
                "vjp_count": 0,
                "hvp_count": 0,
                "adam_epochs": self.config.epochs,
                "lbfgs_max_iter": self.config.lbfgs_max_iter if self.config.use_lbfgs else 0,
            }
        )
        return result

    def save(self, directory: str | Path) -> Path:
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        checkpoint = out / "checkpoint.pt"
        torch.save(
            {
                "model": self.model.state_dict(),
                "log_parameters": {k: v.detach().cpu() for k, v in self.log_parameters.items()},
                "config": asdict(self.config),
            },
            checkpoint,
        )
        raw_paths: dict[str, str] = {}
        for name, matrix in (("F_raw", self.F_raw), ("F_gamma", self.F_gamma), ("I_obs", self.I_obs)):
            if matrix is not None:
                path = out / f"{name}.npy"
                np.save(path, matrix.detach().cpu().numpy())
                raw_paths[name] = str(path)
        checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        manifest = self.to_manifest()
        manifest["checkpoint_path"] = str(checkpoint)
        manifest["checkpoint_sha256"] = checkpoint_hash
        manifest["raw_paths"] = raw_paths
        self.manifest.update({"checkpoint_path": str(checkpoint), "checkpoint_sha256": checkpoint_hash, "raw_paths": raw_paths})
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return checkpoint


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _jacobians(
    model: _StateNet,
    config: HeatPINNConfig,
    observation: HeatObservation,
    log_parameters: dict[str, nn.Parameter],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # Direct autograd columns avoid mutating a module during functional Jacobian
    # evaluation and keep the state/physical blocks explicit for auditability.
    residual = weighted_residual(model, config, observation, log_parameters, create_graph=True)
    state_parameters = tuple(model.parameters())
    nuisance_parameters = tuple(log_parameters[name] for name in config.nuisance_parameter_names)
    state_parameters = state_parameters + nuisance_parameters
    physical_parameters = tuple(log_parameters[name] for name in config.unknown_parameters)
    Jw_rows: list[torch.Tensor] = []
    Jp_rows: list[torch.Tensor] = []
    for value in residual:
        grads = torch.autograd.grad(value, state_parameters + physical_parameters, retain_graph=True, allow_unused=True)
        state_grad = torch.cat([g.reshape(-1) if g is not None else torch.zeros(p.numel(), dtype=residual.dtype) for g, p in zip(grads[: len(state_parameters)], state_parameters)])
        physical_grad = torch.cat([g.reshape(-1) if g is not None else torch.zeros(1, dtype=residual.dtype) for g in grads[len(state_parameters):]])
        Jw_rows.append(state_grad)
        Jp_rows.append(physical_grad)
    return residual.detach(), torch.stack(Jw_rows).detach(), torch.stack(Jp_rows).detach()


def run_heat_pinn(config: HeatPINNConfig | None = None) -> HeatPINNRun:
    """Train one pilot checkpoint and compute RAW/finite-γ/FIM diagnostics."""
    config = config or HeatPINNConfig()
    torch.manual_seed(int(config.optimizer_seed))
    np.random.seed(int(config.optimizer_seed))
    observation = generate_heat_observations(config)
    model = _StateNet(config.width, config.depth).to(dtype=config.torch_dtype)
    # Fixed development initialisation, independent of the hidden/test truth.
    # The truth is used only for deterministic data generation and the separate
    # analytic reference FIM.
    initial = {"k": np.log(0.5), "C": np.log(1.0), "a": np.log(1.0)}
    log_parameters = {name: nn.Parameter(torch.tensor(initial[name], dtype=config.torch_dtype)) for name in config.trainable_parameters}
    optimizer = torch.optim.Adam(list(model.parameters()) + list(log_parameters.values()), lr=config.learning_rate)
    start = time.perf_counter()
    for _ in range(config.epochs):
        optimizer.zero_grad(set_to_none=True)
        residual = weighted_residual(model, config, observation, log_parameters, create_graph=True)
        loss = 0.5 * torch.mean(residual * residual)
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            for value in log_parameters.values():
                value.clamp_(config.lower_log_parameter, config.upper_log_parameter)
    if config.use_lbfgs:
        # A bounded, deterministic quasi-Newton polish is useful for the tiny
        # analytic benchmark while remaining an explicitly declared training
        # tool (never a reliability baseline).
        lbfgs = torch.optim.LBFGS(
            list(model.parameters()) + list(log_parameters.values()),
            max_iter=config.lbfgs_max_iter,
            history_size=20,
            line_search_fn="strong_wolfe",
        )

        def closure() -> torch.Tensor:
            lbfgs.zero_grad(set_to_none=True)
            current = weighted_residual(model, config, observation, log_parameters, create_graph=True)
            objective = 0.5 * torch.mean(current * current)
            objective.backward()
            with torch.no_grad():
                for value in log_parameters.values():
                    value.clamp_(config.lower_log_parameter, config.upper_log_parameter)
            return objective

        lbfgs.step(closure)
    elapsed = time.perf_counter() - start
    residual, Jw, Jp = _jacobians(model, config, observation, log_parameters)
    raw = Jp.T @ Jp
    jw_normal = Jw.T @ Jw
    scale = float(torch.linalg.eigvalsh(jw_normal).max().clamp_min(torch.finfo(jw_normal.dtype).eps).item())
    gamma = config.gamma_alpha * scale
    try:
        finite_gamma = finite_gamma_reduced_curvature(Jw, Jp, gamma)
        compute_status = "PASS"
    except (RuntimeError, ValueError, torch.linalg.LinAlgError):
        finite_gamma = None
        compute_status = "FAIL"
    final_loss = float(0.5 * torch.mean(residual * residual).item())
    gradients = torch.autograd.grad(0.5 * torch.mean(weighted_residual(model, config, observation, log_parameters, create_graph=True) ** 2), tuple(model.parameters()) + tuple(log_parameters.values()), allow_unused=True)
    grad_norm = float(torch.sqrt(sum(torch.sum(g.detach() ** 2) for g in gradients if g is not None)).item())
    fit_status = "PASS" if compute_status == "PASS" and np.isfinite(grad_norm) and grad_norm <= config.grad_tolerance and final_loss <= config.loss_tolerance else "FAIL"
    # Profiles are intentionally not implemented in this pilot; never imply that
    # a local Jacobian is a nonlinear profile result.
    profile_status = "NOT_ELIGIBLE"
    x, t = observation.x, observation.t
    Jobs = benchmark_observation_jacobian(config.benchmark, x, t, k=config.k_true, C=config.C_true, amplitude=config.amplitude_true)
    if config.benchmark == "B1" or config.benchmark == "B2":
        Jobs = Jobs[:, :1] * config.k_true
    elif config.benchmark == "B3":
        Jobs = Jobs[:, :2] * torch.tensor([config.k_true, config.C_true], dtype=config.torch_dtype)
    elif config.benchmark == "B4":
        # benchmark_observation_jacobian already selects (k, amplitude) for B4.
        Jobs = Jobs * torch.tensor([config.k_true, config.amplitude_true], dtype=config.torch_dtype)
    fim = observation_fim(Jobs, sigma=max(config.noise_sigma, 1.0e-12))
    run = HeatPINNRun(config, observation, model, log_parameters, residual, Jw, Jp, raw, finite_gamma, fim, gamma, final_loss, grad_norm, compute_status, fit_status, profile_status)
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run.manifest.update({"config_sha256": config.as_hash(), "source_sha256": source_hash, "code_sha256": source_hash, "git_commit": _git_revision(), "elapsed_training_seconds": elapsed, "profile_implemented": False, "coordinate_system": "log(k),log(C),log(a)", "residual_normalization": "weighted residual blocks; mean-square objective", "solver_iterations": {"adam": config.epochs, "lbfgs": config.lbfgs_max_iter if config.use_lbfgs else 0}})
    if config.output_dir:
        run.save(config.output_dir)
    return run


__all__ = [
    "BENCHMARKS",
    "HeatObservation",
    "HeatPINNConfig",
    "HeatPINN",
    "HeatPINNRun",
    "generate_heat_observations",
    "run_heat_pinn",
    "weighted_residual",
    "heat_pinn_residual",
    "run_one",
    "train_heat_pinn",
]

# Public aliases keep the adapter convenient for tests and small scripts while
# retaining the private implementation name in checkpoint internals.
HeatPINN = _StateNet
heat_pinn_residual = weighted_residual
run_one = run_heat_pinn
train_heat_pinn = run_heat_pinn
