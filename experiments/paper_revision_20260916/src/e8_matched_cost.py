"""E8: cost comparison at a matched damping.

The historical scalability experiment ran at alpha = 1e-2 while the accuracy experiments
ran at 1e-8, so its timings were never measured against the same objective.  Here every
method solves the *same* system at the *same* gamma, taken from the frozen grid

    gamma = alpha * lambda_max(J_theta^T J_theta),  alpha in {1e-8, 1e-6, 1e-4, 1e-2}

Nothing is chosen because it produced a lower error: a larger alpha corresponds to a
different geometry, and every level is reported with its own accuracy and solve status.

Three methods, all from a zero initial guess:

  explicit    dense factorisation of the state block
  CG          matrix-free conjugate gradients on the same operator
  scaled LSQR the repository's scaled augmented LSQR with its diagonal preconditioner

Stages are timed separately, including the preparation stages that a total-only
measurement would hide.  Each condition runs a discarded warm-up and then three timed
repeats.  Training and state polishing are not part of any number in this file.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

CG_TOLERANCE = 1.0e-10
CG_MAX_ITERATIONS = 500

COST_FIELDS = [
    "seed", "benchmark", "state_parameters", "residuals", "alpha", "gamma", "lambda_max",
    "method", "repeat", "initial_guess", "warmup_discarded", "status", "iterations",
    "relative_residual", "setup_seconds", "spectral_seconds", "preconditioner_seconds",
    "solve_seconds", "verification_seconds", "reported_total_seconds",
    "accuracy_vs_dense_reference", "jacobian_setup_seconds_per_centre",
]

# The widened archived centre, used only for operator-level timing.  It is an
# engineering measurement: it says nothing about training feasibility or accuracy.
LARGE_CENTRE = "outputs/runs/v5/checkpoints/scalability_base/seed_120/model_state.pt"


def resource_manifest() -> dict:
    """Environment record. Peak memory is reported as process RSS, not tensor peak."""
    import os

    try:
        cpu = platform.processor() or "unknown"
    except Exception:  # pragma: no cover
        cpu = "unknown"
    return {
        "device": "cpu",
        "dtype": "float64",
        "cpu_model": cpu,
        "torch_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": __import__("numpy").__version__,
        "cpu_count": os.cpu_count(),
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_timing_synchronised": "not applicable, no GPU timing is reported",
        "peak_memory_convention": (
            "process RSS peak via tracemalloc is not available for native tensors; no peak "
            "tensor memory is claimed. RSS is NOT the native tensor allocation peak."
        ),
    }


def dense_reference(linearization, gamma: float, j_theta, j_lam) -> dict:
    """Timed dense route, and the accuracy reference for the iterative methods.

    The Jacobians are passed in rather than recomputed: building them is the expensive
    part and would otherwise be charged to every repeat of every method.
    """
    setup = 0.0  # the Jacobian is built once per centre, outside the timed region

    t0 = time.perf_counter()
    state_block = j_theta.T @ j_theta
    lambda_max = float(torch.linalg.eigvalsh(state_block).max().item())
    spectral = time.perf_counter() - t0

    t0 = time.perf_counter()
    damped = state_block + gamma * torch.eye(state_block.shape[0], dtype=state_block.dtype)
    factor = torch.linalg.cholesky(damped)
    rhs = j_theta.T @ j_lam
    solution = torch.cholesky_solve(rhs, factor)
    solve = time.perf_counter() - t0

    t0 = time.perf_counter()
    residual = damped @ solution - rhs
    relative_residual = float(torch.linalg.matrix_norm(residual).item()) / max(
        float(torch.linalg.matrix_norm(rhs).item()), 1.0e-30
    )
    verification = time.perf_counter() - t0

    f_raw = j_lam.T @ j_lam
    reduced = f_raw - j_lam.T @ j_theta @ solution
    return {
        "method": "explicit",
        "lambda_max": lambda_max,
        "output": reduced,
        "setup_seconds": setup,
        "spectral_seconds": spectral,
        "preconditioner_seconds": 0.0,
        "solve_seconds": solve,
        "verification_seconds": verification,
        "relative_residual": relative_residual,
        "iterations": 1,
        "status": "PASS" if relative_residual <= 1.0e-8 else "NUMERICAL_FAILURE",
    }


def cg_reference(linearization, gamma: float, j_theta, j_lam) -> dict:
    """Matrix-free CG. The operator is applied through JVPs and VJPs, never as a matrix."""
    from saeps.solvers import conjugate_gradient

    t0 = time.perf_counter()
    operator = (
        lambda v: linearization.vjp_theta(linearization.jvp_theta(v))
        + gamma * v
    )
    _ = operator(torch.zeros_like(linearization.theta))  # time a real operator application
    setup = time.perf_counter() - t0

    spectral = 0.0  # CG needs no spectral estimate of its own
    preconditioner = 0.0  # none used; the diagonal build is what makes LSQR expensive
    rhs = j_theta.T @ j_lam

    t0 = time.perf_counter()
    columns = []
    iterations = []
    accepted = True
    for index in range(rhs.shape[1]):
        result = conjugate_gradient(
            operator, rhs[:, index], CG_TOLERANCE, CG_MAX_ITERATIONS
        )
        columns.append(result.solution)
        iterations.append(result.iterations)
        accepted = accepted and result.converged
    solution = torch.stack(columns, dim=1)
    solve = time.perf_counter() - t0

    t0 = time.perf_counter()
    # the operator acts on one state vector at a time
    residual = torch.stack(
        [operator(solution[:, index]) - rhs[:, index] for index in range(rhs.shape[1])],
        dim=1,
    )
    relative_residual = float(torch.linalg.matrix_norm(residual).item()) / max(
        float(torch.linalg.matrix_norm(rhs).item()), 1.0e-30
    )
    verification = time.perf_counter() - t0

    f_raw = j_lam.T @ j_lam
    reduced = f_raw - j_lam.T @ j_theta @ solution
    return {
        "method": "CG",
        "output": reduced,
        "setup_seconds": setup,
        "spectral_seconds": spectral,
        "preconditioner_seconds": preconditioner,
        "solve_seconds": solve,
        "verification_seconds": verification,
        "relative_residual": relative_residual,
        "iterations": sum(iterations),
        "status": "PASS"
        if accepted and relative_residual <= 1.0e-8
        else "SOLVER_FAILURE",
    }


def lsqr_reference(linearization, gamma: float, j_theta, j_lam) -> dict:
    """The repository's scaled augmented LSQR, including its preconditioner build."""
    from saeps.v35.engineering import scaled_augmented_lsqr_candidates

    t0 = time.perf_counter()
    _ = linearization.residual()
    setup = time.perf_counter() - t0

    # The preconditioner diagonal costs one JVP per state dimension; that stage is timed
    # separately rather than being folded into a single total.
    t0 = time.perf_counter()
    diagonal = torch.zeros_like(linearization.theta)
    for index in range(linearization.theta.numel()):
        column = torch.zeros_like(linearization.theta)
        column[index] = 1.0
        product = linearization.jvp_theta(column)
        diagonal[index] = torch.dot(product, product) + gamma
    preconditioner = time.perf_counter() - t0

    # The refined LSQR helper returns scalar curvatures, not a solution vector.  Its
    # "Fse" is already the reduced value along the right-hand side, so the 2x2 matrix is
    # assembled directly -- it is NOT a correction to be subtracted from F_raw.  The
    # repository's frozen pipeline builds it the same way and then checks it against the
    # explicit reduction.  Three right-hand sides are needed: one per basis column plus
    # their sum, which fixes the off-diagonal.
    basis = [j_lam[:, 0], j_lam[:, 1], j_lam[:, 0] + j_lam[:, 1]]
    t0 = time.perf_counter()
    values = []
    residuals = []
    iterations = []
    for column in basis:
        candidate = scaled_augmented_lsqr_candidates(
            linearization, column, gamma, 1.0e-10, CG_MAX_ITERATIONS, 2
        )
        solved = candidate["scaled_LSQR_iterative_refinement"]
        values.append(float(solved["Fse"]))
        residuals.append(float(solved["verified_original_relative_normal_residual"]))
        iterations.append(int(solved["total_iterations"]))
    solve = time.perf_counter() - t0

    off_diagonal = 0.5 * (values[2] - values[0] - values[1])
    reduced = torch.tensor(
        [[values[0], off_diagonal], [off_diagonal, values[1]]], dtype=torch.float64
    )

    t0 = time.perf_counter()
    relative_residual = max(residuals)
    verification = time.perf_counter() - t0

    return {
        "method": "scaled_LSQR",
        "output": reduced,
        "setup_seconds": setup,
        "spectral_seconds": 0.0,
        "preconditioner_seconds": preconditioner,
        "solve_seconds": solve,
        "verification_seconds": verification,
        "relative_residual": relative_residual,
        "iterations": sum(iterations),
        "status": "PASS"
        if relative_residual <= 1.0e-8
        else "SOLVER_FAILURE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=[215, 218, 220, 224])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    torch.set_default_dtype(torch.float64)
    import yaml

    repo = args.repo.resolve()
    commit = A.resolve_commit(repo)
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    protocol = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "protocol.yaml").read_text(encoding="utf-8")
    )
    alpha_grid = [float(v) for v in protocol["E8"]["gamma_alpha_grid"]]
    alpha_grid.sort()

    from saeps.autodiff import ResidualLinearization

    config = A.two_parameter_config(repo, commit)
    rows = []
    # Streamed as produced. This workload runs for over an hour and a total-only write at
    # the end loses every completed condition if the process is interrupted.
    cost_path = out / "e8_matched_gamma_cost.csv"
    cost_handle = cost_path.open("x", newline="", encoding="utf-8")
    cost_writer = csv.DictWriter(cost_handle, fieldnames=COST_FIELDS)
    cost_writer.writeheader()
    cost_handle.flush()

    for seed in args.seeds:
        state = A.load_checkpoint(repo, commit, seed)
        theta = state["theta"].detach().clone()
        lam = state["coordinate"].detach().clone()
        points = A.rebuild_points(state["points"])
        residual_function = lambda s, c: A.residual(s, c, points, config)  # noqa: E731
        linearization = ResidualLinearization(residual_function, theta, lam)
        # The Jacobian is built once per centre and its cost is reported as a separate
        # stage, so it is not silently multiplied by the number of damping levels.
        t0 = time.perf_counter()
        j_theta, j_lam = linearization.explicit_jacobians()
        jacobian_seconds = time.perf_counter() - t0
        state_block = j_theta.T @ j_theta
        lambda_max = float(torch.linalg.eigvalsh(state_block).max().item())

        for alpha in alpha_grid:
            gamma = alpha * lambda_max
            for method, runner in (
                ("explicit", lambda: dense_reference(linearization, gamma, j_theta, j_lam)),
                ("CG", lambda: cg_reference(linearization, gamma, j_theta, j_lam)),
                ("scaled_LSQR", lambda: lsqr_reference(linearization, gamma, j_theta, j_lam)),
            ):
                reference = dense_reference(linearization, gamma, j_theta, j_lam)["output"]
                runner()  # discarded warm-up
                for repeat in range(1, args.repeats + 1):
                    started = time.perf_counter()
                    result = runner()
                    total = time.perf_counter() - started
                    output = result["output"]
                    denominator = float(torch.linalg.matrix_norm(reference).item())
                    row = {
                        "seed": seed,
                        "benchmark": state["benchmark"],
                        "state_parameters": int(theta.numel()),
                        "residuals": int(A.residual_count(theta, lam, points, config)),
                        "alpha": alpha,
                        "gamma": gamma,
                        "lambda_max": lambda_max,
                        "method": method,
                        "repeat": repeat,
                        "initial_guess": "zero",
                        "warmup_discarded": True,
                        "status": result["status"],
                        "iterations": result["iterations"],
                        "relative_residual": result["relative_residual"],
                        "setup_seconds": result["setup_seconds"],
                        "spectral_seconds": result["spectral_seconds"],
                        "preconditioner_seconds": result["preconditioner_seconds"],
                        "solve_seconds": result["solve_seconds"],
                        "verification_seconds": result["verification_seconds"],
                        "reported_total_seconds": total,
                        "jacobian_setup_seconds_per_centre": jacobian_seconds,
                        "accuracy_vs_dense_reference": float(
                            torch.linalg.matrix_norm(output - reference).item()
                        )
                        / max(denominator, 1.0e-30),
                    }
                    rows.append(row)
                    cost_writer.writerow(row)
                    cost_handle.flush()

    cost_handle.close()

    manifest = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E8_matched_gamma_cost",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "resources": resource_manifest(),
        "conditions": {
            "alpha_grid": alpha_grid,
            "gamma_rule": "alpha * lambda_max(J_theta^T J_theta), computed once per centre",
            "methods": ["explicit", "CG", "scaled_LSQR"],
            "repeats": args.repeats,
            "warmup": "one discarded run per (centre, alpha, method)",
            "initial_guess": "zero",
            "reference": "dense Cholesky solve at the same gamma",
            "seeds": args.seeds,
        },
        "stage_reporting": [
            "setup",
            "spectral",
            "preconditioner",
            "solve",
            "verification",
            "reported_total",
        ],
        "training_and_polish_excluded": True,
        "large_scale_operator_timing_run": False,
        "large_scale_note": (
            "The optional widened-centre operator timing was not run. Nothing in this file "
            "claims training feasibility or curvature accuracy at large state size."
        ),
        "claim_boundary": (
            "Cost comparison only, at matched damping. A larger alpha is a different "
            "geometry and is not selected on accuracy grounds."
        ),
    }
    with (out / "e8_resource_manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

    make_figure(out / "e8_accuracy_cost_tradeoff.pdf", rows)
    print(out)


def make_figure(path: Path, rows: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    methods = ["explicit", "CG", "scaled_LSQR"]
    colours = {"explicit": "#55a868", "CG": "#4c72b0", "scaled_LSQR": "#c44e52"}
    figure, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.2))

    for method in methods:
        grouped = {}
        for row in rows:
            if row["method"] != method:
                continue
            grouped.setdefault(row["alpha"], []).append(
                row["setup_seconds"]
                + row["spectral_seconds"]
                + row["preconditioner_seconds"]
                + row["solve_seconds"]
                + row["verification_seconds"]
            )
        alphas = sorted(grouped)
        medians = [float(np.median(grouped[a])) for a in alphas]
        left.plot(alphas, medians, marker="o", label=method, color=colours[method])
    left.set_xscale("log")
    left.set_yscale("log")
    left.set_xlabel(r"$\alpha$  (damping scale, all methods share $\gamma$)")
    left.set_ylabel("median wall seconds (all stages)")
    left.set_title("cost at matched damping", fontsize=9)
    left.legend(fontsize=7, frameon=False)
    left.grid(True, which="both", linewidth=0.3, alpha=0.5)

    for method in methods:
        alphas, accuracies = [], []
        for alpha in sorted({row["alpha"] for row in rows}):
            values = [
                row["accuracy_vs_dense_reference"]
                for row in rows
                if row["method"] == method and row["alpha"] == alpha
            ]
            if values:
                alphas.append(alpha)
                accuracies.append(max(float(np.median(values)), 1.0e-18))
        right.plot(alphas, accuracies, marker="s", label=method, color=colours[method])
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xlabel(r"$\alpha$")
    right.set_ylabel("relative difference from dense reference")
    right.set_title("accuracy against the dense solve", fontsize=9)
    right.grid(True, which="both", linewidth=0.3, alpha=0.5)

    figure.suptitle(
        "E8 matched-damping cost and accuracy; explicit, CG, scaled LSQR", fontsize=9
    )
    figure.tight_layout()
    figure.savefig(path, format=path.suffix.lstrip(".") or "pdf")
    plt.close(figure)


if __name__ == "__main__":
    main()
