"""Build the final V5 evidence adjudication exclusively from frozen aggregates."""

from __future__ import annotations

import csv
import io
import json
import subprocess
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file


SOURCE_FILES = [
    "docs/evidence/v4_2_confirmation.json",
    "docs/evidence/v4_4_allen_confirmation.json",
    "docs/evidence/v4_5_controlled_confirmation.json",
    "docs/evidence/v4_7_scalability.json",
    "docs/evidence/v4_8_robustness.json",
    "docs/evidence/v4_final_audit.json",
    "docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.json",
    "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json",
    "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json",
    "docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.json",
    "docs/evidence/v5/V5_BASELINE_CONSOLIDATION.json",
]


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def build_final_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    burgers = _load(root, SOURCE_FILES[0])["summary"]
    allen = _load(root, SOURCE_FILES[1])["summary"]
    controlled = _load(root, SOURCE_FILES[2])["summary"]
    v4_scaling = _load(root, SOURCE_FILES[3])
    robustness = _load(root, SOURCE_FILES[4])
    gamma = _load(root, SOURCE_FILES[6])
    profile = _load(root, SOURCE_FILES[7])
    two = _load(root, SOURCE_FILES[8])
    residual_scaling = _load(root, SOURCE_FILES[9])
    baseline = _load(root, SOURCE_FILES[10])
    evidence = [
        {
            "evidence": "Burgers scalar comparative",
            "status": burgers["scientific_status"],
            "result": f"{burgers['strict_wins_out_of_planned_15']}/15 planned wins; {burgers['valid']}/{burgers['valid']} valid wins; median E_SAEPS={burgers['secondary']['E_SAEPS_median']:.6g}; p={burgers['exact_one_sided_sign_p']:.8g}",
            "claim_role": "PRIMARY_SUPPORTED",
        },
        {
            "evidence": "Allen-Cahn scalar replication",
            "status": allen["scientific_status"],
            "result": f"{allen['strict_wins_out_of_planned']}/10 planned wins; {allen['valid']}/{allen['valid']} valid wins; median E_SAEPS={allen['secondary']['E_SAEPS_median']:.6g}; p={allen['exact_one_sided_sign_p']:.8g}",
            "claim_role": "INDEPENDENT_REPLICATION_SUPPORTED",
        },
        {
            "evidence": "Noise/sparsity robustness",
            "status": "DESCRIPTIVE_WITH_EXACT_ANCHOR_SUPPORT",
            "result": f"{robustness['binding_valid']}/{robustness['planned']} binding-valid; {robustness['exact_anchors']['strict_SAEPS_wins']}/{robustness['exact_anchors']['binding_valid']} exact-anchor wins",
            "claim_role": "SECONDARY",
        },
        {
            "evidence": "Controlled tangent-overlap mechanism",
            "status": controlled["scientific_status"],
            "result": f"{controlled['monotonic_planned_seeds']}/10 planned monotonic; {controlled['valid']}/10 valid; valid median Spearman={controlled['median_valid_seed_spearman']:.6g}",
            "claim_role": "CONDITIONAL_ONLY",
        },
        {
            "evidence": "Finite-gamma family",
            "status": "DESCRIPTIVE_COMPLETE",
            "result": f"{gamma['terminal_count']}/42 terminal; {gamma['pass_count']}/42 numerical PASS; no nominal-gamma recalibration",
            "claim_role": "SENSITIVITY_AUDIT_NONBINDING",
        },
        {
            "evidence": "Nonlinear profile bridge",
            "status": profile["scientific_status"],
            "result": f"{profile['evaluable_count']}/5 evaluable; {profile['profile_valid_count']}/5 PROFILE_VALID",
            "claim_role": "CLAIM_DELETED",
        },
        {
            "evidence": "Two-parameter comparative geometry",
            "status": two["scientific_status"],
            "result": f"{two['binding_valid_count']}/10 valid; {two['planned_win_count']}/10 planned wins; valid sign p={two['one_sided_exact_sign_test_p']:.8g}",
            "claim_role": "DIRECTIONAL_EVIDENCE_NONBINDING",
        },
        {
            "evidence": "State-parameter scalability",
            "status": v4_scaling["status"],
            "result": "up to n_theta=100001; inherited function-preserving controlled checkpoint; cost-only",
            "claim_role": "ENGINEERING_COST",
        },
        {
            "evidence": "Residual-dimension scalability",
            "status": residual_scaling["engineering_status"],
            "result": f"{residual_scaling['pass_count']}/27 PASS; actual residuals m=213,853,3413; no exponent fit",
            "claim_role": "ENGINEERING_COST",
        },
        {
            "evidence": "Wide architecture",
            "status": "UNTESTED_DUE_INVALID_CENTERS",
            "result": "0/5 width32 center-valid in inherited V4.8",
            "claim_role": "LIMITATION",
        },
    ]
    claims = [
        {
            "claim": "SAEPS-GN is closer than raw fixed-state curvature to exact finite-gamma scalar reduced curvature on Burgers and Allen-Cahn.",
            "decision": "ALLOWED",
            "evidence": [SOURCE_FILES[0], SOURCE_FILES[1]],
        },
        {
            "claim": "SAEPS-GN exactly recovers the reduced Hessian.",
            "decision": "FORBIDDEN",
            "evidence": [SOURCE_FILES[0], SOURCE_FILES[1]],
        },
        {
            "claim": "SAEPS predicts the nonlinear reoptimized reduced objective curvature.",
            "decision": "FORBIDDEN",
            "evidence": [SOURCE_FILES[7], SOURCE_FILES[10]],
        },
        {
            "claim": "The full coupled multi-parameter comparative geometry is empirically supported.",
            "decision": "FORBIDDEN",
            "evidence": [SOURCE_FILES[8]],
        },
        {
            "claim": "All valid V5 two-parameter seeds favor SAEPS over raw.",
            "decision": "ALLOWED_WITH_PLANNED_DENOMINATOR_8_OF_10",
            "evidence": [SOURCE_FILES[8]],
        },
        {
            "claim": "Matrix-free execution is demonstrated to n_theta=100001 and real residual dimension m=3413.",
            "decision": "ALLOWED_AS_COST_ONLY",
            "evidence": [SOURCE_FILES[3], SOURCE_FILES[9]],
        },
    ]
    failures = [
        {"phase": "V5.1", "classification": "numerical", "planned": 42, "affected": 4, "decision": "retained; descriptive audit complete"},
        {"phase": "V5.2", "classification": "scientific", "planned": 5, "affected": 4, "decision": "NOT_SUPPORTED; nonlinear-profile claim deleted"},
        {"phase": "V5.3", "classification": "benchmark numerical availability", "planned": 10, "affected": 2, "decision": "INCONCLUSIVE; no replacements or rescue"},
        {"phase": "V5.4", "classification": "measurement limitation", "planned": 27, "affected": 27, "decision": "peak CPU tensor memory unavailable; all timing solves retained"},
    ]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    return {
        "schema_version": 1,
        "phase": "V5_6_FINAL_JCP_EVIDENCE_AUDIT",
        "audit_status": "PASSED_WITH_SCIENTIFIC_LIMITATIONS",
        "scientific_conclusion": "PARTIALLY_SUPPORTED",
        "paper_readiness": "CLAIM_NARROWING_REQUIRED",
        "recommended_scope": "scalar-focused finite-gamma local reduced-curvature methods paper",
        "full_general_JCP_claim_ready": False,
        "new_training_or_reconstruction_count": 29,
        "training_ceiling": 29,
        "audit_generation_parent_commit": head,
        "evidence_table": evidence,
        "claim_to_evidence": claims,
        "deviations_and_failures": failures,
        "baseline_consolidation_status": baseline["scientific_status_inherited"],
        "source_sha256": {relative: sha256_file(root / relative) for relative in SOURCE_FILES},
        "required_paper_actions": [
            "Lead with paired scalar comparative efficacy against exact finite-gamma reduced curvature.",
            "Report Burgers and Allen-Cahn absolute SAEPS errors; do not claim exact Hessian recovery.",
            "Delete nonlinear-profile-equivalence language and report V5.2 as NOT_SUPPORTED.",
            "Present two-parameter results as availability-limited directional evidence, not confirmation.",
            "Keep controlled mechanism, gamma family, robustness and scalability explicitly secondary or descriptive.",
            "State that wide-architecture curvature remains untested because frozen centers were invalid.",
        ],
        "further_scientific_execution_authorized": False,
    }


