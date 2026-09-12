"""Reliability-aware gamma paths and selective decisions for RI-2 records.

The functions here keep the finite-gamma SAEPS curvature separate from the
independent observation Fisher information.  Decisions use only checkpoint
 diagnostics (fit status, observation information, and fixed numerical rules);
truth is consumed only by the evaluation helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

# Frozen by the reliability_audit_v1 protocol.  Do not select a value per run.
GAMMA_ALPHA_GRID: tuple[float, ...] = (1.0e-12, 1.0e-10, 1.0e-8, 1.0e-6, 1.0e-4, 1.0e-2)
DEFAULT_RANK_TOLERANCE = 1.0e-10
DEFAULT_INFORMATION_FLOOR = 1.0
DEFAULT_ERROR_TOLERANCE = float(np.log(1.10))


def _as_matrix(value: Any, name: str) -> np.ndarray:
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} contains non-finite values")
    return matrix


def _sym(value: np.ndarray) -> np.ndarray:
    return 0.5 * (value + value.T)


def _eigh(value: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eigenvalues, eigenvectors = np.linalg.eigh(_sym(value))
    order = np.argsort(eigenvalues)[::-1]
    return eigenvalues[order], eigenvectors[:, order]


def _rank_cutoff(scale: float, relative_tolerance: float) -> float:
    # Include a floating-point floor so tiny absolute round-off in a nearly
    # zero projected matrix is reported as unresolved rather than as rank.
    return max(float(relative_tolerance) * max(float(scale), np.finfo(np.float64).tiny), 100.0 * np.finfo(np.float64).eps * max(1.0, float(scale)))


def _positive_values(eigenvalues: np.ndarray, relative_tolerance: float) -> tuple[np.ndarray, float]:
    scale = max(float(np.max(np.abs(eigenvalues), initial=0.0)), np.finfo(np.float64).eps)
    cutoff = _rank_cutoff(scale, relative_tolerance)
    return eigenvalues[eigenvalues > cutoff], cutoff


def effective_rank(matrix: Any, relative_tolerance: float = DEFAULT_RANK_TOLERANCE) -> int:
    """SVD rank using the declared relative tolerance and round-off floor."""
    if relative_tolerance <= 0:
        raise ValueError("relative_tolerance must be positive")
    values = np.linalg.svd(_as_matrix(matrix, "matrix"), compute_uv=False)
    if values.size == 0 or values[0] <= 0:
        return 0
    return int(np.count_nonzero(values > _rank_cutoff(float(values[0]), relative_tolerance)))


def _projector(eigenvectors: np.ndarray, rank: int) -> np.ndarray:
    if rank <= 0:
        return np.zeros((eigenvectors.shape[0], eigenvectors.shape[0]), dtype=np.float64)
    basis = eigenvectors[:, :rank]
    return basis @ basis.T


def gamma_path_from_jacobians(
    jacobian_state: Any,
    jacobian_parameter: Any,
    *,
    gamma_alpha_grid: Sequence[float] = GAMMA_ALPHA_GRID,
    relative_tolerance: float = DEFAULT_RANK_TOLERANCE,
) -> dict[str, Any]:
    """Compute full finite-gamma curvature and subspace diagnostics.

    SVD of ``Jw`` is used to evaluate the projection without forming a large
    state normal inverse.  The returned ``F0`` is the exact SVD zero-damping
    projection and is reported as a diagnostic, never as a claim of global
    identifiability.
    """
    jw = _as_matrix(jacobian_state, "jacobian_state")
    jp = _as_matrix(jacobian_parameter, "jacobian_parameter")
    if jw.shape[0] != jp.shape[0]:
        raise ValueError("jacobian_state and jacobian_parameter need equal rows")
    grid = tuple(float(value) for value in gamma_alpha_grid)
    if not grid or any(value <= 0 or not np.isfinite(value) for value in grid):
        raise ValueError("gamma_alpha_grid must contain positive finite values")
    if relative_tolerance <= 0:
        raise ValueError("relative_tolerance must be positive")

    # Compact SVD gives U and singular values in residual space.
    u, singular_values, _ = np.linalg.svd(jw, full_matrices=False)
    state_scale = float(singular_values[0] ** 2) if singular_values.size else 0.0
    if state_scale <= 0:
        state_scale = float(np.finfo(np.float64).eps)
    cutoff = relative_tolerance * (float(singular_values[0]) if singular_values.size else 0.0)
    state_rank = int(np.count_nonzero(singular_values > cutoff)) if singular_values.size else 0
    # U columns with zero singular values contribute no state projector.
    if state_rank:
        u_active = u[:, :state_rank]
        s2 = singular_values[:state_rank] ** 2
    else:
        u_active = np.zeros((jw.shape[0], 0), dtype=np.float64)
        s2 = np.zeros((0,), dtype=np.float64)
    jp_proj = jp.copy()
    if state_rank:
        jp_proj = u_active.T @ jp
    f0 = jp.T @ jp
    if state_rank:
        f0 = f0 - jp_proj.T @ jp_proj
    f0 = _sym(f0)
    f0_values, f0_vectors = _eigh(f0)
    f0_scale = max(float(np.max(np.abs(f0_values), initial=0.0)), np.finfo(np.float64).eps)
    f0_rank = int(np.count_nonzero(f0_values > _rank_cutoff(f0_scale, relative_tolerance)))
    fraw = _sym(jp.T @ jp)
    fraw_values, fraw_vectors = _eigh(fraw)
    fraw_scale = max(float(np.max(np.abs(fraw_values), initial=0.0)), np.finfo(np.float64).eps)
    fraw_rank = int(np.count_nonzero(fraw_values > _rank_cutoff(fraw_scale, relative_tolerance)))
    p0 = _projector(f0_vectors, f0_rank)

    path: list[dict[str, Any]] = []
    for alpha in grid:
        gamma = float(alpha * state_scale)
        # I - U diag(s^2/(s^2 + gamma)) U^T applied to Jp.
        retained = jp.copy()
        if state_rank:
            coefficients = s2 / (s2 + gamma)
            retained = jp - u_active @ (coefficients[:, None] * jp_proj)
        f_gamma = _sym(jp.T @ retained)
        eigenvalues, eigenvectors = _eigh(f_gamma)
        scale = max(float(np.max(np.abs(eigenvalues), initial=0.0)), np.finfo(np.float64).eps)
        positive, rank_cutoff = _positive_values(eigenvalues, relative_tolerance)
        rank = int(positive.size)
        projector = _projector(eigenvectors, rank)
        projector_distance = float(np.linalg.norm(projector - p0, ord="fro") / np.sqrt(2.0))
        condition = None if positive.size == 0 else float(positive[0] / positive[-1])
        path.append(
            {
                "gamma_alpha": alpha,
                "gamma": gamma,
                "eigenvalues": eigenvalues.tolist(),
                "rank": rank,
                "rank_cutoff": rank_cutoff,
                "condition_number_positive": condition,
                "projector_distance_to_F0": projector_distance,
                "F_gamma": f_gamma.tolist(),
            }
        )
    positive_path = [row["eigenvalues"] for row in path]
    # A score in [0, 1] used only for fixed threshold risk/coverage curves.
    if path:
        normalized_floor = []
        for row in path:
            vals = np.asarray(row["eigenvalues"], dtype=np.float64)
            positive, _ = _positive_values(vals, relative_tolerance)
            top = max(float(np.max(np.abs(vals), initial=0.0)), np.finfo(np.float64).eps)
            normalized_floor.append(0.0 if positive.size == 0 else float(np.min(positive) / top))
        gamma_stability = float(min(normalized_floor))
    else:
        gamma_stability = 0.0
    return {
        "gamma_alpha_grid": list(grid),
        "gamma_scale": state_scale,
        "gamma_scale_definition": "lambda_max(J_state.T @ J_state)",
        "state_singular_values": singular_values.tolist(),
        "state_rank": state_rank,
        "F_raw": fraw.tolist(),
        "F_raw_eigenvalues": fraw_values.tolist(),
        "F_raw_rank": fraw_rank,
        "F0": f0.tolist(),
        "F0_eigenvalues": f0_values.tolist(),
        "F0_rank": f0_rank,
        "gamma_path": path,
        "gamma_stability_score": gamma_stability,
    }


def _fim_rank_and_values(fim: Any, relative_tolerance: float) -> tuple[int, np.ndarray, np.ndarray]:
    values, vectors = _eigh(_as_matrix(fim, "I_obs"))
    scale = max(float(np.max(np.abs(values), initial=0.0)), np.finfo(np.float64).eps)
    rank = int(np.count_nonzero(values > _rank_cutoff(scale, relative_tolerance)))
    return rank, values, vectors


def classify_record(
    manifest: Mapping[str, Any],
    path_result: Mapping[str, Any] | None,
    *,
    relative_tolerance: float = DEFAULT_RANK_TOLERANCE,
    information_floor: float = DEFAULT_INFORMATION_FLOOR,
) -> dict[str, Any]:
    """Apply the fixed abstaining decision rule using diagnostics only."""
    if information_floor <= 0:
        raise ValueError("information_floor must be positive")
    unknown = manifest.get("unknown_parameters") or []
    n_unknown = len(unknown)
    if str(manifest.get("execution_status", "")) != "PASS" or str(manifest.get("fit_status", "")) != "PASS":
        return {"decision": "INVALID_CHECKPOINT", "accepted": False, "selective_candidate": False, "reason": "execution_or_fit_gate_failed", "confidence_score": 0.0}
    if path_result is None:
        return {"decision": "UNRESOLVED_NUMERICAL", "accepted": False, "selective_candidate": False, "reason": "gamma_path_unavailable", "confidence_score": 0.0}
    try:
        obs_rank, obs_values, obs_vectors = _fim_rank_and_values(manifest["_I_obs_matrix"], relative_tolerance)
    except (KeyError, ValueError):
        return {"decision": "UNRESOLVED_NUMERICAL", "accepted": False, "selective_candidate": False, "reason": "observation_fim_unavailable", "confidence_score": 0.0}
    benchmark = str(manifest.get("benchmark", "")).upper()
    named = {
        "B3": {"identifiable": ["log(k)-log(C)"], "null": ["log(k)+log(C)"]},
        "B4": {"identifiable": ["log(a)-pi^2*t_star*k/C"], "null": ["state/amplitude compensation tangent"]},
    }.get(benchmark, {})
    subspace = {
        "coordinate_system": manifest.get("coordinate_system", "log-parameter coordinates"),
        "rank": obs_rank,
        "eigenvectors_descending": obs_vectors[:, :obs_rank].tolist() if obs_rank else [],
        "named_combinations": named,
        "interpretation": "Independent observation-FIM supported directions; parameter combinations are reported as subspaces, not individual confidence scores.",
    }
    min_information = float(np.min(obs_values)) if obs_values.size else 0.0
    gamma_score = float(path_result.get("gamma_stability_score", 0.0))
    information_score = float(min(1.0, max(0.0, min_information / information_floor)))
    confidence_score = float(min(gamma_score, information_score))
    # Candidate means the checkpoint and independent physical rank are valid
    # enough to appear on a selective risk/coverage curve.  A weak candidate is
    # still abstained from the declared reliable set below.
    selective_candidate = bool(obs_rank >= n_unknown)
    if obs_rank < n_unknown:
        return {"decision": "WEAK_OR_CONFOUNDED", "accepted": False, "selective_candidate": False, "reason": "independent_observation_rank_deficient", "confidence_score": 0.0, "observation_rank": obs_rank, "observation_eigenvalues": obs_values.tolist(), "identified_subspace": subspace, "n_unknown": n_unknown}
    elif min_information < information_floor:
        decision, accepted, reason = "WEAK_OR_CONFOUNDED", False, "independent_information_below_floor"
    elif int(path_result.get("F0_rank", 0)) < n_unknown:
        decision, accepted, reason = "WEAK_OR_CONFOUNDED", False, "zero_damping_state_elimination_rank_deficient"
    else:
        decision, accepted, reason = "SUPPORTED_COMBINATION", True, "full_rank_and_information_gate"
    return {
        "decision": decision,
        "accepted": accepted,
        "selective_candidate": selective_candidate,
        "reason": reason,
        "observation_rank": obs_rank,
        "observation_eigenvalues": obs_values.tolist(),
        "identified_subspace": subspace,
        "minimum_observation_information": min_information,
        "information_floor": information_floor,
        "confidence_score": confidence_score,
        "gamma_stability_score": gamma_score,
        "F0_rank": int(path_result.get("F0_rank", 0)),
        "n_unknown": n_unknown,
    }


def target_log_error(manifest: Mapping[str, Any]) -> float | None:
    """Return the predeclared identifiable target error for one pilot record."""
    estimates = manifest.get("parameter_estimates") or {}
    truth = manifest.get("physical_truth") or {}
    benchmark = str(manifest.get("benchmark", "")).upper()
    try:
        if benchmark in {"B1", "B2"}:
            return float(abs(np.log(float(estimates["k"]) / float(truth["k"]))))
        if benchmark == "B3":
            estimated = np.log(float(estimates["k"]) / float(estimates["C"]))
            reference = np.log(float(truth["k"]) / float(truth["C"]))
            return float(abs(estimated - reference))
        if benchmark == "B4":
            # Single-time temperature identifies log(a) - pi^2*t*k/C.
            t_star = 0.2
            estimated = np.log(float(estimates["a"])) - np.pi**2 * t_star * float(estimates["k"]) / float(truth["C"])
            reference = np.log(float(truth["a"])) - np.pi**2 * t_star * float(truth["k"]) / float(truth["C"])
            return float(abs(estimated - reference))
    except (KeyError, TypeError, ValueError, FloatingPointError):
        return None
    return None


def selective_metrics(
    records: Sequence[Mapping[str, Any]],
    *,
    thresholds: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
    error_tolerance: float = DEFAULT_ERROR_TOLERANCE,
) -> dict[str, Any]:
    """Compute denominator-preserving risk/coverage from diagnostic scores."""
    rows: list[dict[str, Any]] = []
    for record in records:
        diagnostics = dict(record.get("decision_record") or {})
        error = target_log_error(record)
        rows.append({"run_id": record.get("run_id"), "score": float(diagnostics.get("confidence_score", 0.0)), "eligible": bool(diagnostics.get("selective_candidate", diagnostics.get("accepted", False))), "error": error, "benchmark": record.get("benchmark")})
    curves: list[dict[str, Any]] = []
    total = len(rows)
    for threshold in thresholds:
        threshold = float(threshold)
        selected = [row for row in rows if row["eligible"] and row["score"] >= threshold]
        evaluated = [row for row in selected if row["error"] is not None]
        false_reliable = sum(float(row["error"]) > error_tolerance for row in evaluated)
        curves.append({"threshold": threshold, "accepted": len(selected), "evaluated": len(evaluated), "planned_denominator": total, "coverage": (len(selected) / total if total else None), "risk": (false_reliable / len(evaluated) if evaluated else None), "false_reliable_count": false_reliable, "error_tolerance": error_tolerance})
    # Explicitly retain the all-abstain operating point.  Its undefined risk
    # is represented as null; coverage is zero, so universal abstention cannot
    # be mistaken for a useful zero-risk method.
    curves.append({"threshold": "ALL_ABSTAIN", "accepted": 0, "evaluated": 0, "planned_denominator": total, "coverage": 0.0 if total else None, "risk": None, "false_reliable_count": 0, "error_tolerance": error_tolerance})
    return {"planned_denominator": total, "rows": rows, "risk_coverage": curves, "all_abstain": curves[-1], "error_tolerance": error_tolerance}


__all__ = [
    "GAMMA_ALPHA_GRID", "DEFAULT_RANK_TOLERANCE", "DEFAULT_INFORMATION_FLOOR", "DEFAULT_ERROR_TOLERANCE",
    "effective_rank", "gamma_path_from_jacobians", "classify_record", "target_log_error", "selective_metrics",
]
