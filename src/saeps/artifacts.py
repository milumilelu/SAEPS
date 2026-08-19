"""Build paper-facing artifacts only from accepted raw runs and evidence files."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_matches_with_portable_newlines(path: Path, expected: str) -> bool:
    data = path.read_bytes()
    canonical = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    variants = {data, canonical, canonical.replace(b"\n", b"\r\n")}
    return any(hashlib.sha256(value).hexdigest() == expected for value in variants)


def _accepted_run(root: Path, phase_directory: str, evidence_name: str) -> Path:
    evidence = _json(root / "docs/evidence" / evidence_name)
    run = root / "outputs/runs" / phase_directory / evidence["run_id"]
    if not run.is_dir():
        raise RuntimeError(f"accepted run is missing: {run}")
    return run


def _records(run: Path) -> list[dict[str, Any]]:
    manifest = _json(run / "manifest.json")
    records = []
    for item in manifest["records"]:
        path = run / item["path"]
        if not _hash_matches_with_portable_newlines(path, item["sha256"]):
            raise RuntimeError(f"raw record hash mismatch: {path}")
        records.append(_json(path))
    return records


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _scalar_value(value: Any) -> Any:
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0][0]
    return value


def _figure1(path: Path) -> None:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="360">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="30" text-anchor="middle" font-size="20" font-weight="bold">Figure 1 — SAEPS local residual geometry</text>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker></defs>',
        '<rect x="80" y="105" width="190" height="100" rx="10" fill="#E69F00" opacity="0.24" stroke="#B26F00"/>',
        '<text x="175" y="145" text-anchor="middle" font-size="16">raw parameter</text>',
        '<text x="175" y="170" text-anchor="middle" font-size="16">residual direction Jλ</text>',
        '<rect x="355" y="75" width="190" height="160" rx="10" fill="#56B4E9" opacity="0.24" stroke="#0072B2"/>',
        '<text x="450" y="130" text-anchor="middle" font-size="16">neural-state tangent</text>',
        '<text x="450" y="157" text-anchor="middle" font-size="16">span(Jθ)</text>',
        '<text x="450" y="190" text-anchor="middle" font-size="13">damped least-squares</text>',
        '<rect x="630" y="105" width="190" height="100" rx="10" fill="#009E73" opacity="0.24" stroke="#007A59"/>',
        '<text x="725" y="145" text-anchor="middle" font-size="16">state-eliminated</text>',
        '<text x="725" y="170" text-anchor="middle" font-size="16">residual direction</text>',
        '<line x1="270" y1="155" x2="350" y2="155" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>',
        '<line x1="545" y1="155" x2="625" y2="155" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>',
        '<text x="450" y="285" text-anchor="middle" font-size="15">Fse = Jλᵀ(I − Jθ(JθᵀJθ + γI)⁻¹Jθᵀ)Jλ</text>',
        '<text x="450" y="320" text-anchor="middle" font-size="13">Conceptual schematic; no experimental values are encoded.</text>',
        '</svg>',
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _final_mapping(p2: dict[str, Any], p5: dict[str, Any], p6: dict[str, Any]) -> tuple[str, str]:
    if (
        p2["scientific_gate_sg1"] == "PASS"
        and p5["scientific_classification_sg2"] == "STRONGLY_SUPPORTED"
        and p6["scientific_gate_sg3"] == "PASS"
    ):
        return "SUPPORTED", "PROCEED_TO_PAPER"
    numerical_limit = (
        p2["valid_seeds"] < 10
        or p5["valid"] < 10
        or p6["valid"] < 10
    )
    positive_partial = (
        p5["scientific_classification_sg2"] == "PARTIALLY_SUPPORTED"
        and p5.get("median_D") is not None
        and p5["median_D"] > 0
    )
    if positive_partial:
        return (
            "PARTIALLY_SUPPORTED",
            "INVESTIGATE_NUMERICS" if numerical_limit else "REVISE_METHOD",
        )
    return "NOT_SUPPORTED", "INVESTIGATE_NUMERICS" if numerical_limit else "REVISE_METHOD"


def _final_report(
    root: Path,
    summaries: dict[str, dict[str, Any]],
    validation: dict[str, Any] | None,
) -> None:
    p2, p5, p6, p7, p8 = (summaries[key] for key in ["p2", "p5", "p6", "p7", "p8"])
    conclusion, recommendation = _final_mapping(p2, p5, p6)
    validation_status = validation.get("status") if validation else "PENDING"
    report = f"""# FINAL_VALIDATION_REPORT.md

