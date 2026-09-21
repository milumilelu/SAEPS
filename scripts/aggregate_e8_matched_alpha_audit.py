"""Aggregate the small matched-alpha operator audit."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/posthoc/paper_strengthening/e8_matched_alpha_seed215"
OUT = ROOT / "outputs/posthoc/paper_strengthening/e8_matched_alpha_summary.json"
DOC = ROOT / "docs/paper_strengthening/E8_MATCHED_ALPHA_AUDIT.md"
CONFIG = ROOT / "configs/paper_strengthening/e8_matched_alpha_audit.yaml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows = list(csv.DictReader((RUN / "e8_matched_gamma_cost.csv").open(encoding="utf-8")))
    expected = {(str(alpha), method) for alpha in ["1e-08", "1e-06", "0.0001", "0.01"] for method in ["explicit", "CG", "scaled_LSQR"]}
    observed = {(row["alpha"], row["method"]) for row in rows}
    valid = [row for row in rows if row["status"] == "PASS"]
    summary = {
        "audit_type": "E8_MATCHED_ALPHA_OPERATOR_AUDIT",
        "historical_outputs_immutable": True,
        "planned_rows": len(expected),
        "observed_rows": len(rows),
        "pass_rows": len(valid),
        "complete_grid": observed == expected,
        "max_relative_residual": max(float(row["relative_residual"]) for row in rows),
        "max_accuracy_vs_dense_reference": max(float(row["accuracy_vs_dense_reference"]) for row in rows),
        "by_alpha": {},
        "source_sha256": sha256(RUN / "e8_matched_gamma_cost.csv"),
        "resource_manifest_sha256": sha256(RUN / "e8_resource_manifest.json"),
        "config_sha256": sha256(CONFIG),
        "claim_boundary": "Same-gamma dense/CG/LSQR agreement only; no large-network trained accuracy claim.",
    }
    for alpha in sorted({row["alpha"] for row in rows}, key=float):
        group = [row for row in rows if row["alpha"] == alpha]
        summary["by_alpha"][alpha] = {
            "rows": len(group),
            "pass": sum(row["status"] == "PASS" for row in group),
            "max_relative_residual": max(float(row["relative_residual"]) for row in group),
            "max_accuracy_vs_dense_reference": max(float(row["accuracy_vs_dense_reference"]) for row in group),
            "methods": {row["method"]: {"iterations": int(row["iterations"]), "reported_total_seconds": float(row["reported_total_seconds"])} for row in group},
        }
    OUT.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Matched-alpha operator audit",
        "",
        "A small, read-only operator audit at seed 215 evaluates explicit dense, matrix-free CG and scaled LSQR against the dense solve at the same gamma.",
        "",
        f"- grid completeness: {'PASS' if summary['complete_grid'] else 'FAIL'} ({summary['observed_rows']}/{summary['planned_rows']} rows)",
        f"- solver pass rows: {summary['pass_rows']}/{summary['observed_rows']}",
        f"- maximum relative residual: {summary['max_relative_residual']:.3e}",
        f"- maximum difference from dense reference: {summary['max_accuracy_vs_dense_reference']:.3e}",
        "",
        "| alpha | PASS | max residual | max dense difference |",
        "|---:|---:|---:|---:|",
    ]
    for alpha, values in summary["by_alpha"].items():
        lines.append(f"| {alpha} | {values['pass']}/{values['rows']} | {values['max_relative_residual']:.3e} | {values['max_accuracy_vs_dense_reference']:.3e} |")
    lines += [
        "",
        "The audit supports the narrower statement that the matrix-free operator agrees with the dense reference across the tested damping levels on this small coupled checkpoint. It does not convert the alpha=1e-2 large-state timing experiment into an alpha=1e-8 trained-accuracy result.",
        "",
        "Machine-readable lineage: `outputs/posthoc/paper_strengthening/e8_matched_alpha_summary.json`.",
    ]
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "pass": len(valid), "max_accuracy": summary["max_accuracy_vs_dense_reference"]}, indent=2))


if __name__ == "__main__":
    main()
