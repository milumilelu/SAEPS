"""P6 multi-parameter development and locked confirmation pipeline."""

from __future__ import annotations

import hashlib
import csv
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
from saeps.profile import ProfileFitError, _reoptimize_point, fit_local_quadratic, profile_reoptimized
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


def _direction_profile(checkpoint: Any, points: Any, direction: torch.Tensor, config: dict[str, Any]) -> dict[str, Any]:
    offsets=[float(value) for value in config["profile"]["offsets"]]
    def objective(theta:torch.Tensor,coordinate:torch.Tensor)->torch.Tensor:
        residual=multi_residual(theta,coordinate,points,config); return .5*torch.mean(residual.square())
    values=profile_reoptimized(objective,checkpoint.theta,checkpoint.coordinate,direction,offsets,config["profile"]["optimizer"],config["profile"]["stopping"])
    result={"offsets":offsets,"losses":[point.loss for point in values],"statuses":[point.status for point in values]}
    try:
        fit=fit_local_quadratic(values,config["profile"]["fit_quality"],offsets)
        result.update({"fit_status":"PASS","curvature":fit.curvature,"minimum":fit.minimum,"r_squared":fit.r_squared,"normalized_rmse":fit.normalized_rmse})
    except ProfileFitError as error:
        result.update({"fit_status":"PROFILE_FAILURE","failure_reason":str(error)})
    return result


def _write_multi_svg(path:Path,records:list[dict[str,Any]])->None:
    valid=[record for record in records if record["status"]=="PASS"]
    lines=['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="440">','<rect width="100%" height="100%" fill="white"/>','<text x="360" y="28" text-anchor="middle" font-size="18" font-weight="bold">Multi-parameter directional curvature</text>','<line x1="70" y1="380" x2="690" y2="380" stroke="black"/>','<line x1="70" y1="45" x2="70" y2="380" stroke="black"/>']
    maximum=max([max(record["profile_curvature_min"],record["profile_curvature_max"]) for record in valid],default=1.)
    for index,record in enumerate(valid):
        x=100+index*(560/max(len(valid),1)); low=300*record["profile_curvature_min"]/max(maximum,1e-30); high=300*record["profile_curvature_max"]/max(maximum,1e-30)
        lines.append(f'<rect x="{x:.1f}" y="{380-low:.1f}" width="16" height="{low:.1f}" fill="#009E73"/>');lines.append(f'<rect x="{x+18:.1f}" y="{380-high:.1f}" width="16" height="{high:.1f}" fill="#CC79A7"/>');lines.append(f'<text x="{x+17:.1f}" y="400" text-anchor="middle" font-size="12">{record["seed"]}</text>')
    lines.extend(['<text x="350" y="425" text-anchor="middle" font-size="14">confirmation seed</text>','</svg>'])
    path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")


