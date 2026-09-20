"""Build read-only audits for the two proposed pre-submission remediations.

The script does not modify locked results, rerun confirmation, or choose a new
scientific threshold.  It reads the archived E7 profile rows and P5 records and
writes machine-readable post-hoc audits plus short Markdown reports.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
E7 = ROOT / "experiments/paper_revision_20260916/outputs/heldout/e7/e7_profile_resolution.csv"
E7_SCOPE = ROOT / "experiments/paper_revision_20260916/outputs/heldout/e7/e7_scope_levels.json"
P5 = ROOT / "outputs/runs/p5_scalar/p5-scalar-s10-20260819T082303.440919+0000-ecf337e72926/records"
OUT = ROOT / "outputs/posthoc/paper_strengthening"
DOC = ROOT / "docs/paper_strengthening"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def gate_audit() -> dict:
    rows = list(csv.DictReader(E7.open(encoding="utf-8", newline="")))
    branch = {}
    for row in rows:
        key = (row["data_seed"], row["step"], row["side"])
        branch.setdefault(key, []).append(row)
    gradients = {
        key: min(float(row["normalized_full_penalty_gradient"]) for row in values)
        for key, values in branch.items()
    }
    steps = sorted({(seed, step) for seed, step, _ in gradients}, key=lambda x: (int(x[0]), -float(x[1])))
    thresholds = [1.0e-4, 1.0e-5, 1.0e-6, 1.0e-7, 1.0e-8, 1.0e-9, 1.0e-10, 1.0e-12]
    counts = {}
    for threshold in thresholds:
        branch_count = sum(value <= threshold for value in gradients.values())
        step_count = sum(
            gradients[(seed, step, "plus")] <= threshold
            and gradients[(seed, step, "minus")] <= threshold
            for seed, step in steps
        )
        counts[f"{threshold:.0e}"] = {
            "branch_pass": branch_count,
            "branch_total": len(gradients),
            "step_pass": step_count,
            "step_total": len(steps),
        }
    scope = json.loads(E7_SCOPE.read_text(encoding="utf-8"))
    return {
        "audit_type": "E7_GATE_SENSITIVITY_POSTHOC",
        "interpretation": "Threshold sensitivity only; no locked verdict is changed.",
        "source_sha256": {str(E7.relative_to(ROOT)): sha256(E7), str(E7_SCOPE.relative_to(ROOT)): sha256(E7_SCOPE)},
        "source_scope": scope,
        "threshold_counts": counts,
        "steps": [
            {
                "data_seed": seed,
                "step": float(step),
                "max_branch_gradient": max(
                    gradients[(seed, step, "plus")], gradients[(seed, step, "minus")]
                ),
            }
            for seed, step in steps
        ],
        "claim_boundary": (
            "A relaxed gradient threshold can classify numerical optimization as adequate, "
            "but it does not certify finite-displacement profile curvature. The h^-2 error "
            "budget and multiscale fit remain separate requirements."
        ),
    }


def classical_audit() -> dict:
    records = []
    for path in sorted(P5.glob("seed_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        classical = record.get("classical_profile")
        records.append(
            {
                "seed": record.get("seed"),
                "status": record.get("status"),
                "classical_status": classical.get("status") if classical else None,
                "classical_minimum": classical.get("minimum") if classical else None,
                "classical_curvature": classical.get("curvature") if classical else None,
                "classical_r_squared": classical.get("r_squared") if classical else None,
                "classical_normalized_rmse": classical.get("normalized_rmse") if classical else None,
                "profile_fit_status": (record.get("reoptimized_profile") or {}).get("fit_status"),
            }
        )
    valid = [row for row in records if row["classical_status"] == "PASS"]
    return {
        "audit_type": "P5_CLASSICAL_FORWARD_PROFILE_POSTHOC",
        "interpretation": "Classical profile registry; it is not a new confirmation gate.",
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in sorted(P5.glob("seed_*.json"))
        },
        "planned": len(records),
        "classical_profile_pass": len(valid),
        "classical_profile_total_with_record": len(valid),
        "classical_profile_medians": {
            key: statistics.median(float(row[key]) for row in valid)
            for key in (
                "classical_minimum",
                "classical_curvature",
                "classical_r_squared",
                "classical_normalized_rmse",
            )
        },
        "records": records,
        "claim_boundary": (
            "The classical forward profile supplies an independent conventional-state reference "
            "where available. It does not create an exact gamma=0 neural-state elimination target "
            "and does not by itself establish superiority over variable projection."
        ),
    }


def write_docs(gate: dict, classical: dict) -> None:
    gate_counts = gate["threshold_counts"]
    lines = [
        "# Profile gate sensitivity audit",
        "",
        "This is an aggregation-only audit. It does not alter the locked E7 verdict.",
        "",
        "| Normalized gradient threshold | Branches passing | Paired steps passing |",
        "|---:|---:|---:|",
    ]
    for threshold, count in gate_counts.items():
        lines.append(
            f"| `{threshold}` | {count['branch_pass']}/{count['branch_total']} | "
            f"{count['step_pass']}/{count['step_total']} |"
        )
    lines += [
        "",
        "The audit shows that the original (10^{-8}) requirement is the binding "
        "numerical gate, while (h^{-2}) amplification remains a separate profile-error "
        "requirement. A relaxed threshold is therefore a candidate for a new predeclared "
        "rescue protocol, not a retrospective reclassification.",
        "",
        f"Source: `{E7.relative_to(ROOT)}` (SHA256 `{gate['source_sha256'][str(E7.relative_to(ROOT))]}`).",
    ]
    (DOC / "PROFILE_GATE_SENSITIVITY_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    med = classical["classical_profile_medians"]
    lines = [
        "# Classical forward profile baseline audit",
        "",
        "This audit registers the classical profiles already present in P5 records. It is non-binding and does not alter P5 scientific status.",
        "",
        f"- Planned P5 records: {classical['planned']}",
        f"- Classical profile records with `PASS`: {classical['classical_profile_pass']}/{classical['planned']}",
        f"- Median classical minimum: `{med['classical_minimum']:.8g}`",
        f"- Median classical curvature: `{med['classical_curvature']:.8g}`",
        f"- Median classical (R^2): `{med['classical_r_squared']:.8g}`",
        f"- Median classical normalized RMSE: `{med['classical_normalized_rmse']:.8g}`",
        "",
        "The registry supports an independent conventional-state reference where available. It does not supply an exact gamma=0 neural-state target; that separate VP0/SVD analysis remains availability-limited by the 0/12 and 0/9 admissibility counts.",
        "",
        f"Source directory: `{P5.relative_to(ROOT)}`.",
    ]
    (DOC / "CLASSICAL_FORWARD_PROFILE_BASELINE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    gate = gate_audit()
    classical = classical_audit()
    write_json(OUT / "profile_gate_sensitivity.json", gate)
    write_json(OUT / "classical_forward_profile_baseline.json", classical)
    write_docs(gate, classical)
    print(json.dumps({"gate": gate["threshold_counts"], "classical": {k: classical[k] for k in ("planned", "classical_profile_pass")}}, indent=2))


if __name__ == "__main__":
    main()
