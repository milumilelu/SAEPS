"""Run the P4 development-only scalar benchmark screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.p4_screening import run_p4_screening


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/p4_screening.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p4_screening"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_p4_screening(
        root / args.config if not args.config.is_absolute() else args.config,
        root / args.output_root if not args.output_root.is_absolute() else args.output_root,
        root,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "status": result["status"],
        "selected_candidate": result["selected_candidate"],
        "summaries": {
            name: value["summary"] for name, value in result["candidate_results"].items()
        },
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
