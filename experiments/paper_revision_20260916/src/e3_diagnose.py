"""E3 blocker diagnosis: is the non-positive state block a budget problem or a real saddle?

The development cohort failed exact reference reduction for 8/8 fits at alpha=1e-8, with
state Hessian blocks as negative as -0.27.  Two explanations must be separated:

  1. the state polish stopped at its iteration cap, so the state is not a stationary point
     and the Hessian is simply being evaluated at a non-minimiser; or
  2. the polished state is genuinely saddle-like, and the benchmark's state block is not
     positive definite at the primary damping.

This script sweeps the polish budget on the same fits and reports, per budget, the
normalised state gradient and the spectrum of the exact state Hessian.  Nothing is
clamped; a state block that stays indefinite keeps failing.

Usage:
    python src/e3_diagnose.py --out <dir> [--seeds 916001 ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.func as tf

sys.path.insert(0, str(Path(__file__).resolve().parent))

import e3_saturation as E  # noqa: E402
import repo_adapter as A  # noqa: E402

BUDGETS = (0, 1000, 3000, 10000, 30000)


def spectrum(theta, lam, points, local) -> dict:
    """Exact state Hessian spectrum of the sum objective at fixed parameter."""
    hessian = tf.hessian(lambda z: E.sum_objective(z, lam, points, local))(theta)
    symmetric = 0.5 * (hessian + hessian.T)
    eigenvalues = torch.linalg.eigvalsh(symmetric)
    floor = 1.0e-10 * max(float(eigenvalues.abs().max().item()), 1.0)
    return {
        "min_eigenvalue": float(eigenvalues.min().item()),
        "max_eigenvalue": float(eigenvalues.max().item()),
        "negative_count": int((eigenvalues < 0).sum().item()),
        "below_positivity_tolerance_count": int((eigenvalues <= floor).sum().item()),
        "positivity_tolerance": floor,
    }


def run(seed: int, init_seed: int, noise: float, config: dict, repo, commit) -> list[dict]:
    local = E.prepare(config, seed, noise)
    points = local["_points"]
    width = int(config["architecture"][1])
    m = E.residual_count(config)

    generator = torch.Generator(device="cpu").manual_seed(init_seed)
    theta = (
        0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    ).requires_grad_(True)
    lam = torch.log(
        torch.tensor([config["kappa_initial"]], dtype=torch.float64)
    ).requires_grad_(True)

    optimizer_spec = config["optimizer"]
    adam = torch.optim.Adam([theta, lam], lr=float(optimizer_spec["adam_learning_rate"]))
    for _ in range(int(optimizer_spec["adam_steps"])):
        adam.zero_grad(set_to_none=True)
        E.sum_objective(theta, lam, points, local).backward()
        adam.step()

    lbfgs = torch.optim.LBFGS(
        [theta, lam],
        max_iter=int(optimizer_spec["lbfgs_max_iterations"]),
        history_size=50,
        tolerance_grad=0.0,
        tolerance_change=0.0,
        line_search_fn="strong_wolfe",
    )

    def closure():
        lbfgs.zero_grad(set_to_none=True)
        value = E.sum_objective(theta, lam, points, local)
        value.backward()
        return value

    lbfgs.step(closure)
    lam_fixed = lam.detach().clone()
    joint_iterations = int(lbfgs.state[theta].get("n_iter", 0))

    rows = []
    for budget in BUDGETS:
        state = theta.detach().clone()
        if budget > 0:
            state = state.requires_grad_(True)
            polish = torch.optim.LBFGS(
                [state],
                max_iter=budget,
                history_size=50,
                tolerance_grad=0.0,
                tolerance_change=0.0,
                line_search_fn="strong_wolfe",
            )

            def polish_closure():
                polish.zero_grad(set_to_none=True)
                value = E.sum_objective(state, lam_fixed, points, local)
                value.backward()
                return value

            polish.step(polish_closure)
            used = int(polish.state[state].get("n_iter", 0))
            state = state.detach()
        else:
            used = 0
        value = E.sum_objective(state, lam_fixed, points, local)
        probe = state.detach().clone().requires_grad_(True)
        probe_value = E.sum_objective(probe, lam_fixed, points, local)
        gradient = torch.autograd.grad(probe_value, probe)[0].detach()
        normalized = float(torch.linalg.vector_norm(gradient).item()) / (
            m * max(float(torch.linalg.vector_norm(state).item()), 1.0)
        )
        rows.append(
            {
                "data_seed": seed,
                "initialization_seed": init_seed,
                "noise_level": noise,
                "polish_budget": budget,
                "polish_iterations_used": used,
                # LBFGS is configured with zero gradient/change tolerances, so it always
                # runs to the cap; this flag records that fact only and is NOT by itself
                # evidence of non-convergence. Read the gradient and objective columns.
                "ran_to_iteration_cap": bool(budget > 0 and used >= budget),
                "kappa": float(torch.exp(lam_fixed.reshape(())).item()),
                "objective": float(value.item()),
                "normalized_state_gradient": normalized,
                **spectrum(state, lam_fixed, points, local),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=[916001])
    parser.add_argument("--inits", type=int, nargs="*", default=[926001])
    parser.add_argument("--noise", type=float, nargs="*", default=[0.0])
    args = parser.parse_args()

    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    commit = A.resolve_commit(repo)
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)
    config = E.load_config(repo, commit)

    rows = []
    for seed in args.seeds:
        for init in args.inits:
            for noise in args.noise:
                rows.extend(run(seed, init, noise, config, repo, commit))

    import csv

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e3_block_diagnosis.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(out)


if __name__ == "__main__":
    main()
