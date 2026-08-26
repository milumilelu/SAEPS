from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/posthoc/exact_fixed_state_v3"
SUMMARY = ROOT / "docs/evidence/posthoc_exact_fixed_state_v3.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v3_raw_manifest_hashes_and_denominators_are_exact() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["planned"] == 25
    assert manifest["original_binding_valid"] == 21
    assert manifest["reproduction_pass"] == 21
    assert manifest["analysis_valid"] == 21
    assert len(manifest["records"]) == 25
    for row in manifest["records"]:
        assert digest(OUTPUT / row["path"]) == row["sha256"]


def test_v3_artifact_hashes_match_canonical_committed_bytes() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["hash_basis"] == "SHA-256 of canonical committed Git blob bytes"
    for name, expected in manifest["artifacts"].items():
        if name == "hash_basis":
            continue
        relative = name if name.startswith("docs/") else f"outputs/posthoc/exact_fixed_state_v3/{name}"
        committed = subprocess.run(
            ["git", "show", f"e30f65df3b9321422439b5f28d99b157f14ae100:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(committed).hexdigest() == expected


def test_v3_statuses_reproduce_frozen_validity_without_replacements() -> None:
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(OUTPUT.glob("*/seed_*.json"))
    ]
    assert len(records) == 25
    invalid = {record["seed"] for record in records if not record["original_binding_valid"]}
    assert invalid == {57, 61, 63, 81}
    valid = [record for record in records if record["original_binding_valid"]]
    assert all(record["reproduction_status"] == "REPRODUCTION_PASS" for record in valid)
    assert all(record["numerical_status"] == "PASS" for record in valid)
    assert all(record["analysis_valid"] for record in valid)
    assert all(not record["analysis_valid"] for record in records if record["seed"] in invalid)
    assert all(record["decomposition"]["identity_relative_residual"] == 0.0 for record in valid)


def test_v3_aggregate_medians_rebuild_from_raw_records() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    for cohort in ("burgers", "allen_cahn"):
        records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((OUTPUT / cohort).glob("seed_*.json"))
        ]
        valid = [record for record in records if record["analysis_valid"]]
        for metric in (
            "E_raw",
            "E_SAEPS",
            "E_fix_exact_to_reduced",
            "E_GN_fix_native",
            "E_GN_fix_reduced_scale",
            "E_relax",
            "rho_relax",
            "R_freezing_to_GN",
        ):
            observed = statistics.median(float(record["metrics"][metric]) for record in valid)
            expected = summary["cohorts"][cohort]["metrics"][metric]["median"]
            assert observed == expected
        delta = statistics.median(
            float(record["GN_remainder_diagnostics"]["delta"]) for record in valid
        )
        assert delta == summary["cohorts"][cohort]["metrics"]["delta"]["median"]
