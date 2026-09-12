"""Build the frozen independent analytic profile artifacts for B1/B3--B6.

The command has no PINN or test-truth optimisation path.  It uses the
closed-form heat observations and writes one JSON artifact per benchmark plus
an index containing the declared grid, data seed and covariance scales.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.identifiability.profile_reference import (
    DEFAULT_C,
    DEFAULT_K,
    DEFAULT_AMPLITUDE,
    frozen_profile_grid,
    generate_analytic_observations,
    profile_heat_observation,
    write_profile_json,
)


BENCHMARKS = ("B1", "B3", "B4", "B5", "B6")


def build(output_dir: Path, *, noise_rho: float = 0.01, data_seed: int = 10) -> dict:
    """Generate all declared benchmark profiles and return the index."""

    output_dir.mkdir(parents=True, exist_ok=True)
    grid = frozen_profile_grid(DEFAULT_K)
    rows = []
    for benchmark in BENCHMARKS:
        data = generate_analytic_observations(
            benchmark,
            k=DEFAULT_K,
            C=DEFAULT_C,
            amplitude=DEFAULT_AMPLITUDE,
            noise_rho=noise_rho,
            data_seed=data_seed,
        )
        profile = profile_heat_observation(data, parameter_grid=grid)
        path = output_dir / f"{benchmark}_ANALYTIC_PROFILE.json"
        write_profile_json(profile, path)
        rows.append(
            {
                "benchmark": benchmark,
                "path": path.name,
                "grid_size": len(profile["points"]),
                "profile_status": profile["profile_status"],
                "flat_profile": profile["flat_profile"],
                "minimum_scan_value": profile["minimum_scan_value"],
                "objective_span_half_chi2": profile["objective_span_half_chi2"],
            }
        )
    index = {
        "schema_version": 1,
        "protocol_id": "reliability_audit_v1",
        "reference_kind": "independent_analytic_heat_profiles",
        "benchmarks": list(BENCHMARKS),
        "truth_used_only_for_data_generation": {"k": DEFAULT_K, "C": DEFAULT_C, "a": DEFAULT_AMPLITUDE},
        "noise_rho": float(noise_rho),
        "data_seed": int(data_seed),
        "profile_grid": grid.tolist(),
        "rows": rows,
    }
    (output_dir / "PROFILE_INDEX.json").write_text(
        json.dumps(index, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/reliability_audit_v1/pilot/ri1/profiles"))
    parser.add_argument("--noise-rho", type=float, default=0.01)
    parser.add_argument("--data-seed", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir, noise_rho=args.noise_rho, data_seed=args.data_seed), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
