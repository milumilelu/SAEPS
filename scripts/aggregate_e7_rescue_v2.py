"""Aggregate the fixed E7 rescue-v2 cohort without touching historical output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/posthoc/paper_strengthening"
DOC = ROOT / "docs/paper_strengthening"
RUNS = [
    OUT / "e7_rescue_v2_seed916101_final2",
    OUT / "e7_rescue_v2_seed916102_final2",
    OUT / "e7_rescue_v2_seed916103_final2",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    records = []
    for run in RUNS:
        summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
        branches = json.loads((run / "branch_results.json").read_text(encoding="utf-8"))
        starts = json.loads((run / "start_results.json").read_text(encoding="utf-8"))
        fits = json.loads((run / "multiscale_fits.json").read_text(encoding="utf-8"))
        records.append(
            {
                "path": str(run.relative_to(ROOT)),
                "summary_sha256": sha256(run / "summary.json"),
                "branch_sha256": sha256(run / "branch_results.json"),
                "start_sha256": sha256(run / "start_results.json"),
                "fit_sha256": sha256(run / "multiscale_fits.json"),
                "summary": summary,
                "branches": branches,
                "starts": starts,
                "fits": fits,
            }
        )

    planned = sum(len(record["branches"]) for record in records)
    valid_points = sum(
        sum(1 for branch in record["branches"] if branch.get("profile_point_valid"))
        for record in records
    )
    valid_profiles = sum(1 for record in records for fit in record["fits"] if fit.get("profile_valid"))
    fallback_count = sum(1 for record in records for row in record["starts"] if row.get("strict_raw_fallback_used"))
    positive_count = sum(1 for record in records for row in record["starts"] if row.get("positive_hessian"))
    start_count = sum(len(record["starts"]) for record in records)
    aggregate = {
        "audit_type": "E7_RESCUE_V2_AGGREGATE",
        "historical_e7_unchanged": True,
        "planned_centres": len(records),
        "planned_profile_points": planned,
        "profile_points_valid": valid_points,
        "profiles_valid": valid_profiles,
        "independent_start_records": start_count,
        "strict_raw_fallback_records": fallback_count,
        "positive_hessian_start_records": positive_count,
        "runs": records,
        "interpretation": {
            "solver": "The rescue separates the residual-normalised acceptance metric from LBFGS raw-gradient stopping and applies a safeguarded Newton polish. A strict raw-gradient fallback is used only when the normal path cannot produce the predeclared local certificate.",
            "scientific_result": "The corrected solver establishes high-precision stationary points for some branches, but no centre satisfies the complete three-scale profile certificate. Failures are retained as basin/positive-Hessian or finite-displacement limitations; the historical E7 and V5 verdicts are unchanged.",
            "claim_boundary": "Development-only rescue evidence. It supports a numerical-consistency diagnosis at selected finite steps, not a retrospective nonlinear-profile equivalence claim.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    (OUT / "e7_rescue_v2_summary.json").write_text(json.dumps(aggregate, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "# E7 corrected profile rescue v2",
        "",
        "This is a new development-only rescue cohort. The locked E7 output and V5 profile bridge are unchanged.",
        "",
        f"- planned centres: {len(records)}",
        f"- planned profile points: {planned}",
        f"- profile points passing the full stationarity/Hessian/start-agreement certificate: {valid_points}/{planned}",
        f"- centres passing the fixed three-scale h^2 profile certificate: {valid_profiles}/{len(records)}",
        f"- independent start records: {start_count}; positive-Hessian records: {positive_count}; strict raw fallbacks: {fallback_count}",
        "",
        "| Centre | Valid points | h² intercept | R² | Intercept relative error | Profile certificate |",
        "|---:|---:|---:|---:|---:|:---:|",
    ]
    for record in records:
        seed = record["summary"].get("fit_rows", [{}])[0].get("data_seed", "?")
        valid = sum(1 for branch in record["branches"] if branch.get("profile_point_valid"))
        fit = record["fits"][0]
        if "intercept" in fit:
            lines.append(
                f"| {seed} | {valid}/3 | {fit['intercept']:.6g} | {fit['r2']:.3f} | {fit['relative_error_to_reference']:.3f} | {'PASS' if fit.get('profile_valid') else 'FAIL'} |"
            )
        else:
            lines.append(f"| {seed} | {valid}/3 | — | — | — | FAIL ({fit.get('status')}) |")
    lines += [
        "",
        "The corrected numerical path removes the old raw-vs-normalised tolerance mismatch and certifies the objective error where the damped state Hessian is positive. It does not restore the profile claim: 916101 has three numerically certified points but an h² extrapolation R² of about 0.40 and a 12% intercept discrepancy; 916102 has an independent-start/basin failure at one scale; 916103 has no fully certified point because the displaced solves do not reach a positive-Hessian stationary branch from both starts.",
        "",
        "This result is evidence about the failure mechanism and the limits of finite-displacement interpretation. It does not reclassify the original 0/21 stationarity or 1/5 profile verdict.",
        "",
        "Machine-readable lineage: `outputs/posthoc/paper_strengthening/e7_rescue_v2_summary.json`.",
    ]
    (DOC / "E7_RESCUE_V2_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"planned": planned, "valid_points": valid_points, "valid_profiles": valid_profiles}, indent=2))


if __name__ == "__main__":
    main()
