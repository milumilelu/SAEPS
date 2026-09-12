"""Independent analytic profiles for the heat identifiability benchmarks.

This module is deliberately NumPy-only.  It evaluates the closed-form
single-mode heat solution and a Gaussian observation objective, without using
the PINN residual, checkpoint, or test-truth errors during optimisation.  The
result is an independent reference for the nonlinear profile (R3) protocol.

The profile scans are frozen in log coordinates: thirty-one values spanning
``[1/3, 3]`` times the declared reference value.  Nuisance parameters are
re-optimised at every scan point.  Amplitude is solved by bounded variable
projection; ``C`` is solved by a deterministic bounded golden-section search.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


DEFAULT_K = 0.6
DEFAULT_C = 1.2
DEFAULT_AMPLITUDE = 1.0
DEFAULT_X = np.asarray([0.2, 0.4, 0.7], dtype=np.float64)
DEFAULT_MULTI_TIMES = np.asarray([0.02, 0.08, 0.2, 0.4], dtype=np.float64)
DEFAULT_EARLY_TIMES = np.asarray([1.0e-5, 4.0e-5, 7.0e-5, 1.0e-4], dtype=np.float64)
DEFAULT_PROFILE_POINTS = 31
DEFAULT_PROFILE_LOG_HALF_WIDTH = float(np.log(3.0))
DEFAULT_LOG_NUISANCE_BOUNDS = (-4.0, 2.0)


def frozen_profile_grid(
    reference: float = DEFAULT_K,
    *,
    points: int = DEFAULT_PROFILE_POINTS,
    log_half_width: float = DEFAULT_PROFILE_LOG_HALF_WIDTH,
) -> np.ndarray:
    """Return the predeclared positive scan grid in log coordinates.

    The defaults are part of ``reliability_audit_v1`` and must not be changed
    after confirmation is locked.  Validation here prevents accidental use of
    a sparse grid or a data-dependent range.
    """

    reference = float(reference)
    points = int(points)
    log_half_width = float(log_half_width)
    if reference <= 0 or points < 31 or points % 2 == 0 or log_half_width <= 0:
        raise ValueError("reference > 0, odd points >= 31 and positive width required")
    return reference * np.exp(np.linspace(-log_half_width, log_half_width, points))


def heat_temperature_np(x: np.ndarray, t: np.ndarray, k: float, C: float, amplitude: float = 1.0) -> np.ndarray:
    """Single-mode solution ``a sin(pi*x) exp(-pi²(k/C)t)``."""

    x, t = _coordinates(x, t)
    if float(k) <= 0 or float(C) <= 0:
        raise ValueError("k and C must be positive")
    return float(amplitude) * np.sin(np.pi * x) * np.exp(-np.pi**2 * (float(k) / float(C)) * t)


def heat_flux_np(x: np.ndarray, t: np.ndarray, k: float, C: float, amplitude: float = 1.0) -> np.ndarray:
    """Calibrated heat flux ``q=-k T_x`` for the single-mode solution."""

    x, t = _coordinates(x, t)
    if float(k) <= 0 or float(C) <= 0:
        raise ValueError("k and C must be positive")
    return -float(k) * float(amplitude) * np.pi * np.cos(np.pi * x) * np.exp(
        -np.pi**2 * (float(k) / float(C)) * t
    )


def _coordinates(x: np.ndarray, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    t = np.asarray(t, dtype=np.float64).reshape(-1)
    if x.shape != t.shape or x.size == 0 or not np.isfinite(x).all() or not np.isfinite(t).all():
        raise ValueError("x and t must be finite, non-empty vectors of equal length")
    if np.any(x <= 0) or np.any(x >= 1) or np.any(t < 0):
        raise ValueError("observation coordinates must have 0 < x < 1 and t >= 0")
    return x, t


@dataclass(frozen=True)
class HeatAnalyticObservations:
    """Independent observations and scales used by a profile objective."""

    benchmark: str
    x_temperature: np.ndarray
    t_temperature: np.ndarray
    y_temperature: np.ndarray
    sigma_temperature: np.ndarray
    x_flux: np.ndarray | None = None
    t_flux: np.ndarray | None = None
    y_flux: np.ndarray | None = None
    sigma_flux: np.ndarray | None = None
    data_seed: int | None = None
    noise_rho: float = 0.0
    truth: Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        benchmark = str(self.benchmark).upper()
        if benchmark not in {"B1", "B2", "B3", "B4", "B5", "B6"}:
            raise ValueError("benchmark must be B1, B2, B3, B4, B5 or B6")
        object.__setattr__(self, "benchmark", benchmark)
        x, t = _coordinates(self.x_temperature, self.t_temperature)
        y = np.asarray(self.y_temperature, dtype=np.float64).reshape(-1)
        st = np.asarray(self.sigma_temperature, dtype=np.float64).reshape(-1)
        if y.shape != x.shape or st.shape != x.shape or not np.isfinite(y).all() or not np.isfinite(st).all():
            raise ValueError("temperature observations and scales must match coordinates")
        if np.any(st <= 0):
            raise ValueError("temperature scales must be positive")
        object.__setattr__(self, "x_temperature", x)
        object.__setattr__(self, "t_temperature", t)
        object.__setattr__(self, "y_temperature", y)
        object.__setattr__(self, "sigma_temperature", st)
        if benchmark == "B6":
            if any(v is None for v in (self.x_flux, self.t_flux, self.y_flux, self.sigma_flux)):
                raise ValueError("B6 requires calibrated flux observations and scales")
        if self.x_flux is not None:
            xf, tf = _coordinates(self.x_flux, self.t_flux)  # type: ignore[arg-type]
            yf = np.asarray(self.y_flux, dtype=np.float64).reshape(-1)  # type: ignore[arg-type]
            sf = np.asarray(self.sigma_flux, dtype=np.float64).reshape(-1)  # type: ignore[arg-type]
            if yf.shape != xf.shape or sf.shape != xf.shape or not np.isfinite(yf).all() or not np.isfinite(sf).all():
                raise ValueError("flux observations and scales must match coordinates")
            if np.any(sf <= 0):
                raise ValueError("flux scales must be positive")
            object.__setattr__(self, "x_flux", xf)
            object.__setattr__(self, "t_flux", tf)
            object.__setattr__(self, "y_flux", yf)
            object.__setattr__(self, "sigma_flux", sf)

    def to_jsonable(self) -> dict[str, Any]:
        """Return an explicit, machine-readable observation record."""

        result: dict[str, Any] = {
            "benchmark": self.benchmark,
            "x_temperature": self.x_temperature.tolist(),
            "t_temperature": self.t_temperature.tolist(),
            "y_temperature": self.y_temperature.tolist(),
            "sigma_temperature": self.sigma_temperature.tolist(),
            "data_seed": self.data_seed,
            "noise_rho": float(self.noise_rho),
            "truth": dict(self.truth) if self.truth is not None else None,
        }
        for name in ("x_flux", "t_flux", "y_flux", "sigma_flux"):
            value = getattr(self, name)
            result[name] = None if value is None else value.tolist()
        return result


def default_observation_design(benchmark: str) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Return the frozen B1--B6 coordinate design."""

    benchmark = str(benchmark).upper()
    if benchmark == "B2":
        times = DEFAULT_EARLY_TIMES
    elif benchmark == "B4":
        times = np.asarray([0.2])
    elif benchmark == "B5":
        times = np.asarray([0.2, 0.4])
    else:
        times = DEFAULT_MULTI_TIMES
    x = np.repeat(DEFAULT_X, times.size)
    t = np.tile(times, DEFAULT_X.size)
    if benchmark == "B6":
        return x, t, x.copy(), t.copy()
    return x, t, None, None