def run_multi_confirmation(config_path:str|Path,output_root:str|Path,repo_root:str|Path)->dict[str,Any]:
    started=time.perf_counter();config=load_config(config_path);seeds=list(config["confirmation_seeds"])
    if config.get("phase")!="P6_MULTI_CONFIRMATION" or seeds!=list(range(10,20)):raise ValueError("invalid locked P6 config")
    provenance=environment_provenance(repo_root,config["dtype"],config["device"]);digest=config_hash(config);aggregate_id=make_run_id("P6-multi",10,digest,provenance["timestamp"])
    destination=Path(output_root)/aggregate_id;records_dir=destination/"records";records_dir.mkdir(parents=True,exist_ok=False)
    records=[];manifest=[];grid_source=None
    for seed in seeds:
        checkpoint,points=train_multi_checkpoint(config,seed)
        lin=ResidualLinearization(lambda th,q:multi_residual(th,q,points,config),checkpoint.theta,checkpoint.coordinate);residual=lin.residual();jt,jl=lin.explicit_jacobians();st,sp=_stationarity(jt,residual),_stationarity(jl,residual)
        valid_checkpoint=st<=float(config["stationarity_gates"]["theta"]) and sp<=float(config["stationarity_gates"]["parameter"]) and checkpoint.state_rmse<=float(config["state_rmse_max_validation_only"])
        record={"schema_version":1,"run_id":f"{aggregate_id}-seed{seed}","timestamp":provenance["timestamp"],"git_commit":provenance["git_commit"],"config_path":"configs/locked/multi.yaml","config_hash":digest,"seed":seed,"split":"confirmation","benchmark":config["benchmark"]["name"],"architecture":config["network"]["architecture"],"dtype":config["dtype"],"hardware":provenance["processor"] or provenance["machine"],"parameter_coordinates":config["benchmark"]["coordinates"],"training_points":config["points"],"diagnostic_points":config["points"],"sensor_layout":"fixed_seeded_uniform_per_run","loss_weights":config["loss_weights"],"optimizer":config["optimizer"],"learning_rate":config["optimizer"]["adam_learning_rate"],"training_stop_reason":checkpoint.stop_reason,"checkpoint_epoch":checkpoint.adam_epochs,"theta_stationarity":st,"lambda_stationarity":sp,"residuals":{"total_weighted_rms":float(torch.sqrt(torch.mean(residual.square())).item())},"state_error":{"value":checkpoint.state_rmse,"validation_only":True},"parameter_error":{"value":checkpoint.parameter_relative_errors,"validation_only":True},"gamma_alpha":float(config["nominal_gamma_alpha"]),"training_time":checkpoint.elapsed_seconds,"peak_memory":None}
        if not valid_checkpoint:
            record.update({"status":"CHECKPOINT_INVALID","failure_reason":"locked multi checkpoint gate failed","Fraw":None,"Fse":None,"gse":None,"eta":None,"profile_points":config["profile"]["offsets"],"profile_curvature":None,"profile_fit_quality":None})
        else:
            try:
                lambda_max=float(torch.linalg.eigvalsh(jt.T@jt).max().item());gamma=float(config["nominal_gamma_alpha"])*lambda_max;saeps=compute_matrix_free_saeps(lin,gamma,float(config["gamma"]["cg_tolerance"]),int(config["gamma"]["cg_max_iterations"]));symmetric=.5*(saeps.eliminated_curvature+saeps.eliminated_curvature.T);eigenvalues,eigenvectors=torch.linalg.eigh(symmetric);vmin=eigenvectors[:,0];vmax=eigenvectors[:,-1]
                low=_direction_profile(checkpoint,points,vmin,config);high=_direction_profile(checkpoint,points,vmax,config);profile_ok=low.get("fit_status")=="PASS" and high.get("fit_status")=="PASS"
                count=residual.numel();hmin=float(low["curvature"])*count if profile_ok else None;hmax=float(high["curvature"])*count if profile_ok else None
                if profile_ok:
                    predicted_ratio=float(eigenvalues[-1].item()/max(eigenvalues[0].item(),1e-30));profile_ratio=hmax/max(hmin,1e-30);ratio_error=abs(predicted_ratio-profile_ratio)/max(abs(profile_ratio),1e-30);status="PASS";failure=None
                else: predicted_ratio=profile_ratio=ratio_error=None;status="PROFILE_FAILURE";failure="locked eigendirection profile fit failed"
                record.update({"status":status,"failure_reason":failure,"gamma":gamma,"CG_iterations":[solve.iterations for solve in saeps.solves],"CG_relative_residual":[solve.relative_residual for solve in saeps.solves],"JVP_count":saeps.operation_counts.get("jvp_theta",0)+saeps.operation_counts.get("jvp_parameter",0),"VJP_count":saeps.operation_counts.get("vjp_theta",0),"Fraw":saeps.raw_curvature.tolist(),"Fse":saeps.eliminated_curvature.tolist(),"gse":saeps.eliminated_score.tolist(),"eta":saeps.eta.tolist(),"eigenvalues":eigenvalues.tolist(),"eigenvectors":eigenvectors.tolist(),"condition_number":float(eigenvalues[-1].item()/max(eigenvalues[0].item(),1e-30)),"trace":float(torch.trace(symmetric).item()),"determinant":float(torch.linalg.det(symmetric).item()),"coupling":float(symmetric[0,1].item()/torch.sqrt(symmetric[0,0]*symmetric[1,1]).item()),"profile_points":config["profile"]["offsets"],"profile_min_direction":low,"profile_max_direction":high,"profile_curvature_min":hmin,"profile_curvature_max":hmax,"profile_fit_quality":{"min_r_squared":low.get("r_squared"),"max_r_squared":high.get("r_squared")} if profile_ok else None,"directional_predicted_ratio":predicted_ratio,"directional_profile_ratio":profile_ratio,"directional_curvature_ratio_error":ratio_error})
                if status=="PASS" and grid_source is None:grid_source=(seed,checkpoint,points)
            except Exception as error:
                record.update({"status":"SOLVER_FAILURE","failure_reason":f"{type(error).__name__}: {error}","Fraw":None,"Fse":None,"gse":None,"eta":None,"profile_points":config["profile"]["offsets"],"profile_curvature":None,"profile_fit_quality":None})
        path=records_dir/f"seed_{seed}.json";path.write_text(json.dumps(record,allow_nan=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n");manifest.append({"seed":seed,"status":record["status"],"path":str(path.relative_to(destination)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()});records.append(record)
    grid_result=None
    if grid_source is not None:
        seed,checkpoint,points=grid_source;half=float(config["grid"]["half_width"]);size=int(config["grid"]["size"]);axis=torch.linspace(-half,half,size,dtype=checkpoint.theta.dtype);values=[]
        def objective(th:torch.Tensor,q:torch.Tensor)->torch.Tensor:
            r=multi_residual(th,q,points,config);return .5*torch.mean(r.square())
        for first in axis:
            for second in axis:
                coordinate=checkpoint.coordinate+torch.stack([first,second]);point=_reoptimize_point(objective,checkpoint.theta,coordinate,float(first.item()*1000+second.item()),config["profile"]["optimizer"],config["profile"]["stopping"]);values.append({"delta":[float(first.item()),float(second.item())],"loss":point.loss,"status":point.status})
        grid_result={"seed":seed,"selection_rule":config["grid"]["seed_rule"],"axis":axis.tolist(),"values":values};(destination/"grid_5x5.json").write_text(json.dumps(grid_result,allow_nan=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    valid=[r for r in records if r["status"]=="PASS"];ordering=sum(r["profile_curvature_max"]>r["profile_curvature_min"] for r in valid);scientific="PASS" if len(valid)==10 and ordering>=int(config["scientific_gate"]["ordering_required_out_of_planned_10"]) else "FAIL"
    summary={"schema_version":1,"phase":"P6","run_id":aggregate_id,"engineering_gate":"PASSED" if len(records)==10 and (grid_source is None or grid_result is not None) else "FAILED","scientific_gate_sg3":scientific,"planned":10,"valid":len(valid),"ordering_consistent_out_of_planned_10":ordering,"status_counts":{status:sum(r["status"]==status for r in records) for status in ["PASS","CHECKPOINT_INVALID","PROFILE_FAILURE","SOLVER_FAILURE"]},"grid_seed":grid_result["seed"] if grid_result else None,"per_seed":[{"seed":r["seed"],"status":r["status"],"eigenvalues":r.get("eigenvalues"),"profile_curvature_min":r.get("profile_curvature_min"),"profile_curvature_max":r.get("profile_curvature_max"),"directional_curvature_ratio_error":r.get("directional_curvature_ratio_error")} for r in records],"config_hash":digest,"provenance":provenance,"elapsed_seconds":time.perf_counter()-started}
    (destination/"manifest.json").write_text(json.dumps({"schema_version":1,"planned":10,"records":manifest},indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n");(destination/"summary.json").write_text(json.dumps(summary,allow_nan=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    with (destination/"table3_multi.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["seed","status","eigenvalues","profile_curvature_min","profile_curvature_max","directional_curvature_ratio_error"]);writer.writeheader();writer.writerows(summary["per_seed"])
    _write_multi_svg(destination/"figure5_multi_directional.svg",records);return summary
