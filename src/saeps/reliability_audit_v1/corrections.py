"""P0 correction-layer primitives for the RI-v6 review.

The historical reliability-audit records are intentionally untouched.  This
module contains small, explicit building blocks for a new development layer:
decision-input provenance, scale-consistent heat residuals, side-effect-free
optimizer closures, bound checks and the written reference-refinement rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Callable, Mapping

import torch


class DecisionMode(str, Enum):
    """Names of the four separately auditable decision interfaces."""

    SAEPS_ONLY = "SAEPS_ONLY"
    PHYSICAL_FIM_PLUGIN = "PHYSICAL_FIM_PLUGIN"
    ORACLE_FIM_REFERENCE = "ORACLE_FIM_REFERENCE"
    FIM_ASSISTED_SAEPS = "FIM_ASSISTED_SAEPS"


# String aliases make the protocol labels convenient to use in manifests while
# retaining an enum for type-safe dispatch.
SAEPS_ONLY = DecisionMode.SAEPS_ONLY
PHYSICAL_FIM_PLUGIN = DecisionMode.PHYSICAL_FIM_PLUGIN
ORACLE_FIM_REFERENCE = DecisionMode.ORACLE_FIM_REFERENCE
FIM_ASSISTED_SAEPS = DecisionMode.FIM_ASSISTED_SAEPS


_SAEPS_FIELDS = frozenset(
    {"observation", "known_constants", "checkpoint", "noise_sigma", "residual_weights", "numerical_config"}
)
_FORBIDDEN_SAEPS_FIELDS = frozenset(
    {
        "truth",
        "physical_truth",
        "true_parameters",
        "k_true",
        "C_true",
        "amplitude_true",
        "oracle_fim",
        "fim_at_truth",
        "I_obs",
        "reference_fim",
    }
)
_PLUGIN_FIELDS = frozenset(
    {"observation", "known_constants", "checkpoint", "estimated_parameters", "noise_sigma", "numerical_config"}
)
_ORACLE_FIELDS = frozenset({"observation", "true_parameters", "noise_sigma", "numerical_config"})


def _copy_mapping(mapping: Mapping[str, Any], *, allowed: frozenset[str]) -> dict[str, Any]:
    unknown = set(mapping) - allowed
    if unknown:
        raise TypeError(f"unsupported decision-input fields: {sorted(unknown)}")
    return dict(mapping)


def _nested_forbidden_keys(value: Any) -> set[str]:
    """Find oracle-looking keys in nested mapping payloads (fail closed)."""

    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_SAEPS_FIELDS:
                found.add(key_text)
            found.update(_nested_forbidden_keys(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(_nested_forbidden_keys(child))
    return found


@dataclass(frozen=True)
class SaepsOnlyInput:
    """Inputs that a deployable SAEPS decision is allowed to receive.

    ``from_mapping`` is deliberately fail-closed: hidden truth and any FIM
    reference are rejected by field name rather than merely ignored.
    """

    observation: Any
    known_constants: Mapping[str, Any]
    checkpoint: Any
    noise_sigma: float
    residual_weights: Mapping[str, float]
    numerical_config: Mapping[str, Any]
    mode: DecisionMode = DecisionMode.SAEPS_ONLY

    def __post_init__(self) -> None:
        if self.mode is not DecisionMode.SAEPS_ONLY:
            raise ValueError("SaepsOnlyInput must use SAEPS_ONLY mode")
        if not math.isfinite(float(self.noise_sigma)) or float(self.noise_sigma) < 0:
            raise ValueError("noise_sigma must be finite and non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "SaepsOnlyInput":
        forbidden = set(values) & _FORBIDDEN_SAEPS_FIELDS
        for field in _SAEPS_FIELDS:
            forbidden.update(_nested_forbidden_keys(values.get(field)))
        if forbidden:
            raise TypeError(f"SAEPS_ONLY rejects oracle/reference fields: {sorted(forbidden)}")
        data = _copy_mapping(values, allowed=_SAEPS_FIELDS)
        missing = _SAEPS_FIELDS - set(data)
        if missing:
            raise TypeError(f"missing SAEPS_ONLY fields: {sorted(missing)}")
        return cls(**data)


@dataclass(frozen=True)
class PhysicalFIMPluginInput:
    """Explicit plug-in interface using an estimated/external parameter value."""

    observation: Any
    known_constants: Mapping[str, Any]
    checkpoint: Any
    estimated_parameters: Mapping[str, float]
    noise_sigma: float
    numerical_config: Mapping[str, Any]
    mode: DecisionMode = DecisionMode.PHYSICAL_FIM_PLUGIN

    def __post_init__(self) -> None:
        if self.mode is not DecisionMode.PHYSICAL_FIM_PLUGIN:
            raise ValueError("PhysicalFIMPluginInput must use PHYSICAL_FIM_PLUGIN mode")
        if not math.isfinite(float(self.noise_sigma)) or float(self.noise_sigma) < 0:
            raise ValueError("noise_sigma must be finite and non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "PhysicalFIMPluginInput":
        data = _copy_mapping(values, allowed=_PLUGIN_FIELDS)
        missing = _PLUGIN_FIELDS - set(data)
        if missing:
            raise TypeError(f"missing PHYSICAL_FIM_PLUGIN fields: {sorted(missing)}")
        return cls(**data)


@dataclass(frozen=True)
class OracleFIMReferenceInput:
    """Reference-only interface; never use this object for a deployable decision."""

    observation: Any
    true_parameters: Mapping[str, float]
    noise_sigma: float
    numerical_config: Mapping[str, Any]
    mode: DecisionMode = DecisionMode.ORACLE_FIM_REFERENCE

    def __post_init__(self) -> None:
        if self.mode is not DecisionMode.ORACLE_FIM_REFERENCE:
            raise ValueError("OracleFIMReferenceInput must use ORACLE_FIM_REFERENCE mode")
        if not math.isfinite(float(self.noise_sigma)) or float(self.noise_sigma) < 0:
            raise ValueError("noise_sigma must be finite and non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "OracleFIMReferenceInput":
        data = _copy_mapping(values, allowed=_ORACLE_FIELDS)
        missing = _ORACLE_FIELDS - set(data)
        if missing:
            raise TypeError(f"missing ORACLE_FIM_REFERENCE fields: {sorted(missing)}")
        return cls(**data)


@dataclass(frozen=True)
class FIMAssistedSaepsInput:
    """SAEPS input with an explicitly declared, separately-costed FIM assist."""

    saeps: SaepsOnlyInput
    fim: Any
    mode: DecisionMode = DecisionMode.FIM_ASSISTED_SAEPS

    def __post_init__(self) -> None:
        if self.mode is not DecisionMode.FIM_ASSISTED_SAEPS:
            raise ValueError("FIMAssistedSaepsInput must use FIM_ASSISTED_SAEPS mode")
        if not isinstance(self.saeps, SaepsOnlyInput):
            raise TypeError("FIM_ASSISTED_SAEPS requires a SaepsOnlyInput payload")


# Backwards/serialization-friendly acronym spelling.
SAEPSOnlyInput = SaepsOnlyInput


def normalized_heat_residual(
    u_t: torch.Tensor,
    u_xx: torch.Tensor,
    k_over_c: torch.Tensor | float,
    *,
    s_phys: torch.Tensor | float = 1.0,
) -> torch.Tensor:
    """Return ``(u_t - (k/C) u_xx) / s_phys`` for the constant-C heat equation."""

    scale = torch.as_tensor(s_phys, dtype=u_t.dtype, device=u_t.device)
    if torch.any(~torch.isfinite(scale)) or torch.any(scale <= 0):
        raise ValueError("s_phys must be finite and strictly positive")
    ratio = torch.as_tensor(k_over_c, dtype=u_t.dtype, device=u_t.device)
    if torch.any(~torch.isfinite(ratio)):
        raise ValueError("k_over_c must be finite")
    return (u_t - ratio * u_xx) / scale


def normalized_heat_residual_from_parameters(
    u_t: torch.Tensor,
    u_xx: torch.Tensor,
    k: torch.Tensor | float,
    C: torch.Tensor | float,
    *,
    s_phys: torch.Tensor | float = 1.0,
) -> torch.Tensor:
    """Parameter form of :func:`normalized_heat_residual`, with positive ``C``."""

    c = torch.as_tensor(C, dtype=u_t.dtype, device=u_t.device)
    if torch.any(~torch.isfinite(c)) or torch.any(c <= 0):
        raise ValueError("C must be finite and strictly positive")
    return normalized_heat_residual(u_t, u_xx, torch.as_tensor(k, dtype=u_t.dtype, device=u_t.device) / c, s_phys=s_phys)


def normalized_quadrature_weights(count: int, *, dtype: torch.dtype = torch.float64, device: torch.device | None = None) -> torch.Tensor:
    """Return equal weights whose total mass is one on a fixed domain."""

    if int(count) < 1:
        raise ValueError("count must be positive")
    return torch.full((int(count),), 1.0 / float(count), dtype=dtype, device=device)


def weighted_residual_mean_square(residual: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Compute a quadrature-weighted mean square with explicit mass checks."""

    if residual.ndim != 1 or weights.ndim != 1 or residual.numel() != weights.numel():
        raise ValueError("residual and weights must be one-dimensional and equally sized")
    if torch.any(weights < 0) or not torch.isclose(weights.sum(), torch.ones((), dtype=weights.dtype, device=weights.device)):
        raise ValueError("weights must be non-negative and sum to one")
    return torch.sum(weights.to(dtype=residual.dtype, device=residual.device) * residual.square())


