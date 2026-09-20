"""Development-only audit of finite-gamma center refinement.

The existing profile-point records are immutable inputs.  This diagnostic only
reoptimizes the lambda0 center and recomputes the symmetric curvature using
that center loss; it does not change the failed S2 protocol or authorize
confirmation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth
from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v5.finite_gamma import _load_checkpoint, _runtime
from saeps.v5.governance import sha256_file


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fit(record: dict[str, Any], center_loss: float, h_values: list[float], gate: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row for row in record["profile_points"]
        if row["status"] == "PASS" and abs(float(row["h"])) in h_values
    ]
    if len(rows) != 2 * len(h_values):
        return {"status": "PROFILE_FAILURE", "point_count": len(rows), "fit_quality_gate": "FAIL"}
    x = torch.tensor([0.0] + [float(row["offset"]) for row in rows], dtype=torch.float64)
    y = torch.tensor([center_loss] + [float(row["loss_mean"]) for row in rows], dtype=torch.float64)
    design = torch.stack([torch.ones_like(x), x, 0.5 * x.square()], dim=1)
    coefficient = torch.linalg.lstsq(design, y).solution
    residual = y - design @ coefficient
    total = y - y.mean()
    rss = float(torch.dot(residual, residual).item())
    tss = float(torch.dot(total, total).item())
    r_squared = 1.0 if tss == 0.0 else 1.0 - rss / tss
    normalized_rmse = float(torch.sqrt(torch.mean(residual.square())).item()) / max(
        float((y.max() - y.min()).item()), torch.finfo(y.dtype).eps
    )
    condition = float(torch.linalg.cond(design).item())
    curvature = float(coefficient[2].item())
    passed = (
        r_squared >= float(gate["minimum_r_squared"])
        and normalized_rmse <= float(gate["maximum_normalized_rmse"])
        and condition <= float(gate["maximum_design_condition"])
        and (not gate["positive_curvature_required"] or curvature > 0.0)
    )
    return {
        "status": "PASS",
        "point_count": len(rows),
        "r_squared": r_squared,
        "normalized_rmse": normalized_rmse,
        "design_condition": condition,
        "curvature": curvature,
        "fit_quality_gate": "PASS" if passed else "FAIL",
    }


def run(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root / "configs/paper_strengthening/center_refinement_development.yaml")
    p3 = load_config(root / "configs/p3_profile.yaml")
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    local = copy.deepcopy(numerical["center"]["local_minimum"])
    local["normalized_gradient_tolerance"] = float(config["center_refinement"]["normalized_gradient_tolerance"])
    local["stopping"]["normalized_gradient"] = float(config["center_refinement"]["normalized_gradient_tolerance"])
    provenance = environment_provenance(root, "float64", "cpu")
    output_root = root / config["output_root"]
    rows: list[dict[str, Any]] = []
    for seed in config["development_seeds"]:
        destination = output_root / f"seed_{seed}"
        if destination.exists():
            raise RuntimeError(f"center-refinement output already exists: {destination}")
        destination.mkdir(parents=True, exist_ok=False)
        started = time.perf_counter()
        theta0, parameter0, points, manifest, _ = _load_checkpoint(root, "allen_cahn", int(seed))
        runtime, runtime_hashes, benchmark = _runtime(root, "allen_cahn")
        truth = solve_truth(runtime, benchmark)
        residual_function = lambda state, coordinate: scalar_residual(
            state, coordinate, benchmark, points, truth, runtime
        )
        linearization = ResidualLinearization(residual_function, theta0, parameter0)
        jacobian_theta, _ = linearization.explicit_jacobians()
        gamma = float(config["gamma_alpha"]) * float(torch.linalg.svdvals(jacobian_theta)[0].square())
        objective = _mean_residual_objective(residual_function, parameter0, theta0, gamma, True)
        before = float(objective(theta0).item())
        refined, optimization = optimize_state_local_minimum(objective, theta0, local)
        if refined is None:
            raise RuntimeError(f"center refinement failed for seed {seed}: {optimization}")
        diagnostics, _, _, _ = exact_state_diagnostics(objective, refined, local)
        after = float(objective(refined).item())
        source = root / config["source_profile_root"] / f"seed_{seed}/result.json"
        profile = json.loads(source.read_text(encoding="utf-8"))
        losses = {float(row["offset"]): float(row["loss_mean"]) for row in profile["profile_points"]}
        curvatures = []
        for h in [float(value) for value in config["fit_windows"][0]["h_values"]]:
            value = profile["m"] * (losses[h] - 2.0 * after + losses[-h]) / (h * h)
            curvatures.append({"h": h, "curvature": value})
        fits = {
            window["id"]: _fit(profile, after, [float(value) for value in window["h_values"]], p3["fit_quality"])
            for window in config["fit_windows"]
        }
        row = {
            "schema_version": 1,
            "protocol_id": config["protocol_id"],
            "phase": config["phase"],
            "role": "development_only_center_definition_diagnostic",
            "namespace": config["namespace"],
            "benchmark": benchmark,
            "seed": int(seed),
            "status": "PASS" if diagnostics["local_minimum_gate"] == "PASS" else "PROFILE_FAILURE",
            "confirmation_authorized": False,
            "config_hash": config_hash(config),
            "source_hashes": {
                "source_profile_record": _sha256(source),
                "source_checkpoint_manifest": sha256_file(
                    root / "outputs/runs/v5/checkpoints/allen_cahn" / f"seed_{seed}/checkpoint_manifest.json"
                ),
                "source_model_state": manifest["model_state_hash"],
                **runtime_hashes,
            },
            "provenance": provenance,
            "gamma_alpha": float(config["gamma_alpha"]),
            "gamma": gamma,
            "center_before_loss_mean": before,
            "center_after_loss_mean": after,
            "center_loss_improvement": before - after,
            "center_optimization": optimization,
            "center_diagnostics": diagnostics,
            "profile_points_reused_read_only": True,
            "curvatures_with_refined_center": curvatures,
            "fit_windows": fits,
            "elapsed_seconds": time.perf_counter() - started,
        }
        write_json_atomic(destination / "result.json", row)
        rows.append(row)

    window_summary = []
    for window in config["fit_windows"]:
        values = [row["fit_windows"][window["id"]] for row in rows]
        window_summary.append(
            {
                "window_id": window["id"],
                "planned_seed_count": len(values),
                "fit_quality_pass_count": sum(value["fit_quality_gate"] == "PASS" for value in values),
                "median_normalized_rmse": statistics.median(
                    value["normalized_rmse"] for value in values if value["status"] == "PASS"
                ),
            }
        )
    summary = {
        "schema_version": 1,
        "protocol_id": config["protocol_id"],
        "phase": config["phase"],
        "namespace": config["namespace"],
        "config_hash": config_hash(config),
        "planned_denominator": len(config["development_seeds"]),
        "terminal_count": len(rows),
        "center_gate_pass_count": sum(row["status"] == "PASS" for row in rows),
        "fit_window_summaries": window_summary,
        "confirmation_authorized": False,
        "scientific_profile_claim_authorized": False,
        "source_records": [
            f"{config['output_root']}/seed_{row['seed']}/result.json" for row in rows
        ],
        "provenance": provenance,
    }
    write_json_atomic(output_root / "S2_CENTER_REFINEMENT_SUMMARY.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
