"""E4: parameter-coordinate and state-metric audit.

Two separate questions, kept apart on purpose.

Parameter coordinate.  For a physical coefficient ``a`` and ``lambda = log a``, with
``D = diag(a)`` and ``g_a`` the gradient in physical coordinates:

    F_se(lambda) = D F_se(a) D                       (Gauss-Newton reduction is equivariant)
    H_red(lambda) = D H_red(a) D + diag(a * g_a)     (the exact Hessian is not)

The second relation carries a gradient term.  At a non-stationary point that term is
non-zero and dropping it is an error, so both forms are reported and the naive form is
shown to fail rather than assumed away.

State coordinate.  Reparameterising the state as ``theta = theta_0 + T z`` turns the
Euclidean penalty into ``(gamma/2) z^T T^T T z``.  Two controls are run and must be read
differently:

  control 1  keeps the metric ``T^T T``.  The objective is unchanged, so the reduced
             curvature must be invariant.
  control 2  uses the identity metric instead.  That changes the objective, so invariance
             must NOT be required; the deviation is the point of the control.

Nothing here claims invariance under arbitrary reparameterisation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import torch
import torch.func as tf

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

FLOOR = 1.0e-30
ORTHOGONAL_SEED = 20260916


def relative(left: torch.Tensor, right: torch.Tensor, floor: float = FLOOR) -> float:
    denominator = float(torch.linalg.matrix_norm(right).item())
    if denominator == 0.0:
        denominator = floor
    return float(torch.linalg.matrix_norm(left - right).item()) / denominator


def make_transforms(size: int) -> dict[str, torch.Tensor]:
    """One orthogonal and two diagonal transforms, fixed before any result is seen."""
    generator = torch.Generator(device="cpu").manual_seed(ORTHOGONAL_SEED)
    raw = torch.randn(size, size, dtype=torch.float64, generator=generator)
    q, r = torch.linalg.qr(raw)
    q = q * torch.sign(torch.diagonal(r)).unsqueeze(0)
    transforms = {"orthogonal": q}
    for condition in (10.0, 100.0):
        # geometric spread about one, so the transform is well scaled and its condition
        # number is exactly the requested value
        exponent = torch.linspace(-0.5, 0.5, size, dtype=torch.float64)
        diagonal = condition**exponent
        transforms[f"diag_cond{int(condition)}"] = torch.diag(diagonal)
    return transforms


def objective(theta, lam, points, config) -> torch.Tensor:
    r = A.residual(theta, lam, points, config)
    return 0.5 * (r * r).sum()


def schur(joint: torch.Tensor, state_size: int, metric: torch.Tensor, gamma: float) -> torch.Tensor:
    """Eliminate the state block and return the reduced parameter curvature."""
    state = joint[:state_size, :state_size] + gamma * metric
    cross = joint[:state_size, state_size:]
    mixed = joint[state_size:, :state_size]
    parameter = joint[state_size:, state_size:]
    return parameter - mixed @ torch.linalg.solve(state, cross)


def audit_centre(repo: Path, commit: str, seed: int, config: dict) -> list[dict]:
    from saeps.autodiff import ResidualLinearization
    from saeps.v3.foundation import full_hessian_references

    state = A.load_checkpoint(repo, commit, seed)
    theta0 = state["theta"].detach().clone()
    lam0 = state["coordinate"].detach().clone()
    points = A.rebuild_points(state["points"])
    residual_function = lambda s, c: A.residual(s, c, points, config)  # noqa: E731
    rows = []

    linearization = ResidualLinearization(residual_function, theta0, lam0)
    j_theta, j_lam = linearization.explicit_jacobians()
    g_theta = j_theta.T @ linearization.residual()
    state_block = j_theta.T @ j_theta
    gamma = config["_gamma_alpha"] * float(torch.linalg.eigvalsh(state_block).max().item())

    def gn_reduction(j_state, j_parameter, metric):
        block = j_state.T @ j_state + gamma * metric
        return j_parameter.T @ j_parameter - j_parameter.T @ j_state @ torch.linalg.solve(
            block, j_state.T @ j_parameter
        )

    # --- parameter coordinate -------------------------------------------------
    physical = torch.exp(lam0)
    j_physical = torch.vstack(
        [
            j_lam[:, 0] / physical[0],
            j_lam[:, 1] / physical[1],
        ]
    ).T
    f_se_log = gn_reduction(j_theta, j_lam, torch.eye(theta0.numel(), dtype=theta0.dtype))
    f_se_physical = gn_reduction(j_theta, j_physical, torch.eye(theta0.numel(), dtype=theta0.dtype))
    d = torch.diag(physical)
    scaled = d @ f_se_physical @ d

    exact = full_hessian_references(
        residual_function, theta0, lam0, gamma, config["_exact_hessian"]
    )
    h_red_log = (
        torch.tensor(exact["gamma_matched"]["reduced_hessian"], dtype=torch.float64)
        if exact["gamma_matched"]["status"] == "PASS"
        else None
    )
    h_red_physical = None
    if h_red_log is not None:
        lam_physical = torch.log(physical).detach()
        physical_function = lambda s, a: residual_function(s, torch.log(a))  # noqa: E731
        exact_physical = full_hessian_references(
            physical_function, theta0, physical, gamma, config["_exact_hessian"]
        )
        if exact_physical["gamma_matched"]["status"] == "PASS":
            h_red_physical = torch.tensor(
                exact_physical["gamma_matched"]["reduced_hessian"], dtype=torch.float64
            )

    # d ell / d a = (1/a) d ell / d lambda, componentwise
    gradient_physical = (j_lam.T @ linearization.residual()) / physical

    rows.append(
        {
            "seed": seed,
            "test": "parameter_coordinate_gn_equivariance",
            "quantity": "F_se(lambda) - D F_se(a) D",
            "relative_error": relative(f_se_log, scaled),
            "tolerance": 1.0e-10,
            "required": True,
        }
    )
    if h_red_log is not None and h_red_physical is not None:
        with_gradient = d @ h_red_physical @ d + torch.diag(physical * gradient_physical)
        without_gradient = d @ h_red_physical @ d
        rows.append(
            {
                "seed": seed,
                "test": "parameter_coordinate_exact_equivariance_with_gradient_term",
                "quantity": "H_red(lambda) - (D H_red(a) D + diag(a g_a))",
                "relative_error": relative(h_red_log, with_gradient),
                "tolerance": 1.0e-10,
                "required": True,
            }
        )
        rows.append(
            {
                "seed": seed,
                "test": "parameter_coordinate_exact_naive_without_gradient_term",
                "quantity": "H_red(lambda) - D H_red(a) D",
                "relative_error": relative(h_red_log, without_gradient),
                "tolerance": 1.0e-10,
                "required": False,
                "note": "drops the gradient term; must fail at a non-stationary point",
            }
        )
        rows[-1]["gradient_term_norm"] = float(
            torch.linalg.matrix_norm(torch.diag(physical * gradient_physical)).item()
        )
        rows[-1]["stationarity_parameter_gradient_norm"] = float(
            torch.linalg.vector_norm(gradient_physical).item()
        )

    # --- state coordinate -----------------------------------------------------
    size = theta0.numel()
    identity = torch.eye(size, dtype=torch.float64)
    base_objective = float(objective(theta0, lam0, points, config).item())
    # A fixed non-zero displacement, so the penalty term is actually exercised. At z = 0
    # every metric gives the same penalty value and the control would be vacuous.
    probe_generator = torch.Generator(device="cpu").manual_seed(ORTHOGONAL_SEED + 1)
    z_probe = torch.randn(size, dtype=torch.float64, generator=probe_generator)
    z_probe = 1.0e-3 * z_probe / float(torch.linalg.vector_norm(z_probe).item())

    for name, transform in make_transforms(size).items():
        inverse = torch.linalg.inv(transform)

        def z_residual(z, ll):
            return residual_function((theta0 + transform @ z).reshape(-1), ll)

        z0 = torch.zeros(size, dtype=torch.float64)  # the archived state sits at z = 0

        # Hessian of the unpenalised objective in z. The damping metric is supplied to
        # schur() instead, exactly as the theta-space reference does, so the two routes
        # differ only in the metric under test and not by a double-counted penalty.
        joint_z = tf.hessian(
            lambda joint_vector: 0.5
            * (z_residual(joint_vector[:size], joint_vector[size:]) ** 2).sum()
        )(torch.cat([z0, lam0]))

        metric = transform.T @ transform
        reduced_kept = schur(joint_z, size, metric, gamma)
        reduced_identity = schur(joint_z, size, identity, gamma)

        # Penalty comparison on the fixed probe displacement: control 1 reproduces the
        # Euclidean penalty, control 2 does not.
        penalty_kept = float((0.5 * gamma * (z_probe @ metric @ z_probe)).item())
        moved = (transform @ z_probe).reshape(-1)
        penalty_reference = float((0.5 * gamma * (moved @ moved)).item())
        penalty_identity = float((0.5 * gamma * (z_probe @ z_probe)).item())

        entry_base = {
            "seed": seed,
            "transform": name,
            "condition_number": float(torch.linalg.cond(transform).item()),
        }
        rows.append(
            {
                **entry_base,
                "test": "state_metric_control1_metric_TtT_penalty",
                "quantity": "|penalty(z, T^T T) - penalty(theta)| relative",
                "relative_error": abs(penalty_kept - penalty_reference)
                / max(abs(penalty_reference), FLOOR),
                "tolerance": 1.0e-10,
                "required": True,
            }
        )
        if h_red_log is not None:
            rows.append(
                {
                    **entry_base,
                    "test": "state_metric_control1_metric_TtT_reduced_curvature",
                    "quantity": "H_red(z, metric T^T T) - H_red(theta)",
                    "relative_error": relative(reduced_kept, h_red_log),
                    "tolerance": 1.0e-8,
                    "required": True,
                }
            )
            rows.append(
                {
                    **entry_base,
                    "test": "state_metric_control2_identity_metric_reduced_curvature",
                    "quantity": "H_red(z, identity metric) - H_red(theta)",
                    "relative_error": relative(reduced_identity, h_red_log),
                    "tolerance": None,
                    "required": False,
                    "note": "the identity metric changes the objective; invariance is not "
                    "expected, and for the orthogonal transform the two metrics coincide",
                }
            )
        rows.append(
            {
                **entry_base,
                "test": "state_metric_control2_identity_metric_penalty",
                "quantity": "|penalty(z, identity metric) - penalty(theta)| relative",
                "relative_error": abs(penalty_identity - penalty_reference)
                / max(abs(penalty_reference), FLOOR),
                "tolerance": None,
                "required": False,
                "note": "expected to be non-zero except for the orthogonal transform",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(A.TWO_PARAMETER_SEEDS))
    args = parser.parse_args()

    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    commit = A.resolve_commit(repo)
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    config = A.two_parameter_config(repo, commit)
    config["_gamma_alpha"] = config["_gamma_alpha"]
    import yaml

    config["_exact_hessian"] = yaml.safe_load(
        A.read_blob(repo, commit, "configs/v4_6/two_parameter_development.yaml")
    )["exact_hessian"]

    report = A.read_json(
        repo, commit, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json"
    )
    validity = {int(r["seed"]): bool(r["binding_valid"]) for r in report["seed_rows"]}

    rows = []
    for seed in args.seeds:
        for row in audit_centre(repo, commit, seed, config):
            row["binding_valid"] = validity.get(seed)
            rows.append(row)

    fieldnames = sorted({k for row in rows for k in row})
    with (out / "e4_coordinate_metric_audit.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    required = [r for r in rows if r["required"]]
    control2 = [r for r in rows if r.get("test", "").startswith("state_metric_control2")]
    naive = [r for r in rows if r["test"].endswith("naive_without_gradient_term")]
    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E4_coordinate_metric_audit",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "centres": len(args.seeds),
        "rows": len(rows),
        "required_checks": len(required),
        "required_checks_passing": sum(1 for r in required if r["relative_error"] <= r["tolerance"]),
        "required_checks_passing_binding_valid": sum(
            1 for r in required if r["binding_valid"] and r["relative_error"] <= r["tolerance"]
        ),
        "required_checks_binding_valid": sum(1 for r in required if r["binding_valid"]),
        "naive_gradient_term_dropped_max_error": max(
            (r["relative_error"] for r in naive), default=None
        ),
        "naive_gradient_term_dropped_min_error": min(
            (r["relative_error"] for r in naive), default=None
        ),
        "control2_max_deviation": max((r["relative_error"] for r in control2), default=None),
        "claim_boundary": (
            "No claim of invariance under arbitrary reparameterisation. Only the linear "
            "state transform with the matching metric is invariant, and the physical-coordinate "
            "exact Hessian requires the gradient term."
        ),
    }
    with (out / "e4_coordinate_metric_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(out)


if __name__ == "__main__":
    main()
