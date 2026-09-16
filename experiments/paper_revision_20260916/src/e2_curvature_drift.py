"""E2 curvature drift: how far the exact reference moves along a state-refinement path.

The stationarity run answered "can the refinement budget reach a small gradient".  That
does not say whether the curvature reference itself drifts.  This script answers the
second question directly.

For each archived two-parameter centre the penalty objective is minimised with the
anchor, the parameter and the damping all frozen:

    L_gamma(theta) = 1/2 ||r(theta, lambda_0)||^2 + gamma/2 ||theta - theta_0||^2

and at each snapshot of the refinement path the three reduced 2x2 matrices are
recomputed with the repository's own routines:

    F_raw  = J_l^T J_l
    F_se   = F_raw - J_l^T J_t (J_t^T J_t + gamma I)^-1 J_t^T J_l     (SAEPS, dense)
    H_red  = exact reduced Hessian at the same gamma

Two conventions are reported for the error metrics.  ``repo`` reproduces the historical
definition, whose whitening metric is rebuilt from the level's own ``F_raw``.  ``fixed``
holds the anchor metric for every level, which is what a drift comparison needs: changing
the ruler between levels would confound drift with a change of norm.

The refinement is run as nested budgets from the same anchor, so snapshot k is the state
after exactly k L-BFGS iterations of the full run.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

ITERATION_PATH = (0, 25, 100, 400, 1000)
FLOOR = 1.0e-30
TAU_RELATIVE = 1.0e-10
DENOMINATOR_FLOOR = 1.0e-30


def _whiten(matrix: torch.Tensor, cholesky: torch.Tensor) -> torch.Tensor:
    left = torch.linalg.solve_triangular(cholesky, matrix, upper=False)
    return torch.linalg.solve_triangular(cholesky, left.T, upper=False).T


def context(repo: Path, commit: str, seed: int):
    """Everything needed to evaluate curvature at an arbitrary state of one centre."""
    import yaml
    from saeps.autodiff import ResidualLinearization
    from saeps.multi import multi_residual
    from saeps.v3.foundation import full_hessian_references

    config = A.two_parameter_config(repo, commit)
    inherited = yaml.safe_load(
        A.read_blob(repo, commit, "configs/v4_6/two_parameter_development.yaml")
    )
    state = A.load_checkpoint(repo, commit, seed)
    theta0 = state["theta"].detach().clone()
    lam0 = state["coordinate"].detach().clone()
    points = A.rebuild_points(state["points"])
    residual_function = lambda s, c: multi_residual(s, c, points, config)  # noqa: E731
    return {
        "config": config,
        "inherited": inherited,
        "state": state,
        "theta0": theta0,
        "lam0": lam0,
        "points": points,
        "residual_function": residual_function,
        "linearization_cls": ResidualLinearization,
        "full_hessian_references": full_hessian_references,
    }


def curvature_at(ctx, theta: torch.Tensor, gamma: float) -> dict:
    """Recompute F_raw, F_se and H_red with the repository's own definitions."""
    linearization = ctx["linearization_cls"](ctx["residual_function"], theta, ctx["lam0"])
    jt, jl = linearization.explicit_jacobians()
    identity = torch.eye(theta.numel(), dtype=theta.dtype)
    raw = jl.T @ jl
    explicit = raw - jl.T @ jt @ torch.linalg.solve(jt.T @ jt + gamma * identity, jt.T @ jl)
    exact = ctx["full_hessian_references"](
        ctx["residual_function"], theta, ctx["lam0"], gamma, ctx["inherited"]["exact_hessian"]
    )
    matched = exact["gamma_matched"]
    gold = (
        torch.tensor(matched["reduced_hessian"], dtype=theta.dtype)
        if matched["status"] == "PASS"
        else None
    )
    return {
        "raw": raw,
        "explicit": explicit,
        "gold": gold,
        "exact_status": exact["status"],
        "exact_symmetry_relative_error": exact["symmetry_relative_error"],
        "reduction_status": matched["status"],
    }


def anchor_metric(raw0: torch.Tensor):
    """The historical primary metric B, frozen at the anchor for every later level."""
    tau = TAU_RELATIVE * max(float(torch.trace(raw0).item()) / 2.0, 1.0)
    metric = 0.5 * (raw0 + raw0.T) + tau * torch.eye(2, dtype=raw0.dtype)
    return metric, torch.linalg.cholesky(metric)


