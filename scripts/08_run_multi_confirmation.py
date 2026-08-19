"""Run locked P6 multi-parameter confirmation."""
from __future__ import annotations
import json
from pathlib import Path
from saeps.p6_pipeline import run_multi_confirmation
if __name__=="__main__":
    root=Path(__file__).resolve().parents[1];result=run_multi_confirmation(root/"configs/locked/multi.yaml",root/"outputs/runs/p6_multi",root);print(json.dumps({key:result[key] for key in ["run_id","engineering_gate","scientific_gate_sg3","valid","ordering_consistent_out_of_planned_10","grid_seed"]},indent=2,sort_keys=True));raise SystemExit(0 if result["engineering_gate"]=="PASSED" else 1)
