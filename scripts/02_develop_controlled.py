"""Run P2 development-only direction and gamma selection, then write the phase lock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.controlled import run_controlled_development


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/p2_development.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p2_development"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_controlled_development(
        root / args.config if not args.config.is_absolute() else args.config,
        root / args.output_root if not args.output_root.is_absolute() else args.output_root,
        root,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "status": result["status"],
        "selected": result["selected"],
        "locked_config_sha256": result["locked_config_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

