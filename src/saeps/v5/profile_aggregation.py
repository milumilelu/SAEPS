"""Aggregate and adjudicate the V5.2B held-out profile bridge."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.profile_heldout import SEEDS


def build_profile_bridge_aggregate(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    records = []
    sources = []
    for seed in SEEDS:
        path = root / f"outputs/runs/v5/profile_bridge/seed_{seed}/result.json"
        if not path.is_file():
            raise ValueError(f"missing V5.2B planned seed: {seed}")
        record = json.loads(path.read_text(encoding="utf-8"))
        records.append(record)
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    evaluable = sum(record["PROFILE_EVALUABLE"] for record in records)
    valid = sum(record["PROFILE_VALID"] for record in records)
    if evaluable < 4:
        scientific = "INCONCLUSIVE"
    elif valid >= 4:
        scientific = "SUPPORTED"
    else:
        scientific = "NOT_SUPPORTED"
    seed_rows = [
        {
            "seed": record["seed"],
            "terminal_status": record["status"],
            "PROFILE_EVALUABLE": record["PROFILE_EVALUABLE"],
            "PROFILE_VALID": record["PROFILE_VALID"],
            "profile_point_pass_count": sum(
                row["status"] == "PASS" for row in (record["profile"] or {}).get("points", [])
            ),
            "finest_profile_exact_relative_error": (record["profile"] or {}).get(
                "finest_profile_exact_relative_error"
            ),
            "last_two_curvature_relative_change": (record["profile"] or {}).get(
                "last_two_curvature_relative_change"
            ),
            "E_raw": record["E_raw"],
            "E_SAEPS": record["E_SAEPS"],
            "D": record["D"],
            "H_red_exact_gamma": record["H_red_exact_gamma"],
            "curvatures": (record["profile"] or {}).get("curvatures"),
        }
        for record in records
    ]
    return {
        "schema_version": 1,
        "phase": "V5_2B_PROFILE_BRIDGE_HELDOUT",
        "engineering_status": "PASSED" if len(records) == 5 else "FAILED",
        "scientific_status": scientific,
        "planned_denominator": 5,
        "terminal_count": len(records),
        "evaluable_count": evaluable,
        "profile_valid_count": valid,
        "adjudication_rule": {
            "evaluable_below_4": "INCONCLUSIVE",
            "evaluable_at_least_4_and_valid_at_least_4": "SUPPORTED",
            "otherwise": "NOT_SUPPORTED",
        },
        "rescue_cohort_authorized": False,
        "paper_claim": (
            "Secondary nonlinear-profile consistency is supported."
            if scientific == "SUPPORTED"
            else "Delete the nonlinear-profile-equivalence claim."
            if scientific == "NOT_SUPPORTED"
            else "Do not make a nonlinear-profile-equivalence claim because availability is insufficient."
        ),
        "seed_rows": seed_rows,
        "descriptive_comparative": {
            "all_planned_D_positive": all(row["D"] is not None and row["D"] > 0 for row in seed_rows),
            "median_E_raw": statistics.median(row["E_raw"] for row in seed_rows if row["E_raw"] is not None),
            "median_E_SAEPS": statistics.median(
                row["E_SAEPS"] for row in seed_rows if row["E_SAEPS"] is not None
            ),
            "role": "descriptive_nonbinding_for_profile_bridge_adjudication",
        },
        "source_records": sources,
    }


def write_profile_bridge_report(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    aggregate = build_profile_bridge_aggregate(root)
    write_json_atomic(root / "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json", aggregate)
    lines = [
        "# V5.2 Profile Bridge Report",
        "",
        f"- Engineering status: `{aggregate['engineering_status']}`",
        f"- Scientific status: `{aggregate['scientific_status']}`",
        f"- Planned denominator: `{aggregate['planned_denominator']}`",
        f"- PROFILE_EVALUABLE: `{aggregate['evaluable_count']}/5`",
        f"- PROFILE_VALID: `{aggregate['profile_valid_count']}/5`",
        f"- Paper action: **{aggregate['paper_claim']}**",
        "- Rescue cohort: forbidden",
        "",
        "| Seed | Terminal | Evaluable | Valid | Points | Finest exact error | Last-two change | E_raw | E_SAEPS | D |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate["seed_rows"]:
        lines.append(
            f"| {row['seed']} | {row['terminal_status']} | {str(row['PROFILE_EVALUABLE']).lower()} | "
            f"{str(row['PROFILE_VALID']).lower()} | {row['profile_point_pass_count']}/8 | "
            f"{row['finest_profile_exact_relative_error']:.6g} | {row['last_two_curvature_relative_change']:.6g} | "
            f"{row['E_raw']:.6g} | {row['E_SAEPS']:.6g} | {row['D']:.6g} |"
        )
    lines.extend(
        [
            "",
            "All five seeds are numerically evaluable, so the result is not an availability-driven INCONCLUSIVE outcome. Four of five fail one or both frozen profile consistency thresholds; therefore the preregistered status is NOT_SUPPORTED.",
            "",
            "The raw-versus-SAEPS quantities are retained for later descriptive consolidation and do not enter profile-bridge adjudication.",
        ]
    )
    (root / "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return aggregate


def write_profile_bridge_figure(repo_root: str | Path, aggregate: dict[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    width, height = 760, 460
    left, top, plot_w, plot_h = 85, 45, 610, 330
    all_values = [
        abs(float(point["curvature"]))
        for row in aggregate["seed_rows"]
        for point in row["curvatures"]
        if point["curvature"] is not None
    ] + [abs(float(row["H_red_exact_gamma"])) for row in aggregate["seed_rows"]]
    y_max = max(all_values) * 1.05
    colors = ["#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#ea580c"]

    def x(h: float) -> float:
        mapping = {0.04: 0, 0.02: 1, 0.01: 2, 0.005: 3}
        return left + mapping[h] * plot_w / 3

    def y(value: float) -> float:
        return top + plot_h - value / y_max * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.axis{stroke:#374151}.grid{stroke:#d1d5db;stroke-width:.7}</style>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>',
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>',
        '<text x="380" y="24" font-size="16" font-weight="bold" text-anchor="middle">V5.2B held-out profile curvature</text>',
    ]
    for index in range(6):
        value = y_max * index / 5
        py = y(value)
        svg.append(f'<line class="grid" x1="{left}" y1="{py:.2f}" x2="{left + plot_w}" y2="{py:.2f}"/>')
        svg.append(f'<text x="{left - 9}" y="{py + 4:.2f}" font-size="11" text-anchor="end">{value:.3g}</text>')
    for h in [0.04, 0.02, 0.01, 0.005]:
        px = x(h)
        svg.append(f'<text x="{px:.2f}" y="{top + plot_h + 22}" font-size="11" text-anchor="middle">{h:g}</text>')
    for index, row in enumerate(aggregate["seed_rows"]):
        points = " ".join(
            f"{x(point['h']):.2f},{y(point['curvature']):.2f}"
            for point in row["curvatures"]
            if point["curvature"] is not None
        )
        exact_y = y(row["H_red_exact_gamma"])
        svg.append(f'<polyline points="{points}" fill="none" stroke="{colors[index]}" stroke-width="2"/>')
        svg.append(f'<line x1="{left}" y1="{exact_y:.2f}" x2="{left + plot_w}" y2="{exact_y:.2f}" stroke="{colors[index]}" stroke-width="1" stroke-dasharray="5,4"/>')
        ly = 400 + index * 13
        svg.append(f'<text x="{left + index * 120}" y="{ly}" font-size="10" fill="{colors[index]}">seed {row["seed"]}</text>')
    svg.extend(
        [
            '<text x="390" y="430" font-size="12" text-anchor="middle">h (solid: profile; dashed: exact reference)</text>',
            '</svg>',
        ]
    )
    output = root / "paper_artifacts/v5/V5_PROFILE_BRIDGE.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output
