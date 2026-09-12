#!/usr/bin/env python3
"""Build the independent finite-difference heat reference refinement report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.reliability_audit_v1.physical_solver import heat_fd_temperature, refinement_difference
from saeps.identifiability.profile_reference import heat_temperature_np


def build(output: Path, *, noise_scale: float = 0.01) -> dict:
    x = np.repeat(np.asarray([0.2, 0.4, 0.7]), 4)
    t = np.tile(np.asarray([0.02, 0.08, 0.2, 0.4]), 3)
    truth = heat_temperature_np(x, t, 0.6, 1.2, 1.0)
    rows = []
    for n in (32, 64, 128):
        numerical = heat_fd_temperature(x, t, k=0.6, C=1.2, amplitude=1.0, interior_count=n).values
        rows.append({"interior_count": n, "spacing": 1.0/(n+1), "max_abs_error_to_closed_form": float(np.max(np.abs(numerical-truth))), "max_abs_value": float(np.max(np.abs(numerical)))})
    discrepancy = refinement_difference(x, t, k=0.6, C=1.2, coarse_count=64, fine_count=128)
    report = {"schema_version":1,"protocol_id":"reliability_audit_v1","reference_kind":"independent_finite_difference_heat_solver","coordinates":{"x":x.tolist(),"t":t.tolist()},"truth_used_only_for_convergence_check":{"k":0.6,"C":1.2,"a":1.0},"declared_noise_scale":float(noise_scale),"refinement_rows":rows,"final_two_level_difference":discrepancy,"refinement_gate_pass":bool(discrepancy < noise_scale),"solver":"symmetric finite-difference Dirichlet Laplacian with eigen decomposition","no_pinn_objective_used":True}
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
