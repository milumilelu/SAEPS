"""Run one fixed V5 engineering checkpoint reconstruction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v5.reconstruction import reconstruct_all_checkpoints, reconstruct_checkpoint


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--family", choices=["burgers", "allen_cahn", "scalability_base"])
    parser.add_argument("--seed", type=int)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if arguments.all:
        if arguments.family is not None or arguments.seed is not None:
            parser.error("--all cannot be combined with --family or --seed")
        results = reconstruct_all_checkpoints(root)
        summary = [
            {key: result[key] for key in ["benchmark", "seed", "status", "binding_valid", "elapsed_seconds"]}
            for result in results
        ]
        print(json.dumps(summary, indent=2))
    else:
        if arguments.family is None or arguments.seed is None:
            parser.error("single reconstruction requires both --family and --seed")
        result = reconstruct_checkpoint(root, arguments.family, arguments.seed)
        print(json.dumps({key: result[key] for key in ["benchmark", "seed", "status", "binding_valid", "elapsed_seconds"]}, indent=2))
