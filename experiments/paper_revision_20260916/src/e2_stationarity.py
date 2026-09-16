"""E2: fixed-anchor stationarity sensitivity at archived centres.

The penalty objective is the original one, with the anchor, the parameter value and the
damping all held at their recorded values:

    L_gamma(theta) = ell(theta, lambda_old) + gamma/2 * ||theta - theta_old||^2
    gamma          = alpha * lambda_max(J_theta^T J_theta),  alpha = 1e-8

Refinement never re-anchors and never re-estimates the spectral scale; re-deriving either
would change the target.  Three normalised gradient levels are attempted with a fixed
inner budget, and a budget exhaustion is reported as a failure to reach the level rather
than resolved by extending the run.

The prescribed scalar queue (Burgers 55/60/69, Allen-Cahn 75/79/84) is NOT_AVAILABLE
because the scalar archive stores no state tensor.  This runner therefore reports
availability for that queue explicitly and runs the real two-parameter centres, which do
carry state tensors, points and parameters.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

PRESCRIBED_SCALAR_QUEUE = {
    "Burgers": (55, 60, 69),
    "Allen-Cahn": (75, 79, 84),
}
TARGET_LEVELS = (1.0e-6, 1.0e-8, 1.0e-10)
MAX_INNER_ITERATIONS = 1000


def normalized_gradient(gradient: torch.Tensor, theta: torch.Tensor, m: int) -> float:
    return float(torch.linalg.vector_norm(gradient).item()) / (
        m * max(float(torch.linalg.vector_norm(theta).item()), 1.0)
    )


def state_exact_blocks(theta, lam0, points, config):
    from torch.autograd.functional import hessian, jacobian

    theta_v = theta.detach().clone().requires_grad_(True)
    field = lambda v: A.residual(v, lam0, points, config)  # noqa: E731
    J = jacobian(field, theta_v, strategy="forward-mode", vectorize=True)
    r = field(theta_v).detach()
    H = hessian(lambda v: 0.5 * (field(v) ** 2).sum(), theta_v)
    return {"J": J.detach(), "r": r, "G": J.T @ J, "g": J.T @ r, "H": H.detach()}


def refine(theta_anchor, lam0, points, config, gamma, level, m):
    """Minimise the fixed-anchor penalty objective to one normalised gradient level."""
    theta = theta_anchor.detach().clone().requires_grad_(True)

    def objective(v):
        return A.sum_objective(v, lam0, points, config) + 0.5 * gamma * (v - theta_anchor).pow(2).sum()

    optimizer = torch.optim.LBFGS(
        [theta],
        max_iter=MAX_INNER_ITERATIONS,
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )
    trajectory = []

    def closure():
        optimizer.zero_grad(set_to_none=True)
        value = objective(theta)
        value.backward()
        trajectory.append(normalized_gradient(theta.grad.detach(), theta.detach(), m))
        return value

    optimizer.step(closure)
    value = objective(theta)
    gradient = torch.autograd.grad(value, theta)[0]
    final = normalized_gradient(gradient, theta.detach(), m)
    iterations = int(optimizer.state[theta].get("n_iter", 0))
    return {
        "theta": theta.detach().clone(),
        "objective": float(value.detach().item()),
        "gradient_norm": float(torch.linalg.vector_norm(gradient).item()),
        "normalized_gradient": final,
        "reached": final <= level,
        "inner_iterations": iterations,
        "inner_closure_calls": len(trajectory),
        "budget_exhausted": iterations >= MAX_INNER_ITERATIONS,
        "iterations_to_level": next(
            (index + 1 for index, value in enumerate(trajectory) if value <= level), None
        ),
        "final_trajectory_value": trajectory[-1] if trajectory else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--ref", default=A.DEFAULT_REF)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(A.TWO_PARAMETER_SEEDS))
    args = parser.parse_args()

    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    commit = A.resolve_commit(repo, args.ref)
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    config = A.two_parameter_config(repo, commit)
    alpha = config["_gamma_alpha"]
    report = A.read_json(repo, commit, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json")
    validity = {int(row["seed"]): row for row in report["seed_rows"]}

    scalar_availability = []
    for benchmark, seeds in PRESCRIBED_SCALAR_QUEUE.items():
        for seed in seeds:
            record = A.scalar_posthoc_record(repo, commit, benchmark, seed)
            scalar_availability.append(
                {
                    "point_id": f"scalar:{benchmark}:{seed}",
                    "binding_valid": bool(record.get("original_binding_valid")),
                    "state_tensor_available": False,
                    "status": "NOT_AVAILABLE",
                    "reason": "scalar posthoc record stores parameter/state blocks only; no theta, no observation set, no residual",
                    "source_path": record["_path"],
                    "source_sha256": record["_sha256"],
                }
            )

    rows = []
    manifests = []
    for seed in args.seeds:
        state = A.load_checkpoint(repo, commit, seed)
        theta_anchor = state["theta"].detach().clone()
        lam0 = state["coordinate"].detach().clone()
        points = A.rebuild_points(state["points"])
        m = A.residual_count(theta_anchor, lam0, points, config)

        blocks = state_exact_blocks(theta_anchor, lam0, points, config)
        gamma = alpha * float(torch.linalg.eigvalsh(blocks["G"]).max().item())
        anchor_gradient = blocks["g"] + gamma * (theta_anchor - theta_anchor)
        normalized_anchor = normalized_gradient(anchor_gradient, theta_anchor, m)

        shifted = blocks["H"] + gamma * torch.eye(blocks["H"].shape[0], dtype=blocks["H"].dtype)
        eigenvalues = torch.linalg.eigvalsh(0.5 * (shifted + shifted.T))
        delta_theta = torch.linalg.solve(shifted, -blocks["g"])

        info = validity.get(seed, {})
        entry = {
            "point_id": f"two_parameter:{seed}",
            "seed": seed,
            "binding_valid": bool(info.get("binding_valid")),
            "terminal_status": info.get("terminal_status"),
            "residual_count": m,
            "gamma": gamma,
            "alpha": alpha,
            "lambda_max_G_theta_theta": float(torch.linalg.eigvalsh(blocks["G"]).max().item()),
            "normalized_full_gradient_at_anchor": normalized_anchor,
            "raw_gradient_norm_at_anchor": float(torch.linalg.vector_norm(anchor_gradient).item()),
            "theta_norm": float(torch.linalg.vector_norm(theta_anchor).item()),
            "state_block_min_eigenvalue_plus_gamma": float(eigenvalues[0].item()),
            "newton_step_norm": float(torch.linalg.vector_norm(delta_theta).item()),
            "objective_sum_at_anchor": float(A.sum_objective(theta_anchor, lam0, points, config).item()),
            "penalty_objective_at_anchor": float(
                (A.sum_objective(theta_anchor, lam0, points, config)).item()
            ),
        }
        manifests.append(
            {
                "seed": seed,
                "anchor_is_checkpoint_state": True,
                "parameter_frozen": True,
                "anchor_theta_sha256": hashlib.sha256(
                    theta_anchor.numpy().tobytes()
                ).hexdigest(),
                "checkpoint_sha256": state["_sha256"],
                "checkpoint_path": state["_path"],
                "gamma": gamma,
                "reanchor_forbidden": True,
                "gamma_reestimation_forbidden": True,
            }
        )

        previous = None
        for level in TARGET_LEVELS:
            result = refine(theta_anchor, lam0, points, config, gamma, level, m)
            entry.update(
                {
                    f"reached_{level:.0e}": result["reached"],
                    f"normalized_gradient_after_{level:.0e}": result["normalized_gradient"],
                    f"inner_iterations_to_{level:.0e}": result["inner_iterations"],
                    f"closure_calls_to_{level:.0e}": result["inner_closure_calls"],
                    f"budget_exhausted_at_{level:.0e}": result["budget_exhausted"],
                    f"penalty_objective_after_{level:.0e}": result["objective"],
                    f"state_displacement_to_{level:.0e}": float(
                        torch.linalg.vector_norm(result["theta"] - theta_anchor).item()
                    ),
                }
            )
            if previous is not None:
                entry[f"penalty_objective_change_{previous:.0e}_to_{level:.0e}"] = (
                    entry[f"penalty_objective_after_{level:.0e}"]
                    - entry[f"penalty_objective_after_{previous:.0e}"]
                )
            previous = level
        rows.append(entry)

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e2_stationarity_path.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E2_fixed_anchor_stationarity_sensitivity",
        "environment": A.frozen_environment(repo, args.ref),
        "objective": "ell(theta, lambda_old) + gamma/2 * ||theta - theta_old||^2",
        "gamma_rule": "gamma = alpha * lambda_max(J_theta^T J_theta) at the anchor, alpha = 1e-8",
        "alpha": alpha,
        "anchor_policy": "theta_old is the recorded checkpoint state; parameter held at its recorded value; no re-anchoring, no gamma re-estimation",
        "max_inner_iterations_per_level": MAX_INNER_ITERATIONS,
        "target_levels": list(TARGET_LEVELS),
        "prescribed_scalar_queue_availability": scalar_availability,
        "prescribed_scalar_queue_status": "NOT_AVAILABLE",
        "units": manifests,
        "counts": {
            "two_parameter_centres_run": len(rows),
            "two_parameter_binding_valid": sum(1 for row in rows if row["binding_valid"]),
            "scalar_prescribed_points_unavailable": len(scalar_availability),
        },
    }
    with (out / "e2_fixed_anchor_manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(out)


if __name__ == "__main__":
    main()