def generate_analytic_observations(
    benchmark: str,
    *,
    k: float = DEFAULT_K,
    C: float = DEFAULT_C,
    amplitude: float = DEFAULT_AMPLITUDE,
    noise_rho: float = 0.01,
    data_seed: int = 10,
) -> HeatAnalyticObservations:
    """Generate one deterministic analytic data realisation.

    Temperature and flux use separate deterministic RNG streams.  Their
    scales are fixed from the clean signal (``rho * max(abs(signal))``), so a
    noisy realisation cannot alter the declared covariance after the fact.
    """

    benchmark = str(benchmark).upper()
    xt, tt, xf, tf = default_observation_design(benchmark)
    clean_t = heat_temperature_np(xt, tt, k, C, amplitude)
    rho = float(noise_rho)
    if rho < 0:
        raise ValueError("noise_rho must be non-negative")
    scale_t = max(float(np.max(np.abs(clean_t))), np.finfo(float).eps) * max(rho, 1.0e-12)
    rng_t = np.random.default_rng(int(data_seed))
    y_t = clean_t + (rng_t.normal(size=clean_t.shape) * scale_t if rho > 0 else 0.0)
    y_f = sf = None
    if benchmark == "B6":
        assert xf is not None and tf is not None
        clean_f = heat_flux_np(xf, tf, k, C, amplitude)
        scale_f = max(float(np.max(np.abs(clean_f))), np.finfo(float).eps) * max(rho, 1.0e-12)
        rng_f = np.random.default_rng(int(data_seed) + 1_000_003)
        y_f = clean_f + (rng_f.normal(size=clean_f.shape) * scale_f if rho > 0 else 0.0)
        sf = np.full(clean_f.shape, scale_f)
    return HeatAnalyticObservations(
        benchmark,
        xt,
        tt,
        y_t,
        np.full(clean_t.shape, scale_t),
        xf,
        tf,
        y_f,
        sf,
        int(data_seed),
        rho,
        {"k": float(k), "C": float(C), "a": float(amplitude)},
    )