def refine(ctx, gamma: float, max_iterations: int) -> tuple[torch.Tensor, int, float]:
    """Minimise the frozen penalty objective from the anchor with a nested budget."""
    theta0 = ctx["theta0"]
    lam0 = ctx["lam0"]
    points = ctx["points"]
    config = ctx["config"]
    theta = theta0.detach().clone().requires_grad_(True)

    def objective(v):
        residual = A.residual(v, lam0, points, config)
        return 0.5 * (residual * residual).sum() + 0.5 * gamma * (v - theta0).pow(2).sum()

    if max_iterations > 0:
        optimizer = torch.optim.LBFGS(
            [theta],
            max_iter=max_iterations,
            history_size=50,
            tolerance_grad=0.0,
            tolerance_change=0.0,
            line_search_fn="strong_wolfe",
        )

        def closure():
            optimizer.zero_grad(set_to_none=True)
            value = objective(theta)
            value.backward()
            return value

        optimizer.step(closure)
        iterations = int(optimizer.state[theta].get("n_iter", 0))
    else:
        iterations = 0
    value = objective(theta)
    gradient = torch.autograd.grad(value, theta)[0]
    m = int(A.residual_count(theta0, lam0, points, config))
    normalized = float(torch.linalg.vector_norm(gradient).item()) / (
        m * max(float(torch.linalg.vector_norm(theta.detach()).item()), 1.0)
    )
    return theta.detach().clone(), iterations, normalized


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

    rows = []
    consistency = []
    matrices = {}

    for seed in args.seeds:
        ctx = context(repo, commit, seed)
        historical = A.read_json(
            repo, commit, f"outputs/runs/v5/two_parameter/confirmation/seed_{seed}/result.json"
        )
        # The frozen pipeline computes the diagnostic gamma only inside its valid branch.
        if historical.get("gamma") is not None:
            gamma = float(historical["gamma"])
            gamma_source = "historical_recorded"
        else:
            gamma = 1.0e-8 * float(
                torch.linalg.svdvals(
                    ctx["linearization_cls"](
                        ctx["residual_function"], ctx["theta0"], ctx["lam0"]
                    ).explicit_jacobians()[0]
                )[0].square()
            )
            gamma_source = "new_posthoc_sensitivity_target"

        anchor = curvature_at(ctx, ctx["theta0"], gamma)
        metric0, chol0 = anchor_metric(anchor["raw"])
        denom0 = float(torch.linalg.matrix_norm(_whiten(anchor["gold"], chol0)).item()) + DENOMINATOR_FLOOR

        # Level 0 against the historical record: validates the recomputation route.
        if historical.get("F_raw") is not None:
            for name, mine, theirs in (
                ("F_raw", anchor["raw"], historical["F_raw"]),
                ("F_se_GN_explicit", anchor["explicit"], historical["F_se_GN_explicit"]),
                ("H_red_exact_gamma", anchor["gold"], historical["H_red_exact_gamma"]),
            ):
                if theirs is None:
                    continue
                reference = torch.tensor(theirs, dtype=torch.float64)
                consistency.append(
                    {
                        "seed": seed,
                        "quantity": name,
                        "recomputed_sha_relative_error": float(
                            torch.linalg.matrix_norm(mine - reference).item()
                        )
                        / max(float(torch.linalg.matrix_norm(reference).item()), FLOOR),
                        "recomputed_00": float(mine[0, 0].item()),
                        "historical_00": float(reference[0, 0].item()),
                        "recomputed_01": float(mine[0, 1].item()),
                        "historical_01": float(reference[0, 1].item()),
                    }
                )

        drift_denom = float(torch.linalg.matrix_norm(_whiten(anchor["gold"], chol0)).item()) + FLOOR
        raw_denom = float(torch.linalg.matrix_norm(_whiten(anchor["raw"], chol0)).item()) + FLOOR
        se_denom = float(torch.linalg.matrix_norm(_whiten(anchor["explicit"], chol0)).item()) + FLOOR

        for budget in ITERATION_PATH:
            theta, iterations, normalized = refine(ctx, gamma, budget)
            level = curvature_at(ctx, theta, gamma)
            gold = level["gold"]
            if gold is None:
                rows.append(
                    {
                        "seed": seed,
                        "iteration_budget": budget,
                        "lbfgs_iterations": iterations,
                        "status": "REFERENCE_REDUCTION_FAILED",
                    }
                )
                continue

            whiten_fixed = lambda m: _whiten(m, chol0)  # noqa: E731
            # repository convention: metric rebuilt from this level's own F_raw
            _, chol_k = anchor_metric(level["raw"])
            whiten_repo = lambda m: _whiten(m, chol_k)  # noqa: E731

            e_raw_fixed = float(torch.linalg.matrix_norm(whiten_fixed(level["raw"] - gold)).item())
            e_se_fixed = float(torch.linalg.matrix_norm(whiten_fixed(level["explicit"] - gold)).item())
            gold_fixed = float(torch.linalg.matrix_norm(whiten_fixed(gold)).item()) + DENOMINATOR_FLOOR

            e_raw_repo = float(torch.linalg.matrix_norm(whiten_repo(level["raw"] - gold)).item())
            e_se_repo = float(torch.linalg.matrix_norm(whiten_repo(level["explicit"] - gold)).item())
            gold_repo = float(torch.linalg.matrix_norm(whiten_repo(gold)).item()) + DENOMINATOR_FLOOR

            rows.append(
                {
                    "seed": seed,
                    "iteration_budget": budget,
                    "lbfgs_iterations": iterations,
                    "normalized_penalty_gradient": normalized,
                    "gamma": gamma,
                    "gamma_source": gamma_source,
                    "state_displacement_from_anchor": float(
                        torch.linalg.vector_norm(theta - ctx["theta0"]).item()
                    ),
                    "drift_H_red": float(
                        torch.linalg.matrix_norm(whiten_fixed(gold - anchor["gold"])).item()
                    )
                    / drift_denom,
                    "drift_F_raw": float(
                        torch.linalg.matrix_norm(whiten_fixed(level["raw"] - anchor["raw"])).item()
                    )
                    / raw_denom,
                    "drift_F_se": float(
                        torch.linalg.matrix_norm(whiten_fixed(level["explicit"] - anchor["explicit"])).item()
                    )
                    / se_denom,
                    "E_raw2_fixed_metric": e_raw_fixed / gold_fixed,
                    "E_SAEPS2_fixed_metric": e_se_fixed / gold_fixed,
                    "E_raw2_repo_metric": e_raw_repo / gold_repo,
                    "E_SAEPS2_repo_metric": e_se_repo / gold_repo,
                    "drift_H_red_over_SAEPS2": (
                        float(torch.linalg.matrix_norm(whiten_fixed(gold - anchor["gold"])).item())
                        / drift_denom
                    )
                    / (e_se_fixed / gold_fixed)
                    if e_se_fixed > 0.0
                    else None,
                    "method_preferred_same_level_reference": "SAEPS"
                    if e_se_fixed < e_raw_fixed
                    else "raw",
                    "reference_reduction_status": level["reduction_status"],
                }
            )
            matrices[f"seed{seed}_iter{budget}_F_raw"] = level["raw"].detach().numpy()
            matrices[f"seed{seed}_iter{budget}_F_se"] = level["explicit"].detach().numpy()
            matrices[f"seed{seed}_iter{budget}_H_red"] = gold.detach().numpy()

    import numpy as np

    np.savez_compressed(out / "e2_curvature_matrices.npz", **matrices)

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e2_curvature_drift.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with (out / "e2_matrix_consistency.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "seed",
                "quantity",
                "recomputed_sha_relative_error",
                "recomputed_00",
                "historical_00",
                "recomputed_01",
                "historical_01",
            ],
        )
        writer.writeheader()
        writer.writerows(consistency)

    terminal = [r for r in rows if r.get("iteration_budget") == ITERATION_PATH[-1]]
    valid = [r for r in terminal if r["seed"] not in (219, 221)]
    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E2_curvature_drift",
        "environment": A.frozen_environment(repo, args.ref),
        "objective": "1/2 ||r(theta, lambda_0)||^2 + gamma/2 ||theta - theta_0||^2 (sum scale, m=736)",
        "gamma_policy": "gamma fixed at its level-0 value for every level; alpha = 1e-8; never re-estimated during refinement",
        "gamma_source_rule": "historical_recorded when the frozen record stores it; otherwise a new post-hoc sensitivity target computed by the same frozen rule on the archived state",
        "whitening_policy": "repo convention rebuilds the metric per level; the drift comparison holds the anchor metric fixed",
        "iteration_path": list(ITERATION_PATH),
        "counts": {
            "centres": len(args.seeds),
            "grid_rows": len(rows),
            "terminal_rows": len(terminal),
            "valid_centres": len(valid),
            "gamma_from_history": sum(1 for r in terminal if r.get("gamma_source") == "historical_recorded"),
            "gamma_new_posthoc": sum(
                1 for r in terminal if r.get("gamma_source") == "new_posthoc_sensitivity_target"
            ),
        },
        "matrix_consistency": {
            "rows": len(consistency),
            "max_relative_error": max(
                (c["recomputed_sha_relative_error"] for c in consistency), default=None
            ),
        },
        "terminal_reference_drift_max": max((r["drift_H_red"] for r in valid), default=None),
        "terminal_reference_drift_min": min((r["drift_H_red"] for r in valid), default=None),
        "terminal_SAEPS_error_max": max((r["E_SAEPS2_fixed_metric"] for r in valid), default=None),
        "terminal_drift_over_SAEPS2_max": max(
            (r["drift_H_red_over_SAEPS2"] for r in valid if r["drift_H_red_over_SAEPS2"] is not None),
            default=None,
        ),
        "terminal_drift_over_SAEPS2_min": min(
            (r["drift_H_red_over_SAEPS2"] for r in valid if r["drift_H_red_over_SAEPS2"] is not None),
            default=None,
        ),
        "same_magnitude_as_SAEPS_error": sorted(
            r["seed"]
            for r in valid
            if r["drift_H_red_over_SAEPS2"] is not None and r["drift_H_red_over_SAEPS2"] >= 0.1
        ),
        "method_ordering_changed_centres": [
            r["seed"]
            for r in valid
            if r["method_preferred_same_level_reference"]
            != next(
                a["method_preferred_same_level_reference"]
                for a in rows
                if a.get("seed") == r["seed"] and a.get("iteration_budget") == 0
            )
        ],
    }
    with (out / "e2_curvature_drift_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(out)


if __name__ == "__main__":
    main()