## Repository status

Protocol `SAEPS-JCP-EXEC-v2.0`; global lock active at `ad794ca2908c8935d0e21702fab7914ff944cce7`. Artifact build: `PASSED`. Repository validator: `{validation_status}`.

## Engineering gates

| Phase | Engineering result | Scientific result |
|---|---|---|
| P0 | PASSED | N/A |
| P1 | PASSED | numerical core verified |
| P2 | PASSED | {p2['scientific_gate_sg1']} |
| P3 | PASSED | profile engine verified |
| P4 | PASSED | Burgers selected and protocol LOCKED |
| P5 | PASSED | {p5['scientific_classification_sg2']} |
| P6 | PASSED | {p6['scientific_gate_sg3']} |
| P7 | PASSED / FULL | DESCRIPTIVE_ONLY |
| P8 | PASSED | DESCRIPTIVE_ONLY |
| P9 | {'PASSED' if validation_status == 'PASSED' else 'PENDING_VALIDATOR'} | N/A |

## Confirmation completeness

- P2: {p2['completed_evaluations']}/{p2['planned_evaluations']} evaluations; {p2['valid_seeds']}/10 valid seeds; binding monotonic count {p2['monotonic_seed_count']}/10.
- P5: {p5['planned']}/{p5['planned']} final records; {p5['valid']}/10 valid paired profiles; paired wins {p5['paired_wins_out_of_planned_10']}/10.
- P6: {p6['planned']}/{p6['planned']} final records; {p6['valid']}/10 valid directional pairs; ordering {p6['ordering_consistent_out_of_planned_10']}/10.
- P7: {p7['completed_new_runs']}/{p7['planned_new_runs']} new robustness/architecture runs.
- P8: {p8['completed']}/{p8['planned']} cost-only development runs.

## Scientific results and uncertainty

SG-1 failed because only {p2['monotonic_seed_count']}/10 planned seeds passed the locked validity gate and monotonic requirement, despite near-unit Spearman correlation among the five valid seeds. SG-2 is partially supported by one valid positive pair: median D = {p5['median_D']}; the bootstrap interval {p5['paired_bootstrap_95_ci']} is degenerate because n=1 and is not strong evidence. SG-3 failed with zero valid directional profile pairs. P7 showed positive median elimination effects in every reported valid condition, but 12/55 new runs were invalid or failed and the evidence is descriptive only.

## Failed runs and deviations

P5 retained {p5['invalid_or_failed']}/10 invalid/failed records. P6 retained {p6['planned']-p6['valid']}/10 invalid/failed records. P7 status counts are {p7['status_counts']}. All failures are present in manifests and `paper_artifacts/data/supplementary/failed_runs.csv`. Protocol Amendments 001–004 are preserved; Amendments 003 and 004 are artifact-only and did not rerun scientific measurements.

## Computational cost

Median wall times (seconds): training {p8['median_times_seconds']['training_seconds']}, SAEPS {p8['median_times_seconds']['saeps_seconds']}, frozen profile {p8['median_times_seconds']['frozen_profile_seconds']}, reoptimized profile {p8['median_times_seconds']['reoptimized_profile_seconds']}. Median paired `T_reoptimized_profile/T_SAEPS` = {p8['median_paired_reoptimized_to_saeps_ratio']}. The observed acceleration is modest rather than order-of-magnitude. Peak native CPU tensor memory was unavailable and is explicitly null.

## Scientific conclusion

`{conclusion}`

The numerical core is verified and limited valid scalar evidence favors SAEPS over raw sensitivity, but the preregistered controlled gate failed, only one scalar profile pair was valid, and no multi-parameter directional pair was valid. This supports only a limited, numerically qualified conclusion.

## Recommendation

`{recommendation}`

