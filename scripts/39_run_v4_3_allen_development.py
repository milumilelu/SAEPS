from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v43.pipeline import run_allen_development_seed


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    arguments = parser.parse_args()
    result = run_allen_development_seed(
        arguments.seed,
        ROOT / "configs/v4_3/allen_cahn_development.yaml",
        ROOT / "outputs/runs/v4_3_allen_cahn_development",
        ROOT,
    )
    print(json.dumps({"seed": arguments.seed, "status": result["status"], "statuses": result["statuses"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

