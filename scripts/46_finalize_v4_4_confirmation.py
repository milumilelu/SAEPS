"""Generate v4.4 evidence solely from immutable raw and aggregate artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v44.result_validation import validate_v44_result


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    failed = json.loads((run / "failed_seeds.json").read_text(encoding="utf-8"))
    audit = validate_v44_result(root)
    if audit["status"] != "PASSED":
        raise RuntimeError("v4.4 result validation must pass before evidence generation")
    _write_json(
        root / "docs/evidence/v4_4_allen_confirmation.json",
        {"schema_version": 1, "summary": summary, "result_audit": audit},
    )
    secondary = summary["secondary"]
    indicator = summary["gn_indicator"]
    report = f"""# v4.4 Allen--Cahn External Confirmation Report

**Scientific status:** `{summary['scientific_status']}`  
**Planned / valid / invalid:** `{summary['planned']} / {summary['valid']} / {summary['invalid']}`  
**Strict wins in planned denominator:** `{summary['strict_wins_out_of_planned']}/10`

## Locked primary adjudication

All four preregistered conditions pass: minimum valid pairs `{summary['primary_conditions']['minimum_valid_pairs']}`, planned wins `{summary['primary_conditions']['planned_seed_wins']}`, positive median D `{summary['primary_conditions']['positive_median_D']}`, and exact one-sided sign test `{summary['primary_conditions']['exact_sign_test']}`. Median D is `{summary['median_D']:.12g}` and the exact one-sided p-value is `{summary['exact_one_sided_sign_p']:.12g}`.

The v4.4 external Allen--Cahn comparative claim is `SUPPORTED`: SAEPS is closer than raw fixed-state curvature to the exact finite-gamma reduced Hessian on all nine valid seeds. Seed 81 is center-invalid and remains a planned non-win.

## Secondary absolute accuracy and profile bridge

E_SAEPS median is `{secondary['E_SAEPS_median']:.6%}`, IQR `{secondary['E_SAEPS_IQR']:.6%}`, and range `{secondary['E_SAEPS_range'][0]:.6%}` to `{secondary['E_SAEPS_range'][1]:.6%}`. `{secondary['E_SAEPS_within_5_percent_count']}/9` valid seeds are within 5%. SAEPS therefore improves the comparative endpoint strongly but is not a uniformly accurate exact-Hessian surrogate.

The frozen GN indicator has classification accuracy `{indicator['accuracy']:.3f}`, Spearman association `{indicator['spearman_with_E_SAEPS']:.6f}`, and median absolute calibration error `{indicator['median_absolute_calibration_error']:.6f}` on nine valid seeds. This remains secondary, non-recalibrated evidence.

The gamma-matched nonlinear profile bridge passes only `{secondary['profile_bridge_PASS']}/10` planned seeds. It is nonbinding by protocol and does not change the curvature-primary result, but nonlinear-profile agreement is not established.

## Execution audit

All ten seed computations were performed exactly once. After the frozen aggregate summary was written, packaging attempted to hash an incorrect directory. The recorded recovery only hashed the already committed raw files at their actual paths and generated the missing manifest and failed-seed file. Independent raw-to-frozen-aggregate reproduction passes; no seed, raw value, threshold or status rule changed.

Raw manifest hash: `{audit['raw_records_sha256']}`. V4.4 is permanently closed and cannot be rerun.
"""
    (root / "docs/evidence/V4_4_ALLEN_CONFIRMATION_REPORT.md").write_text(
        report, encoding="utf-8", newline="\n"
    )
    lines = [
        "# v4.4 Failed or Invalid Seeds",
        "",
        "Every invalid planned seed remains a non-win; none was replaced or rerun.",
        "",
        "| Seed | Status | Reason |",
        "|---:|---|---|",
    ]
    lines.extend(
        f"| {row['seed']} | {row['status']} | {row['failure_reason']} |"
        for row in failed["failed"]
    )
    (root / "docs/evidence/V4_4_FAILED_SEEDS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