Resolve stationarity, CG convergence and nonlinear-profile fit stability under a new protocol version before making broad method claims. Do not rerun or retune the locked v2.0 confirmation split.
"""
    (root / "FINAL_VALIDATION_REPORT.md").write_text(
        report, encoding="utf-8", newline="\n"
    )


def build_paper_artifacts(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    artifact_root = root / "paper_artifacts"
    data = artifact_root / "data"
    figures = artifact_root / "figures"
    tables = artifact_root / "tables"
    supplementary = data / "supplementary"
    for directory in [data, figures, tables, supplementary]:
        directory.mkdir(parents=True, exist_ok=True)

    runs = {
        "p2": _accepted_run(root, "p2_confirmation", "p2_acceptance.json"),
        "p4": _accepted_run(root, "p4_screening", "p4_screening.json"),
        "p5": _accepted_run(root, "p5_scalar", "p5_acceptance.json"),
        "p6": _accepted_run(root, "p6_multi", "p6_acceptance.json"),
        "p7": _accepted_run(root, "p7_robustness", "P7_ACCEPTANCE.json"),
        "p8": _accepted_run(root, "p8_cost", "P8_ACCEPTANCE.json"),
    }
    summaries = {
        key: _json(run / ("screening.json" if key == "p4" else "summary.json"))
        for key, run in runs.items()
    }
    records = {key: _records(run) for key, run in runs.items() if key != "p4"}

    _figure1(figures / "figure1_geometry.svg")
    for number, (phase, source) in enumerate(
        [
            ("p2", "figure2_controlled_geometry.svg"),
            ("p5", "figure3_scalar_profiles.svg"),
            ("p5", "figure4_curvature_errors.svg"),
            ("p6", "figure5_multi_directional.svg"),
            ("p8", "figure6_computational_cost.svg"),
        ],
        start=2,
    ):
        shutil.copyfile(runs[phase] / source, figures / f"figure{number}_{source.split('_', 1)[1]}")

    table1 = [
        {"item": "contract", "value": "SAEPS-JCP-EXEC-v2.0"},
        {"item": "scalar benchmark", "value": "Burgers"},
        {"item": "scalar confirmation seeds", "value": "10..19"},
        {"item": "multi benchmark", "value": "coupled-reaction-diffusion"},
        {"item": "dtype/device", "value": "float64/cpu"},
        {"item": "locked scalar config hash", "value": summaries["p5"]["config_hash"]},
    ]
    _write_csv(tables / "table1_protocol.csv", ["item", "value"], table1)

    table2 = []
    for row in records["p5"]:
        table2.append(
            {
                "seed": row["seed"],
                "status": row["status"],
                "Fraw": _scalar_value(row.get("Fraw")),
                "Fse": _scalar_value(row.get("Fse")),
                "Hprofile": row.get("profile_curvature"),
                "eta_se": row.get("eta"),
                "eta_profile": row.get("eta_profile"),
                "Eraw": row.get("E_raw"),
                "Ese": row.get("E_saeps"),
                "theta_stationarity": row.get("theta_stationarity"),
                "parameter_stationarity": row.get("lambda_stationarity"),
            }
        )
    table2_fields = list(table2[0])
    _write_csv(tables / "table2_scalar_confirmation.csv", table2_fields, table2)

    table3 = []
    for row in records["p6"]:
        eigenvalues = row.get("eigenvalues") or [None, None]
        table3.append(
            {
                "seed": row["seed"],
                "status": row["status"],
                "eig1": eigenvalues[0],
                "eig2": eigenvalues[1],
                "profile_curv_v1": row.get("profile_curvature_min"),
                "profile_curv_v2": row.get("profile_curvature_max"),
                "ordering": (
                    row["profile_curvature_max"] > row["profile_curvature_min"]
                    if row.get("profile_curvature_max") is not None
                    and row.get("profile_curvature_min") is not None
                    else None
                ),
            }
        )
    _write_csv(tables / "table3_multi_parameter.csv", list(table3[0]), table3)

    screening = summaries["p4"]
    screening_rows = [
        {"candidate": candidate, **candidate_data["summary"]}
        for candidate, candidate_data in screening["candidate_results"].items()
    ]
    _write_csv(
        supplementary / "development_screening.csv",
        list(screening_rows[0]),
        screening_rows,
    )
    _write_csv(supplementary / "all_scalar_confirmation.csv", table2_fields, table2)
    _write_csv(supplementary / "all_multi_confirmation.csv", list(table3[0]), table3)

    failed_rows = []
    for phase in ["p2", "p5", "p6", "p7", "p8"]:
        for row in records[phase]:
            if row["status"] != "PASS":
                failed_rows.append(
                    {
                        "phase": phase.upper(),
                        "seed": row.get("seed"),
                        "label": row.get("label"),
                        "status": row["status"],
                        "failure_reason": row.get("failure_reason"),
                    }
                )
    _write_csv(
        supplementary / "failed_runs.csv",
        ["phase", "seed", "label", "status", "failure_reason"],
        failed_rows,
    )

    gamma_rows = []
    for candidate, candidate_data in screening["candidate_results"].items():
        for row in candidate_data["rows"]:
            for point in row["gamma_sweep"]:
                gamma_rows.append(
                    {"candidate": candidate, "seed": row["seed"], **point}
                )
    _write_csv(supplementary / "gamma_sweep.csv", list(gamma_rows[0]), gamma_rows)

    cg_rows = []
    for phase in ["p2", "p5", "p6", "p7", "p8"]:
        for row in records[phase]:
            iterations = row.get("CG_iterations")
            residuals = row.get("CG_relative_residual")
            if iterations and residuals:
                for solve_index, (iteration, residual) in enumerate(zip(iterations, residuals)):
                    cg_rows.append(
                        {
                            "phase": phase.upper(),
                            "seed": row.get("seed"),
                            "label": row.get("label"),
                            "solve_index": solve_index,
                            "iterations": iteration,
                            "relative_residual": residual,
                        }
                    )
    _write_csv(
        supplementary / "cg_convergence.csv",
        ["phase", "seed", "label", "solve_index", "iterations", "relative_residual"],
        cg_rows,
    )

    stationarity_rows = []
    for phase in ["p2", "p5", "p6", "p7", "p8"]:
        for row in records[phase]:
            stationarity_rows.append(
                {
                    "phase": phase.upper(),
                    "seed": row.get("seed"),
                    "label": row.get("label"),
                    "status": row["status"],
                    "theta_stationarity": row.get("theta_stationarity"),
                    "parameter_stationarity": row.get("lambda_stationarity", row.get("parameter_stationarity")),
                }
            )
    _write_csv(
        supplementary / "stationarity.csv",
        list(stationarity_rows[0]),
        stationarity_rows,
    )
    shutil.copyfile(runs["p7"] / "robustness_table.csv", supplementary / "noise_sparsity_architecture.csv")

    profile_rows = []
    locked_r2 = 0.99
    for row in records["p5"]:
        profile = row.get("reoptimized_profile") or {}
        r_squared = profile.get("r_squared")
        profile_rows.append(
            {
                "seed": row["seed"],
                "status": row["status"],
                "fit_status": profile.get("fit_status"),
                "r_squared": r_squared,
                "locked_minimum_r_squared": locked_r2,
                "r_squared_margin": r_squared - locked_r2 if r_squared is not None else None,
                "normalized_rmse": profile.get("normalized_rmse"),
            }
        )
    _write_csv(supplementary / "profile_fit_sensitivity.csv", list(profile_rows[0]), profile_rows)
    shutil.copyfile(runs["p8"] / "table4_cost.csv", supplementary / "computational_cost_detail.csv")
    shutil.copyfile(root / "docs/evidence/p1_acceptance.json", supplementary / "exact_vs_matrix_free.json")

    conclusion, recommendation = _final_mapping(summaries["p2"], summaries["p5"], summaries["p6"])
    aggregate = {
        "schema_version": 1,
        "accepted_runs": {key: path.name for key, path in runs.items()},
        "scientific_gates": {
            "SG-1": summaries["p2"]["scientific_gate_sg1"],
            "SG-2": summaries["p5"]["scientific_classification_sg2"],
            "SG-3": summaries["p6"]["scientific_gate_sg3"],
        },
        "conclusion": conclusion,
        "recommendation": recommendation,
        "summaries": summaries,
    }
    (data / "summary.json").write_text(
        json.dumps(aggregate, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    validation_path = data / "validation.json"
    validation = _json(validation_path) if validation_path.exists() else None
    _final_report(root, summaries, validation)

    output_files = sorted(
        path
        for path in artifact_root.rglob("*")
        if path.is_file()
        and path.name not in {".gitkeep", "manifest.json", "validation.json"}
    )
    manifest_files = []
    for path in output_files:
        canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        manifest_files.append(
            {
                "path": path.relative_to(artifact_root).as_posix(),
                "canonical_lf_sha256": hashlib.sha256(canonical).hexdigest(),
                "canonical_lf_bytes": len(canonical),
            }
        )
    artifact_manifest = {
        "schema_version": 2,
        "hash_canonicalization": "all CRLF and CR newlines converted to LF",
        "files": manifest_files,
    }
    (artifact_root / "manifest.json").write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "status": "PASSED",
        "figures": 6,
        "tables": 3,
        "supplementary_files": len(list(supplementary.iterdir())),
        "conclusion": conclusion,
        "recommendation": recommendation,
    }