def _objective(data: HeatAnalyticObservations, *, k: float, C: float, amplitude: float) -> float:
    prediction = heat_temperature_np(data.x_temperature, data.t_temperature, k, C, amplitude)
    total = float(np.sum(((prediction - data.y_temperature) / data.sigma_temperature) ** 2))
    if data.benchmark == "B6":
        assert data.x_flux is not None and data.t_flux is not None and data.y_flux is not None and data.sigma_flux is not None
        prediction_f = heat_flux_np(data.x_flux, data.t_flux, k, C, amplitude)
        total += float(np.sum(((prediction_f - data.y_flux) / data.sigma_flux) ** 2))
    return 0.5 * total


def _golden_minimize(objective: Any, lower: float, upper: float, *, iterations: int = 100) -> tuple[float, float]:
    """Deterministic scalar bounded minimisation in log coordinates."""

    if not lower < upper:
        raise ValueError("golden-section bounds must be ordered")
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    a, b = float(lower), float(upper)
    c, d = b - (b - a) / phi, a + (b - a) / phi
    fc, fd = float(objective(c)), float(objective(d))
    for _ in range(int(iterations)):
        if fc <= fd:
            b, d, fd = d, c, fc
            c = b - (b - a) / phi
            fc = float(objective(c))
        else:
            a, c, fc = c, d, fd
            d = a + (b - a) / phi
            fd = float(objective(d))
    z = (a + b) / 2.0
    return z, float(objective(z))


