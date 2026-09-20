"""Aggregate the isolated E7 rescue probes without changing the locked result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = ROOT / "experiments/paper_revision_20260916/outputs/heldout"
OUT = ROOT / "outputs/posthoc/paper_strengthening"
DOC = ROOT / "docs/paper_strengthening"
PROBES = [
    NAMESPACE / "e7_rescue_probe_30000_seed916101/e7_rescue_probe.json",
    NAMESPACE / "e7_rescue_probe_30000_seed916102/e7_rescue_probe.json",
    NAMESPACE / "e7_rescue_probe_30000_seed916103/e7_rescue_probe.json",
    NAMESPACE / "e7_rescue_probe_100000_seed916103_h003/e7_rescue_probe.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    records = [json.loads(path.read_text(encoding="utf-8")) for path in PROBES]
    summary = {
        "audit_type": "E7_RESCUE_PROBE_AGGREGATE",
        "historical_e7_unchanged": True,
        "probes": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "seed": record["seed"],
                "max_inner_iterations": record["max_inner_iterations"],
                "steps": record["steps"],
                "rows": record["rows"],
            }
            for path, record in zip(PROBES, records)
        ],
        "interpretation": {
            "budget_effect": "The 30000-step probes substantially reduce normalized gradients and give sub-3-percent Schur agreement at the tested scales for seeds 916101 and 916102.",
            "remaining_failure": "For seed 916103 at h=0.003, increasing the budget from 30000 to 100000 does not remove the approximately 15-percent discrepancy although both branch gradients are below 1e-8.",
            "claim_boundary": "These are development-only probes. They motivate a new predeclared rescue protocol but do not alter the original E7 0/21 stationarity or V5 1/5 profile verdicts.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e7_rescue_probe_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# E7 profile rescue probe report",
        "",
        "These probes are development-only and leave the locked E7 output unchanged.",
        "",
        "| Seed | Budget | Step | Maximum branch gradient | Relative Schur difference |",
        "|---:|---:|---:|---:|---:|",
    ]
    for record in summary["probes"]:
        grouped = {}
        for row in record["rows"]:
            grouped.setdefault(float(row["step"]), []).append(row)
        for step, rows in sorted(grouped.items(), reverse=True):
            lines.append(
                f"| {record['seed']} | {record['max_inner_iterations']} | {step:g} | "
                f"{max(float(row['normalized_full_penalty_gradient']) for row in rows):.3e} | "
                f"{float(rows[0]['relative_difference']):.4f} |"
            )
    lines += [
        "",
        "The 30000-step probes show that the original 1000-step budget was a real numerical limitation: seeds 916101 and 916102 reach sub-3-percent reference differences at the tested scales. The 916103 h=0.003 probe remains at 14.4% after 30000 steps and 15.5% after 100000 steps, even though both branch gradients are below 1e-8 in the longer run. This rules out a pure threshold explanation and points to finite-displacement branch, basin, or model-nonlinearity effects.",
        "",
        "The result supports a rescue protocol with separate solver stopping and profile-error certification. It does not support changing the historical 0/21 stationarity or 1/5 profile-valid verdict.",
        "",
        "Source records are listed in `outputs/posthoc/paper_strengthening/e7_rescue_probe_summary.json`.",
    ]
    (DOC / "E7_RESCUE_PROBE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"probes": len(PROBES), "output": str(OUT / "e7_rescue_probe_summary.json")}, indent=2))


if __name__ == "__main__":
    main()
