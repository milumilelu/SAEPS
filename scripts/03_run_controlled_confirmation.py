"""Run the locked 10-seed, 50-evaluation P2 confirmation protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.controlled import run_controlled_confirmation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("outputs/runs/p2_confirmation"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_controlled_confirmation(
        root / args.output_root if not args.output_root.is_absolute() else args.output_root,
        root,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "engineering_gate": result["engineering_gate"],
        "scientific_gate_sg1": result["scientific_gate_sg1"],
        "valid_seeds": result["valid_seeds"],
        "spearman_median": result["spearman"]["median"],
        "monotonic_seed_count": result["monotonic_seed_count"],
    }, indent=2, sort_keys=True))
    return 0 if result["engineering_gate"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

