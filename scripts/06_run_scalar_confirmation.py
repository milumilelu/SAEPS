"""Run the globally locked P5 scalar confirmation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.p5_confirmation import run_p5_confirmation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/locked/scalar.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p5_scalar"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_p5_confirmation(
        root / args.config if not args.config.is_absolute() else args.config,
        root / args.output_root if not args.output_root.is_absolute() else args.output_root,
        root,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "engineering_gate": result["engineering_gate"],
        "scientific_classification_sg2": result["scientific_classification_sg2"],
        "valid": result["valid"],
        "paired_wins_out_of_planned_10": result["paired_wins_out_of_planned_10"],
        "median_D": result["median_D"],
        "paired_bootstrap_95_ci": result["paired_bootstrap_95_ci"],
    }, indent=2, sort_keys=True))
    return 0 if result["engineering_gate"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

