from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v49.pipeline import run_robustness_seed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True, choices=["noise_sparsity", "architecture"])
    parser.add_argument("--seed", required=True, type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(run_robustness_seed(root, args.family, args.seed), indent=2, sort_keys=True))
