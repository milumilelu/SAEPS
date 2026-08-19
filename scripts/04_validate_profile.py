"""Run the P3 nonlinear profile-engine acceptance suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.p3_validation import run_profile_validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/p3_profile.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p3"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_profile_validation(
        root / args.config if not args.config.is_absolute() else args.config,
        root / args.output_root if not args.output_root.is_absolute() else args.output_root,
        root,
    )
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "errors": result["errors"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

