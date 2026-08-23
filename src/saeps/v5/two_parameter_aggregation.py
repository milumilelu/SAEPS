"""Aggregate and adjudicate V5.3C two-parameter confirmation."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.two_parameter_frozen import CONFIRMATION_SEEDS


def _one_sided_sign_pvalue(wins: int, non_tied: int) -> float:
    return sum(math.comb(non_tied, value) for value in range(wins, non_tied + 1)) / (
        2**non_tied
    )


def build_two_parameter_confirmation(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    records = []
    sources = []
    for seed in CONFIRMATION_SEEDS:
        path = root / f"outputs/runs/v5/two_parameter/confirmation/seed_{seed}/result.json"
        if not path.is_file():
            raise ValueError(f"missing V5.3C planned seed: {seed}")
        record = json.loads(path.read_text(encoding="utf-8"))
        records.append(record)
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    valid_records = [record for record in records if record["binding_valid"]]
    d_values = [float(record["primary"]["D2"]) for record in valid_records]
    wins = sum(value > 0.0 for value in d_values)
    ties = sum(abs(value) <= 0.0 for value in d_values)
    non_tied = len(d_values) - ties
    p_value = _one_sided_sign_pvalue(wins, non_tied) if non_tied else 1.0
    planned_wins = wins
    valid_count = len(valid_records)
    median_d = statistics.median(d_values) if d_values else None
    if valid_count < 9:
        scientific = "INCONCLUSIVE"
    elif (
        planned_wins >= 9
        and median_d is not None
        and median_d > 0.0
        and p_value <= 0.05
    ):
        scientific = "SUPPORTED"
    else:
        scientific = "NOT_SUPPORTED"
    seed_rows = []
    for record in records:
        primary = record["primary"] or {}
        geometry = record["generalized_geometry"] or {}
        seed_rows.append(
            {
                "seed": record["seed"],
                "terminal_status": record["status"],
                "binding_valid": record["binding_valid"],
                "planned_win": bool(record["binding_valid"] and primary.get("D2", 0.0) > 0.0),
                "E_raw2": primary.get("E_raw2"),
                "E_SAEPS2": primary.get("E_SAEPS2"),
                "D2": primary.get("D2"),
                "coupling": record["coupling"],
                "relative_eigengap": geometry.get("relative_eigengap"),
                "failure_stage": record["failure_stage"],
                "failure_reason": record["failure_reason"],
            }
        )
    return {
        "schema_version": 1,
        "phase": "V5_3C_TWO_PARAMETER_CONFIRMATION",
        "engineering_status": "PASSED" if len(records) == 10 else "FAILED",
        "scientific_status": scientific,
        "planned_denominator": 10,
        "terminal_count": len(records),
        "binding_valid_count": valid_count,
        "planned_win_count": planned_wins,
        "valid_median_D2": median_d,
        "valid_non_tied_count": non_tied,
        "valid_win_count": wins,
        "one_sided_exact_sign_test_p": p_value,
        "primary_gate": {
            "minimum_valid": 9,
            "minimum_planned_wins": 9,
            "median_D2_positive": True,
            "p_value_max": 0.05,
            "valid_gate_pass": valid_count >= 9,
            "planned_win_gate_pass": planned_wins >= 9,
            "median_gate_pass": median_d is not None and median_d > 0.0,
            "sign_test_gate_pass": p_value <= 0.05,
        },
        "generalized_geometry_role": "secondary_nonbinding_no_orientation_claim",
        "seed_rows": seed_rows,
        "source_records": sources,
    }


def write_two_parameter_confirmation_report(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    aggregate = build_two_parameter_confirmation(root)
    write_json_atomic(
        root / "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json",
        aggregate,
    )
    lines = [
        "# V5.3 Two-Parameter Confirmation Report",
        "",
        f"- Engineering status: `{aggregate['engineering_status']}`",
        f"- Scientific status: `{aggregate['scientific_status']}`",
        f"- Binding-valid: `{aggregate['binding_valid_count']}/10` (required >=9)",
        f"- Planned wins: `{aggregate['planned_win_count']}/10` (required >=9)",
        f"- Valid median D2: `{aggregate['valid_median_D2']:.6g}`",
        f"- One-sided exact sign test: `{aggregate['valid_win_count']}/{aggregate['valid_non_tied_count']}`, p=`{aggregate['one_sided_exact_sign_test_p']:.8g}`",
        "",
        "The direction of the comparison is positive for every valid seed, but the preregistered minimum-valid and planned-win gates fail because seeds219 and221 are checkpoint-invalid. The correct status is INCONCLUSIVE, not NOT_SUPPORTED.",
        "",
        "| Seed | Terminal | Valid | Planned win | E_raw2 | E_SAEPS2 | D2 | Coupling | Eigengap (nonbinding) |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate["seed_rows"]:
        def value(name: str) -> str:
            item = row[name]
            return "NA" if item is None else f"{item:.6g}"

        lines.append(
            f"| {row['seed']} | {row['terminal_status']} | {str(row['binding_valid']).lower()} | "
            f"{str(row['planned_win']).lower()} | {value('E_raw2')} | {value('E_SAEPS2')} | "
            f"{value('D2')} | {value('coupling')} | {value('relative_eigengap')} |"
        )
    (root / "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return aggregate


def write_two_parameter_figure(repo_root: str | Path, aggregate: dict[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    valid = [row for row in aggregate["seed_rows"] if row["binding_valid"]]
    width, height = 850, 440
    left, top, plot_w, plot_h = 75, 45, 700, 320
    maximum = max(row["E_raw2"] for row in valid) * 1.08

    def y(value: float) -> float:
        return top + plot_h - value / maximum * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#111827}.axis{stroke:#374151}.grid{stroke:#d1d5db;stroke-width:.7}</style>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>',
        f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>',
        '<text x="425" y="24" font-size="16" font-weight="bold" text-anchor="middle">V5.3C whitened matrix errors</text>',
    ]
    for index in range(6):
        value = maximum * index / 5
        py = y(value)
        svg.append(f'<line class="grid" x1="{left}" y1="{py:.2f}" x2="{left + plot_w}" y2="{py:.2f}"/>')
        svg.append(f'<text x="{left - 8}" y="{py + 4:.2f}" font-size="11" text-anchor="end">{value:.3g}</text>')
    group_width = plot_w / len(valid)
    for index, row in enumerate(valid):
        center = left + (index + 0.5) * group_width
        bar_width = group_width * 0.28
        for offset, key, color in [(-bar_width, "E_raw2", "#9ca3af"), (0.0, "E_SAEPS2", "#2563eb")]:
            py = y(row[key])
            svg.append(f'<rect x="{center + offset:.2f}" y="{py:.2f}" width="{bar_width:.2f}" height="{top + plot_h - py:.2f}" fill="{color}"/>')
        svg.append(f'<text x="{center:.2f}" y="{top + plot_h + 20}" font-size="11" text-anchor="middle">{row["seed"]}</text>')
    svg.extend(
        [
            '<rect x="600" y="392" width="13" height="13" fill="#9ca3af"/><text x="620" y="403" font-size="11">E_raw2</text>',
            '<rect x="680" y="392" width="13" height="13" fill="#2563eb"/><text x="700" y="403" font-size="11">E_SAEPS2</text>',
            '<text x="425" y="428" font-size="12" text-anchor="middle">Confirmation seed (invalid 219 and 221 omitted from numeric bars)</text>',
            '</svg>',
        ]
    )
    output = root / "paper_artifacts/v5/V5_TWO_PARAMETER_CONFIRMATION.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output
