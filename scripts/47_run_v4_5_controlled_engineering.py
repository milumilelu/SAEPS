from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v45.pipeline import run_v45_engineering_seed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    result = run_v45_engineering_seed(Path(__file__).resolve().parents[1], args.seed)
    print(json.dumps({"seed": result["seed"], "status": result["status"]}, indent=2))
