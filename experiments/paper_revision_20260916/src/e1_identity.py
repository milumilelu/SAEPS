"""E1: parameter-gradient identity at archived centres.

For the benchmarks in scope the fixed-state residual is affine in the physical
coefficients:  r(theta, a) = c(theta) + sum_j a_j b_j(theta).  Differentiating
twice in the physical coordinate gives d2r/da2 = 0, hence

    H_aa - G_aa = 0                       (physical coordinates)
    H_ll - G_ll = diag(g_l)               (log coordinates, a = exp(l))

with H the exact Hessian of the sum objective, G = J^T J the Gauss-Newton
matrix, and g the gradient.  This script checks both relations on the real
frozen checkpoints with autograd, and separately re-derives the archived scalar
parameter blocks from their stored 1x1 entries.

Read-only: nothing here trains or overwrites a historical record.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.autograd.functional import hessian, jacobian

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

IDENTITY_RTOL = 1.0e-10
IDENTITY_ATOL = 1.0e-12


def coordinate_blocks(theta, lam0, points, config, coordinate: str) -> dict:
    """Exact J, G, g and H in the requested parameter coordinate.

    ``lam0`` is always the archived log-coordinate centre; the physical branch
    starts from ``exp(lam0)`` so that the two coordinates describe the same point.
    """
    if coordinate == "log":
        v0 = lam0.detach().clone()
        field = lambda v: A.residual(theta, v, points, config)  # noqa: E731
    elif coordinate == "physical":
        v0 = lam0.detach().clone().exp()
        field = lambda v: A.residual(theta, torch.log(v), points, config)  # noqa: E731
    else:
        raise ValueError(coordinate)
    v0 = v0.requires_grad_(True)
    J = jacobian(field, v0, strategy="forward-mode", vectorize=True)
    r = field(v0).detach()
    G = J.T @ J
    g = J.T @ r
    H = hessian(lambda v: 0.5 * (field(v) ** 2).sum(), v0)
    return {"J": J, "r": r, "G": G, "g": g, "H": H}


def state_blocks(theta, lam0, points, config) -> dict:
    """State-side g, G and H at fixed parameters (diagnostic input for E2)."""
    theta = theta.detach().clone().requires_grad_(True)
    field = lambda v: A.residual(v, lam0, points, config)  # noqa: E731
    J = jacobian(field, theta, strategy="forward-mode", vectorize=True)
    r = field(theta).detach()
    H = hessian(lambda v: 0.5 * (field(v) ** 2).sum(), theta)
    return {"G": J.T @ J, "g": J.T @ r, "H": H}


def identity_error(H, G, target) -> tuple[float, float, bool]:
    """Frobenius norm of ``H - G - target`` plus its mixed abs/rel tolerance."""
    residual = H - G - target
    eps = float(torch.linalg.matrix_norm(residual).item())
    scale = max(
        float(torch.linalg.matrix_norm(H).item()),
        float(torch.linalg.matrix_norm(G).item()),
        float(torch.linalg.matrix_norm(target).item()),
        1.0,
    )
    return eps, IDENTITY_ATOL + IDENTITY_RTOL * scale, eps <= IDENTITY_ATOL + IDENTITY_RTOL * scale


def scalar_archived_identity(repo: Path, commit: str) -> list[dict]:
    """Re-derive the parameter block difference from the stored 1x1 entries."""
    from saeps.multi import multi_residual  # noqa: F401  (import check only)

    rows = []
    for benchmark, seeds in A.SCALAR_COHORTS.items():
        for seed in seeds:
            record = A.scalar_posthoc_record(repo, commit, benchmark, seed)
            exact_blocks = record.get("exact_blocks")
            gn_blocks = record.get("GN_blocks")
            if not exact_blocks or not gn_blocks:
                rows.append(
                    {
                        "point_id": f"scalar:{benchmark}:{seed}",
                        "kind": "scalar_archived_block",
                        "benchmark": benchmark,
                        "seed": seed,
                        "binding_valid": bool(record.get("original_binding_valid")),
                        "H_ll": None,
                        "G_ll": None,
                        "H_minus_G": None,
                        "stored_norm_R_ll_2": None,
                        "abs_identity_error": None,
                        "identity_satisfied": None,
                        "state_tensor_available": False,
                        "note": f"NOT_AVAILABLE: no parameter blocks archived (status={record.get('original_status')}, "
                        f"failure_reason={record.get('failure_reason')})",
                        "source_path": record["_path"],
                        "source_sha256": record["_sha256"],
                    }
                )
                continue
            H_ll = np.asarray(exact_blocks["H_ll"], dtype=float)
            G_ll = np.asarray(gn_blocks["G_ll"], dtype=float)
            diff = H_ll - G_ll
            stored = record.get("GN_remainder_diagnostics", {}).get("norm_R_ll_2")
            eps = abs(float(np.linalg.norm(diff, ord=2)) - float(stored)) if stored is not None else None
            rows.append(
                {
                    "point_id": f"scalar:{benchmark}:{seed}",
                    "kind": "scalar_archived_block",
                    "benchmark": benchmark,
                    "seed": seed,
                    "binding_valid": bool(record.get("original_binding_valid")),
                    "H_ll": float(H_ll[0, 0]),
                    "G_ll": float(G_ll[0, 0]),
                    "H_minus_G": float(diff[0, 0]),
                    "stored_norm_R_ll_2": stored,
                    "abs_identity_error": eps,
                    "identity_satisfied": (eps is not None and eps <= IDENTITY_ATOL + IDENTITY_RTOL * max(abs(float(stored)), 1.0)),
                    "state_tensor_available": False,
                    "note": "archive stores parameter/state blocks only; no state tensor, observation set or residual",
                    "source_path": record["_path"],
                    "source_sha256": record["_sha256"],
                }
            )
    return rows


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
    report = A.read_json(repo, commit, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json")
    validity = {int(row["seed"]): row for row in report["seed_rows"]}

    adapter_checks = []
    rows = []
    blocks_npz = {}

    for seed in args.seeds:
        state = A.load_checkpoint(repo, commit, seed)
        theta = state["theta"]
        lam0 = state["coordinate"]
        points = A.rebuild_points(state["points"])

        regenerated = A.regenerate_points(config, int(state["source_seed"]))
        max_dev = max(
            float((getattr(points, f) - getattr(regenerated, f)).abs().max().item())
            for f in ("pde_x", "pde_t", "data_x", "data_t", "initial_x", "boundary_t")
        )
        adapter_checks.append({"seed": seed, "point_regeneration_max_abs_deviation": max_dev})

        m = A.residual_count(theta, lam0, points, config)
        logb = coordinate_blocks(theta, lam0, points, config, "log")
        physb = coordinate_blocks(theta, lam0, points, config, "physical")
        stats = A.sum_objective(theta, lam0, points, config)

        eps, tol, ok = identity_error(logb["H"], logb["G"], torch.diag(logb["g"]))
        eps_phys, tol_phys, ok_phys = identity_error(
            physb["H"], physb["G"], torch.zeros_like(physb["G"])
        )

        row_info = validity.get(seed, {})
        rows.append(
            {
                "point_id": f"two_parameter:{seed}",
                "kind": "two_parameter_rebuilt",
                "benchmark": state["benchmark"],
                "seed": seed,
                "binding_valid": bool(row_info.get("binding_valid")),
                "terminal_status": row_info.get("terminal_status"),
                "residual_count": m,
                "objective_sum": float(stats.item()),
                "g_log_1": float(logb["g"][0].detach()),
                "g_log_2": float(logb["g"][1].detach()),
                "H_ll_minus_G_ll_11": float((logb["H"] - logb["G"])[0, 0].detach()),
                "H_ll_minus_G_ll_22": float((logb["H"] - logb["G"])[1, 1].detach()),
                "H_ll_minus_G_ll_12": float((logb["H"] - logb["G"])[0, 1].detach()),
                "log_identity_error": eps,
                "log_identity_tolerance": tol,
                "log_identity_satisfied": ok,
                "physical_identity_error": eps_phys,
                "physical_identity_tolerance": tol_phys,
                "physical_identity_satisfied": ok_phys,
            }
        )

        blocks_npz[f"seed{seed}_J_log"] = logb["J"].detach().numpy()
        blocks_npz[f"seed{seed}_H_log"] = logb["H"].detach().numpy()
        blocks_npz[f"seed{seed}_G_log"] = logb["G"].detach().numpy()
        blocks_npz[f"seed{seed}_g_log"] = logb["g"].detach().numpy()
        blocks_npz[f"seed{seed}_H_physical"] = physb["H"].detach().numpy()
        blocks_npz[f"seed{seed}_G_physical"] = physb["G"].detach().numpy()
        blocks_npz[f"seed{seed}_g_physical"] = physb["g"].detach().numpy()
        blocks_npz[f"seed{seed}_residual"] = logb["r"].detach().numpy()

    scalar_rows = scalar_archived_identity(repo, commit)
    rows.extend(scalar_rows)
    for r in scalar_rows:
        if r["H_minus_G"] is None:
            continue
        key = r["point_id"].replace(":", "_")
        blocks_npz[f"{key}_H_minus_G"] = np.array([[r["H_minus_G"]]])

    np.savez_compressed(out / "e1_coordinate_blocks.npz", **blocks_npz)

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e1_identity.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    two_param = [r for r in rows if r["kind"] == "two_parameter_rebuilt"]
    valid_rebuilt = [r for r in two_param if r["binding_valid"]]
    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E1_parameter_gradient_identity",
        "environment": A.frozen_environment(repo, args.ref),
        "coordinate_identity_checked": "H_ll - G_ll - diag(g_l) = 0 in log coordinates; H_aa - G_aa = 0 in physical coordinates",
        "objective": "sum objective 0.5 * sum r_i^2 (historical training used the mean, i.e. this objective / m)",
        "config": {
            "declared_width": config["_declared_width"],
            "effective_width": config["_effective_width"],
            "gamma_alpha": config["_gamma_alpha"],
        },
        "adapter_validation": adapter_checks,
        "counts": {
            "two_parameter_planned": 10,
            "two_parameter_binding_valid": sum(1 for r in two_param if r["binding_valid"]),
            "two_parameter_rebuilt": len(two_param),
            "two_parameter_log_identity_satisfied": sum(1 for r in two_param if r["log_identity_satisfied"]),
            "two_parameter_physical_identity_satisfied": sum(1 for r in two_param if r["physical_identity_satisfied"]),
            "scalar_archived_points": len(scalar_rows),
            "scalar_archived_binding_valid": sum(1 for r in scalar_rows if r["binding_valid"]),
            "scalar_archived_identity_satisfied": sum(1 for r in scalar_rows if r["identity_satisfied"]),
        },
        "scalar_limitation": "The scalar archive stores parameter/state blocks but no state tensor, observation set or residual, so the identity is re-derived from the stored blocks only and is NOT_AVAILABLE as an independent autograd check.",
        "valid_rebuilt_seeds": [r["seed"] for r in valid_rebuilt],
        "max_log_identity_error": max((r["log_identity_error"] for r in valid_rebuilt), default=None),
        "max_physical_identity_error": max((r["physical_identity_error"] for r in valid_rebuilt), default=None),
    }
    with (out / "e1_identity_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(out)


if __name__ == "__main__":
    main()