def profile_heat_observation(
    data: HeatAnalyticObservations,
    *,
    parameter_grid: np.ndarray | None = None,
    reference_k: float = DEFAULT_K,
    known_C: float = DEFAULT_C,
    known_amplitude: float = DEFAULT_AMPLITUDE,
    reference_C: float | None = None,
    reference_amplitude: float | None = None,
    nuisance_log_bounds: tuple[float, float] = DEFAULT_LOG_NUISANCE_BOUNDS,
) -> dict[str, Any]:
    """Compute an independent profile over ``k`` for one B1--B6 dataset.

    ``B4``/``B5`` use bounded variable projection for the nuisance amplitude;
    ``B3``/``B6`` optimise ``log(C)`` by a fixed golden-section search.  The
    returned status and boundary fields prevent a search boundary from being
    misreported as a confidence interval.
    """

    reference_k = float(reference_k)
    known_C = float(known_C)
    known_amplitude = float(known_amplitude)
    reference_C = known_C if reference_C is None else float(reference_C)
    reference_amplitude = known_amplitude if reference_amplitude is None else float(reference_amplitude)
    if reference_k <= 0 or known_C <= 0 or reference_C <= 0 or known_amplitude <= 0 or reference_amplitude <= 0:
        raise ValueError("reference and known positive parameters must be valid")
    if parameter_grid is None:
        parameter_grid = frozen_profile_grid(reference_k)
    grid = np.asarray(parameter_grid, dtype=np.float64).reshape(-1)
    if grid.size < 31 or np.any(~np.isfinite(grid)) or np.any(grid <= 0):
        raise ValueError("parameter_grid must contain at least 31 finite positive values")
    if np.any(np.diff(grid) <= 0):
        raise ValueError("parameter_grid must be strictly increasing")
    low, high = map(float, nuisance_log_bounds)
    if not low < high:
        raise ValueError("nuisance_log_bounds must be ordered")
    rows: list[dict[str, Any]] = []
    for k_value in grid:
        k_value = float(k_value)
        nuisance: dict[str, float] = {}
        boundary = False
        if data.benchmark in {"B4", "B5"}:
            basis = heat_temperature_np(data.x_temperature, data.t_temperature, k_value, known_C, 1.0)
            weights = 1.0 / data.sigma_temperature**2
            numerator = float(np.sum(weights * basis * data.y_temperature))
            denominator = float(np.sum(weights * basis * basis))
            amplitude = numerator / denominator if denominator > 0 else np.nan
            a_lower, a_upper = reference_amplitude * np.exp(low), reference_amplitude * np.exp(high)
            clipped = float(np.clip(amplitude, a_lower, a_upper))
            boundary = bool(clipped != amplitude or clipped in (a_lower, a_upper))
            amplitude = clipped
            C_value = known_C
            nuisance["a"] = amplitude
        elif data.benchmark in {"B3", "B6"}:
            def objective_log_C(log_c: float) -> float:
                return _objective(data, k=k_value, C=reference_C * float(np.exp(log_c)), amplitude=known_amplitude)
            log_c, _ = _golden_minimize(objective_log_C, low, high)
            C_value = reference_C * float(np.exp(log_c))
            amplitude = known_amplitude
            nuisance["C"] = C_value
            boundary = bool(abs(log_c - low) < 1.0e-8 or abs(log_c - high) < 1.0e-8)
        else:
            C_value, amplitude = known_C, known_amplitude
        value = _objective(data, k=k_value, C=C_value, amplitude=amplitude)
        rows.append({
            "scan_parameter": "k",
            "scan_value": k_value,
            "scan_log_offset": float(np.log(k_value / reference_k)),
            "nuisance": nuisance,
            "objective_half_chi2": float(value),
            "status": "BOUNDARY" if boundary else "PASS",
            "boundary": boundary,
        })
    objectives = np.asarray([r["objective_half_chi2"] for r in rows], dtype=np.float64)
    minimum_index = int(np.argmin(objectives))
    minimum_value = float(objectives[minimum_index])
    span = float(np.max(objectives) - np.min(objectives))
    # This scale-relative test only identifies a numerically flat profile; it
    # does not turn a broad but informative profile into a confidence interval.
    flat = bool(span <= 1.0e-7 * max(1.0, abs(float(np.max(objectives))), abs(minimum_value)))
    local_minima = [] if flat else [i for i in range(1, len(rows) - 1) if objectives[i] <= objectives[i - 1] and objectives[i] <= objectives[i + 1]]
    for row in rows:
        row["objective_delta_half_chi2"] = float(row["objective_half_chi2"] - minimum_value)
    boundary_truncated = bool(minimum_index in (0, len(rows) - 1)) and not flat
    profile_status = "FLAT" if flat else ("BOUNDARY_TRUNCATED" if boundary_truncated else "PASS")
    nuisance_boundary_count = int(sum(bool(row["boundary"]) for row in rows))
    return {
        "schema_version": 1,
        "reference_kind": "independent_analytic_heat_profile",
        "protocol_id": "reliability_audit_v1",
        "benchmark": data.benchmark,
        "grid_rule": "31 log-spaced values in [reference/3, 3*reference]",
        "reference_k": float(reference_k),
        "known_C": known_C,
        "known_amplitude": known_amplitude,
        "reference_C": reference_C,
        "reference_amplitude": reference_amplitude,
        "nuisance_log_bounds": [low, high],
        "observations": data.to_jsonable(),
        "points": rows,
        "minimum_index": minimum_index,
        "minimum_scan_value": float(grid[minimum_index]),
        "minimum_objective_half_chi2": minimum_value,
        "objective_span_half_chi2": span,
        "flat_profile": flat,
        "boundary_truncated": boundary_truncated,
        "nuisance_boundary_count": nuisance_boundary_count,
        "any_nuisance_boundary": bool(nuisance_boundary_count),
        "local_minima_count": len(local_minima),
        "multimodal": bool(len(local_minima) > 1),
        "profile_status": profile_status,
    }


def write_profile_json(profile: Mapping[str, Any], path: str | Path) -> None:
    """Write a profile artifact with stable formatting."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(profile, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


__all__ = [
    "DEFAULT_C",
    "DEFAULT_K",
    "DEFAULT_AMPLITUDE",
    "DEFAULT_X",
    "DEFAULT_MULTI_TIMES",
    "DEFAULT_EARLY_TIMES",
    "HeatAnalyticObservations",
    "default_observation_design",
    "frozen_profile_grid",
    "generate_analytic_observations",
    "heat_temperature_np",
    "heat_flux_np",
    "profile_heat_observation",
    "write_profile_json",
]
