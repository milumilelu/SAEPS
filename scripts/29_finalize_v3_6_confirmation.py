"""Generate v3.6 frozen evidence exclusively from immutable raw outputs."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v36.result_validation import validate_v3_6_result


def _write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run = root / "outputs/runs/v3_6_scalar_confirmation"
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    failed = json.loads((run / "failed_seeds.json").read_text(encoding="utf-8"))
    audit = validate_v3_6_result(root)
    evidence = {
        "schema_version": 1,
        "summary": summary,
        "result_audit": audit,
    }
    _write(root / "docs/evidence/v3_6_confirmation.json", evidence)

    counts = summary["status_counts"]
    report = f"""# v3.6 Scalar Confirmation Report

**Scientific status:** `{summary['scientific_status']}`  
**Execution status:** `PERMANENTLY_CLOSED_IMPLEMENTATION_FAILURE`  
**Planned / valid / invalid:** `{summary['planned']} / {summary['valid']} / {summary['invalid']}`

## Locked adjudication

All four frozen primary conditions are false. There are no valid pairs, no planned wins, no median D and no computable sign test. The locked result is therefore `NOT_SUPPORTED` because the minimum-valid-pair condition failed.

This result does **not** show that SAEPS is worse than raw curvature. The comparative hypothesis was not tested because no valid paired estimand was produced.

## Terminal statuses

- `PASS`: {counts['PASS']}
- `CHECKPOINT_INVALID`: {counts['CHECKPOINT_INVALID']}
- `SOLVER_FAILURE`: {counts['SOLVER_FAILURE']}
- `NUMERICAL_FAILURE`: {counts['NUMERICAL_FAILURE']}
- `PROFILE_FAILURE`: {counts['PROFILE_FAILURE']}

## Mandatory implementation finding

The read-only audit isolates a protocol-implementation defect on all 14 solver-failed seeds. The explicit augmented reference combined the parameter-curvature RHS with an excluded residual/score RHS and bound the maximum residual across both to the gate. For every affected seed, the parameter reference, selected two-pass scaled-LSQR residual and curvature agreement pass their frozen curvature thresholds; only the excluded score RHS exceeds the direct-reference threshold.

Because v3.6 is one-shot and the raw records do not contain all primary quantities for these failed seeds, no corrected v3.6 reaggregation or rerun is permitted. The failure classification is `implementation failure / numerical availability failure`, not comparative scientific failure.

## Permanent closure

Seeds 30--44 have exactly one terminal result each. The run is permanently closed. Any correction must use a new named `POST_CONFIRMATION_DEVELOPMENT` version with new seeds and a new untouched confirmation cohort.

Machine evidence: `docs/evidence/v3_6_confirmation.json`; raw manifest hash: `{audit['raw_records_sha256']}`.
"""
    (root / "docs/evidence/V3_6_CONFIRMATION_REPORT.md").write_text(
        report, encoding="utf-8", newline="\n"
    )
    failure_lines = [
        "# v3.6 Failed Seeds",
        "",
        "All entries are retained in the planned denominator. No seed was replaced or rerun.",
        "",
        "| Seed | Terminal status | Stage | Reason |",
        "|---:|---|---|---|",
    ]
    failure_lines.extend(
        f"| {row['seed']} | {row['status']} | {row['failure_stage']} | {row['failure_reason']} |"
        for row in failed["failed"]
    )
    (root / "docs/evidence/V3_6_FAILED_SEEDS.md").write_text(
        "\n".join(failure_lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)

