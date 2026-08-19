"""End-to-end repository validator for the SAEPS v2.0 execution contract."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from saeps.p5_confirmation import _bootstrap_interval


LOCK_COMMIT = "ad794ca2908c8935d0e21702fab7914ff944cce7"
LOCKED_HASHES = {
    "configs/locked/scalar.yaml": "cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8",
    "configs/locked/multi.yaml": "b985ccee5cf2daf5c40a4226a3e4bf8aa7c47e7dbbb3e4792e04c47a7082b9bb",
    "configs/locked/robustness.yaml": "058decc716579f7129157d61917eceb1a557273b7bfa57ef1b57e66c904a8859",
}
LEGAL_STATUSES = {
    "PASS",
    "CHECKPOINT_INVALID",
    "PROFILE_FAILURE",
    "SOLVER_FAILURE",
    "NUMERICAL_FAILURE",
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_matches_with_portable_newlines(path: Path, expected: str) -> bool:
    data = path.read_bytes()
    canonical = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    variants = {data, canonical, canonical.replace(b"\n", b"\r\n")}
    return any(hashlib.sha256(value).hexdigest() == expected for value in variants)


def _evidence_run(root: Path, phase: str, evidence: str) -> Path:
    run_id = _json(root / "docs/evidence" / evidence)["run_id"]
    return root / "outputs/runs" / phase / run_id


def _verify_manifest(run: Path) -> list[dict[str, Any]]:
    manifest = _json(run / "manifest.json")
    rows = []
    for item in manifest["records"]:
        path = run / item["path"]
        if not path.is_file():
            raise AssertionError(f"manifest path missing: {path}")
        if not _hash_matches_with_portable_newlines(path, item["sha256"]):
            raise AssertionError(f"manifest hash mismatch: {path}")
        row = _json(path)
        if row["status"] not in LEGAL_STATUSES:
            raise AssertionError(f"illegal status in {path}: {row['status']}")
        rows.append(row)
    return rows


def _same(left: float | None, right: float | None, tolerance: float = 1.0e-12) -> bool:
    if left is None or right is None:
        return left is right
    return abs(float(left) - float(right)) <= tolerance * max(abs(float(right)), 1.0)


def _run_check(checks: dict[str, Any], name: str, action: Callable[[], Any]) -> None:
    try:
        detail = action()
        checks[name] = {"status": "PASS", "detail": detail}
    except Exception as error:
        checks[name] = {
            "status": "FAIL",
            "detail": f"{type(error).__name__}: {error}",
        }


def validate_repository(
    repo_root: str | Path, *, write_output: bool = False
) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def tests() -> str:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)
        return completed.stdout.splitlines()[0]

    _run_check(checks, "unit_and_integration_tests", tests)

    def locked_configs() -> str:
        for relative, expected in LOCKED_HASHES.items():
            current = (root / relative).read_bytes()
            if hashlib.sha256(current).hexdigest() != expected:
                raise AssertionError(f"locked hash changed: {relative}")
            committed = subprocess.run(
                ["git", "show", f"{LOCK_COMMIT}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
            if current != committed:
                raise AssertionError(f"locked bytes differ from lock commit: {relative}")
        return "3 locked configs match recorded hashes and lock commit bytes"

    _run_check(checks, "locked_hashes_and_mutation", locked_configs)

    def load_runs() -> str:
        run_paths = {
            "p2": _evidence_run(root, "p2_confirmation", "p2_acceptance.json"),
            "p5": _evidence_run(root, "p5_scalar", "p5_acceptance.json"),
            "p6": _evidence_run(root, "p6_multi", "p6_acceptance.json"),
            "p7": _evidence_run(root, "p7_robustness", "P7_ACCEPTANCE.json"),
            "p8": _evidence_run(root, "p8_cost", "P8_ACCEPTANCE.json"),
        }
        state["paths"] = run_paths
        state["records"] = {phase: _verify_manifest(path) for phase, path in run_paths.items()}
        state["summaries"] = {phase: _json(path / "summary.json") for phase, path in run_paths.items()}
        return "all accepted run manifests and raw SHA-256 hashes verified"

    _run_check(checks, "raw_manifests", load_runs)

    def completeness() -> str:
        records = state["records"]
        if len(records["p2"]) != 50:
            raise AssertionError("P2 does not contain 50 records")
        p2_pairs = {(row["seed"], row["alpha"]) for row in records["p2"]}
        if len(p2_pairs) != 50 or {seed for seed, _ in p2_pairs} != set(range(10, 20)):
            raise AssertionError("P2 seed/alpha matrix is incomplete")
        if [len(records[key]) for key in ["p5", "p6", "p7", "p8"]] != [10, 10, 55, 3]:
            raise AssertionError("P5-P8 record counts are incomplete")
        if {row["seed"] for row in records["p5"]} != set(range(10, 20)):
            raise AssertionError("P5 seeds are incomplete")
        if {row["seed"] for row in records["p6"]} != set(range(10, 20)):
            raise AssertionError("P6 seeds are incomplete")
        return "P2=50, P5=10, P6=10, P7=55, P8=3"

    _run_check(checks, "seed_and_run_completeness", completeness)

    def aggregate_equality() -> str:
        records, summaries = state["records"], state["summaries"]
        for phase in ["p2", "p5", "p6", "p7", "p8"]:
            observed = Counter(row["status"] for row in records[phase])
            expected = Counter(summaries[phase]["status_counts"])
            for status, count in expected.items():
                if observed[status] != count:
                    raise AssertionError(f"{phase} aggregate mismatch for {status}")
        p5_valid = [row for row in records["p5"] if row["status"] == "PASS"]
        differences = [float(row["D_paired"]) for row in p5_valid]
        if not _same(statistics.median(differences), summaries["p5"]["median_D"]):
            raise AssertionError("P5 median D mismatch")
        return "status counts and P5 paired median reproduce from raw records"

    _run_check(checks, "raw_to_aggregate_equality", aggregate_equality)

    def bootstrap_lineage() -> str:
        records, summary = state["records"]["p5"], state["summaries"]["p5"]
        values = [float(row["D_paired"]) for row in records if row["status"] == "PASS"]
        locked = _json(root / "docs/evidence/p5_acceptance.json")
        import yaml

        scalar = yaml.safe_load((root / "configs/locked/scalar.yaml").read_text(encoding="utf-8"))
        interval = _bootstrap_interval(values, scalar["bootstrap"])
        if interval is None or not all(
            _same(value, expected)
            for value, expected in zip(interval, summary["paired_bootstrap_95_ci"])
        ):
            raise AssertionError("P5 bootstrap does not reproduce")
        if locked["paired_bootstrap_95_ci"] != summary["paired_bootstrap_95_ci"]:
            raise AssertionError("P5 evidence bootstrap differs from raw summary")
        return "10,000-resample paired percentile bootstrap reproduces exactly"

    _run_check(checks, "bootstrap_lineage", bootstrap_lineage)

    def cost_lineage() -> str:
        records, summary = state["records"]["p8"], state["summaries"]["p8"]
        for key, reported in summary["median_times_seconds"].items():
            if not _same(statistics.median(float(row[key]) for row in records if row.get(key) is not None), reported):
                raise AssertionError(f"cost median mismatch: {key}")
        paired = statistics.median(float(row["reoptimized_to_saeps_ratio"]) for row in records)
        if not _same(paired, summary["median_paired_reoptimized_to_saeps_ratio"]):
            raise AssertionError("paired cost ratio mismatch")
        counts = summary["aggregate_operation_counts"]
        if counts["median_JVP_count"] != statistics.median(row["JVP_count"] for row in records):
            raise AssertionError("JVP aggregate mismatch")
        if counts["median_VJP_count"] != statistics.median(row["VJP_count"] for row in records):
            raise AssertionError("VJP aggregate mismatch")
        return "times, paired ratio, CG/JVP/VJP lineage reproduce from raw records"

    _run_check(checks, "cost_lineage", cost_lineage)

    def provenance() -> str:
        for phase, summary in state["summaries"].items():
            info = summary["provenance"]
            required = ["git_commit", "git_dirty", "python_version", "packages", "dtype", "device", "processor"]
            if any(key not in info for key in required):
                raise AssertionError(f"{phase} provenance incomplete")
            if info["git_dirty"]:
                raise AssertionError(f"{phase} formal run used dirty worktree")
        return "P2 and P5-P8 formal summaries contain clean-commit environment provenance"

    _run_check(checks, "provenance_completeness", provenance)

    def artifacts() -> str:
        artifact_root = root / "paper_artifacts"
        manifest = _json(artifact_root / "manifest.json")
        for item in manifest["files"]:
            path = artifact_root / item["path"]
            if manifest["schema_version"] == 2:
                canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                if len(canonical) != item["canonical_lf_bytes"]:
                    raise AssertionError(f"paper artifact canonical size mismatch: {path}")
                if hashlib.sha256(canonical).hexdigest() != item["canonical_lf_sha256"]:
                    raise AssertionError(f"paper artifact canonical hash mismatch: {path}")
            elif not _hash_matches_with_portable_newlines(path, item["sha256"]):
                raise AssertionError(f"paper artifact hash mismatch: {path}")
        figures = sorted((artifact_root / "figures").glob("figure*.svg"))
        tables = sorted((artifact_root / "tables").glob("table*.csv"))
        if len(figures) != 6 or len(tables) != 3:
            raise AssertionError("expected exactly Figures 1-6 and Tables 1-3")
        for figure in figures:
            ET.parse(figure)
        expected_rows = {"table1_protocol.csv": 6, "table2_scalar_confirmation.csv": 10, "table3_multi_parameter.csv": 10}
        for table in tables:
            with table.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != expected_rows[table.name]:
                raise AssertionError(f"unexpected table row count: {table}")
        return "artifact manifest, 6 SVG figures and 3 CSV tables verified"

    _run_check(checks, "paper_artifacts", artifacts)

    def failed_reporting() -> str:
        raw_failed = [
            row
            for phase_records in state["records"].values()
            for row in phase_records
            if row["status"] != "PASS"
        ]
        path = root / "paper_artifacts/data/supplementary/failed_runs.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            reported = list(csv.DictReader(stream))
        if len(raw_failed) != len(reported):
            raise AssertionError(
                f"failed-run count mismatch: raw={len(raw_failed)} artifact={len(reported)}"
            )
        return f"all {len(raw_failed)} failed/invalid raw records are reported"

    _run_check(checks, "failed_run_reporting", failed_reporting)

    def scientific_gates() -> str:
        summaries = state["summaries"]
        observed = [
            summaries["p2"]["scientific_gate_sg1"],
            summaries["p5"]["scientific_classification_sg2"],
            summaries["p6"]["scientific_gate_sg3"],
        ]
        if observed != ["FAIL", "PARTIALLY_SUPPORTED", "FAIL"]:
            raise AssertionError(f"unexpected scientific gate lineage: {observed}")
        aggregate = _json(root / "paper_artifacts/data/summary.json")
        if aggregate["conclusion"] != "PARTIALLY_SUPPORTED" or aggregate["recommendation"] != "INVESTIGATE_NUMERICS":
            raise AssertionError("final mapping mismatch")
        report = (root / "FINAL_VALIDATION_REPORT.md").read_text(encoding="utf-8")
        for required in ["`PARTIALLY_SUPPORTED`", "`INVESTIGATE_NUMERICS`"]:
            if required not in report:
                raise AssertionError(f"final report missing {required}")
        return "scientific FAIL/PARTIAL results retained without causing engineering failure"

    _run_check(checks, "scientific_gate_and_final_mapping", scientific_gates)

    status = "PASSED" if all(check["status"] == "PASS" for check in checks.values()) else "FAILED"
    result = {
        "schema_version": 1,
        "phase": "P9",
        "status": status,
        "checks": checks,
        "scientific_failure_is_engineering_failure": False,
    }
    if write_output:
        destination = root / "paper_artifacts/data/validation.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return result
