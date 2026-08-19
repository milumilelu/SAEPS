"""P6 multi-parameter development and locked confirmation pipeline."""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

import torch
import yaml

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import MatrixFreeEliminator, compute_matrix_free_saeps, explicit_tikhonov_operator
from saeps.multi import multi_residual, train_multi_checkpoint
from saeps.p4_screening import _stationarity
from saeps.profile import ProfileFitError, fit_local_quadratic, profile_reoptimized
from saeps.provenance import environment_provenance, make_run_id
from saeps.solvers import conjugate_gradient


def _multi_gamma_sweep(
    linearization: ResidualLinearization,
    jt: torch.Tensor,
    jl: torch.Tensor,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
    raw = jl.T @ jl
    rows: list[dict[str, Any]] = []
    for alpha in config["gamma"]["alpha_grid"]:
        gamma = float(alpha) * lambda_max
        explicit_operator = explicit_tikhonov_operator(jt, gamma)
        explicit_curvature = jl.T @ explicit_operator @ jl
        eliminator = MatrixFreeEliminator(
            linearization, gamma, float(config["gamma"]["cg_tolerance"]), int(config["gamma"]["cg_max_iterations"])
        )
        columns: list[torch.Tensor] = []
        solves = []
        for index in range(jl.shape[1]):
            vector = jl[:, index]
            rhs = linearization.vjp_theta(vector)
            solve = conjugate_gradient(
                eliminator.normal_operator, rhs, float(config["gamma"]["cg_tolerance"]), int(config["gamma"]["cg_max_iterations"])
            )
            columns.append(vector - linearization.jvp_theta(solve.solution)); solves.append(solve)
        mf_curvature = jl.T @ torch.stack(columns, dim=1)
        comparison = float(
            (torch.linalg.matrix_norm(mf_curvature-explicit_curvature)/(torch.linalg.matrix_norm(explicit_curvature)+torch.finfo(jt.dtype).eps)).item()
        )
        rows.append({
            "gamma_alpha": float(alpha), "gamma": gamma,
            "explicit_trace_eta": float(torch.trace(explicit_curvature).item()/torch.trace(raw).item()),
            "cg_converged": all(solve.converged for solve in solves),
            "cg_iterations": [solve.iterations for solve in solves],
            "cg_relative_residual": [solve.relative_residual for solve in solves],
            "explicit_mf_relative_error": comparison,
        })
    return rows


def _select_multi_gamma(sweeps: list[list[dict[str, Any]]], config: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    grid = [float(value) for value in config["gamma"]["alpha_grid"]]
    eligible, medians = [], []
    for index in range(len(grid)):
        rows = [sweep[index] for sweep in sweeps]
        eligible.append(all(
            row["cg_converged"]
            and max(row["cg_relative_residual"]) <= float(config["gamma"]["cg_acceptance"])
            and row["explicit_mf_relative_error"] < float(config["gamma"]["explicit_mf_relative_tolerance"])
            for row in rows
        ))
        medians.append(statistics.median(row["explicit_trace_eta"] for row in rows))
    changes = [abs(medians[i+1]-medians[i])/max(abs(medians[i]),1e-30) for i in range(len(grid)-1)]
    candidates = [i for i in range(1,len(grid)) if eligible[i] and changes[i-1] <= float(config["gamma"]["plateau_relative_tolerance"])]
    if not candidates:
        raise RuntimeError(f"no eligible multi gamma: eligible={eligible}, changes={changes}")
    selected = candidates[0]
    return grid[selected], {"eligible":eligible,"median_explicit_trace_eta":medians,"adjacent_relative_changes":changes,"selected_index":selected}


def run_multi_development(config_path: str|Path, output_root: str|Path, repo_root: str|Path) -> dict[str,Any]:
    started=time.perf_counter(); config=load_config(config_path)
    if config["development_seeds"] != [0,1,2]: raise ValueError("multi development seeds must be 0,1,2")
    rows=[]; sweeps=[]
    for seed in config["development_seeds"]:
        checkpoint,points=train_multi_checkpoint(config,int(seed))
        lin=ResidualLinearization(lambda th,q:multi_residual(th,q,points,config),checkpoint.theta,checkpoint.coordinate)
        residual=lin.residual(); jt,jl=lin.explicit_jacobians()
        sweep=_multi_gamma_sweep(lin,jt,jl,config); sweeps.append(sweep)
        st,sp=_stationarity(jt,residual),_stationarity(jl,residual)
        rows.append({"seed":seed,"training_loss":checkpoint.training_loss,"state_rmse_validation_only":checkpoint.state_rmse,"parameter_relative_errors_validation_only":checkpoint.parameter_relative_errors,"theta_stationarity":st,"parameter_stationarity":sp,"stationarity_pass":st<=float(config["stationarity_gates"]["theta"]) and sp<=float(config["stationarity_gates"]["parameter"]),"gamma_sweep":sweep})
    nominal,evidence=_select_multi_gamma(sweeps,config)
    provenance=environment_provenance(repo_root,config["dtype"],config["device"]); digest=config_hash(config)
    run_id=make_run_id("P6-development",0,digest,provenance["timestamp"])
    status="PASS" if sum(row["stationarity_pass"] for row in rows)>=1 and all(row["state_rmse_validation_only"]<=float(config["state_rmse_max_validation_only"]) for row in rows) else "DEVELOPMENT_FAILURE"
    result={"schema_version":1,"phase":"P6_DEVELOPMENT","run_id":run_id,"status":status,"config_hash":digest,"rows":rows,"nominal_gamma_alpha":nominal,"gamma_selection":evidence,"provenance":provenance,"elapsed_seconds":time.perf_counter()-started}
    destination=Path(output_root)/run_id; destination.mkdir(parents=True,exist_ok=False)
    (destination/"development.json").write_text(json.dumps(result,allow_nan=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    if status=="PASS":
        locked={**config,"phase":"P6_MULTI_CONFIRMATION","nominal_gamma_alpha":nominal,"development_run_id":run_id,"development_config_hash":digest}
        locked_path=Path(repo_root)/"configs"/"locked"/"multi.yaml"
        locked_path.write_text(yaml.safe_dump(locked,sort_keys=False,allow_unicode=True),encoding="utf-8",newline="\n")
        digest_file=hashlib.sha256(locked_path.read_bytes()).hexdigest()
        locked_path.with_suffix(".sha256").write_text(f"{digest_file}  multi.yaml\n",encoding="utf-8",newline="\n")
        result["locked_config_sha256"]=digest_file
    return result