def final_report_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# SAEPS V5 Final JCP Evidence Audit Report",
        "",
        f"- Audit status: `{audit['audit_status']}`",
        f"- Scientific conclusion: `{audit['scientific_conclusion']}`",
        f"- Paper readiness: `{audit['paper_readiness']}`",
        f"- Recommended scope: **{audit['recommended_scope']}**",
        f"- New training/reconstruction: `{audit['new_training_or_reconstruction_count']}/{audit['training_ceiling']}`",
        "",
        "## Final evidence table",
        "",
        "| Evidence | Status | Result | Paper role |",
        "|---|---|---|---|",
    ]
    for row in audit["evidence_table"]:
        lines.append(f"| {row['evidence']} | `{row['status']}` | {row['result']} | `{row['claim_role']}` |")
    lines.extend([
        "",
        "## Final judgment",
        "",
        "V5 closes the planned execution program but does not close every scientific gap. The two independently confirmed scalar PDE results support the comparative claim that local neural-state elimination is substantially closer than frozen-state curvature to exact finite-damping reduced curvature. This is the strongest paper-facing result.",
        "",
        "The nonlinear profile bridge is not supported (1/5 valid). The coupled two-parameter result is inconclusive because only 8/10 planned seeds are valid, although all eight valid pairs favor SAEPS. Therefore the repository does not support claims of nonlinear-profile equivalence or empirically confirmed general multi-parameter geometry.",
        "",
        "A JCP manuscript is defensible only after narrowing the title, abstract, and conclusions to scalar finite-gamma local reduced curvature, with the two-parameter experiment reported as nonbinding directional evidence and the profile failure as a limitation. The full general claim is not ready.",
        "",
        "## Required claim edits",
        "",
    ])
    lines.extend(f"- {item}" for item in audit["required_paper_actions"])
    lines.extend([
        "",
        "## Deviations and retained failures",
        "",
        "| Phase | Classification | Planned | Affected | Resolution |",
        "|---|---|---:|---:|---|",
    ])
    for row in audit["deviations_and_failures"]:
        lines.append(f"| {row['phase']} | {row['classification']} | {row['planned']} | {row['affected']} | {row['decision']} |")
    return "\n".join(lines) + "\n"


def _csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def write_final_artifacts(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit = build_final_audit(root)
    write_json_atomic(root / "docs/evidence/v5_final_audit.json", audit)
    (root / "V5_FINAL_JCP_AUDIT_REPORT.md").write_text(final_report_markdown(audit), encoding="utf-8")
    artifact_root = root / "paper_artifacts/v5"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "V5_FINAL_EVIDENCE_TABLE.csv").write_text(_csv(audit["evidence_table"]), encoding="utf-8", newline="")
    claim_rows = [
        {"claim": row["claim"], "decision": row["decision"], "evidence": ";".join(row["evidence"])}
        for row in audit["claim_to_evidence"]
    ]
    (artifact_root / "V5_CLAIM_TO_EVIDENCE.csv").write_text(_csv(claim_rows), encoding="utf-8", newline="")
    artifact_paths = sorted(path for path in artifact_root.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest = {
        "schema_version": 1,
        "phase": "V5_6_SUBMISSION_PACKAGING",
        "artifacts": [
            {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in artifact_paths
        ],
    }
    write_json_atomic(artifact_root / "manifest.json", manifest)
    return audit
