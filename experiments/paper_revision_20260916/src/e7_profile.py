"""E7: does the exact Schur reference survive an independent profile check.

E3's exact reference is a fixed-state Schur reduction: it assumes the state stays where it
is when the parameter moves.  The honest test is to let the state actually re-minimise and
measure the resulting profile curvature.

At the frozen anchor the penalised objective is

    L_gamma(theta, lambda) = 1/2 ||rbar(theta, lambda)||^2 + gamma/2 ||theta - theta_0||^2

with ``theta_0``, ``lambda_0`` and ``gamma`` all held at their recorded values: the run may
not re-anchor and may not re-estimate the damping.  The profile is

    Phi_gamma(lambda) = min_theta L_gamma(theta, lambda)

and the expansion carries a linear term, so the curvature is read from the symmetric
difference where that term cancels:

    C(h) = [Phi(lambda_0 + h) - 2 Phi(lambda_0) + Phi(lambda_0 - h)] / h^2

A one-sided quotient divided by h^2 would not cancel it.  Each displaced solve starts from
a first-order implicit-function prediction of the new state and is run at three gradient
tolerances, because the state optimisation error is amplified by h^-2 and a smaller step
is therefore not automatically more accurate.

Two judgements are kept apart.  The reference check asks whether the symmetric difference
agrees with the exact Schur value.  The method comparison asks whether SAEPS beats raw
against that same reference, and it never enters the validity filter of the first.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import center_cache as C  # noqa: E402
import e3_saturation as E3  # noqa: E402
import repo_adapter as A  # noqa: E402

ARCHITECTURE = [2, 16, 1]
MAX_INNER_ITERATIONS = 1000
FLOOR = 1.0e-30


def penalised(fit: dict, theta: torch.Tensor, lam: torch.Tensor, gamma: float) -> torch.Tensor:
    """L_gamma at an arbitrary parameter value, anchored at the recorded centre."""
    return C.objective(theta, lam, fit["points"], fit["local"], fit["architecture"]) + 0.5 * gamma * (
        theta - fit["theta"]
    ).pow(2).sum()


def refine(
    fit: dict,
    lam_value: torch.Tensor,
    theta_init: torch.Tensor,
    gamma: float,
    tolerance: float,
) -> dict:
    """Minimise L_gamma over the state at a fixed parameter, stopping at the tolerance."""
    state = theta_init.detach().clone().requires_grad_(True)
    optimizer = torch.optim.LBFGS(
        [state],
        max_iter=MAX_INNER_ITERATIONS,
        history_size=50,
        tolerance_grad=tolerance,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def closure():
        optimizer.zero_grad(set_to_none=True)
        value = penalised(fit, state, lam_value, gamma)
        value.backward()
        return value

    optimizer.step(closure)
    value = penalised(fit, state, lam_value, gamma)
    gradient = torch.autograd.grad(value, state)[0]
    m = fit["residuals"]
    normalized = float(torch.linalg.vector_norm(gradient).item()) / (
        m * max(float(torch.linalg.vector_norm(state.detach()).item()), 1.0)
    )
    return {
        "theta": state.detach().clone(),
        "phi": float(value.detach().item()),
        "iterations": int(optimizer.state[state].get("n_iter", 0)),
        "normalized_full_penalty_gradient": normalized,
        "max_abs_gradient": float(gradient.abs().max().item()),
        "displacement_from_anchor": float(
            torch.linalg.vector_norm(state.detach() - fit["theta"]).item()
        ),
    }



def curvature_at(fit: dict, theta: torch.Tensor, lam_value: torch.Tensor, gamma: float):
    """F_raw and F_se_GN at an arbitrary state and parameter, for the method comparison."""
    from torch.autograd.functional import jacobian

    points, local, arch = fit["points"], fit["local"], fit["architecture"]
    rfun = lambda t, l: C.weighted_residual(t, l, points, local, arch)  # noqa: E731
    theta_v = theta.detach().clone().requires_grad_(True)
    lam_v = lam_value.detach().clone().reshape(1).requires_grad_(True)
    j_theta = jacobian(lambda t: rfun(t, lam_v), theta_v, strategy="forward-mode", vectorize=True)
    j_lam = jacobian(lambda l: rfun(theta_v, l), lam_v, strategy="forward-mode", vectorize=True)
    state_block = j_theta.T @ j_theta
    f_raw = float((j_lam.T @ j_lam)[0, 0].item())
    reduced = j_lam.T @ j_lam - j_lam.T @ j_theta @ torch.linalg.solve(
        state_block + gamma * torch.eye(theta.numel(), dtype=theta.dtype), j_theta.T @ j_lam
    )
    return f_raw, float(reduced[0, 0].item())


def anchor_context(fit: dict, alpha: float, exact_spec: dict) -> dict:
    """gamma, the exact Schur reference and the implicit-function direction."""
    from saeps.v3.foundation import full_hessian_references

    theta, lam = fit["theta"], fit["lam"]
    points, local, arch = fit["points"], fit["local"], fit["architecture"]
    rfun = lambda t, l: C.weighted_residual(t, l, points, local, arch)  # noqa: E731

    state_size = theta.numel()
    joint = torch.cat([theta, lam]).detach()
    loss = lambda v: 0.5 * (rfun(v[:state_size], v[state_size:]) ** 2).sum()  # noqa: E731
    hessian = torch.func.hessian(loss)(joint)
    state_block = hessian[:state_size, :state_size]
    cross = hessian[:state_size, state_size:]
    lambda_max = float(torch.linalg.eigvalsh(state_block).max().item())
    gamma = alpha * lambda_max

    exact = full_hessian_references(rfun, theta, lam, gamma, exact_spec)
    matched = exact["gamma_matched"]
    reference = (
        float(matched["reduced_hessian"][0][0]) if matched["status"] == "PASS" else None
    )
    # first-order implicit-function prediction: dtheta/dlambda = -(L_tt)^-1 L_tl
    damped = state_block + gamma * torch.eye(state_size, dtype=theta.dtype)
    # flatten: cross is (n, 1) and a (n, 1) direction would broadcast theta to (n, n)
    direction = torch.linalg.solve(damped, -cross).reshape(-1)
    eigenvalues = torch.linalg.eigvalsh(0.5 * (damped + damped.T))
    return {
        "gamma": gamma,
        "lambda_max": lambda_max,
        "reference": reference,
        "reference_status": matched["status"],
        "state_direction": direction,
        "min_state_eigenvalue_plus_gamma": float(eigenvalues[0].item()),
        "objective": float(loss(joint).item()),
    }


def main() -> None:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=None)
    args = parser.parse_args()

    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)
    cache = args.cache or (out / "centres")

    protocol = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "protocol.yaml").read_text(encoding="utf-8")
    )
    e7 = protocol["E7"]
    grid = [float(v) for v in e7["log_parameter_step_grid"]]
    tolerances = [float(v) for v in e7["state_gradient_tolerances"]]
    wall_cap = float(e7["wall_cap_seconds_per_center"])
    config = E3.load_config(repo, A.resolve_commit(repo))
    budget = int(protocol["E3"]["optimizer_proposal"]["fixed_parameter_state_polish_max_iterations"])

    resolution_fields = [
        "data_seed", "initialization_seed", "noise_level", "step", "side", "tolerance",
        "phi", "phi_relative_to_anchor", "iterations", "normalized_full_penalty_gradient",
        "max_abs_gradient", "displacement_from_anchor", "tolerance_reached",
        "wall_seconds", "timed_out",
    ]
    branch_fields = [
        "data_seed", "step", "symmetric_curvature_C", "exact_schur_reference",
        "relative_difference", "phi_plus", "phi_minus", "phi_anchor",
        "displacement_plus", "displacement_minus", "branch_separation",
        "branches_comparable", "reference_check_passes",
        "E_raw_same_reference", "E_SAEPS_same_reference",
        "SAEPS_wins_same_reference", "wall_seconds",
    ]
    resolution_handle = (out / "e7_profile_resolution.csv").open("x", newline="", encoding="utf-8")
    resolution_writer = csv.DictWriter(resolution_handle, fieldnames=resolution_fields)
    resolution_writer.writeheader()
    resolution_handle.flush()
    branch_handle = (out / "e7_branch_diagnostics.csv").open("x", newline="", encoding="utf-8")
    branch_writer = csv.DictWriter(branch_handle, fieldnames=branch_fields)
    branch_writer.writeheader()
    branch_handle.flush()

    branch_rows = []
    for data_seed in [int(v) for v in e7["new_center_data_seeds"]]:
        centre_started = time.perf_counter()
        fit = C.load_or_train(
            cache,
            config,
            ARCHITECTURE,
            data_seed,
            int(e7["initialization_seed"]),
            float(e7["noise_level"]),
            budget,
        )
        context = anchor_context(fit, config["gamma_alpha"], config["exact_hessian"])
        if context["reference"] is None:
            branch_rows.append(
                {
                    "data_seed": data_seed,
                    "step": None,
                    "branches_comparable": False,
                    "reference_check_passes": False,
                    "note": f"anchor reference unavailable: {context['reference_status']}",
                }
            )
            continue

        lam0 = fit["lam"].detach().clone()
        anchor = {
            "theta": fit["theta"],
            "phi": float(penalised(fit, fit["theta"], lam0, context["gamma"]).item()),
        }
        curve = {}
        for step in grid:
            if time.perf_counter() - centre_started > wall_cap:
                branch_rows.append(
                    {
                        "data_seed": data_seed,
                        "step": step,
                        "branches_comparable": False,
                        "reference_check_passes": False,
                        "note": "wall cap reached; reported as timed out",
                    }
                )
                break
            for sign in (1.0, -1.0):
                lam_value = lam0 + sign * step
                prediction = (
                    anchor["theta"] + sign * step * context["state_direction"]
                ).reshape(-1)
                for tolerance in tolerances:
                    started = time.perf_counter()
                    result = refine(fit, lam_value, prediction, context["gamma"], tolerance)
                    elapsed = time.perf_counter() - started
                    resolution_writer.writerow(
                        {
                            "data_seed": data_seed,
                            "initialization_seed": int(e7["initialization_seed"]),
                            "noise_level": float(e7["noise_level"]),
                            "step": step,
                            "side": "plus" if sign > 0 else "minus",
                            "tolerance": tolerance,
                            "phi": result["phi"],
                            "phi_relative_to_anchor": (result["phi"] - anchor["phi"])
                            / max(abs(anchor["phi"]), FLOOR),
                            "iterations": result["iterations"],
                            "normalized_full_penalty_gradient": result[
                                "normalized_full_penalty_gradient"
                            ],
                            "max_abs_gradient": result["max_abs_gradient"],
                            "displacement_from_anchor": result["displacement_from_anchor"],
                            "tolerance_reached": result["normalized_full_penalty_gradient"]
                            <= tolerance,
                            "wall_seconds": elapsed,
                            "timed_out": result["iterations"] >= MAX_INNER_ITERATIONS,
                        }
                    )
                    resolution_handle.flush()
                    curve[(step, sign, tolerance)] = result
        # the symmetric difference uses the tightest tolerance available at each side
        for step in grid:
            plus = curve.get((step, 1.0, tolerances[-1]))
            minus = curve.get((step, -1.0, tolerances[-1]))
            if plus is None or minus is None:
                continue
            symmetric = (plus["phi"] - 2.0 * anchor["phi"] + minus["phi"]) / (step * step)
            separation = abs(
                plus["displacement_from_anchor"] - minus["displacement_from_anchor"]
            )
            comparable = separation < 10.0 * max(
                abs(plus["displacement_from_anchor"]), 1.0e-30
            )
            relative = abs(symmetric - context["reference"]) / max(
                abs(context["reference"]), FLOOR
            )
            # method comparison against the same reference, kept out of the validity filter
            f_raw, f_se = curvature_at(fit, plus["theta"], lam0 + step, context["gamma"])
            scale = max(abs(context["reference"]), FLOOR)
            e_raw = abs(f_raw - context["reference"]) / scale
            e_saeps = abs(f_se - context["reference"]) / scale
            branch_rows.append(
                {
                    "data_seed": data_seed,
                    "step": step,
                    "symmetric_curvature_C": symmetric,
                    "exact_schur_reference": context["reference"],
                    "relative_difference": relative,
                    "phi_plus": plus["phi"],
                    "phi_minus": minus["phi"],
                    "phi_anchor": anchor["phi"],
                    "displacement_plus": plus["displacement_from_anchor"],
                    "displacement_minus": minus["displacement_from_anchor"],
                    "branch_separation": separation,
                    "branches_comparable": comparable,
                    "reference_check_passes": bool(comparable and relative <= 0.1),
                    "E_raw_same_reference": e_raw,
                    "E_SAEPS_same_reference": e_saeps,
                    "SAEPS_wins_same_reference": bool(e_saeps < e_raw),
                    "wall_seconds": None,
                }
            )
            branch_writer.writerow(branch_rows[-1])
            branch_handle.flush()
            print(
                f"  seed={data_seed} h={step:g} C={symmetric:.6g} ref={context['reference']:.6g} "
                f"relerr={relative:.3e}",
                flush=True,
            )

    resolution_handle.close()
    branch_handle.close()

    usable = [r for r in branch_rows if r.get("branches_comparable")]
    summary = {
        "classification": "NEW_EXPERIMENT",
        "task": "E7_profile_resolution",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "centres": len([int(v) for v in e7["new_center_data_seeds"]]),
        "step_grid": grid,
        "state_gradient_tolerances": tolerances,
        "max_inner_iterations_per_point": MAX_INNER_ITERATIONS,
        "wall_cap_seconds_per_center": wall_cap,
        "reanchor_forbidden": True,
        "gamma_reestimation_forbidden": True,
        "steps_evaluated": len(branch_rows),
        "steps_comparable": len(usable),
        "steps_passing_reference_check": sum(
            1 for r in usable if r.get("reference_check_passes")
        ),
        "median_relative_difference": statistics.median(
            [r["relative_difference"] for r in usable]
        )
        if usable
        else None,
        "min_relative_difference": min(
            (r["relative_difference"] for r in usable), default=None
        ),
        "claim_boundary": (
            "The reference check and the method comparison are separate. A failure here "
            "does not invalidate the local algebraic results; it bounds the profile "
            "interpretation. Optimisation error is amplified by h^-2, so the smallest step "
            "is not automatically the most accurate."
        ),
    }
    (out / "e7_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    make_figure(out / "e7_resolution_ladder.pdf", branch_rows, grid)
    print(out)


def make_figure(path: Path, branch_rows: list[dict], grid: list[float]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    figure, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    seeds = sorted({r["data_seed"] for r in branch_rows if r.get("step")})
    colours = plt.cm.viridis(np.linspace(0.15, 0.85, max(len(seeds), 1)))

    references = []
    for index, seed in enumerate(seeds):
        group = sorted(
            [r for r in branch_rows if r.get("data_seed") == seed and r.get("symmetric_curvature_C")],
            key=lambda r: r["step"],
        )
        if not group:
            continue
        left.plot(
            [r["step"] for r in group],
            [r["symmetric_curvature_C"] for r in group],
            marker="o",
            color=colours[index],
            label=f"data {seed}",
        )
        references.append(group[0]["exact_schur_reference"])
        right.plot(
            [r["step"] for r in group],
            [max(r["relative_difference"], 1e-16) for r in group],
            marker="s",
            color=colours[index],
            label=f"data {seed}",
        )

    for value in sorted(set(references)):
        left.axhline(value, color="black", linewidth=1.0, linestyle="--")
    left.set_xscale("log")
    left.set_yscale("log")
    left.set_xlabel("log-parameter step $h$")
    left.set_ylabel(r"symmetric curvature $C(h)$")
    left.set_title("profile curvature against step size\n(dashed: exact Schur reference)", fontsize=9)
    left.legend(fontsize=7, frameon=False)
    left.grid(True, which="both", linewidth=0.3, alpha=0.5)

    right.axhline(0.1, color="black", linewidth=1.0, linestyle=":")
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xlabel("log-parameter step $h$")
    right.set_ylabel("relative difference from reference")
    right.set_title("resolution error, amplified as $h^{-2}$\n(dotted: 10% acceptance)", fontsize=9)
    right.legend(fontsize=7, frameon=False)
    right.grid(True, which="both", linewidth=0.3, alpha=0.5)

    figure.suptitle("E7 profile resolution ladder at fixed anchor and fixed damping", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, format=path.suffix.lstrip(".") or "pdf")
    plt.close(figure)


if __name__ == "__main__":
    main()
