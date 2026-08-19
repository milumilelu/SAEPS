"""Run the P0 tiny-PINN checkpoint round-trip acceptance test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.smoke import run_smoke_from_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/base.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/smoke"))
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    metadata = run_smoke_from_config(
        config_path=(repo_root / args.config) if not args.config.is_absolute() else args.config,
        output_root=(repo_root / args.output_root) if not args.output_root.is_absolute() else args.output_root,
        repo_root=repo_root,
    )
    summary = {
        "run_id": metadata["run_id"],
        "status": metadata["status"],
        "state_rmse": metadata["trained_metrics"]["state_rmse"],
        "roundtrip_max_abs_error": metadata["roundtrip"]["max_abs_error"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

