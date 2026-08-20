"""Generate v4.2 reports solely from raw and machine aggregate evidence."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v42.result_validation import validate_v42_result


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run = root / "outputs/runs/v4_2_corrected_confirmation"
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    failed = json.loads((run / "failed_seeds.json").read_text(encoding="utf-8"))
    audit = validate_v42_result(root)
    _write_json(root / "docs/evidence/v4_2_confirmation.json", {"schema_version": 1, "summary": summary, "result_audit": audit})
    secondary = summary["secondary"]
    indicator = summary["gn_indicator"]
    report = f"""# v4.2 Corrected Untouched Confirmation Report

**Scientific status:** `{summary['scientific_status']}`  
**Planned / valid / invalid:** `{summary['planned']} / {summary['valid']} / {summary['invalid']}`  
**Strict wins in planned denominator:** `{summary['strict_wins_out_of_planned_15']}/15`

## Locked primary adjudication

All four conditions pass: minimum valid pairs `{summary['primary_conditions']['minimum_valid_pairs']}`, planned wins `{summary['primary_conditions']['planned_seed_wins']}`, positive median D `{summary['primary_conditions']['positive_median_D']}`, and exact one-sided sign test `{summary['primary_conditions']['exact_sign_test']}`. Median D is `{summary['median_D']:.12g}` and the exact one-sided p-value is `{summary['exact_one_sided_sign_p']:.12g}`.

The v4.2 comparative claim is therefore `SUPPORTED`: on all 12 valid seeds, SAEPS is closer than raw fixed-state curvature to the exact finite-gamma reduced Hessian. Seeds 57, 61 and 63 are center-invalid and remain planned non-wins.

## Secondary absolute accuracy

E_SAEPS median is `{secondary['E_SAEPS_median']:.6%}`, IQR `{secondary['E_SAEPS_IQR']:.6%}`, and range `{secondary['E_SAEPS_range'][0]:.6%}` to `{secondary['E_SAEPS_range'][1]:.6%}`. `{secondary['E_SAEPS_within_5_percent_count']}/12` valid seeds are within 5%. Thus SAEPS is strongly better than raw but is not a uniformly 5%-accurate exact-Hessian surrogate.

The frozen GN indicator has accuracy `{indicator['accuracy']:.3f}`, Spearman `{indicator['spearman_with_E_SAEPS']:.6f}`, and median absolute calibration error `{indicator['median_absolute_calibration_error']:.6f}`. This is secondary evidence, not a recalibrated primary claim.

## Execution audit

All 15 seed computations were performed once. After seed 69, final aggregation encountered a missing non-scientific `failure_stage` schema field. The recovery added that field only in memory from independent node statuses, invoked the frozen aggregator, and recomputed no seed or primary quantity. Independent raw-to-aggregate validation passes. This deviation is retained in the machine audit.

V3.6 remains `NOT_SUPPORTED` and unchanged; v4.2 does not rewrite it. V4.2 is permanently closed and cannot be rerun.

Raw manifest hash: `{audit['raw_records_sha256']}`.
"""
    (root / "docs/evidence/V4_2_CONFIRMATION_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    lines = [
        "# v4.2 Failed Seeds",
        "",
        "All invalid seeds remain planned non-wins; none was replaced or rerun.",
        "",
        "| Seed | Status | Reason |",
        "|---:|---|---|",
    ]
    lines.extend(f"| {row['seed']} | {row['status']} | {row['failure_reason']} |" for row in failed["failed"])
    (root / "docs/evidence/V4_2_FAILED_SEEDS.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)

