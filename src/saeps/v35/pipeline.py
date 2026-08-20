"""Cohort runner for v3.5 diagnostics and engineering."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v31.pipeline import V2_SCALAR_SHA256, _mean_residual_objective
from saeps.v33.pipeline import (
    _augmented_lsqr_reference,
    _direct_augmented_reference,
    _matrix_free_normal_solvers,
    _relative,
)
from saeps.v35.engineering import (
    center_with_registered_rescue,
    scaled_augmented_lsqr_candidates,
)
from saeps.v35.second_order import second_order_reduced_decomposition


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        average = 0.5 * (index + end - 1) + 1.0
        for location in range(index, end):
            result[order[location]] = average
        index = end
    return result


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3:
        return None
    left_rank, right_rank = _rank(left), _rank(right)
    left_center = statistics.mean(left_rank)
    right_center = statistics.mean(right_rank)
    numerator = sum(
        (x - left_center) * (y - right_center)
        for x, y in zip(left_rank, right_rank)
    )
    denominator = (
        sum((x - left_center) ** 2 for x in left_rank)
        * sum((y - right_center) ** 2 for y in right_rank)
    ) ** 0.5
    return numerator / denominator if denominator > 0.0 else None


def run_v35_cohort(
    role: str,
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    role_to_seeds = {
        "RETROSPECTIVE_DIAGNOSTIC": specification["retrospective_diagnostic_seeds"],
        "ENGINEERING_SELECTION": specification["engineering_seeds"],
        "HELDOUT_DEVELOPMENT": specification["heldout_development_seeds"],
    }
    if role not in role_to_seeds or specification["confirmation_authorized"] is not False:
        raise ValueError("invalid v3.5 cohort role")
    if role == "HELDOUT_DEVELOPMENT" and not (
        root / "configs/v3_5/locked_engineering_choice.json"
    ).exists():
        raise RuntimeError("held-out development is forbidden before engineering freeze")
    seeds = [int(value) for value in role_to_seeds[role]]
    locked_path = root / specification["source_scalar_config"]
    if hashlib.sha256(locked_path.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
        raise RuntimeError("v2 scalar lock changed")
    locked = load_config(locked_path)
    runtime = _runtime_config(locked)
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(specification)
    run_id = make_run_id(
        f"V3-5-{role.lower()}", seeds[0], digest, provenance["timestamp"]
    )
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for seed in seeds:
        truth = solve_truth(runtime, "Burgers")
        checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
        residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
            theta, parameter, "Burgers", points, truth, runtime
        )
        parameter = checkpoint.log_parameter.detach().clone()
        objective = _mean_residual_objective(
            residual_function, parameter, checkpoint.theta, 0.0, False
        )
        theta, center = center_with_registered_rescue(
            objective,
            checkpoint.theta,
            specification["local_minimum"],
            specification["enhanced_center"],
        )
        record: dict[str, Any] = {
            "seed": seed,
            "status": "NUMERICAL_FAILURE" if theta is None else "PASS",
            "center": center,
            "center_stationarity": None,
            "gamma": None,
            "second_order_decomposition": None,
            "solver_candidates": None,
        }
        if theta is not None:
            linearization = ResidualLinearization(residual_function, theta, parameter)
            residual = linearization.residual()
            jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
            g_theta = float(center["baseline"]["final"]["normalized_objective_gradient"])
            if center["selected_method"] != "baseline_v3_4_exact_trust":
                g_theta = float(center["enhanced"]["final"]["normalized_objective_gradient"])
            s_theta = _stationarity(jacobian_theta, residual)
            center_pass = (
                g_theta < float(specification["center"]["required_objective_gradient_tolerance"])
                and s_theta < float(specification["center"]["residual_stationarity_tolerance"])
            )
            record["center_stationarity"] = {
                "G_theta": g_theta,
                "S_theta": s_theta,
                "S_lambda": _stationarity(jacobian_parameter, residual),
                "status": "PASS" if center_pass else "NUMERICAL_FAILURE",
            }
            if center_pass:
                gamma = float(specification["gamma"]["alpha"]) * float(
                    torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
                )
                record["gamma"] = gamma
                decomposition = second_order_reduced_decomposition(
                    residual_function,
                    theta,
                    parameter,
                    gamma,
                    float(specification["decomposition"]["denominator_floor"]),
                )
                shapley_pass = decomposition["shapley_reproduction_relative_error"] <= float(
                    specification["decomposition"][
                        "shapley_reproduction_relative_tolerance"
                    ]
                )
                decomposition["status"] = "PASS" if shapley_pass else "NUMERICAL_FAILURE"
                record["second_order_decomposition"] = decomposition
                if role != "RETROSPECTIVE_DIAGNOSTIC":
                    solver_spec = specification["solvers"]
                    explicit = _direct_augmented_reference(
                        jacobian_theta,
                        jacobian_parameter,
                        residual,
                        gamma,
                        {
                            "explicit_relative_normal_residual": 1.0e-10,
                            "explicit_objective_identity_tolerance": 1.0e-10,
                        },
                    )
                    matrix_free = _matrix_free_normal_solvers(
                        linearization,
                        linearization.parameter_columns_matrix_free(),
                        residual,
                        gamma,
                        {
                            "normal_equation_tolerance": solver_spec["tolerance"],
                            "max_iterations": solver_spec["max_iterations"],
                            "acceptance_relative_residual": solver_spec[
                                "parameter_residual_acceptance"
                            ],
                        },
                    )
                    lsqr = _augmented_lsqr_reference(
                        linearization,
                        jacobian_parameter,
                        residual,
                        gamma,
                        {
                            "lsqr_relative_normal_residual": solver_spec["tolerance"],
                            "lsqr_curvature_relative_tolerance": solver_spec[
                                "curvature_relative_acceptance"
                            ],
                            "max_iterations": solver_spec["max_iterations"],
                        },
                        float(explicit["Fse"][0][0]),
                    )
                    scaled = scaled_augmented_lsqr_candidates(
                        linearization,
                        jacobian_parameter[:, 0],
                        gamma,
                        float(solver_spec["tolerance"]),
                        int(solver_spec["max_iterations"]),
                        int(solver_spec["refinement_passes"]),
                    )
                    reference = float(explicit["Fse"][0][0])
                    candidates = {
                        "standard_CG": {
                            "Fse": float(matrix_free["standard_cg"]["Fse"][0][0]),
                            "residual": float(
                                matrix_free["standard_cg"]["verified_relative_residuals"][0]
                            ),
                            "iterations": int(matrix_free["standard_cg"]["iterations"][0]),
                        },
                        "augmented_LSQR": {
                            "Fse": float(lsqr["Fse"][0][0]),
                            "residual": float(lsqr["relative_normal_residuals"][0]),
                            "iterations": int(lsqr["iterations"][0]),
                        },
                        "scaled_LSQR": {
                            "Fse": scaled["scaled_LSQR"]["Fse"],
                            "residual": scaled["scaled_LSQR"][
                                "verified_original_relative_normal_residual"
                            ],
                            "iterations": int(scaled["scaled_LSQR"]["iterations"]),
                        },
                        "scaled_LSQR_iterative_refinement": {
                            "Fse": scaled["scaled_LSQR_iterative_refinement"]["Fse"],
                            "residual": scaled["scaled_LSQR_iterative_refinement"][
                                "verified_original_relative_normal_residual"
                            ],
                            "iterations": int(
                                scaled["scaled_LSQR_iterative_refinement"][
                                    "total_iterations"
                                ]
                            ),
                        },
                    }
                    for candidate in candidates.values():
                        candidate["curvature_relative_error"] = _relative(
                            candidate["Fse"], reference
                        )
                        candidate["status"] = (
                            "PASS"
                            if candidate["residual"]
                            <= float(solver_spec["parameter_residual_acceptance"])
                            and candidate["curvature_relative_error"]
                            < float(solver_spec["curvature_relative_acceptance"])
                            else "SOLVER_FAILURE"
                        )
                    record["solver_candidates"] = {
                        "explicit_Fse": reference,
                        "candidates": candidates,
                        "scaled_detail": scaled,
                    }
        records.append(record)

    indicator_associations = None
    valid = [
        row for row in records if row["second_order_decomposition"] is not None
    ]
    if role == "RETROSPECTIVE_DIAGNOSTIC" and valid:
        target = [
            row["second_order_decomposition"]["GN_to_exact_relative_error"]
            for row in valid
        ]
        names = list(
            valid[0]["second_order_decomposition"][
                "block_ratios_and_indicators"
            ].keys()
        )
        indicator_associations = {
            name: {
                "values": [
                    row["second_order_decomposition"][
                        "block_ratios_and_indicators"
                    ][name]
                    for row in valid
                ],
                "spearman_with_GN_error": _spearman(
                    [
                        row["second_order_decomposition"][
                            "block_ratios_and_indicators"
                        ][name]
                        for row in valid
                    ],
                    target,
                ),
            }
            for name in names
        }
    result = {
        "schema_version": 1,
        "phase": specification["phase"],
        "role": role,
        "run_id": run_id,
        "seeds": seeds,
        "config_hash": digest,
        "provenance": provenance,
        "records": records,
        "indicator_associations": indicator_associations,
        "confirmation_authorized": False,
        "engineering_gate": "PASSED",
    }
    result_path = destination / "result.json"
    result_path.write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "records": [
            {
                "path": "result.json",
                "status": "PASS",
                "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

