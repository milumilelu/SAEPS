#!/usr/bin/env python3
"""Analyze saved RI-2 checkpoints on the frozen gamma path.

The input pilot directories are immutable.  Jacobians are reconstructed from
checkpoints when the raw Jacobian arrays were not retained by the pilot runner;
all derived arrays are written under the analysis output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# Keep script runnable from a source checkout without an editable install.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.reliability_audit_v1.heat_pinn import (  # noqa: E402
    HeatPINNConfig,
    _StateNet,
    _jacobians,
    generate_heat_observations,
    weighted_residual,
)
from saeps.reliability_audit_v1.reliability import (  # noqa: E402
    GAMMA_ALPHA_GRID,
    DEFAULT_INFORMATION_FLOOR,
    DEFAULT_RANK_TOLERANCE,
    classify_record,
    classify_saeps_only,
    gamma_path_from_jacobians,
    selective_metrics,
)
import torch  # noqa: E402
from torch import nn  # noqa: E402


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jacobians_from_checkpoint(model: _StateNet, config: HeatPINNConfig, observation: Any, logs: dict[str, nn.Parameter], manifest: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Recompute Jacobians while preserving the manifest's pilot coordinate map.

    Early RI-2 B4 manifests treated ``a`` as a physical column; later adapter
    revisions classify it as a nuisance coordinate.  The saved F_raw shape and
    manifest unknown list are authoritative for this retrospective analysis.
    """
    manifest_unknown = tuple(str(name) for name in (manifest.get("unknown_parameters") or ()))
    if manifest_unknown == tuple(config.unknown_parameters):
        return _jacobians(model, config, observation, logs)
    residual = weighted_residual(model, config, observation, logs, create_graph=True)
    state_parameters = tuple(model.parameters())
    physical_parameters = tuple(logs[name] for name in manifest_unknown)
    state_rows: list[torch.Tensor] = []
    physical_rows: list[torch.Tensor] = []
    for value in residual:
        grads = torch.autograd.grad(value, state_parameters + physical_parameters, retain_graph=True, allow_unused=True)
        state_rows.append(torch.cat([g.reshape(-1) if g is not None else torch.zeros(p.numel(), dtype=residual.dtype) for g, p in zip(grads[:len(state_parameters)], state_parameters)]))
        physical_rows.append(torch.cat([g.reshape(-1) if g is not None else torch.zeros(1, dtype=residual.dtype) for g in grads[len(state_parameters):]]))
    return residual.detach(), torch.stack(state_rows).detach(), torch.stack(physical_rows).detach()


