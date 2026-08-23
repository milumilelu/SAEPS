"""Machine aggregation and reporting for the V5.1 descriptive audit."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.finite_gamma import ALPHAS, CHECKPOINTS
from saeps.v5.governance import sha256_file


def _records(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    rows = []
    for family, seeds in CHECKPOINTS.items():
        for seed in seeds:
            for alpha in ALPHAS:
                slug = f"{alpha:.0e}".replace("+", "p").replace("-", "m")
                path = (
                    root
                    / "outputs/runs/v5/finite_gamma"
                    / family
                    / f"seed_{seed}"
                    / f"alpha_{slug}"
                    / "result.json"
                )
                if not path.is_file():
                    raise ValueError(f"missing V5.1 terminal record: {family}/{seed}/{alpha}")
                rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return rows


def build_finite_gamma_aggregate(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    records = _records(root)
    alpha_rows = []
    for alpha in ALPHAS:
        selected = [row for _, row in records if float(row["alpha"]) == alpha]
        computable = [row for row in selected if row.get("eta") is not None]
        exact_computable = [row for row in selected if row.get("E_SAEPS") is not None]
        alpha_rows.append(
            {
                "alpha": alpha,
                "terminal_count": len(selected),
                "pass_count": sum(row["status"] == "PASS" for row in selected),
                "eta_median_all_computable": statistics.median(row["eta"] for row in computable),
                "effective_rank_median": statistics.median(row["effective_rank"] for row in selected),
                "E_SAEPS_median_all_exact_computable": statistics.median(
                    row["E_SAEPS"] for row in exact_computable
                )
                if exact_computable
                else None,
                "E_raw_median_all_exact_computable": statistics.median(
                    row["E_raw"] for row in exact_computable
                )
                if exact_computable
                else None,
            }
        )
    per_checkpoint = []
    for family, seeds in CHECKPOINTS.items():
        for seed in seeds:
            selected = [
                row
                for _, row in records
                if row["family"] == family and int(row["seed"]) == seed
            ]
            selected.sort(key=lambda row: float(row["alpha"]))
            eta = [float(row["eta"]) for row in selected]
            high = selected[-1]
            per_checkpoint.append(
                {
                    "family": family,
                    "seed": seed,
                    "eta_nondecreasing": all(
                        eta[index + 1] >= eta[index] - 1.0e-12
                        for index in range(len(eta) - 1)
                    ),
                    "small_alpha_eta": eta[0],
                    "high_alpha_eta": eta[-1],
                    "high_alpha_relative_Fse_to_Fraw": abs(
                        float(high["F_se_GN_explicit"]) - float(high["F_raw"])
                    )
                    / max(abs(float(high["F_raw"])), 1.0e-30),
                    "effective_rank_small_alpha": float(selected[0]["effective_rank"]),
                    "effective_rank_high_alpha": float(selected[-1]["effective_rank"]),
                }
            )
    failures = [
        {
            "family": row["family"],
            "seed": row["seed"],
            "alpha": row["alpha"],
            "status": row["status"],
            "failure_stage": row["failure_stage"],
            "failure_reason": row["failure_reason"],
        }
        for _, row in records
        if row["status"] != "PASS"
    ]
    pass_count = sum(row["status"] == "PASS" for _, row in records)
    high_errors = [row["high_alpha_relative_Fse_to_Fraw"] for row in per_checkpoint]
    return {
        "schema_version": 1,
        "phase": "V5_1_FINITE_GAMMA",
        "phase_type": "descriptive_audit",
        "engineering_status": "PASSED" if len(records) == 42 else "FAILED",
        "scientific_status": None,
        "scientific_win_gate": None,
        "nominal_gamma_recalibrated": False,
        "planned_terminal_count": 42,
        "terminal_count": len(records),
        "pass_count": pass_count,
        "failure_count": len(records) - pass_count,
        "status_counts": {
            status: sum(row["status"] == status for _, row in records)
            for status in ["PASS", "SOLVER_FAILURE", "NUMERICAL_FAILURE"]
        },
        "alpha_summaries": alpha_rows,
        "checkpoint_summaries": per_checkpoint,
        "high_gamma_GN_limit": {
            "alpha": ALPHAS[-1],
            "median_relative_Fse_to_Fraw": statistics.median(high_errors),
            "maximum_relative_Fse_to_Fraw": max(high_errors),
            "all_checkpoint_eta_nondecreasing": all(
                row["eta_nondecreasing"] for row in per_checkpoint
            ),
        },
        "failures": failures,
        "source_records": [
            {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}
            for path, _ in records
        ],
    }


def write_finite_gamma_report(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    aggregate = build_finite_gamma_aggregate(root)
    evidence_root = root / "docs/evidence/v5"
    json_path = evidence_root / "V5_FINITE_GAMMA_AUDIT.json"
    markdown_path = evidence_root / "V5_FINITE_GAMMA_AUDIT.md"
    write_json_atomic(json_path, aggregate)
    lines = [
        "# V5.1 Finite-Gamma / Effective-Rank Audit",
        "",
        f"- Engineering status: `{aggregate['engineering_status']}`",
        f"- Terminal records: `{aggregate['terminal_count']}/42`",
        f"- Numerical PASS: `{aggregate['pass_count']}/42`",
        f"- Failed terminal records retained: `{aggregate['failure_count']}`",
        "- Scientific win gate: none (descriptive audit)",
        "- Nominal gamma recalibration: forbidden and not performed",
        "",
        "## Alpha summary (all computable quantities retained)",
        "",
        "| alpha | PASS/6 | median eta | median effective rank | median E_SAEPS | median E_raw |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate["alpha_summaries"]:
        lines.append(
            f"| {row['alpha']:.0e} | {row['pass_count']}/6 | {row['eta_median_all_computable']:.6g} | "
            f"{row['effective_rank_median']:.6g} | "
            f"{row['E_SAEPS_median_all_exact_computable'] if row['E_SAEPS_median_all_exact_computable'] is not None else 'NA'} | "
            f"{row['E_raw_median_all_exact_computable'] if row['E_raw_median_all_exact_computable'] is not None else 'NA'} |"
        )
    limit = aggregate["high_gamma_GN_limit"]
    lines.extend(
        [
            "",
            "## Registered limit checks",
            "",
            f"At alpha=1e2, median relative |Fse_GN-Fraw|/|Fraw| is `{limit['median_relative_Fse_to_Fraw']:.6g}` and the maximum is `{limit['maximum_relative_Fse_to_Fraw']:.6g}`.",
            f"Eta is nondecreasing over the registered grid for all six checkpoints: `{str(limit['all_checkpoint_eta_nondecreasing']).lower()}`.",
            "No analogous high-gamma convergence claim is imposed on the exact Hessian.",
            "",
            "## Failed terminal records",
            "",
            "| Family | Seed | alpha | Status | Stage | Reason |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    lines.extend(
        f"| {row['family']} | {row['seed']} | {row['alpha']:.0e} | {row['status']} | {row['failure_stage']} | {row['failure_reason']} |"
        for row in aggregate["failures"]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return aggregate


def write_finite_gamma_figure(repo_root: str | Path, aggregate: dict[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    records = [row for _, row in _records(root)]
    width, height = 1100, 440
    panels = [(70, 45, 440, 330), (620, 45, 440, 330)]
    colors = ["#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#ea580c", "#0891b2"]
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.axis{stroke:#374151;stroke-width:1}.grid{stroke:#d1d5db;stroke-width:.7}.line{fill:none;stroke-width:2}.point{stroke:white;stroke-width:1}</style>',
    ]
    for x, y, panel_width, panel_height in panels:
        svg.extend(
            [
                f'<line class="axis" x1="{x}" y1="{y + panel_height}" x2="{x + panel_width}" y2="{y + panel_height}"/>',
                f'<line class="axis" x1="{x}" y1="{y}" x2="{x}" y2="{y + panel_height}"/>',
            ]
        )
    log_alpha_min, log_alpha_max = -10.0, 2.0

    def x_position(alpha: float, panel: int) -> float:
        x, _, panel_width, _ = panels[panel]
        return x + (math.log10(alpha) - log_alpha_min) / (log_alpha_max - log_alpha_min) * panel_width

    import math

    for tick in ALPHAS:
        for panel in [0, 1]:
            x = x_position(tick, panel)
            _, y, _, panel_height = panels[panel]
            svg.append(f'<line class="grid" x1="{x:.2f}" y1="{y}" x2="{x:.2f}" y2="{y + panel_height}"/>')
            svg.append(f'<text x="{x:.2f}" y="{y + panel_height + 20}" font-size="11" text-anchor="middle">{tick:.0e}</text>')
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x, y, panel_width, panel_height = panels[0]
        py = y + panel_height - tick * panel_height
        svg.append(f'<line class="grid" x1="{x}" y1="{py:.2f}" x2="{x + panel_width}" y2="{py:.2f}"/>')
        svg.append(f'<text x="{x - 10}" y="{py + 4:.2f}" font-size="11" text-anchor="end">{tick:g}</text>')
    rank_min, rank_max = 1.0e-2, 1.0e2
    for tick in [1.0e-2, 1.0e-1, 1.0, 10.0, 100.0]:
        x, y, panel_width, panel_height = panels[1]
        py = y + panel_height - (math.log10(tick) - math.log10(rank_min)) / (math.log10(rank_max) - math.log10(rank_min)) * panel_height
        svg.append(f'<line class="grid" x1="{x}" y1="{py:.2f}" x2="{x + panel_width}" y2="{py:.2f}"/>')
        svg.append(f'<text x="{x - 10}" y="{py + 4:.2f}" font-size="11" text-anchor="end">{tick:g}</text>')
    series_index = 0
    for family, seeds in CHECKPOINTS.items():
        for seed in seeds:
            selected = sorted(
                [row for row in records if row["family"] == family and row["seed"] == seed],
                key=lambda row: row["alpha"],
            )
            color = colors[series_index]
            eta_points = []
            rank_points = []
            for row in selected:
                eta_points.append(f"{x_position(row['alpha'], 0):.2f},{panels[0][1] + panels[0][3] - min(max(row['eta'], 0.0), 1.0) * panels[0][3]:.2f}")
                rank_fraction = (math.log10(max(row["effective_rank"], rank_min)) - math.log10(rank_min)) / (math.log10(rank_max) - math.log10(rank_min))
                rank_points.append(f"{x_position(row['alpha'], 1):.2f},{panels[1][1] + panels[1][3] - rank_fraction * panels[1][3]:.2f}")
            svg.append(f'<polyline class="line" stroke="{color}" points="{" ".join(eta_points)}"/>')
            svg.append(f'<polyline class="line" stroke="{color}" points="{" ".join(rank_points)}"/>')
            label_y = 395 + series_index * 16
            svg.append(f'<line x1="70" y1="{label_y}" x2="92" y2="{label_y}" stroke="{color}" stroke-width="3"/>')
            svg.append(f'<text x="98" y="{label_y + 4}" font-size="11">{family} {seed}</text>')
            series_index += 1
    svg.extend(
        [
            '<text x="290" y="24" font-size="15" font-weight="bold" text-anchor="middle">State-eliminated curvature ratio</text>',
            '<text x="840" y="24" font-size="15" font-weight="bold" text-anchor="middle">Damping-dependent effective rank</text>',
            '<text x="290" y="430" font-size="12" text-anchor="middle">alpha</text>',
            '<text x="840" y="430" font-size="12" text-anchor="middle">alpha</text>',
            '</svg>',
        ]
    )
    output = root / "paper_artifacts/v5/V5_FINITE_GAMMA_AUDIT.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output
