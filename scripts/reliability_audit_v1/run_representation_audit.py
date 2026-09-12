#!/usr/bin/env python3
"""Run a small predeclared architecture/loss-weight robustness audit.

This development audit varies representation and residual weighting without
using parameter truth to select a decision.  It is deliberately small and is
not a confirmation cohort.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.reliability_audit_v1.heat_pinn import HeatPINNConfig, run_heat_pinn


def build(output: Path) -> dict:
    cases = []
    for width in (8, 16, 32):
        cases.append((f"width{width}", {"width": width, "depth": 2}))
    for weight_data in (5.0, 10.0, 20.0):
        cases.append((f"data_weight{weight_data:g}", {"width": 16, "depth": 2, "weight_data": weight_data}))
    rows = []
    for label, overrides in cases:
        case_dir = output / label
        config = HeatPINNConfig(benchmark="B3", data_seed=10, noise_seed=10010, optimizer_seed=100, epochs=100, **overrides, output_dir=str(case_dir))
        run = run_heat_pinn(config)
        values = [] if run.F_gamma is None else run.F_gamma.detach().cpu().numpy().tolist()
        rows.append({"case": label, "config_sha256": config.as_hash(), "fit_status": run.fit_status, "compute_status": run.compute_status, "gradient_norm": run.gradient_norm, "train_loss": run.train_loss, "F_gamma": values, "F_gamma_eigenvalues": [] if run.F_gamma is None else __import__('numpy').linalg.eigvalsh(run.F_gamma.detach().cpu().numpy()).tolist()})
    report = {"schema_version":1,"protocol_id":"reliability_audit_v1","audit":"representation_and_weight_robustness_development","benchmark":"B3","data_seed":10,"noise_seed":10010,"optimizer_seed":100,"cases":rows,"truth_used_for_evaluation_only":True,"interpretation":"Small development audit; no invariance or confirmation claim."}
    output.mkdir(parents=True, exist_ok=True)
    (output / "REPRESENTATION_AUDIT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args(); print(json.dumps(build(args.output),indent=2))


if __name__ == "__main__":
    main()
