"""Execute the RI-2 heat PINN pilot.

By default this command runs one B1 smoke case.  ``--all`` runs the frozen
development grid (B1--B4, three data seeds and two optimiser seeds).  Every
attempt writes its own checkpoint and manifest; failures are retained.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.reliability_audit_v1 import HeatPINNConfig, run_heat_pinn


def _cases(all_cases: bool) -> list[HeatPINNConfig]:
    if not all_cases:
        return [HeatPINNConfig(benchmark="B1", data_seed=10, optimizer_seed=100)]
    return [
        HeatPINNConfig(benchmark=benchmark, data_seed=data_seed, optimizer_seed=optimizer_seed)
        for benchmark in ("B1", "B2", "B3", "B4")
        for data_seed in (10, 11, 12)
        for optimizer_seed in (100, 101)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="run all 24 pilot cases")
    parser.add_argument("--output", type=Path, default=Path("outputs/reliability_audit_v1/pilot/ri2"))
    parser.add_argument("--epochs", type=int, default=None, help="development override for a smoke run")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for config in _cases(args.all):
        if args.epochs is not None:
            config = HeatPINNConfig(**{**config.__dict__, "epochs": args.epochs, "output_dir": None})
        case_dir = args.output / f"{config.benchmark}_data{config.data_seed}_opt{config.optimizer_seed}"
        try:
            run = run_heat_pinn(HeatPINNConfig(**{**config.__dict__, "output_dir": str(case_dir)}))
            records.append(run.to_manifest())
        except Exception as exc:  # retain terminal failure in the aggregate denominator
            records.append(
                {
                    "schema_version": 1,
                    "protocol_id": "reliability_audit_v1",
                    "benchmark": config.benchmark,
                    "data_seed": config.data_seed,
                    "optimizer_seed": config.optimizer_seed,
                    "execution_status": "SOLVER_FAILURE",
                    "fit_status": "FAIL",
                    "profile_status": "NOT_ELIGIBLE",
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                }
            )
    (args.output / "pilot_index.json").write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"cases": len(records), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
