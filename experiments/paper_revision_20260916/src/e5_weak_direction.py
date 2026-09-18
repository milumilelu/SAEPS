"""E5: what the curvature change actually does to a local weak-direction judgment.

Uses the archived two-parameter centres, in one pre-declared parameter metric: the plain
Euclidean metric on the log coefficients.  That metric is fixed before any result is seen
and is independent of the three curvatures being compared.

The historical whitening metric is deliberately NOT reused here.  In the whitened space
F_raw is close to the identity, so "the weakest direction of raw" would be close to an
arbitrary choice; the whitened errors are still reported, but as the legacy metric, and
the directional analysis uses the Euclidean log metric instead.

Reported per centre: the spectrum of each of F_raw, F_SAEPS and H_red, the relative
eigengap with a resolution flag, the angle between weakest directions via arccos|v.w|,
and the quadratic form along four pre-declared directions -- the two coordinate axes and
the two exact eigen-directions.  The exact eigen-directions are shown for reference only
and are never used to select or tune anything.

The exact parameter curvature can be negative.  Signs are reported as signs; negative
curvature is not converted into a variance and no calibrated ellipses are drawn.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

EIGENGAP_RESOLUTION_THRESHOLD = 0.1
FLOOR = 1.0e-30


def symmetric(matrix: torch.Tensor) -> torch.Tensor:
    return 0.5 * (matrix + matrix.T)


def relative_eigengap(values: torch.Tensor) -> float:
    first, second = float(values[0].item()), float(values[1].item())
    return abs(second - first) / max(abs(first), abs(second), FLOOR)


def angle_between(first: torch.Tensor, second: torch.Tensor) -> float:
    """arccos|v.w| in degrees, invariant to eigenvector sign and scale."""
    v = first / torch.linalg.vector_norm(first)
    w = second / torch.linalg.vector_norm(second)
    cosine = min(1.0, abs(float(torch.dot(v, w).item())))
    return float(torch.rad2deg(torch.arccos(torch.tensor(cosine, dtype=torch.float64))).item())


def build_matrices(repo: Path, commit: str, seed: int, config: dict, exact_spec: dict):
    from saeps.autodiff import ResidualLinearization
    from saeps.v3.foundation import full_hessian_references

    state = A.load_checkpoint(repo, commit, seed)
    theta = state["theta"].detach().clone()
    lam = state["coordinate"].detach().clone()
    points = A.rebuild_points(state["points"])
    residual_function = lambda s, c: A.residual(s, c, points, config)  # noqa: E731

    linearization = ResidualLinearization(residual_function, theta, lam)
    j_theta, j_lam = linearization.explicit_jacobians()
    state_block = j_theta.T @ j_theta
    gamma = config["_gamma_alpha"] * float(torch.linalg.eigvalsh(state_block).max().item())
    identity = torch.eye(theta.numel(), dtype=torch.float64)

    f_raw = symmetric(j_lam.T @ j_lam)
    f_se = symmetric(
        j_lam.T @ j_lam
        - j_lam.T @ j_theta @ torch.linalg.solve(state_block + gamma * identity, j_theta.T @ j_lam)
    )
    exact = full_hessian_references(residual_function, theta, lam, gamma, exact_spec)
    h_red = None
    if exact["gamma_matched"]["status"] == "PASS":
        h_red = symmetric(
            torch.tensor(exact["gamma_matched"]["reduced_hessian"], dtype=torch.float64)
        )
    return {"F_raw": f_raw, "F_SAEPS": f_se, "H_red_exact": h_red}, gamma


def main() -> None:
    import yaml

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
    exact_spec = yaml.safe_load(
        A.read_blob(repo, commit, "configs/v4_6/two_parameter_development.yaml")
    )["exact_hessian"]
    report = A.read_json(
        repo, commit, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json"
    )
    validity = {int(r["seed"]): bool(r["binding_valid"]) for r in report["seed_rows"]}
    legacy = {
        int(r["seed"]): {"legacy_E_raw2": r.get("E_raw2"), "legacy_E_SAEPS2": r.get("E_SAEPS2")}
        for r in report["seed_rows"]
    }

    records = []
    per_seed = {}
    for seed in args.seeds:
        matrices, gamma = build_matrices(repo, commit, seed, config, exact_spec)
        if matrices["H_red_exact"] is None:
            per_seed[seed] = {"status": "REFERENCE_REDUCTION_FAILED", "gamma": gamma}
            continue
        entries = {}
        for name, matrix in matrices.items():
            values, vectors = torch.linalg.eigh(matrix)
            entries[name] = {
                "eigenvalues": [float(v) for v in values.tolist()],
                "weakest_direction": [float(v) for v in vectors[:, 0].tolist()],
                "eigengap": relative_eigengap(values),
                "weakest_eigenvalue": float(values[0].item()),
            }
        # the exact eigen-directions are read from the exact matrix, reference only
        exact_values, exact_vectors = torch.linalg.eigh(matrices["H_red_exact"])
        directions = {
            "axis_log_a": torch.tensor([1.0, 0.0], dtype=torch.float64),
            "axis_log_b": torch.tensor([0.0, 1.0], dtype=torch.float64),
            "exact_dir_weak": exact_vectors[:, 0],
            "exact_dir_strong": exact_vectors[:, 1],
        }
        weak = {name: torch.tensor(e["weakest_direction"], dtype=torch.float64) for name, e in entries.items()}
        angles = {
            "angle_raw_vs_SAEPS": angle_between(weak["F_raw"], weak["F_SAEPS"]),
            "angle_raw_vs_exact": angle_between(weak["F_raw"], weak["H_red_exact"]),
            "angle_SAEPS_vs_exact": angle_between(weak["F_SAEPS"], weak["H_red_exact"]),
        }
        resolved = all(
            e["eigengap"] >= EIGENGAP_RESOLUTION_THRESHOLD for e in entries.values()
        )
        per_seed[seed] = {
            "status": "PASS",
            "gamma": gamma,
            "entries": entries,
            "angles": angles,
            "directions_resolved": resolved,
            "exact_eigen_signs": ["positive" if v > 0 else "negative" if v < 0 else "zero" for v in exact_values.tolist()],
            **legacy.get(seed, {}),
        }

        for name, entry in entries.items():
            records.append(
                {
                    "record_type": "spectrum",
                    "seed": seed,
                    "binding_valid": validity.get(seed),
                    "matrix": name,
                    "eigenvalue_weak": entry["eigenvalues"][0],
                    "eigenvalue_strong": entry["eigenvalues"][1],
                    "relative_eigengap": entry["eigengap"],
                    "direction_resolved": entry["eigengap"] >= EIGENGAP_RESOLUTION_THRESHOLD,
                    "weakest_direction_log_a": entry["weakest_direction"][0],
                    "weakest_direction_log_b": entry["weakest_direction"][1],
                }
            )
        for key, value in angles.items():
            records.append(
                {
                    "record_type": "angle",
                    "seed": seed,
                    "binding_valid": validity.get(seed),
                    "pair": key,
                    "angle_degrees": value,
                    "directions_resolved": resolved,
                }
            )
        for direction_name, vector in directions.items():
            for name, matrix in matrices.items():
                records.append(
                    {
                        "record_type": "directional_curvature",
                        "seed": seed,
                        "binding_valid": validity.get(seed),
                        "matrix": name,
                        "direction": direction_name,
                        "quadratic_form": float((vector @ matrix @ vector).item()),
                        "direction_is_exact_reference": direction_name.startswith("exact_dir"),
                    }
                )

    fieldnames = sorted({k for row in records for k in row})
    with (out / "e5_directional_curvature.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    valid = [s for s in per_seed if per_seed[s].get("status") == "PASS" and validity.get(s)]
    angles = [
        per_seed[s]["angles"][k]
        for s in valid
        for k in ("angle_raw_vs_exact", "angle_SAEPS_vs_exact")
    ]
    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E5_weak_direction_diagnostic",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "parameter_metric": "plain Euclidean metric on the log coefficients",
        "metric_rationale": (
            "fixed before any result and independent of the three curvatures compared; the "
            "whitened space is not used to pick the raw weak direction because F_raw is "
            "approximately the identity there"
        ),
        "eigengap_resolution_threshold": EIGENGAP_RESOLUTION_THRESHOLD,
        "centres_total": len(args.seeds),
        "centres_valid": len(valid),
        "centres_valid_with_resolved_directions": sum(
            1 for s in valid if per_seed[s]["directions_resolved"]
        ),
        "median_angle_raw_vs_exact_degrees": statistics.median(
            [per_seed[s]["angles"]["angle_raw_vs_exact"] for s in valid]
        )
        if valid
        else None,
        "median_angle_SAEPS_vs_exact_degrees": statistics.median(
            [per_seed[s]["angles"]["angle_SAEPS_vs_exact"] for s in valid]
        )
        if valid
        else None,
        "exact_curvature_signs": {
            str(s): per_seed[s]["exact_eigen_signs"] for s in valid
        },
        "per_seed": {str(k): v for k, v in per_seed.items()},
        "claim_boundary": (
            "Local diagnostic only. This does not show improved parameter recovery accuracy, "
            "and negative exact curvature is reported as a sign, never as a variance."
        ),
    }
    with (out / "e5_weak_direction_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")

    make_figure(out / "e5_weak_direction_comparison.pdf", records, per_seed, valid)
    print(out)


def make_figure(path: Path, records: list[dict], per_seed: dict, valid: list[int]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    figure, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    direction_order = ["axis_log_a", "axis_log_b", "exact_dir_weak", "exact_dir_strong"]
    labels = ["log a axis", "log b axis", "exact weak dir", "exact strong dir"]
    matrices = ["F_raw", "F_SAEPS", "H_red_exact"]
    colours = {"F_raw": "#c44e52", "F_SAEPS": "#4c72b0", "H_red_exact": "#55a868"}
    width = 0.26
    positions = np.arange(len(direction_order))
    for offset, name in enumerate(matrices):
        medians, lows, highs = [], [], []
        for direction in direction_order:
            values = [
                row["quadratic_form"]
                for row in records
                if row["record_type"] == "directional_curvature"
                and row["direction"] == direction
                and row["matrix"] == name
                and row["binding_valid"]
            ]
            medians.append(float(np.median(values)) if values else float("nan"))
            lows.append(float(np.min(values)) if values else float("nan"))
            highs.append(float(np.max(values)) if values else float("nan"))
        left.bar(positions + (offset - 1) * width, medians, width, label=name, color=colours[name])
        left.errorbar(
            positions + (offset - 1) * width,
            medians,
            yerr=[np.array(medians) - np.array(lows), np.array(highs) - np.array(medians)],
            fmt="none",
            ecolor="#333333",
            elinewidth=0.8,
            capsize=2,
        )
    left.set_xticks(positions)
    left.set_xticklabels(labels, fontsize=8)
    left.set_ylabel("quadratic form  $v^{T} M v$")
    left.set_title("curvature along pre-declared directions\n(median and range over valid centres)", fontsize=9)
    left.axhline(0.0, color="#999999", linewidth=0.8, linestyle=":")
    left.legend(fontsize=7, frameon=False)

    angle_keys = ["angle_raw_vs_exact", "angle_SAEPS_vs_exact"]
    angle_labels = ["raw vs exact", "SAEPS vs exact"]
    for index, key in enumerate(angle_keys):
        values = [per_seed[s]["angles"][key] for s in valid]
        jitter = np.linspace(-0.08, 0.08, len(values))
        right.scatter(
            np.full(len(values), index) + jitter,
            values,
            s=18,
            color="#4c72b0" if index else "#c44e52",
            alpha=0.8,
        )
        right.hlines(
            float(np.median(values)),
            index - 0.25,
            index + 0.25,
            color="#333333",
            linewidth=1.6,
        )
    right.set_xticks([0, 1])
    right.set_xticklabels(angle_labels, fontsize=8)
    right.set_ylabel("angle between weakest directions (degrees)")
    right.set_title("$\\arccos|v\\cdot w|$ per valid centre\n(bar is the median)", fontsize=9)
    right.set_ylim(0, 90)
    figure.suptitle(
        "E5 local weak-direction diagnostic; Euclidean metric on log coefficients",
        fontsize=9,
    )
    figure.tight_layout()
    figure.savefig(path, format=path.suffix.lstrip(".") or "pdf")
    plt.close(figure)


if __name__ == "__main__":
    main()
