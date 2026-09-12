"""Build the frozen independent analytic profile artifacts for B1--B6.

The command has no PINN or test-truth optimisation path.  It uses the
closed-form heat observations and writes one JSON artifact per benchmark plus
an index containing the declared grid, data seed and covariance scales.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from xml.sax.saxutils import escape

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from saeps.identifiability.profile_reference import (
    DEFAULT_C,
    DEFAULT_K,
    DEFAULT_AMPLITUDE,
    frozen_profile_grid,
    generate_analytic_observations,
    profile_heat_observation,
    write_profile_json,
)


BENCHMARKS = ("B1", "B2", "B3", "B4", "B5", "B6")


def build(output_dir: Path, *, noise_rho: float = 0.01, data_seed: int = 10) -> dict:
    """Generate all declared benchmark profiles and return the index."""

    output_dir.mkdir(parents=True, exist_ok=True)
    grid = frozen_profile_grid(DEFAULT_K)
    rows = []
    curve_rows = []
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
        for index, point in enumerate(profile["points"]):
            curve_rows.append(
                {
                    "benchmark": benchmark,
                    "grid_index": index,
                    "scan_parameter": point["scan_parameter"],
                    "scan_value": point["scan_value"],
                    "objective_half_chi2": point["objective_half_chi2"],
                    "objective_delta_half_chi2": point["objective_delta_half_chi2"],
                    "nuisance": json.dumps(point["nuisance"], sort_keys=True),
                    "status": point["status"],
                    "boundary": point["boundary"],
                }
            )
        rows.append(
            {
                "benchmark": benchmark,
                "path": path.name,
                "grid_size": len(profile["points"]),
                "profile_status": profile["profile_status"],
                "branch_status": profile["branch_status"],
                "flat_profile": profile["flat_profile"],
                "boundary_truncated": profile["boundary_truncated"],
                "nuisance_boundary_count": profile["nuisance_boundary_count"],
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
    curve_path = output_dir / "PROFILE_CURVES.csv"
    with curve_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(curve_rows[0]))
        writer.writeheader()
        writer.writerows(curve_rows)
    _write_profile_svg(output_dir / "PROFILE_CURVES.svg", [
        (benchmark, profile_heat_observation(generate_analytic_observations(
            benchmark, k=DEFAULT_K, C=DEFAULT_C, amplitude=DEFAULT_AMPLITUDE,
            noise_rho=noise_rho, data_seed=data_seed
        ), parameter_grid=grid))
        for benchmark in BENCHMARKS
    ])
    return index


def _write_profile_svg(path: Path, profiles: list[tuple[str, dict]]) -> None:
    """Write a dependency-free overview plot of the six profile curves.

    The ordinate is ``log10(1 + Delta half-chi2)`` so the informative and
    flat profiles can share one deterministic view without clipping.  This is
    a visualization only; all estimands remain in the JSON/CSV artifacts.
    """

    width, height = 900, 620
    panel_w, panel_h = 280, 250
    margin_x, margin_y = 20, 40
    gap_x, gap_y = 15, 25
    x_min, x_max = -float(np.log(3.0)), float(np.log(3.0))
    fragments = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<title>Independent analytic heat-equation profile curves</title>',
        '<desc>Six frozen 31-point profiles. The ordinate is log10(1 plus objective delta).</desc>',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for index, (benchmark, profile) in enumerate(profiles):
        col, row = index % 3, index // 3
        left = margin_x + col * (panel_w + gap_x)
        top = margin_y + row * (panel_h + gap_y)
        plot_left, plot_top = left + 38, top + 28
        plot_right, plot_bottom = left + panel_w - 10, top + panel_h - 32
        values = np.asarray([float(point["objective_delta_half_chi2"]) for point in profile["points"]])
        y_values = np.log10(1.0 + np.maximum(values, 0.0))
        y_max = max(float(np.max(y_values)), 1.0e-12)
        y_max = max(y_max * 1.08, 1.0)
        points = []
        for point, y_value in zip(profile["points"], y_values):
            x_value = float(point["scan_log_offset"])
            px = plot_left + (x_value - x_min) / (x_max - x_min) * (plot_right - plot_left)
            py = plot_bottom - float(y_value) / y_max * (plot_bottom - plot_top)
            points.append(f"{px:.3f},{py:.3f}")
        fragments.extend([
            f'<g id="{escape(benchmark)}">',
            f'<text x="{left + 8}" y="{top + 16}" font-family="sans-serif" font-size="14" font-weight="bold">{escape(benchmark)} ({escape(str(profile["profile_status"]))})</text>',
            f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="#222"/>',
            f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" stroke="#222"/>',
            f'<polyline fill="none" stroke="#0072B2" stroke-width="1.7" points="{" ".join(points)}"/>',
            f'<text x="{plot_left - 4}" y="{plot_bottom + 22}" font-family="sans-serif" font-size="10" text-anchor="middle">−ln3</text>',
            f'<text x="{plot_right}" y="{plot_bottom + 22}" font-family="sans-serif" font-size="10" text-anchor="middle">ln3</text>',
            f'<text x="{plot_left - 7}" y="{plot_top + 4}" font-family="sans-serif" font-size="10" text-anchor="end">{y_max:.1f}</text>',
            f'<text x="{plot_left - 7}" y="{plot_bottom + 4}" font-family="sans-serif" font-size="10" text-anchor="end">0</text>',
            f'<text x="{(plot_left + plot_right) / 2:.1f}" y="{plot_bottom + 34}" font-family="sans-serif" font-size="10" text-anchor="middle">log(k/k_ref)</text>',
            f'<text transform="translate({left + 12},{(plot_top + plot_bottom) / 2:.1f}) rotate(-90)" font-family="sans-serif" font-size="10" text-anchor="middle">log10(1+Δχ²/2)</text>',
            '</g>',
        ])
    fragments.append('</svg>')
    path.write_text("\n".join(fragments) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/reliability_audit_v1/pilot/ri1/profiles"))
    parser.add_argument("--noise-rho", type=float, default=0.01)
    parser.add_argument("--data-seed", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir, noise_rho=args.noise_rho, data_seed=args.data_seed), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
