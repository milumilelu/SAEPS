"""Independent E7 rescue protocol with separated stopping and certification.

This module deliberately lives beside, rather than inside, the historical E7 runner.
It keeps the historical anchor, gamma, steps and centre cache, but fixes the numerical
issue in the old runner: PyTorch LBFGS ``tolerance_grad`` is an unnormalised gradient,
whereas the paper gate is a residual-normalised norm. A short safeguarded Newton polish
then provides a local positive-Hessian objective-error certificate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import center_cache as C  # noqa: E402
import e3_saturation as E3  # noqa: E402
import e7_profile as E7  # noqa: E402
import repo_adapter as A  # noqa: E402

FLOOR = 1.0e-30


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def penalised(fit: dict, theta: torch.Tensor, lam: torch.Tensor, gamma: float) -> torch.Tensor:
    return C.objective(theta, lam, fit["points"], fit["local"], fit["architecture"]) + 0.5 * gamma * (
        theta - fit["theta"]
    ).pow(2).sum()


def normalized_gradient(gradient: torch.Tensor, fit: dict, state: torch.Tensor) -> float:
    return float(torch.linalg.vector_norm(gradient).item()) / (
        fit["residuals"] * max(float(torch.linalg.vector_norm(state.detach()).item()), 1.0)
    )


def lbfgs_refine(
    fit: dict,
    lam_value: torch.Tensor,
    theta_init: torch.Tensor,
    gamma: float,
    target: float,
    max_iterations: int,
    max_eval: int,
    raw_tolerance_override: float | None = None,
) -> dict:
    """Run LBFGS with a raw tolerance derived from the declared normalised target."""
    state = theta_init.detach().clone().requires_grad_(True)
    scale = fit["residuals"] * max(float(torch.linalg.vector_norm(state).item()), 1.0)
    raw_tolerance = target * scale if raw_tolerance_override is None else float(raw_tolerance_override)
    optimizer = torch.optim.LBFGS(
        [state],
        max_iter=max_iterations,
        max_eval=max_eval,
        history_size=50,
        tolerance_grad=raw_tolerance,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def closure():
        optimizer.zero_grad(set_to_none=True)
        value = penalised(fit, state, lam_value, gamma)
        value.backward()
        return value

    started = time.perf_counter()
    optimizer.step(closure)
    value = penalised(fit, state, lam_value, gamma)
    gradient = torch.autograd.grad(value, state)[0]
    normed = normalized_gradient(gradient, fit, state)
    iterations = int(optimizer.state[state].get("n_iter", 0))
    evaluations = int(optimizer.state[state].get("func_evals", 0))
    if normed <= target:
        stop_reason = "normalized_gradient_target"
    elif iterations >= max_iterations or evaluations >= max_eval:
        stop_reason = "iteration_or_evaluation_cap"
    else:
        stop_reason = "lbfgs_termination_without_target"
    return {
        "theta": state.detach().clone(),
        "phi": float(value.detach().item()),
        "gradient_norm": float(torch.linalg.vector_norm(gradient).item()),
        "normalized_gradient": normed,
        "max_abs_gradient": float(gradient.abs().max().item()),
        "raw_tolerance": raw_tolerance,
        "iterations": iterations,
        "function_evaluations": evaluations,
        "stop_reason": stop_reason,
        "wall_seconds": time.perf_counter() - started,
    }


def newton_polish(
    fit: dict,
    lam_value: torch.Tensor,
    result: dict,
    gamma: float,
    target: float,
    max_steps: int,
    c1: float,
    min_fraction: float,
    shift_floor: float,
) -> dict:
    """Safeguarded full-Newton polish with objective-decrease line search."""
    state = result["theta"].detach().clone().requires_grad_(True)
    history = []
    started = time.perf_counter()
    stop_reason = "newton_step_cap"
    for index in range(max_steps):
        objective = lambda s: penalised(fit, s, lam_value, gamma)
        value = objective(state)
        gradient = torch.autograd.grad(value, state, create_graph=False)[0]
        normed = normalized_gradient(gradient, fit, state)
        hessian = torch.autograd.functional.hessian(objective, state)
        hessian = 0.5 * (hessian + hessian.T)
        eigenvalues = torch.linalg.eigvalsh(hessian)
        min_eigenvalue = float(eigenvalues[0].item())
        shift = max(0.0, shift_floor - min_eigenvalue)
        system = hessian + shift * torch.eye(state.numel(), dtype=state.dtype)
        try:
            direction = torch.linalg.solve(system, -gradient)
        except RuntimeError:
            stop_reason = "newton_linear_solve_failure"
            break
        directional = float((gradient * direction).sum().item())
        if not math.isfinite(directional) or directional >= 0.0:
            direction = -gradient
            directional = -float((gradient * gradient).sum().item())
        if normed <= target:
            stop_reason = "newton_normalized_gradient_target"
            history.append({"step": index, "normalized_gradient": normed, "min_eigenvalue": min_eigenvalue, "shift": shift, "accepted_fraction": 0.0})
            break
        old_value = float(value.detach().item())
        fraction = 1.0
        accepted = False
        while fraction >= min_fraction:
            candidate = (state.detach() + fraction * direction).requires_grad_(True)
            candidate_value = float(objective(candidate).detach().item())
            if candidate_value <= old_value + c1 * fraction * directional:
                accepted = True
                break
            fraction *= 0.5
        history.append({"step": index, "normalized_gradient": normed, "min_eigenvalue": min_eigenvalue, "shift": shift, "accepted_fraction": fraction if accepted else 0.0})
        if not accepted:
            stop_reason = "newton_line_search_failure"
            break
        state = candidate
    value = penalised(fit, state, lam_value, gamma)
    gradient = torch.autograd.grad(value, state)[0]
    hessian = torch.autograd.functional.hessian(lambda s: penalised(fit, s, lam_value, gamma), state)
    hessian = 0.5 * (hessian + hessian.T)
    min_eigenvalue = float(torch.linalg.eigvalsh(hessian)[0].item())
    normed = normalized_gradient(gradient, fit, state)
    if normed <= target and stop_reason == "newton_step_cap":
        stop_reason = "newton_normalized_gradient_target"
    return {
        "theta": state.detach().clone(),
        "phi": float(value.detach().item()),
        "gradient_norm": float(torch.linalg.vector_norm(gradient).item()),
        "normalized_gradient": normed,
        "max_abs_gradient": float(gradient.abs().max().item()),
        "min_hessian_eigenvalue": min_eigenvalue,
        "positive_hessian": bool(min_eigenvalue > 0.0),
        "objective_error_bound": (
            float(torch.linalg.vector_norm(gradient).item()) ** 2 / (2.0 * min_eigenvalue)
            if min_eigenvalue > 0.0
            else None
        ),
        "newton_steps": len(history),
        "newton_stop_reason": stop_reason,
        "newton_history": history,
        "wall_seconds": time.perf_counter() - started,
    }


def solve_start(fit, lam_value, theta_init, gamma, solver):
    lbfgs = lbfgs_refine(
        fit,
        lam_value,
        theta_init,
        gamma,
        float(solver["normalized_gradient_target"]),
        int(solver["lbfgs_max_iterations"]),
        int(solver["lbfgs_max_eval"]),
    )
    polished = newton_polish(
        fit,
        lam_value,
        lbfgs,
        gamma,
        float(solver["newton_normalized_gradient_target"]),
        int(solver["newton_max_steps"]),
        float(solver["line_search_c1"]),
        float(solver["min_line_search_fraction"]),
        float(solver["hessian_shift_floor"]),
    )
    # The mapped raw tolerance and Newton polish are the normal path. If the
    # resulting certificate is still unavailable in a non-convex basin, a
    # predeclared strict raw-gradient fallback is used from the original start,
    # followed by the same polish. This is a solver safeguard, not a
    # result-dependent selection of a favourable branch.
    fallback = None
    if polished["normalized_gradient"] > float(solver["newton_normalized_gradient_target"]) or not polished["positive_hessian"]:
        fallback = lbfgs_refine(
            fit,
            lam_value,
            theta_init,
            gamma,
            float(solver["normalized_gradient_target"]),
            int(solver["lbfgs_max_iterations"]),
            int(solver["lbfgs_max_eval"]),
            raw_tolerance_override=1.0e-8,
        )
        lbfgs = fallback
        polished = newton_polish(
            fit,
            lam_value,
            lbfgs,
            gamma,
            float(solver["newton_normalized_gradient_target"]),
            int(solver["newton_max_steps"]),
            float(solver["line_search_c1"]),
            float(solver["min_line_search_fraction"]),
            float(solver["hessian_shift_floor"]),
        )
    polished["lbfgs"] = {key: value for key, value in lbfgs.items() if key != "theta"}
    polished["strict_raw_fallback_used"] = fallback is not None
    return polished


def fit_h2(points: list[dict], reference: float) -> dict:
    x = torch.tensor([float(row["step"]) ** 2 for row in points], dtype=torch.float64)
    y = torch.tensor([float(row["curvature"]) for row in points], dtype=torch.float64)
    design = torch.stack([torch.ones_like(x), x], dim=1)
    coefficients = torch.linalg.lstsq(design, y).solution
    prediction = design @ coefficients
    residual = float(((y - prediction) ** 2).sum().item())
    total = float(((y - y.mean()) ** 2).sum().item())
    r2 = 1.0 if total == 0.0 else 1.0 - residual / total
    intercept = float(coefficients[0].item())
    return {
        "intercept": intercept,
        "slope_h2": float(coefficients[1].item()),
        "r2": r2,
        "relative_error_to_reference": abs(intercept - reference) / max(abs(reference), FLOOR),
        "relative_span": (float(y.max().item()) - float(y.min().item())) / max(abs(reference), FLOOR),
        "predictions": [float(value) for value in prediction],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--data-seeds", type=int, nargs="+", default=None)
    args = parser.parse_args()
    torch.set_default_dtype(torch.float64)
    repo = A.repo_root().resolve()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    cache = args.cache.resolve()
    config_path = repo / "configs/paper_strengthening/e7_profile_rescue_v2.yaml"
    rescue = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source_protocol_path = repo / rescue["source_protocol"]
    source_protocol = yaml.safe_load(source_protocol_path.read_text(encoding="utf-8"))
    e7 = source_protocol["E7"]
    config = E3.load_config(repo, A.resolve_commit(repo, A.DEFAULT_REF))
    train_budget = int(source_protocol["E3"]["optimizer_proposal"]["fixed_parameter_state_polish_max_iterations"])

    branch_rows = []
    start_rows = []
    fit_rows = []
    data_seeds = rescue["data_seeds"] if args.data_seeds is None else args.data_seeds
    for data_seed in data_seeds:
        fit = C.load_or_train(
            cache,
            config,
            list(rescue["architecture"]),
            int(data_seed),
            int(rescue["initialization_seed"]),
            float(rescue["noise_level"]),
            train_budget,
        )
        context = E7.anchor_context(fit, config["gamma_alpha"], config["exact_hessian"])
        if context["reference"] is None:
            branch_rows.append({"data_seed": data_seed, "status": "ANCHOR_REFERENCE_FAILURE"})
            continue
        lam0 = fit["lam"].detach().clone()
        anchor_phi = float(penalised(fit, fit["theta"], lam0, context["gamma"]).item())
        for step in rescue["steps"]:
            side_solutions = {}
            for sign, side in [(1.0, "plus"), (-1.0, "minus")]:
                lam_value = lam0 + sign * float(step)
                starts = {
                    "implicit_prediction": (fit["theta"] + sign * float(step) * context["state_direction"]).reshape(-1),
                    "anchor": fit["theta"].reshape(-1),
                }
                solved = {}
                for start_name in rescue["independent_starts"]:
                    started = time.perf_counter()
                    result = solve_start(fit, lam_value, starts[start_name], context["gamma"], rescue["solver"])
                    result["start_name"] = start_name
                    result["side"] = side
                    result["step"] = float(step)
                    result["data_seed"] = int(data_seed)
                    result["total_wall_seconds"] = time.perf_counter() - started
                    result["objective_error_bound_fraction"] = (
                        result["objective_error_bound"] / max(0.5 * abs(context["reference"]) * float(step) ** 2, FLOOR)
                        if result["objective_error_bound"] is not None
                        else None
                    )
                    solved[start_name] = result
                    start_rows.append({
                        "data_seed": int(data_seed), "step": float(step), "side": side, "start": start_name,
                        "phi": result["phi"], "normalized_gradient": result["normalized_gradient"],
                        "min_hessian_eigenvalue": result["min_hessian_eigenvalue"],
                        "positive_hessian": result["positive_hessian"],
                        "objective_error_bound": result["objective_error_bound"],
                        "objective_error_bound_fraction": result["objective_error_bound_fraction"],
                        "lbfgs_stop_reason": result["lbfgs"]["stop_reason"],
                        "strict_raw_fallback_used": result["strict_raw_fallback_used"],
                        "newton_stop_reason": result["newton_stop_reason"],
                        "lbfgs_iterations": result["lbfgs"]["iterations"],
                        "lbfgs_function_evaluations": result["lbfgs"]["function_evaluations"],
                        "newton_steps": result["newton_steps"],
                        "wall_seconds": result["total_wall_seconds"],
                    })
                selected = min(solved.values(), key=lambda item: item["phi"])
                other = max(solved.values(), key=lambda item: item["phi"])
                start_gap = abs(selected["phi"] - other["phi"])
                gap_limit = max(
                    2.0 * sum(value or 0.0 for value in [selected["objective_error_bound"], other["objective_error_bound"]]),
                    float(rescue["certificate"]["start_gap_relative_floor"]) * max(abs(selected["phi"]), 1.0),
                )
                norm_ok = all(value["normalized_gradient"] <= float(rescue["solver"]["newton_normalized_gradient_target"]) for value in solved.values())
                hess_ok = all(value["positive_hessian"] for value in solved.values())
                bounds_ok = all(
                    value["objective_error_bound_fraction"] is not None
                    and value["objective_error_bound_fraction"] <= float(rescue["certificate"]["profile_error_fraction"])
                    for value in solved.values()
                )
                agreement_ok = start_gap <= gap_limit
                side_solutions[side] = {
                    "selected": selected,
                    "starts": solved,
                    "start_gap": start_gap,
                    "start_gap_limit": gap_limit,
                    "normalized_gradient_ok": norm_ok,
                    "positive_hessian_ok": hess_ok,
                    "objective_error_bound_ok": bounds_ok,
                    "independent_start_agreement": agreement_ok,
                }
            plus, minus = side_solutions["plus"], side_solutions["minus"]
            selected_plus, selected_minus = plus["selected"], minus["selected"]
            curvature = (selected_plus["phi"] - 2.0 * anchor_phi + selected_minus["phi"]) / float(step) ** 2
            raw_bounds = [selected_plus["objective_error_bound"], selected_minus["objective_error_bound"]]
            combined_bound = sum(raw_bounds) if all(value is not None and math.isfinite(value) for value in raw_bounds) else None
            branch = {
                "data_seed": int(data_seed), "step": float(step), "reference": float(context["reference"]),
                "gamma": float(context["gamma"]), "anchor_phi": anchor_phi, "phi_plus": selected_plus["phi"], "phi_minus": selected_minus["phi"],
                "curvature": curvature, "relative_difference": abs(curvature - context["reference"]) / max(abs(context["reference"]), FLOOR),
                "combined_objective_error_bound": combined_bound,
                "combined_error_fraction": (combined_bound / max(abs(context["reference"]) * float(step) ** 2, FLOOR)) if combined_bound is not None else None,
                "plus_start_gap": plus["start_gap"], "minus_start_gap": minus["start_gap"],
                "plus_start_agreement": plus["independent_start_agreement"], "minus_start_agreement": minus["independent_start_agreement"],
                "all_normalized_gradient_ok": plus["normalized_gradient_ok"] and minus["normalized_gradient_ok"],
                "all_positive_hessian": plus["positive_hessian_ok"] and minus["positive_hessian_ok"],
                "all_objective_bounds_ok": plus["objective_error_bound_ok"] and minus["objective_error_bound_ok"],
            }
            branch["profile_point_valid"] = all(branch[key] for key in ["all_normalized_gradient_ok", "all_positive_hessian", "all_objective_bounds_ok", "plus_start_agreement", "minus_start_agreement"])
            branch_rows.append(branch)
        points = [row for row in branch_rows if row.get("data_seed") == int(data_seed) and row.get("profile_point_valid")]
        fit = fit_h2(points, float(context["reference"])) if len(points) == len(rescue["steps"]) else {"status": "INSUFFICIENT_VALID_POINTS", "valid_points": len(points)}
        if "intercept" in fit:
            fit["data_seed"] = int(data_seed)
            fit["profile_valid"] = bool(
                fit["r2"] >= float(rescue["certificate"]["fit_r2_minimum"])
                and fit["relative_error_to_reference"] <= float(rescue["certificate"]["fit_relative_error_maximum"])
                and fit["relative_span"] <= float(rescue["certificate"]["fit_relative_error_maximum"])
            )
        else:
            fit["data_seed"] = int(data_seed)
            fit["profile_valid"] = False
        fit_rows.append(fit)

    (out / "start_results.json").write_text(json.dumps(start_rows, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "branch_results.json").write_text(json.dumps(branch_rows, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "multiscale_fits.json").write_text(json.dumps(fit_rows, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = {
        "classification": "DEVELOPMENT_ONLY_RESCUE_V2",
        "historical_e7_output_untouched": True,
        "config": str(config_path.relative_to(repo)),
        "config_sha256": sha256(config_path),
        "source_protocol_sha256": sha256(source_protocol_path),
        "source_code_sha256": sha256(HERE / "e7_profile.py"),
        "rescue_code_sha256": sha256(HERE / "e7_profile_rescue_v2.py"),
        "planned_centres": len(rescue["data_seeds"]),
        "planned_profile_points": len(rescue["data_seeds"]) * len(rescue["steps"]),
        "profile_points_valid": sum(1 for row in branch_rows if row.get("profile_point_valid")),
        "profile_points_total": len([row for row in branch_rows if "profile_point_valid" in row]),
        "profiles_valid": sum(1 for row in fit_rows if row.get("profile_valid")),
        "profiles_total": len(fit_rows),
        "fit_rows": fit_rows,
        "claim_boundary": rescue["claim_boundary"],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "profile_points_valid": summary["profile_points_valid"], "profiles_valid": summary["profiles_valid"]}, indent=2))


if __name__ == "__main__":
    main()
