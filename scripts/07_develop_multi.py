"""Run P6 development before the global confirmation lock."""
from __future__ import annotations
import json
from pathlib import Path
from saeps.p6_pipeline import run_multi_development

if __name__ == "__main__":
    root=Path(__file__).resolve().parents[1]
    result=run_multi_development(root/"configs/p6_development.yaml",root/"outputs/runs/p6_development",root)
    print(json.dumps({"run_id":result["run_id"],"status":result["status"],"nominal_gamma_alpha":result["nominal_gamma_alpha"],"locked_config_sha256":result.get("locked_config_sha256")},indent=2,sort_keys=True))
    raise SystemExit(0 if result["status"]=="PASS" else 1)

