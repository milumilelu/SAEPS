#!/usr/bin/env python3
"""Small physical-reference bootstrap audit (no PINN interval claim)."""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.identifiability.profile_reference import DEFAULT_K, generate_analytic_observations, profile_heat_observation


def build(output: Path, *, replicates: int = 30, data_seed: int = 10, noise_rho: float = 0.01) -> dict:
    if replicates < 10:
        raise ValueError("replicates must be at least 10")
    rows = []
    for benchmark in ("B1", "B2", "B6"):
        base = generate_analytic_observations(benchmark, data_seed=data_seed, noise_rho=noise_rho)
        estimates = []
        rng = np.random.default_rng(900000 + data_seed)
        for replicate in range(replicates):
            idx_t = rng.integers(0, base.y_temperature.size, size=base.y_temperature.size)
            kwargs = {"x_temperature": base.x_temperature[idx_t], "t_temperature": base.t_temperature[idx_t], "y_temperature": base.y_temperature[idx_t], "sigma_temperature": base.sigma_temperature[idx_t], "data_seed": data_seed, "noise_rho": noise_rho, "truth": base.truth}
            if benchmark == "B6":
                assert base.x_flux is not None and base.t_flux is not None and base.y_flux is not None and base.sigma_flux is not None
                idx_f = rng.integers(0, base.y_flux.size, size=base.y_flux.size)
                kwargs.update({"x_flux": base.x_flux[idx_f], "t_flux": base.t_flux[idx_f], "y_flux": base.y_flux[idx_f], "sigma_flux": base.sigma_flux[idx_f]})
            prof = profile_heat_observation(type(base)(benchmark=benchmark, **kwargs))
            estimates.append(float(prof["minimum_scan_value"]))
        arr = np.asarray(estimates)
        rows.append({"benchmark": benchmark, "replicates": replicates, "estimate_median": float(np.median(arr)), "estimate_mean": float(np.mean(arr)), "estimate_std": float(np.std(arr, ddof=1)), "quantiles_05_95": [float(np.quantile(arr, 0.05)), float(np.quantile(arr, 0.95))], "truth_in_interval": bool(float(np.quantile(arr, 0.05)) <= DEFAULT_K <= float(np.quantile(arr, 0.95))), "interval_kind":"bootstrap percentile over analytic profile scan minima"})
    report={"schema_version":1,"protocol_id":"reliability_audit_v1","reference_kind":"analytic_physical_bootstrap","data_seed":data_seed,"noise_rho":noise_rho,"rows":rows,"truth_used_only_for_posthoc_coverage":True,"pin_retraining_performed":False,"interpretation":"Development reference only; no PINN uncertainty calibration or confidence claim."}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--replicates',type=int,default=30); args=parser.parse_args(); print(json.dumps(build(args.output,replicates=args.replicates),indent=2))

if __name__ == '__main__': main()
