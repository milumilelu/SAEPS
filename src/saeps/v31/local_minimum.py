"""Exact-Hessian local-minimum checks and saddle escape for small state models."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import torch

from saeps.profile import _reoptimize_point


StateObjective = Callable[[torch.Tensor], torch.Tensor]


def exact_state_diagnostics(
    objective: StateObjective,
    theta: torch.Tensor,
    specification: dict[str, Any],
) -> tuple[dict[str, Any], torch.Tensor, torch.Tensor, torch.Tensor]:
    state = theta.detach().clone().requires_grad_(True)
    loss = objective(state)
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise ValueError("state objective must return a finite scalar")
    gradient = torch.autograd.grad(loss, state, create_graph=False)[0]
    hessian = torch.func.hessian(objective)(theta.detach())
    if not torch.all(torch.isfinite(hessian)):
        raise ValueError("state Hessian contains non-finite values")
    symmetric = 0.5 * (hessian + hessian.T)
    eigenvalues, eigenvectors = torch.linalg.eigh(symmetric)
    spectral_scale = max(float(torch.max(torch.abs(eigenvalues)).item()), 1.0)
    tau = max(
        float(specification["hessian_absolute_tolerance"]),
        float(specification["hessian_relative_tolerance"]) * spectral_scale,
    )
    state_scale = max(float(torch.linalg.vector_norm(theta).item()), 1.0)
    normalized_gradient = float(torch.linalg.vector_norm(gradient).item()) / state_scale
    gradient_pass = normalized_gradient <= float(
        specification["normalized_gradient_tolerance"]
    )
    hessian_pass = float(eigenvalues[0].item()) >= -tau
    symmetry = float(torch.linalg.matrix_norm(hessian - hessian.T).item()) / max(
        float(torch.linalg.matrix_norm(hessian).item()), 1.0e-30
    )
    diagnostics = {
        "loss_mean": float(loss.item()),
        "normalized_objective_gradient": normalized_gradient,
        "gradient_tolerance": float(specification["normalized_gradient_tolerance"]),
        "gradient_pass": gradient_pass,
        "minimum_state_eigenvalue_mean_objective": float(eigenvalues[0].item()),
        "maximum_state_eigenvalue_mean_objective": float(eigenvalues[-1].item()),
        "hessian_tau": tau,
        "hessian_pass": hessian_pass,
        "negative_eigenvalue_count": int(torch.count_nonzero(eigenvalues < -tau).item()),
        "hessian_symmetry_relative_error": symmetry,
        "local_minimum_gate": "PASS" if gradient_pass and hessian_pass else "FAIL",
    }
    return diagnostics, gradient.detach(), eigenvalues.detach(), eigenvectors.detach()


def negative_direction_probe(
    objective: StateObjective,
    theta: torch.Tensor,
    eigenvector: torch.Tensor,
    radii: list[float],
) -> dict[str, Any]:
    center_loss = float(objective(theta).item())
    scale = max(float(torch.linalg.vector_norm(theta).item()), 1.0)
    evaluations: list[dict[str, Any]] = []
    best_state = theta.detach().clone()
    best_loss = center_loss
    best_descriptor: dict[str, Any] | None = None
    with torch.no_grad():
        for relative_radius in radii:
            for sign in (-1.0, 1.0):
                step = sign * float(relative_radius) * scale * eigenvector
                candidate = theta + step
                loss = float(objective(candidate).item())
                row = {
                    "relative_radius": float(relative_radius),
                    "sign": int(sign),
                    "absolute_step_norm": float(torch.linalg.vector_norm(step).item()),
                    "loss_mean": loss,
                    "delta_loss": loss - center_loss,
                }
                evaluations.append(row)
                if math.isfinite(loss) and loss < best_loss:
                    best_loss = loss
                    best_state = candidate.detach().clone()
                    best_descriptor = row
    return {
        "center_loss_mean": center_loss,
        "evaluations": evaluations,
        "descent_found": best_descriptor is not None,
        "best": best_descriptor,
        "best_loss_mean": best_loss,
        "best_state": best_state,
    }


def _polish(
    objective: StateObjective,
    theta: torch.Tensor,
    optimizer: dict[str, Any],
    stopping: dict[str, Any],
) -> tuple[torch.Tensor, dict[str, Any]]:
    coordinate = torch.zeros(1, dtype=theta.dtype, device=theta.device)
    point = _reoptimize_point(
        lambda state, _: objective(state),
        theta,
        coordinate,
        0.0,
        optimizer,
        stopping,
    )
    state = point.theta.detach().clone() if point.theta is not None else theta.detach().clone()
    return state, {
        "status": point.status,
        "failure_reason": point.failure_reason,
        "loss_mean": point.loss,
        "outer_steps": point.outer_steps,
        "closure_calls": point.closure_calls,
        "normalized_gradient": point.normalized_gradient,
        "gradient_pass": point.gradient_converged,
        "plateau_pass": point.loss_plateau,
    }


def _candidate_steps(
    gradient: torch.Tensor,
    eigenvalues: torch.Tensor,
    eigenvectors: torch.Tensor,
    state_scale: float,
    relative_radius: float,
    tau: float,
    factors: list[float],
) -> list[tuple[str, torch.Tensor]]:
    radius = relative_radius * state_scale
    candidates: list[tuple[str, torch.Tensor]] = []
    minimum_vector = eigenvectors[:, 0]
    if float(eigenvalues[0].item()) < -tau:
        for factor in factors:
            candidates.append((f"negative_minus_{factor}", -factor * radius * minimum_vector))
            candidates.append((f"negative_plus_{factor}", factor * radius * minimum_vector))
    gradient_norm = float(torch.linalg.vector_norm(gradient).item())
    if gradient_norm > 0.0:
        for factor in factors:
            candidates.append((f"steepest_{factor}", -factor * radius * gradient / gradient_norm))
    shift = max(tau - float(eigenvalues[0].item()), tau)
    spectral_gradient = eigenvectors.T @ gradient
    newton = -(eigenvectors @ (spectral_gradient / (eigenvalues + shift)))
    newton_norm = float(torch.linalg.vector_norm(newton).item())
    if math.isfinite(newton_norm) and newton_norm > 0.0:
        if newton_norm > radius:
            newton = newton * (radius / newton_norm)
        for factor in factors:
            candidates.append((f"shifted_newton_{factor}", factor * newton))
    return candidates


def optimize_state_local_minimum(
    objective: StateObjective,
    theta0: torch.Tensor,
    specification: dict[str, Any],
) -> tuple[torch.Tensor | None, dict[str, Any]]:
    """Use common first-order polish plus exact-Hessian trust-region saddle escape."""
    current, initial_polish = _polish(
        objective,
        theta0,
        specification["optimizer"],
        specification["stopping"],
    )
    history: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    relative_radius = float(specification["trust_initial_relative_radius"])
    minimum_radius = float(specification["trust_minimum_relative_radius"])
    maximum_radius = float(specification["trust_maximum_relative_radius"])
    minimum_decrease = float(specification["minimum_actual_decrease"])
    factors = [float(value) for value in specification["trust_backtracking_factors"]]

    for cycle in range(int(specification["maximum_escape_cycles"]) + 1):
        diagnostics, gradient, eigenvalues, eigenvectors = exact_state_diagnostics(
            objective, current, specification
        )
        diagnostics["cycle"] = cycle
        diagnostics["trust_relative_radius"] = relative_radius
        history.append(diagnostics)
        if diagnostics["local_minimum_gate"] == "PASS":
            return current, {
                "status": "PASS",
                "failure_reason": None,
                "initial_polish": initial_polish,
                "cycles": history,
                "negative_direction_probes": probes,
                "final": diagnostics,
                "escape_cycles_used": cycle,
            }
        if cycle == int(specification["maximum_escape_cycles"]):
            break

        probe_best_state: torch.Tensor | None = None
        probe_best_loss: float | None = None
        if float(eigenvalues[0].item()) < -float(diagnostics["hessian_tau"]):
            probe = negative_direction_probe(
                objective,
                current,
                eigenvectors[:, 0],
                [float(value) for value in specification["negative_probe_relative_radii"]],
            )
            probe_record = {key: value for key, value in probe.items() if key != "best_state"}
            probe_record["cycle"] = cycle
            probes.append(probe_record)
            if probe["descent_found"]:
                probe_best_state = probe["best_state"]
                probe_best_loss = float(probe["best_loss_mean"])

        center_loss = float(diagnostics["loss_mean"])
        state_scale = max(float(torch.linalg.vector_norm(current).item()), 1.0)
        candidates = _candidate_steps(
            gradient,
            eigenvalues,
            eigenvectors,
            state_scale,
            relative_radius,
            float(diagnostics["hessian_tau"]),
            factors,
        )
        best_state = probe_best_state if probe_best_state is not None else current
        best_loss = probe_best_loss if probe_best_loss is not None else center_loss
        best_name: str | None = "registered_negative_probe" if probe_best_state is not None else None
        with torch.no_grad():
            for name, step in candidates:
                candidate = current + step
                candidate_loss = float(objective(candidate).item())
                if math.isfinite(candidate_loss) and candidate_loss < best_loss:
                    best_loss = candidate_loss
                    best_state = candidate.detach().clone()
                    best_name = name
        history[-1].update(
            {
                "accepted_candidate": best_name,
                "candidate_loss_mean": best_loss,
                "actual_decrease": center_loss - best_loss,
            }
        )
        if best_name is None or center_loss - best_loss <= minimum_decrease:
            relative_radius *= 0.5
            if relative_radius < minimum_radius:
                break
            continue
        current, polish = _polish(
            objective,
            best_state,
            specification["polish_optimizer"],
            specification["stopping"],
        )
        history[-1]["post_step_polish"] = polish
        relative_radius = min(relative_radius * 1.5, maximum_radius)

    final, _, _, _ = exact_state_diagnostics(objective, current, specification)
    return None, {
        "status": "NUMERICAL_FAILURE",
        "failure_reason": "combined first-order and exact second-order local-minimum gate failed",
        "initial_polish": initial_polish,
        "cycles": history,
        "negative_direction_probes": probes,
        "final": final,
        "escape_cycles_used": len(history) - 1,
    }
