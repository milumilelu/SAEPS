#!/usr/bin/env python3
"""Evaluate the declared B3->B6 observation intervention independently.

This is a physical-model development reference, not a PINN confirmation.  It
uses the fixed analytic profile engine and independent observation Jacobian to
quantify how calibrated flux measurements change the (k,C) information and
profile width over repeated data realisations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.identifiability.profile_reference import (
    DEFAULT_C, DEFAULT_K, DEFAULT_AMPLITUDE, default_observation_design,
    generate_analytic_observations, heat_temperature_np, heat_flux_np,
    profile_heat_observation,
)
from saeps.identifiability import heat_temperature_sensitivities, heat_flux_sensitivities
import torch


def _fim_eigenvalues(benchmark: str, sigma: float = 0.01) -> np.ndarray:
    x, t, xf, tf = default_observation_design(benchmark)
    dtype = torch.float64
    xt, tt = torch.as_tensor(x, dtype=dtype), torch.as_tensor(t, dtype=dtype)
    jt = heat_temperature_sensitivities(xt, tt, DEFAULT_K, DEFAULT_C, DEFAULT_AMPLITUDE)[:, :2].numpy()
    if benchmark == "B3":
        jac = jt / sigma
    else:
        assert xf is not None and tf is not None
        xf_t, tf_t = torch.as_tensor(xf, dtype=dtype), torch.as_tensor(tf, dtype=dtype)
        jf = heat_flux_sensitivities(xf_t, tf_t, DEFAULT_K, DEFAULT_C, DEFAULT_AMPLITUDE).numpy() / sigma
        jac = np.concatenate((jt / sigma, jf), axis=0)
    return np.linalg.eigvalsh(jac.T @ jac)


def build(output: Path, *, seeds: list[int] | None = None, noise_rho: float = 0.01) -> dict:
    seeds = list(range(10, 30)) if seeds is None else [int(s) for s in seeds]
    rows = []
    for seed in seeds:
        b3 = profile_heat_observation(generate_analytic_observations("B3", data_seed=seed, noise_rho=noise_rho))
        b6 = profile_heat_observation(generate_analytic_observations("B6", data_seed=seed, noise_rho=noise_rho))
        rows.append({"data_seed": seed, "B3": {"status": b3["profile_status"], "flat": b3["flat_profile"], "span": b3["objective_span_half_chi2"]}, "B6": {"status": b6["profile_status"], "flat": b6["flat_profile"], "span": b6["objective_span_half_chi2"], "k_error": abs(np.log(b6["minimum_scan_value"] / DEFAULT_K))}})
    eig_b3, eig_b6 = _fim_eigenvalues("B3", noise_rho), _fim_eigenvalues("B6", noise_rho)
    report = {"schema_version":1,"protocol_id":"reliability_audit_v1","reference_kind":"analytic_observation_intervention","intervention":"B3 temperature-only -> B6 temperature-plus-calibrated-flux","truth_used_only_for_data_generation_and_reference":"k=0.6,C=1.2,a=1.0","noise_rho":float(noise_rho),"data_seeds":seeds,"FIM_eigenvalues":{"B3":eig_b3.tolist(),"B6":eig_b6.tolist()},"smallest_eigenvalue_B3":float(eig_b3.min()),"smallest_eigenvalue_B6":float(eig_b6.min()),"smallest_eigenvalue_gain":float(eig_b6.min()-eig_b3.min()),"rows":rows,"profile_contraction_observed":bool(all((r["B6"]["span"] > r["B3"]["span"] and r["B6"]["flat"] is False) for r in rows)),"pin_retraining_performed":False,"interpretation":"Physical-reference intervention only; no PINN reliability or causal claim."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.output),indent=2))


if __name__ == "__main__":
    main()
