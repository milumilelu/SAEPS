"""E6: does the accuracy hold at larger networks.

The historical width comparison widened the base network by inserting zero-output hidden
units, which preserves the function but not the optimization, and its wide arm produced
no valid centre at all.  This experiment trains genuinely different architectures on the
same data, noise and initializations, so accuracy and widening cost are separated.

Three architectures share data seeds and initializations (paired by construction):

    [2, 16, 1]     n_theta 65    the E3 base structure
    [2, 32, 1]     n_theta 129
    [2, 16, 16, 1] n_theta 337   two hidden layers

Per centre the same curvature quantities are computed as in E3, plus an independent
Hessian-vector-product check: the Hessian assembled from autodiff is compared against a
forward-over-reverse HVP on randomly chosen directions, so a mis-assembled block cannot
pass unnoticed.

Results are streamed to disk as produced; this run takes hours.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import center_cache as C  # noqa: E402
import e3_saturation as E3  # noqa: E402
import repo_adapter as A  # noqa: E402

ARCHITECTURES = {
    "base_2_16_1": [2, 16, 1],
    "wide_2_32_1": [2, 32, 1],
    "deep_2_16_16_1": [2, 16, 16, 1],
}
HVP_DIRECTIONS = 3


def curvature(fit: dict, config: dict) -> dict:
    """F_raw, F_se and the exact reference at the frozen damping rule."""
    from torch.autograd.functional import jacobian
    from saeps.v3.foundation import full_hessian_references

    theta, lam = fit["theta"], fit["lam"]
    points, local, arch = fit["points"], fit["local"], fit["architecture"]
    rfun = lambda t, l: C.weighted_residual(t, l, points, local, arch)  # noqa: E731

    theta_v = theta.detach().clone().requires_grad_(True)
    lam_v = lam.detach().clone().requires_grad_(True)
    j_theta = jacobian(lambda t: rfun(t, lam_v), theta_v, strategy="forward-mode", vectorize=True)
    j_lam = jacobian(lambda l: rfun(theta_v, l), lam_v, strategy="forward-mode", vectorize=True)

    state_block = j_theta.T @ j_theta
    gamma = config["gamma_alpha"] * float(torch.linalg.eigvalsh(state_block).max().item())
    f_raw = j_lam.T @ j_lam
    f_se = f_raw - j_lam.T @ j_theta @ torch.linalg.solve(
        state_block + gamma * torch.eye(theta.numel(), dtype=theta.dtype), j_theta.T @ j_lam
    )
    exact = full_hessian_references(rfun, theta, lam, gamma, config["exact_hessian"])
    matched = exact["gamma_matched"]
    if matched["status"] != "PASS":
        return {
            "available": False,
            "gamma": gamma,
            "failure_reason": matched.get("failure_reason"),
            "minimum_state_eigenvalue": matched.get("minimum_state_eigenvalue"),
        }
    h_red = float(matched["reduced_hessian"][0][0])
    h_fix = float(exact["exact_parameter_block"][0][0])
    raw = float(f_raw[0, 0].item())
    se = float(f_se[0, 0].item())
    floor = config["scalar_error_floor"]
    denom = abs(h_red) + floor
    c_exact = h_red - h_fix
    c_gn = se - raw
    return {
        "available": True,
        "gamma": gamma,
        "minimum_state_eigenvalue": matched.get("minimum_state_eigenvalue"),
        "F_raw": raw,
        "F_se_GN": se,
        "H_fix_exact": h_fix,
        "H_red_exact": h_red,
        "E_raw": abs(raw - h_red) / denom,
        "E_SAEPS": abs(se - h_red) / denom,
        "E_fix": abs(h_fix - h_red) / denom,
        "E_GN_fix": abs(c_gn) / (abs(h_fix) + floor),
        "E_relax": abs(c_gn - c_exact) / (abs(c_exact) + floor),
    }


def hvp_consistency(fit: dict) -> dict:
    """Compare the assembled state Hessian against an independent HVP.

    The assembled block also gives the damping scale, so this checks the matrix the
    reduction actually uses rather than a separate quantity.
    """
    theta, lam = fit["theta"], fit["lam"]
    points, local, arch = fit["points"], fit["local"], fit["architecture"]
    loss = lambda t: C.objective(t, lam, points, local, arch)  # noqa: E731

    probe = theta.detach().clone().requires_grad_(True)
    assembled = torch.func.hessian(loss)(probe)
    worst = 0.0
    for index in range(HVP_DIRECTIONS):
        generator = torch.Generator(device="cpu").manual_seed(7000 + index)
        vector = torch.randn(theta.numel(), dtype=torch.float64, generator=generator)
        vector = vector / torch.linalg.vector_norm(vector)
        from_matrix = assembled @ vector
        gradient = torch.autograd.grad(loss(probe), probe, create_graph=True)[0]
        independent = torch.autograd.grad((gradient * vector).sum(), probe)[0]
        relative = float(torch.linalg.vector_norm(from_matrix - independent).item()) / max(
            float(torch.linalg.vector_norm(independent).item()), 1.0e-30
        )
        worst = max(worst, relative)
    return {"hvp_max_relative_difference": worst, "hvp_directions": HVP_DIRECTIONS}


def main() -> None:
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

    protocol_path = Path(__file__).resolve().parents[1] / "protocol.yaml"
    import yaml

    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    e6 = protocol["E6"]
    budget = int(protocol["E3"]["optimizer_proposal"]["fixed_parameter_state_polish_max_iterations"])
    config = E3.load_config(repo, A.resolve_commit(repo))

    accuracy_path = out / "e6_architecture_accuracy.csv"
    availability_path = out / "e6_center_availability.csv"
    accuracy_fields = [
        "architecture", "label", "state_parameters", "residuals", "data_seed",
        "initialization_seed", "noise_level", "available", "failure_reason", "gamma",
        "minimum_state_eigenvalue", "objective", "normalized_state_gradient",
        "polish_iterations", "train_seconds", "kappa_estimate", "kappa_relative_error",
        "F_raw", "F_se_GN", "H_fix_exact", "H_red_exact", "E_raw", "E_SAEPS", "E_fix",
        "E_GN_fix", "E_relax", "hvp_max_relative_difference",
    ]
    availability_fields = [
        "architecture", "label", "state_parameters", "residuals", "data_seed",
        "initialization_seed", "noise_level", "centre_available", "failure_reason",
        "polish_iterations", "normalized_state_gradient", "train_seconds",
        "reference_reduction_status",
    ]
    accuracy_handle = accuracy_path.open("x", newline="", encoding="utf-8")
    accuracy_writer = csv.DictWriter(accuracy_handle, fieldnames=accuracy_fields)
    accuracy_writer.writeheader()
    accuracy_handle.flush()
    availability_handle = availability_path.open("x", newline="", encoding="utf-8")
    availability_writer = csv.DictWriter(availability_handle, fieldnames=availability_fields)
    availability_writer.writeheader()
    availability_handle.flush()

    accuracy_rows = []
    availability_rows = []
    for label, arch in ARCHITECTURES.items():
        for data_seed in [int(v) for v in e6["data_seeds"]]:
            for init_seed in [int(v) for v in e6["initialization_seeds"]]:
                fit = C.load_or_train(
                    cache, config, arch, data_seed, init_seed, float(e6["noise_level"]), budget
                )
                result = curvature(fit, config)
                result.update(hvp_consistency(fit))
                kappa = float(torch.exp(fit["lam"].reshape(())).item())
                accuracy_rows.append(
                    {
                        "architecture": "_".join(str(v) for v in arch),
                        "label": label,
                        "state_parameters": fit["state_parameters"],
                        "residuals": fit["residuals"],
                        "data_seed": data_seed,
                        "initialization_seed": init_seed,
                        "noise_level": float(e6["noise_level"]),
                        "objective": fit["objective"],
                        "normalized_state_gradient": fit["normalized_state_gradient"],
                        "polish_iterations": fit["polish_iterations"],
                        "train_seconds": fit["seconds"],
                        "kappa_estimate": kappa,
                        "kappa_relative_error": abs(kappa - config["kappa_truth"])
                        / config["kappa_truth"],
                        **result,
                    }
                )
                availability_rows.append(
                    {
                        "architecture": "_".join(str(v) for v in arch),
                        "label": label,
                        "state_parameters": fit["state_parameters"],
                        "residuals": fit["residuals"],
                        "data_seed": data_seed,
                        "initialization_seed": init_seed,
                        "noise_level": float(e6["noise_level"]),
                        "centre_available": result["available"],
                        "failure_reason": result.get("failure_reason"),
                        "polish_iterations": fit["polish_iterations"],
                        "normalized_state_gradient": fit["normalized_state_gradient"],
                        "train_seconds": fit["seconds"],
                        "reference_reduction_status": "PASS"
                        if result["available"]
                        else "REFERENCE_REDUCTION_FAILED",
                    }
                )
                row = accuracy_rows[-1]
                accuracy_writer.writerow({k: row.get(k) for k in accuracy_fields})
                accuracy_handle.flush()
                availability_writer.writerow(availability_rows[-1])
                availability_handle.flush()
                print(
                    f"  {label} data={data_seed} init={init_seed} "
                    f"avail={result['available']} kappa={kappa:.5f} "
                    f"E_SAEPS={result.get('E_SAEPS')}",
                    flush=True,
                )

    accuracy_handle.close()
    availability_handle.close()

    by_arch = {}
    for label in ARCHITECTURES:
        group = [r for r in accuracy_rows if r["label"] == label]
        valid = [r for r in group if r["available"]]
        by_arch[label] = {
            "state_parameters": group[0]["state_parameters"],
            "fits": len(group),
            "centres_available": len(valid),
            "centre_availability_rate": len(valid) / len(group),
            "median_E_raw": statistics.median([r["E_raw"] for r in valid]) if valid else None,
            "median_E_SAEPS": statistics.median([r["E_SAEPS"] for r in valid]) if valid else None,
            "median_E_fix": statistics.median([r["E_fix"] for r in valid]) if valid else None,
            "median_E_GN_fix": statistics.median([r["E_GN_fix"] for r in valid]) if valid else None,
            "median_E_relax": statistics.median([r["E_relax"] for r in valid]) if valid else None,
            "SAEPS_wins": sum(1 for r in valid if r["E_SAEPS"] < r["E_raw"]),
            "median_kappa_relative_error": statistics.median(
                [r["kappa_relative_error"] for r in valid]
            )
            if valid
            else None,
            "median_train_seconds": statistics.median([r["train_seconds"] for r in group]),
            "median_polish_iterations": statistics.median([r["polish_iterations"] for r in group]),
            "max_hvp_relative_difference": max(
                (r["hvp_max_relative_difference"] for r in group), default=None
            ),
        }

    summary = {
        "classification": "NEW_EXPERIMENT",
        "task": "E6_architecture_accuracy",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "label": e6["label"],
        "independent_confirmation": bool(e6["independent_confirmation"]),
        "training_budget": budget,
        "design": "paired: same data seeds, same initializations, same noise for every architecture",
        "by_architecture": by_arch,
        "hvp_check": (
            "the assembled state Hessian is compared against an independent forward-over-reverse "
            "Hessian-vector product on fixed random directions"
        ),
        "claim_boundary": (
            "Architecture extension only. Failures are reported as unavailable centres and are "
            "not replaced by function-preserving widening; nothing here revises the historical "
            "width-32 result, which produced no valid centre."
        ),
    }
    (out / "e6_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    make_figure(out / "e6_accuracy_cost.pdf", accuracy_rows, by_arch)
    print(out)


def make_figure(path: Path, rows: list[dict], by_arch: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    labels = [k for k in ARCHITECTURES if k in by_arch]
    colours = {"base_2_16_1": "#55a868", "wide_2_32_1": "#4c72b0", "deep_2_16_16_1": "#c44e52"}
    figure, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.2))

    for label in labels:
        group = [r for r in rows if r["label"] == label and r["available"]]
        if not group:
            continue
        left.scatter(
            [r["train_seconds"] for r in group],
            [max(r["E_SAEPS"], 1e-18) for r in group],
            s=26,
            color=colours.get(label, "#333333"),
            label=f"{label} (n={by_arch[label]['state_parameters']})",
        )
        left.scatter(
            [statistics.median([r["train_seconds"] for r in group])],
            [statistics.median([r["E_SAEPS"] for r in group])],
            marker="X",
            s=110,
            color=colours.get(label, "#333333"),
            edgecolor="black",
            linewidth=0.6,
        )
    left.set_xscale("log")
    left.set_yscale("log")
    left.set_xlabel("training seconds per centre (log)")
    left.set_ylabel(r"$E_{SAEPS}$ (log)")
    left.set_title("accuracy against cost per centre\n(cross = median)", fontsize=9)
    left.legend(fontsize=7, frameon=False)
    left.grid(True, which="both", linewidth=0.3, alpha=0.5)

    positions = np.arange(len(labels))
    values = [by_arch[label]["centre_availability_rate"] for label in labels]
    right.bar(positions, values, 0.55, color=[colours.get(l, "#333") for l in labels])
    for index, label in enumerate(labels):
        right.text(
            index,
            values[index] + 0.03,
            f"{by_arch[label]['centres_available']}/{by_arch[label]['fits']}",
            ha="center",
            fontsize=8,
        )
    right.set_xticks(positions)
    right.set_xticklabels([f"n={by_arch[l]['state_parameters']}" for l in labels], fontsize=8)
    right.set_ylim(0, 1.25)
    right.set_ylabel("centre availability rate")
    right.set_title("centres with a valid exact reduction", fontsize=9)

    figure.suptitle("E6 architecture accuracy and availability (paired design)", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, format=path.suffix.lstrip(".") or "pdf")
    plt.close(figure)


if __name__ == "__main__":
    main()
