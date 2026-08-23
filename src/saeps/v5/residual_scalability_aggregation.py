"""Aggregate V5.4 cost-only residual-dimension scalability records."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.residual_scalability import REPEATS, RESIDUAL_COUNTS, STATE_COUNTS


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def build_residual_scalability(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    rows: list[dict[str, Any]] = []
    sources = []
    for state_count in STATE_COUNTS:
        for residual_count in RESIDUAL_COUNTS:
            for repeat in REPEATS:
                path = root / (
                    "outputs/runs/v5/residual_scalability/"
                    f"n_{state_count}/m_{residual_count}/repeat_{repeat}/result.json"
                )
                if not path.is_file():
                    raise ValueError(f"missing V5.4 planned timing record: {path}")
                row = json.loads(path.read_text(encoding="utf-8"))
                if row["state_parameter_count"] != state_count or row["residual_count"] != residual_count:
                    raise ValueError("V5.4 record coordinates do not match its path")
                if row["repeat"] != repeat or row["synthetic_residual_padding"] is not False:
                    raise ValueError("V5.4 repeat or real-residual invariant failed")
                rows.append(row)
                sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    conditions = []
    for state_count in STATE_COUNTS:
        for residual_count in RESIDUAL_COUNTS:
            selected = [
                row for row in rows
                if row["state_parameter_count"] == state_count
                and row["residual_count"] == residual_count
            ]
            passed = [row for row in selected if row["status"] == "PASS"]
            conditions.append(
                {
                    "state_parameter_count": state_count,
                    "residual_count": residual_count,
                    "terminal_count": len(selected),
                    "pass_count": len(passed),
                    "wall_seconds": _summary([float(row["wall_seconds"]) for row in passed]) if passed else None,
                    "solve_seconds": _summary([float(row["solve_seconds"]) for row in passed]) if passed else None,
                    "cg_iterations": _summary([float(row["cg_iterations"]) for row in passed]) if passed else None,
                    "verified_relative_residual": _summary(
                        [float(row["verified_relative_residual"]) for row in passed]
                    ) if passed else None,
                    "JVP_count": _summary([float(row["JVP_count"]) for row in passed]) if passed else None,
                    "VJP_count": _summary([float(row["VJP_count"]) for row in passed]) if passed else None,
                    "shared_condition_setup_seconds": float(selected[0]["shared_condition_setup_seconds"]),
                    "peak_memory_available": all(row["peak_memory_bytes"] is not None for row in selected),
                    "failure_reasons": [row["failure_reason"] for row in selected if row["status"] != "PASS"],
                }
            )
    return {
        "schema_version": 1,
        "phase": "V5_4_RESIDUAL_SCALABILITY",
        "role": "cost_only_non_scientific_claim_binding",
        "engineering_status": "PASSED" if len(rows) == 27 and all(row["status"] == "PASS" for row in rows) else "FAILED",
        "terminal_count": len(rows),
        "pass_count": sum(row["status"] == "PASS" for row in rows),
        "planned_count": 27,
        "training_or_reconstruction_runs": 0,
        "real_residual_construction": True,
        "synthetic_residual_padding": False,
        "complexity_exponent_fitted": False,
        "peak_memory_status": "UNAVAILABLE_NATIVE_CPU_TENSOR_PEAK",
        "conditions": conditions,
        "source_records": sources,
    }


def write_residual_scalability_report(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    aggregate = build_residual_scalability(root)
    write_json_atomic(root / "docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.json", aggregate)
    lines = [
        "# V5.4 Residual-Dimension Scalability Report",
        "",
        f"- Engineering status: `{aggregate['engineering_status']}`",
        f"- Terminal/pass records: `{aggregate['terminal_count']}/{aggregate['pass_count']}` of 27",
        "- Role: cost-only evidence; no scientific claim gate.",
        "- Residuals: constructed from actual PDE/data/initial/boundary points; no synthetic padding.",
        "- Peak memory: unavailable because native CPU tensor peak memory is not reliably instrumented.",
        "- Complexity exponent: not fitted or claimed, as preregistered.",
        "",
        "| n_theta | m | PASS | wall s median [min,max] | solve s median | CG iter median | max verified residual |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate["conditions"]:
        wall, solve, iterations, residual = (
            row["wall_seconds"], row["solve_seconds"], row["cg_iterations"], row["verified_relative_residual"]
        )
        lines.append(
            f"| {row['state_parameter_count']} | {row['residual_count']} | {row['pass_count']}/3 | "
            f"{wall['median']:.6g} [{wall['minimum']:.6g},{wall['maximum']:.6g}] | "
            f"{solve['median']:.6g} | {iterations['median']:.0f} | {residual['maximum']:.3e} |"
        )
    (root / "docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return aggregate


def write_residual_scalability_figure(repo_root: str | Path, aggregate: dict[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    width, height = 860, 480
    left, top, plot_w, plot_h = 85, 45, 680, 340
    conditions = aggregate["conditions"]
    maximum = max(row["wall_seconds"]["median"] for row in conditions) * 1.08

    def y(value: float) -> float:
        return top + plot_h - value / maximum * plot_h

    colors = {213: "#2563eb", 853: "#059669", 3413: "#dc2626"}
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.axis{stroke:#374151}.grid{stroke:#d1d5db;stroke-width:.7}</style>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>',
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>',
        '<text x="425" y="24" font-size="16" font-weight="bold" text-anchor="middle">V5.4 matrix-free wall time (three-repeat median)</text>',
    ]
    for index in range(6):
        value = maximum * index / 5
        py = y(value)
        svg.append(f'<line class="grid" x1="{left}" y1="{py:.2f}" x2="{left + plot_w}" y2="{py:.2f}"/>')
        svg.append(f'<text x="{left - 8}" y="{py + 4:.2f}" font-size="11" text-anchor="end">{value:.2f}</text>')
    for residual_count in RESIDUAL_COUNTS:
        points = []
        for index, state_count in enumerate(STATE_COUNTS):
            row = next(item for item in conditions if item["state_parameter_count"] == state_count and item["residual_count"] == residual_count)
            px = left + (index + 0.5) * plot_w / len(STATE_COUNTS)
            py = y(row["wall_seconds"]["median"])
            points.append((px, py))
        svg.append(f'<polyline fill="none" stroke="{colors[residual_count]}" stroke-width="2" points="' + " ".join(f"{x:.2f},{yy:.2f}" for x, yy in points) + '"/>')
        for px, py in points:
            svg.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{colors[residual_count]}"/>')
    for index, state_count in enumerate(STATE_COUNTS):
        px = left + (index + 0.5) * plot_w / len(STATE_COUNTS)
        svg.append(f'<text x="{px:.2f}" y="{top + plot_h + 22}" font-size="11" text-anchor="middle">{state_count}</text>')
    for index, residual_count in enumerate(RESIDUAL_COUNTS):
        y0 = 410 + 20 * index
        svg.append(f'<line x1="650" y1="{y0}" x2="672" y2="{y0}" stroke="{colors[residual_count]}" stroke-width="3"/><text x="680" y="{y0 + 4}" font-size="11">m={residual_count}</text>')
    svg.extend([
        '<text x="425" y="470" font-size="12" text-anchor="middle">State parameter count n_theta (categorical preregistered sizes)</text>',
        '<text x="18" y="215" font-size="12" text-anchor="middle" transform="rotate(-90 18 215)">Wall seconds</text>',
        '</svg>',
    ])
    output = root / "paper_artifacts/v5/V5_RESIDUAL_SCALABILITY.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output
