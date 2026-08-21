"""Current V4 evidence audit assembled from immutable machine-readable evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SOURCES = {
    "burgers": "docs/evidence/v4_2_confirmation.json",
    "allen": "docs/evidence/v4_4_allen_confirmation.json",
    "controlled": "docs/evidence/v4_5_controlled_confirmation.json",
    "two_parameter_engineering": "docs/evidence/v4_6_two_parameter_engineering.json",
    "two_parameter_heldout": "docs/evidence/v4_6_two_parameter_heldout.json",
    "scalability": "docs/evidence/v4_7_scalability.json",
    "robustness": "docs/evidence/v4_8_robustness.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_sources(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    data, hashes = {}, {}
    for name, relative in SOURCES.items():
        path = root / relative
        data[name] = json.loads(path.read_text(encoding="utf-8"))
        hashes[relative] = _sha256(path)
    return data, hashes


def audit_v4(root: Path) -> dict[str, Any]:
    root = root.resolve()
    data, hashes = _load_sources(root)
    burgers = data["burgers"]["summary"]
    allen = data["allen"]["summary"]
    controlled = data["controlled"]["summary"]
    two_engineering = data["two_parameter_engineering"]
    two_heldout = data["two_parameter_heldout"]
    scalability = data["scalability"]
    robustness = data["robustness"]
    untouched_two_parameter = not any(
        (root / "outputs/runs/v4_6_two_parameter" / role / f"seed_{seed}").exists()
        for role in ("confirmation", "heldout", "engineering") for seed in range(105, 115)
    )
    checks = {
        "all_sources_loaded_and_hashed": len(hashes) == len(SOURCES),
        "burgers_result_audit_passed": data["burgers"]["result_audit"]["status"] == "PASSED",
        "allen_result_audit_passed": data["allen"]["result_audit"]["status"] == "PASSED",
        "controlled_result_audit_passed": data["controlled"]["result_audit"]["status"] == "PASSED",
        "two_parameter_confirmation_untouched": untouched_two_parameter and not two_heldout["confirmation_authorized"],
        "scalability_integrity_passed": scalability["status"] == "PASSED" and all(scalability["checks"].values()),
        "robustness_integrity_passed": robustness["integrity_gate"] == "PASS" and robustness["planned"] == robustness["completed"] == 60,
    }
    if not all(checks.values()):
        raise RuntimeError(f"V4 final evidence audit failed: {checks}")
    return {
        "schema_version": 1,
        "phase": "V4_FINAL_EVIDENCE_AUDIT",
        "audit_status": "PASSED_WITH_SCIENTIFIC_LIMITATIONS",
        "scientific_conclusion": "PARTIALLY_SUPPORTED",
        "recommendation": "INVESTIGATE_NUMERICS",
        "paper_readiness": "NOT_READY_FOR_FULL_JCP_CLAIM",
        "checks": checks,
        "source_sha256": hashes,
        "results": {
            "burgers_scalar": {"status": burgers["scientific_status"], "planned": burgers["planned"], "valid": burgers["valid"],
                               "wins": burgers["strict_wins_out_of_planned_15"], "median_D": burgers["median_D"],
                               "median_E_SAEPS": burgers["secondary"]["E_SAEPS_median"], "sign_p": burgers["exact_one_sided_sign_p"]},
            "allen_scalar": {"status": allen["scientific_status"], "planned": allen["planned"], "valid": allen["valid"],
                             "wins": allen["strict_wins_out_of_planned"], "median_D": allen["median_D"],
                             "median_E_SAEPS": allen["secondary"]["E_SAEPS_median"], "sign_p": allen["exact_one_sided_sign_p"],
                             "profile_bridge_pass": allen["secondary"]["profile_bridge_PASS"]},
            "controlled_mechanism": {"status": controlled["scientific_status"], "planned": controlled["planned"],
                                     "valid": controlled["valid"], "planned_monotonic": controlled["monotonic_planned_seeds"],
                                     "valid_median_spearman": controlled["median_valid_seed_spearman"]},
            "two_parameter": {"engineering_status": two_engineering["status"], "heldout_status": two_heldout["status"],
                              "heldout_binding_valid": sum(row["binding_valid"] for row in two_heldout["rows"]),
                              "confirmation_authorized": False, "comparative_hypothesis_tested": False},
            "scalability": {"status": scalability["status"], "maximum_state_parameters": max(row["state_parameter_count"] for row in scalability["rows"]),
                            "largest_solve_seconds": scalability["rows"][-1]["solve_seconds"], "scope_limit": scalability["scope_limit"]},
            "robustness": {"planned": robustness["planned"], "binding_valid": robustness["binding_valid"],
                           "exact_anchor_valid": robustness["exact_anchors"]["binding_valid"],
                           "exact_anchor_wins": robustness["exact_anchors"]["strict_SAEPS_wins"],
                           "wide_architecture_valid": robustness["architecture"]["widths"]["architecture=wide"]["binding_valid"]},
        },
        "claim_boundary": [
            "Exact finite-gamma scalar reduced curvature is supported on Burgers and Allen-Cahn.",
            "SAEPS is a moderate-error Gauss-Newton surrogate, not an exact reduced-Hessian surrogate.",
            "The planned controlled-mechanism gate is not supported because center availability is 6/10.",
            "Two-parameter confirmation is not tested; wide-architecture curvature is not tested.",
            "Scalability evidence is cost-only on a function-preserving padded controlled checkpoint.",
        ],
    }


def render_report(audit: dict[str, Any]) -> str:
    r = audit["results"]
    b, a, c = r["burgers_scalar"], r["allen_scalar"], r["controlled_mechanism"]
    t, s, robust = r["two_parameter"], r["scalability"], r["robustness"]
    return f"""# V4 Final Evidence Audit Report

