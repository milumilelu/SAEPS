"""V5.5 source-derived baseline and nonlinear-profile consolidation."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file


SEEDS = [200, 201, 202, 203, 204]


def build_baseline_consolidation(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    rows, sources = [], []
    for seed in SEEDS:
        path = root / f"outputs/runs/v5/profile_bridge/seed_{seed}/result.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["seed"] != seed or record["PROFILE_EVALUABLE"] is not True:
            raise ValueError("V5.5 requires all five fixed evaluable V5.2 records")
        m = int(record["m"])
        center_total = m * float(record["profile"]["center_loss_mean"])
        slope = float(record["center_stationarity"]["S_lambda"])
        offsets = sorted({float(point["offset"]) for point in record["profile"]["points"]} | {0.0})
        points_by_offset = {float(point["offset"]): point for point in record["profile"]["points"]}
        objective_rows = []
        for offset in offsets:
            profile_total = center_total if offset == 0.0 else m * float(points_by_offset[offset]["loss_mean"])
            objective_rows.append(
                {
                    "offset": offset,
                    "Phi_frozen": center_total + slope * offset + 0.5 * float(record["F_raw"]) * offset**2,
                    "Phi_SAEPS_quadratic": center_total + slope * offset + 0.5 * float(record["F_se_GN_explicit"]) * offset**2,
                    "Phi_reopt_gamma": profile_total,
                    "profile_point_status": "CENTER" if offset == 0.0 else points_by_offset[offset]["status"],
                }
            )
        finest = min(record["profile"]["curvatures"], key=lambda item: float(item["h"]))
        rows.append(
            {
                "seed": seed,
                "PROFILE_VALID": bool(record["PROFILE_VALID"]),
                "objective_units": "total_objective_m_times_reported_mean",
                "objective_rows": objective_rows,
                "curvature": {
                    "F_raw": float(record["F_raw"]),
                    "F_se_GN": float(record["F_se_GN_explicit"]),
                    "H_red_exact_gamma": float(record["H_red_exact_gamma"]),
                    "H_profile_gamma_finest": float(finest["curvature"]),
                    "H_profile_gamma_finest_h": float(finest["h"]),
                    "profile_curvature_binding_valid": bool(record["PROFILE_VALID"]),
                },
            }
        )
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    return {
        "schema_version": 1,
        "phase": "V5_5_BASELINE_CONSOLIDATION",
        "engineering_status": "PASSED",
        "scientific_status_inherited": "NOT_SUPPORTED",
        "training_runs": 0,
        "planned_denominator": 5,
        "profile_evaluable_count": 5,
        "profile_valid_count": sum(row["PROFILE_VALID"] for row in rows),
        "claim_boundary": "The nonlinear-profile-equivalence claim is deleted; invalid finest profile curvatures are displayed only as diagnostics.",
        "median_curvatures": {
            key: statistics.median(row["curvature"][key] for row in rows)
            for key in ["F_raw", "F_se_GN", "H_red_exact_gamma", "H_profile_gamma_finest"]
        },
        "seed_rows": rows,
        "source_records": sources,
    }


def write_baseline_consolidation_report(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    aggregate = build_baseline_consolidation(root)
    write_json_atomic(root / "docs/evidence/v5/V5_BASELINE_CONSOLIDATION.json", aggregate)
    lines = [
        "# V5.5 Baseline Consolidation",
        "",
        "- Engineering status: `PASSED`",
        "- New training: `0`",
        f"- Inherited profile-bridge scientific status: `{aggregate['scientific_status_inherited']}`",
        f"- PROFILE_VALID: `{aggregate['profile_valid_count']}/5`",
        "- Claim boundary: nonlinear-profile equivalence is not supported and must not be claimed.",
        "",
        "The objective curves compare the fixed-state quadratic, the SAEPS-GN quadratic, and the actually reoptimized finite-gamma profile at identical offsets. Reported profile mean losses are multiplied by each record's residual count to match the total-objective curvature units.",
        "",
        "| Seed | Profile valid | F_raw | F_se_GN | H_red_exact,gamma | H_profile,gamma (h=0.005) |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in aggregate["seed_rows"]:
        c = row["curvature"]
        lines.append(
            f"| {row['seed']} | {str(row['PROFILE_VALID']).lower()} | {c['F_raw']:.6g} | "
            f"{c['F_se_GN']:.6g} | {c['H_red_exact_gamma']:.6g} | {c['H_profile_gamma_finest']:.6g} |"
        )
    lines.extend([
        "",
        "Finest-scale profile curvatures for invalid seeds are nonbinding diagnostics, not reference values. Only seed204 passes the frozen profile-validity rules.",
    ])
    (root / "docs/evidence/v5/V5_BASELINE_CONSOLIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return aggregate


def write_baseline_consolidation_figure(repo_root: str | Path, aggregate: dict[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    width, height = 1050, 650
    panel_w, panel_h = 315, 245
    origins = [(55, 55), (375, 55), (695, 55), (215, 350), (535, 350)]
    colors = {"Phi_frozen": "#9ca3af", "Phi_SAEPS_quadratic": "#2563eb", "Phi_reopt_gamma": "#dc2626"}
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.axis{stroke:#374151}.grid{stroke:#e5e7eb;stroke-width:.7}</style>',
        '<text x="525" y="25" font-size="17" font-weight="bold" text-anchor="middle">V5.5 frozen, SAEPS-GN, and nonlinear reoptimized objectives</text>',
    ]
    for row, (ox, oy) in zip(aggregate["seed_rows"], origins):
        data = row["objective_rows"]
        values = [float(point[key]) for point in data for key in colors]
        ymin, ymax = min(values), max(values)
        margin = max((ymax - ymin) * 0.08, 1.0e-8)
        ymin, ymax = ymin - margin, ymax + margin

        def px(offset: float) -> float:
            return ox + (offset + 0.04) / 0.08 * panel_w

        def py(value: float) -> float:
            return oy + panel_h - (value - ymin) / (ymax - ymin) * panel_h

        svg.extend([
            f'<line class="axis" x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy + panel_h}"/>',
            f'<line class="axis" x1="{ox}" y1="{oy + panel_h}" x2="{ox + panel_w}" y2="{oy + panel_h}"/>',
            f'<text x="{ox + panel_w/2}" y="{oy - 9}" font-size="13" font-weight="bold" text-anchor="middle">seed {row["seed"]} — profile {"VALID" if row["PROFILE_VALID"] else "INVALID"}</text>',
        ])
        for key, color in colors.items():
            points = " ".join(f"{px(point['offset']):.2f},{py(point[key]):.2f}" for point in data)
            svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>')
            if key == "Phi_reopt_gamma":
                for point in data:
                    svg.append(f'<circle cx="{px(point["offset"]):.2f}" cy="{py(point[key]):.2f}" r="2.6" fill="{color}"/>')
        for offset in [-0.04, 0.0, 0.04]:
            svg.append(f'<text x="{px(offset):.2f}" y="{oy + panel_h + 17}" font-size="10" text-anchor="middle">{offset:.2f}</text>')
        svg.append(f'<text x="{ox - 4}" y="{oy + 10}" font-size="9" text-anchor="end">{ymax:.3g}</text>')
        svg.append(f'<text x="{ox - 4}" y="{oy + panel_h}" font-size="9" text-anchor="end">{ymin:.3g}</text>')
    legend = [("Phi_frozen", "frozen"), ("Phi_SAEPS_quadratic", "SAEPS quadratic"), ("Phi_reopt_gamma", "reoptimized gamma")]
    for index, (key, label) in enumerate(legend):
        x0 = 735 + index * 100
        svg.append(f'<line x1="{x0}" y1="625" x2="{x0 + 22}" y2="625" stroke="{colors[key]}" stroke-width="3"/><text x="{x0 + 27}" y="629" font-size="10">{label}</text>')
    svg.extend(['<text x="525" y="642" font-size="10" text-anchor="middle">Invalid profile curves are diagnostic only; V5.2 scientific status remains NOT_SUPPORTED.</text>', '</svg>'])
    output = root / "paper_artifacts/v5/V5_BASELINE_CONSOLIDATION.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output
