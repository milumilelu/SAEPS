"""Adapter fidelity: recomputed versus historical matrices at the valid two-parameter points.

Point coordinates reproducing bit-exactly is necessary but not sufficient.  A wrong weight
or a wrong config override would keep the points identical and could still pass the E1
coordinate identity.  The only way to close that gap is to rebuild the three reduced
matrices from the archived tensors and compare them against the historical record.

For each of the eight historically valid two-parameter points this script reports, per
quantity, the recomputed 2x2 matrix, the archived matrix, the absolute and relative
differences, and whether the agreement is inside the repository's declared acceptance.
It also records the provenance that a reader needs to reproduce the comparison: the
declared and effective network width, the residual count, the block weights, the damping,
the checkpoint hash and the source config hash.

The recomputation path is the one used by ``e2_curvature_drift``, whose output
``e2_matrix_consistency.csv`` this table supersedes; the two must agree.
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

import e2_curvature_drift as DRIFT  # noqa: E402
import repo_adapter as A  # noqa: E402

HISTORICAL_ROOT = "outputs/runs/v5/two_parameter/confirmation"
LOCKED_CONFIG = "configs/locked/multi.yaml"
EXECUTION_CONFIG = "configs/v5/two_parameter_development_execution.yaml"
# the repository's declared acceptance for a matrix-free result against its explicit
# reference; the observed agreement should be far tighter than this
DECLARED_RELATIVE_ACCEPTANCE = 1.0e-6
RELATIVE_FLOOR = 1.0e-30

QUANTITIES = (
    ("F_raw", "raw"),
    ("F_se_GN_explicit", "explicit"),
    ("H_red_exact_gamma", "gold"),
)


def matrix(rows, key: str) -> torch.Tensor | None:
    if not rows:
        return None
    return torch.tensor(rows, dtype=torch.float64)


def flatten(matrix_value: torch.Tensor) -> tuple[float, float, float]:
    return (
        float(matrix_value[0, 0].item()),
        float(matrix_value[0, 1].item()),
        float(matrix_value[1, 1].item()),
    )


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
    weights = config["loss_weights"]
    report = A.read_json(
        repo, commit, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json"
    )
    validity = {int(r["seed"]): bool(r["binding_valid"]) for r in report["seed_rows"]}

    config_hashes = {
        LOCKED_CONFIG: A.blob_sha256(repo, commit, LOCKED_CONFIG),
        EXECUTION_CONFIG: A.blob_sha256(repo, commit, EXECUTION_CONFIG),
    }

    rows = []
    for seed in args.seeds:
        historical = A.read_json(
            repo, commit, f"{HISTORICAL_ROOT}/seed_{seed}/result.json"
        )
        if not validity.get(seed):
            rows.append(
                {
                    "seed": seed,
                    "binding_valid": False,
                    "status": "NOT_COMPARABLE",
                    "note": "historically invalid point; no archived reduced matrices to compare",
                }
            )
            continue

        gamma = float(historical["gamma"])
        context = DRIFT.context(repo, commit, seed)
        level = DRIFT.curvature_at(context, context["theta0"], gamma)

        checkpoint_path = context["state"]["_path"]
        checkpoint_sha = context["state"]["_sha256"]
        provenance = {
            "seed": seed,
            "binding_valid": True,
            "status": "COMPARED",
            "declared_width": config["_declared_width"],
            "effective_width": config["_effective_width"],
            "state_parameters": int(context["theta0"].numel()),
            "residual_count": int(
                A.residual_count(
                    context["theta0"], context["lam0"], context["points"], config
                )
            ),
            "weight_pde_u": weights["pde_u"],
            "weight_pde_v": weights["pde_v"],
            "weight_data_u": weights["data_u"],
            "weight_data_v": weights["data_v"],
            "weight_initial_u": weights["initial_u"],
            "weight_initial_v": weights["initial_v"],
            "weight_boundary_u": weights["boundary_u"],
            "weight_boundary_v": weights["boundary_v"],
            "alpha": config["_gamma_alpha"],
            "gamma": gamma,
            "objective": "sum objective 1/2 sum rbar_i^2; historical training used the mean",
            "checkpoint_path": checkpoint_path,
            "checkpoint_sha256": checkpoint_sha,
            "locked_config": LOCKED_CONFIG,
            "locked_config_sha256": config_hashes[LOCKED_CONFIG],
            "execution_config": EXECUTION_CONFIG,
            "execution_config_sha256": config_hashes[EXECUTION_CONFIG],
            "source_record": f"{HISTORICAL_ROOT}/seed_{seed}/result.json",
            "source_record_sha256": A.blob_sha256(
                repo, commit, f"{HISTORICAL_ROOT}/seed_{seed}/result.json"
            ),
        }

        for field, key in QUANTITIES:
            recomputed = level[key]
            archived = matrix(historical.get(field), field)
            if recomputed is None or archived is None:
                rows.append(
                    {**provenance, "quantity": field, "status": "NOT_AVAILABLE"}
                )
                continue
            difference = recomputed - archived
            denominator = float(torch.linalg.matrix_norm(archived).item())
            if denominator == 0.0:
                denominator = RELATIVE_FLOOR
            relative = (
                float(torch.linalg.matrix_norm(difference).item()) / denominator
            )
            absolute = float(torch.linalg.matrix_norm(difference).item())
            r00, r01, r11 = flatten(recomputed)
            h00, h01, h11 = flatten(archived)
            rows.append(
                {
                    **provenance,
                    "quantity": field,
                    "status": "PASS"
                    if relative <= DECLARED_RELATIVE_ACCEPTANCE
                    else "FAIL",
                    "recomputed_00": r00,
                    "recomputed_01": r01,
                    "recomputed_11": r11,
                    "historical_00": h00,
                    "historical_01": h01,
                    "historical_11": h11,
                    "absolute_difference_frobenius": absolute,
                    "relative_difference_frobenius": relative,
                    "declared_relative_acceptance": DECLARED_RELATIVE_ACCEPTANCE,
                }
            )

    compared = [r for r in rows if r.get("status") in ("PASS", "FAIL")]
    fields = sorted({k for row in rows for k in row})
    with (out / "adapter_fidelity.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "adapter_fidelity",
        "environment": A.frozen_environment(repo, A.DEFAULT_REF),
        "quantities": [q[0] for q in QUANTITIES],
        "centres_total": len(args.seeds),
        "centres_reported": len({r["seed"] for r in rows}),
        "comparisons": len(compared),
        "comparisons_passing": sum(1 for r in compared if r["status"] == "PASS"),
        "max_relative_difference": max(
            (r["relative_difference_frobenius"] for r in compared), default=None
        ),
        "max_absolute_difference": max(
            (r["absolute_difference_frobenius"] for r in compared), default=None
        ),
        "declared_relative_acceptance": DECLARED_RELATIVE_ACCEPTANCE,
        "rationale": (
            "Bit-exact point regeneration does not by itself prove that the residual map is "
            "reproduced: a wrong weight or config override would preserve both the points and "
            "the E1 coordinate identity. Rebuilding the three reduced matrices and comparing "
            "them to the archive closes that gap."
        ),
        "note": (
            "Supersedes e2_matrix_consistency.csv, which carries the same recomputation under "
            "a different column layout. The two must agree."
        ),
    }
    (out / "adapter_fidelity_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(out)


if __name__ == "__main__":
    main()