def check_log_parameter_bounds(
    parameters: Mapping[str, torch.Tensor | float],
    lower: float,
    upper: float,
    *,
    atol: float = 0.0,
) -> dict[str, Any]:
    """Return an auditable bound report without modifying any parameter."""

    if not lower < upper:
        raise ValueError("lower must be smaller than upper")
    values: dict[str, float] = {}
    violations: list[str] = []
    for name, value in parameters.items():
        scalar = float(torch.as_tensor(value).detach().cpu().item())
        values[name] = scalar
        if scalar < lower - atol or scalar > upper + atol:
            violations.append(name)
    return {"within_bounds": not violations, "values": values, "lower": float(lower), "upper": float(upper), "violations": violations}


def make_side_effect_free_closure(
    objective: Callable[[], torch.Tensor],
    optimizer: torch.optim.Optimizer,
    parameters: Mapping[str, torch.Tensor],
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> Callable[[], torch.Tensor]:
    """Build an LBFGS-compatible closure that never clamps or mutates parameters.

    Bounds, when supplied, are checked before evaluating the objective.  A
    caller that needs bounded optimization must use a bounded optimizer or a
    smooth parameter transform; this closure intentionally has no in-place
    repair path.
    """

    if (lower is None) != (upper is None):
        raise ValueError("lower and upper must be supplied together")
    if lower is not None and not lower < upper:  # type: ignore[operator]
        raise ValueError("lower must be smaller than upper")

    def closure() -> torch.Tensor:
        if lower is not None:
            report = check_log_parameter_bounds(parameters, lower, upper)  # type: ignore[arg-type]
            if not report["within_bounds"]:
                raise ValueError(f"parameters outside bounds: {report['violations']}")
        optimizer.zero_grad(set_to_none=True)
        value = objective()
        if value.ndim != 0:
            raise ValueError("objective must return a scalar tensor")
        value.backward()
        return value

    return closure


def refinement_threshold(noise_scale: float, noise_fraction: float = 0.01) -> float:
    """Compute the written two-level reference threshold."""

    noise = float(noise_scale)
    fraction = float(noise_fraction)
    if not math.isfinite(noise) or not math.isfinite(fraction) or noise < 0 or fraction < 0:
        raise ValueError("noise_scale and noise_fraction must be finite and non-negative")
    return noise * fraction


def evaluate_refinement(
    previous_value: float,
    current_value: float,
    *,
    noise_scale: float,
    noise_fraction: float = 0.01,
) -> dict[str, Any]:
    """Report both the measured two-level difference and its written pass flag."""

    difference = abs(float(current_value) - float(previous_value))
    threshold = refinement_threshold(noise_scale, noise_fraction)
    return {
        "previous_value": float(previous_value),
        "current_value": float(current_value),
        "difference": difference,
        "noise_scale": float(noise_scale),
        "noise_fraction": float(noise_fraction),
        "threshold": threshold,
        "pass": bool(difference < threshold),
    }


__all__ = [
    "DecisionMode",
    "SAEPS_ONLY",
    "PHYSICAL_FIM_PLUGIN",
    "ORACLE_FIM_REFERENCE",
    "FIM_ASSISTED_SAEPS",
    "SaepsOnlyInput",
    "SAEPSOnlyInput",
    "PhysicalFIMPluginInput",
    "OracleFIMReferenceInput",
    "FIMAssistedSaepsInput",
    "normalized_heat_residual",
    "normalized_heat_residual_from_parameters",
    "normalized_quadrature_weights",
    "weighted_residual_mean_square",
    "check_log_parameter_bounds",
    "make_side_effect_free_closure",
    "refinement_threshold",
    "evaluate_refinement",
]