## Audit outcome

`{audit['audit_status']}`. Scientific conclusion: `{audit['scientific_conclusion']}`.
Recommendation: `{audit['recommendation']}`. Paper readiness:
`{audit['paper_readiness']}`.

All source JSON files were loaded and SHA256-recorded. The V4.2, V4.4 and
V4.5 permanent result audits pass; V4.6 confirmation seeds 105--114 remain
untouched; V4.7 and V4.8 integrity checks pass.

## Evidence ledger

| Node | Result | Planned/valid | Main quantitative evidence |
|---|---|---:|---|
| Burgers scalar V4.2 | {b['status']} | {b['planned']}/{b['valid']} | {b['wins']} planned wins; median D {b['median_D']:.4f}; median E_SAEPS {b['median_E_SAEPS']:.4f}; p={b['sign_p']:.6g} |
| Allen--Cahn scalar V4.4 | {a['status']} | {a['planned']}/{a['valid']} | {a['wins']} planned wins; median D {a['median_D']:.4f}; median E_SAEPS {a['median_E_SAEPS']:.4f}; p={a['sign_p']:.6g}; profile {a['profile_bridge_pass']}/{a['valid']} |
| Controlled mechanism V4.5 | {c['status']} | {c['planned']}/{c['valid']} | {c['planned_monotonic']} planned monotonic; valid median Spearman {c['valid_median_spearman']:.3f} |
| Two-parameter V4.6 | confirmation not tested | 2/{t['heldout_binding_valid']} held-out | engineering {t['engineering_status']}; held-out {t['heldout_status']} |
| Scalability V4.7 | {s['status']} | 5/5 | up to {s['maximum_state_parameters']} state parameters; largest solve {s['largest_solve_seconds']:.3f}s |
| Robustness V4.8 | descriptive | {robust['planned']}/{robust['binding_valid']} | exact anchors {robust['exact_anchor_wins']}/{robust['exact_anchor_valid']} wins; wide valid {robust['wide_architecture_valid']}/5 |

## Scientific judgment

The strongest reproducible result is narrow and specific: local state
elimination is dramatically closer than frozen-state curvature to the exact
finite-gamma scalar reduced Hessian on two PDEs and at the robustness anchor
cells. SAEPS still has non-negligible, PDE-dependent Gauss--Newton error: the
median relative error is about 7.5% on Burgers and 27.9% on Allen--Cahn, and
the Allen nonlinear-profile bridge passes only 1/9 valid seeds.

The full V4 claim is not established. The planned controlled gate is
`NOT_SUPPORTED` because only 6/10 centers are valid, despite perfect
monotonicity among valid seeds. Two-parameter confirmation was never
authorized after its held-out gate passed only 1/2. Width32 architecture has
0/5 valid centers, so its curvature hypothesis is untested. These are major
numerical-availability and scope limitations, not quantities that may be
removed from the denominator.

## Permissible claim

SAEPS captures most of the scalar state-adaptation reduction in tested local,
finite-damping settings and substantially improves on raw fixed-state
curvature, while retaining seed- and PDE-dependent Gauss--Newton error.

Do not claim universal controlled-mechanism validation, exact nonlinear-profile
equivalence, confirmed two-parameter geometry, or wide-architecture validity.
The next scientific work should address center availability and nonlinear
profile reliability under a new preregistered program; none of the closed V4
cohorts may be rerun or retuned.

## Source integrity

Machine-readable audit: `docs/evidence/v4_final_audit.json`. Every source hash
used by this report is stored in that file. This report does not supersede the
historical v2 `FINAL_VALIDATION_REPORT.md`.
"""
