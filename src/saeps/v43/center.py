"""Allen--Cahn development center engineering for small state networks."""

from __future__ import annotations

import copy
import math
from typing import Any, Callable

import torch

from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum


StateObjective = Callable[[torch.Tensor], torch.Tensor]
ResidualAtState = Callable[[torch.Tensor], torch.Tensor]


def exact_gauss_newton_refine(
    residual_at_state: ResidualAtState,
    theta0: torch.Tensor,
    specification: dict[str, Any],
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Deterministic damped GN refinement with audited backtracking."""

    current = theta0.detach().clone()
    damping = float(specification["initial_damping"])
    minimum_damping = float(specification["minimum_damping"])
    maximum_damping = float(specification["maximum_damping"])
    maximum_relative_step = float(specification["maximum_relative_step"])
    history: list[dict[str, Any]] = []
    for iteration in range(int(specification["maximum_iterations"])):
        residual = residual_at_state(current).reshape(-1)
        jacobian = torch.func.jacrev(lambda state: residual_at_state(state).reshape(-1))(current)
        count = residual.numel()
        gradient = jacobian.T @ residual / count
        normal = jacobian.T @ jacobian / count
        identity = torch.eye(current.numel(), dtype=current.dtype, device=current.device)
        step = torch.linalg.solve(normal + damping * identity, -gradient)
        state_scale = max(float(torch.linalg.vector_norm(current).item()), 1.0)
        step_norm = float(torch.linalg.vector_norm(step).item())
        maximum_step = maximum_relative_step * state_scale
        if step_norm > maximum_step:
            step = step * (maximum_step / step_norm)
        loss = float((0.5 * torch.mean(residual.square())).item())
        accepted = False
        accepted_factor = None
        candidate_loss = loss
        candidate_state = current
        with torch.no_grad():
            for factor_value in specification["backtracking_factors"]:
                factor = float(factor_value)
                trial = current + factor * step
                trial_residual = residual_at_state(trial).reshape(-1)
                trial_loss = float((0.5 * torch.mean(trial_residual.square())).item())
                if math.isfinite(trial_loss) and trial_loss < candidate_loss:
                    accepted = True
                    accepted_factor = factor
                    candidate_loss = trial_loss
                    candidate_state = trial.detach().clone()
                    break
        normalized_gradient = float(torch.linalg.vector_norm(gradient).item()) / state_scale
        history.append(
            {
                "iteration": iteration,
                "loss_mean": loss,
                "candidate_loss_mean": candidate_loss,
                "actual_decrease": loss - candidate_loss,
                "normalized_gradient": normalized_gradient,
                "damping": damping,
                "step_norm": float(torch.linalg.vector_norm(step).item()),
                "accepted": accepted,
                "accepted_factor": accepted_factor,
            }
        )
        if accepted:
            current = candidate_state
            damping = max(minimum_damping, damping * float(specification["accepted_damping_factor"]))
        else:
            damping = min(maximum_damping, damping * float(specification["rejected_damping_factor"]))
        if normalized_gradient <= float(specification["normalized_gradient_tolerance"]):
            break
        if damping >= maximum_damping and not accepted:
            break
    return current, {
        "method": "explicit_damped_gauss_newton_backtracking",
        "iterations": len(history),
        "accepted_steps": sum(row["accepted"] for row in history),
        "history": history,
    }


def allen_center_candidates(
    residual_at_state: ResidualAtState,
    objective: StateObjective,
    theta0: torch.Tensor,
    seed: int,
    local_specification: dict[str, Any],
    specification: dict[str, Any],
) -> tuple[torch.Tensor | None, dict[str, Any]]:
    """Try preregistered deterministic starts, accepting only the exact gate."""

    generator = torch.Generator(device="cpu").manual_seed(seed + int(specification["perturbation_seed_offset"]))
    direction = torch.randn(theta0.numel(), dtype=theta0.dtype, generator=generator)
    direction = direction / torch.linalg.vector_norm(direction)
    state_scale = max(float(torch.linalg.vector_norm(theta0).item()), 1.0)
    candidates: list[dict[str, Any]] = []
    best_state: torch.Tensor | None = None
    best_loss = math.inf
    for start_index, radius_value in enumerate(specification["start_relative_radii"]):
        radius = float(radius_value)
        start = theta0.detach().clone() + radius * state_scale * direction
        refined, gn = exact_gauss_newton_refine(residual_at_state, start, specification["gauss_newton"])
        local = copy.deepcopy(local_specification)
        local["maximum_escape_cycles"] = int(specification["post_gn_escape_cycles"])
        state, audit = optimize_state_local_minimum(objective, refined, local)
        final_state = state if state is not None else refined
        diagnostics, _, _, _ = exact_state_diagnostics(objective, final_state, local_specification)
        passed = diagnostics["local_minimum_gate"] == "PASS"
        row = {
            "start_index": start_index,
            "start_relative_radius": radius,
            "gauss_newton": gn,
            "post_gn_local_audit": audit,
            "final_exact_diagnostics": diagnostics,
            "status": "PASS" if passed else "CHECKPOINT_INVALID",
        }
        candidates.append(row)
        if passed and diagnostics["loss_mean"] < best_loss:
            best_loss = float(diagnostics["loss_mean"])
            best_state = final_state.detach().clone()
    return best_state, {
        "method": "deterministic_multistart_GN_then_exact_local_gate",
        "selection_uses": "exact_center_validity_then_minimum_loss_only",
        "candidates": candidates,
        "selected_candidate": (
            min(
                (row for row in candidates if row["status"] == "PASS"),
                key=lambda row: row["final_exact_diagnostics"]["loss_mean"],
            )["start_index"]
            if best_state is not None
            else None
        ),
        "status": "PASS" if best_state is not None else "CHECKPOINT_INVALID",
    }

