"""Run the complete P1 SAEPS numerical-core acceptance suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.p1_validation import run_core_validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/p1_core.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p1"))
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    result = run_core_validation(
        (repo_root / args.config) if not args.config.is_absolute() else args.config,
        (repo_root / args.output_root) if not args.output_root.is_absolute() else args.output_root,
        repo_root,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "status": result["status"],
        "operator_relative_error_max": result["metrics"]["operator_relative_error_max"],
        "curvature_relative_error": result["metrics"]["curvature_relative_error"],
        "finite_difference_theta_relative_error": result["metrics"]["finite_difference_theta_relative_error"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