def _load_jacobians(manifest: dict[str, Any], run_dir: Path, cache_dir: Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    """Load retained arrays or derive them once from the immutable checkpoint."""
    candidates = [run_dir / "J_state.npy", run_dir / "jacobian_state.npy"]
    candidate_p = [run_dir / "J_parameter.npy", run_dir / "jacobian_parameter.npy"]
    for state_path, param_path in zip(candidates, candidate_p):
        if state_path.is_file() and param_path.is_file():
            return np.load(state_path), np.load(param_path), {"J_state": str(state_path), "J_parameter": str(param_path)}
    checkpoint_value = manifest.get("checkpoint_path")
    checkpoint = Path(str(checkpoint_value)) if checkpoint_value else run_dir / "checkpoint.pt"
    if not checkpoint.is_absolute():
        checkpoint = ROOT / checkpoint
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint unavailable: {checkpoint}")
    payload = torch.load(checkpoint, map_location="cpu")
    cfg_payload = dict(payload.get("config", {}))
    cfg_payload["output_dir"] = None
    config = HeatPINNConfig(**cfg_payload)
    model = _StateNet(config.width, config.depth).to(dtype=config.torch_dtype)
    model.load_state_dict(payload["model"])
    model.eval()
    logs_payload = payload.get("log_parameters", {})
    logs = {name: nn.Parameter(torch.as_tensor(logs_payload[name], dtype=config.torch_dtype)) for name in config.trainable_parameters}
    observation = generate_heat_observations(config)
    _, jw, jp = _jacobians_from_checkpoint(model, config, observation, logs, manifest)
    state = jw.detach().cpu().numpy()
    parameter = jp.detach().cpu().numpy()
    out_dir = cache_dir / str(manifest["run_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path, param_path = out_dir / "J_state.npy", out_dir / "J_parameter.npy"
    np.save(state_path, state)
    np.save(param_path, parameter)
    return state, parameter, {"J_state": str(state_path), "J_parameter": str(param_path), "checkpoint": str(checkpoint), "checkpoint_sha256": _hash_file(checkpoint)}


def _manifest_records(runs_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    records = []
    for path in sorted(runs_dir.glob("B*/manifest.json")) + sorted(runs_dir.glob("B*/*/manifest.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not value.get("run_id"):
            continue
        records.append((path.parent, value))
    return records


def analyze(runs_dir: Path, output_dir: Path, *, decision_mode: str = "SAEPS_ONLY") -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "derived_jacobians"
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for run_dir, manifest in _manifest_records(runs_dir):
        row = dict(manifest)
        run_id = str(manifest["run_id"])
        try:
            jw, jp, paths = _load_jacobians(manifest, run_dir, cache_dir)
            path_result = gamma_path_from_jacobians(jw, jp, gamma_alpha_grid=GAMMA_ALPHA_GRID, relative_tolerance=DEFAULT_RANK_TOLERANCE)
            row["gamma_path_artifact"] = path_result
            row["derived_jacobian_paths"] = paths
            if decision_mode == "SAEPS_ONLY":
                decision = classify_saeps_only(path_result, n_unknown=len(manifest.get("unknown_parameters") or []))
            elif decision_mode == "LEGACY_ORACLE_ASSISTED":
                iobs_path = run_dir / "I_obs.npy"
                if not iobs_path.is_file():
                    raise FileNotFoundError(f"I_obs unavailable: {iobs_path}")
                decision_input = dict(row)
                decision_input["_I_obs_matrix"] = np.load(iobs_path)
                decision = classify_record(decision_input, path_result, relative_tolerance=DEFAULT_RANK_TOLERANCE, information_floor=DEFAULT_INFORMATION_FLOOR)
            else:
                raise ValueError(f"unknown decision_mode: {decision_mode}")
            row["decision_record"] = decision
        except Exception as exc:  # preserve every planned record as unresolved
            row["gamma_path_artifact"] = None
            row["derived_jacobian_paths"] = None
            row["decision_record"] = {"decision": "UNRESOLVED_NUMERICAL", "accepted": False, "reason": type(exc).__name__, "confidence_score": 0.0}
            failures.append({"run_id": run_id, "reason": f"{type(exc).__name__}: {exc}"})
        rows.append(row)
    metrics = selective_metrics(rows)
    benchmarks: dict[str, dict[str, int]] = {}
    for row in rows:
        benchmark = str(row.get("benchmark", "UNKNOWN"))
        decision = str((row.get("decision_record") or {}).get("decision", "UNRESOLVED_NUMERICAL"))
        benchmarks.setdefault(benchmark, {})[decision] = benchmarks.setdefault(benchmark, {}).get(decision, 0) + 1
    result = {
        "schema_version": 1,
        "protocol_id": "reliability_audit_v1",
        "analysis": "RI-2 fixed gamma path and abstaining decision layer",
        "source_runs_dir": str(runs_dir),
        "gamma_alpha_grid": list(GAMMA_ALPHA_GRID),
        "gamma_scale_definition": "gamma_alpha * lambda_max(J_state.T @ J_state)",
        "rank_tolerance": DEFAULT_RANK_TOLERANCE,
        "information_floor": DEFAULT_INFORMATION_FLOOR,
        "decision_mode": decision_mode,
        "decision_uses_truth": decision_mode != "SAEPS_ONLY",
        "truth_used_only_for_evaluation": True,
        "planned_denominator": len(rows),
        "records": rows,
        "decision_counts_by_benchmark": benchmarks,
        "selective_metrics": metrics,
        "failures": failures,
    }
    # Avoid serialising transient/private arrays; all matrices are in the path
    # artifact and source paths are retained for reproducibility.
    output_path = output_dir / "RI2_RELIABILITY_ANALYSIS.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--decision-mode", choices=("SAEPS_ONLY", "LEGACY_ORACLE_ASSISTED"), default="SAEPS_ONLY")
    args = parser.parse_args()
    result = analyze(args.runs_dir, args.output_dir, decision_mode=args.decision_mode)
    print(json.dumps({"planned_denominator": result["planned_denominator"], "failures": len(result["failures"]), "decision_counts_by_benchmark": result["decision_counts_by_benchmark"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
