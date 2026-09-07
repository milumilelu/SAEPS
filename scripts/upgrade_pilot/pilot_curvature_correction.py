#!/usr/bin/env python3
"""Matrix-only development pilot for the public SAEPS exact-block archive.

This is NOT a PINN trainer, production matrix-free implementation, or new
experimental evidence. It reads existing JSON blocks without modifying them.
The scalar first correction is already present in SAEPS/v35/second_order.py;
this pilot explores a shared-subspace response correction and its error identity.

Dependencies: Python >= 3.10, NumPy. Run --self-test before using an archive.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np

VERSION = "0.1-development"


def symmetric(a: np.ndarray) -> np.ndarray:
    return (a + a.T) / 2.0


def read_matrix(block: dict[str, Any], key: str) -> np.ndarray:
    a = np.asarray(block[key], dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError(f"{key}: expected a finite two-dimensional array")
    return a


def check_symmetry(a: np.ndarray, label: str, tol: float = 1e-8) -> None:
    if a.shape[0] != a.shape[1]:
        raise ValueError(f"{label}: not square")
    relative = np.linalg.norm(a - a.T) / max(np.linalg.norm(a), 1e-30)
    if relative > tol:
        raise ValueError(f"{label}: relative asymmetry {relative:.3e} > {tol}")


def quadratic_curvature(hll: np.ndarray, c: np.ndarray,
                        a: np.ndarray, z: np.ndarray) -> np.ndarray:
    return symmetric(hll - c.T @ z - z.T @ c + z.T @ a @ z)


def extend_basis(v: np.ndarray, w: np.ndarray, rank_tol: float) -> np.ndarray:
    """Two-pass reorthogonalization; column scaling is only a basis operation."""
    scale = np.linalg.norm(w, axis=0)
    keep = scale > np.finfo(float).tiny
    if not np.any(keep):
        return v
    w = w[:, keep] / scale[keep]
    for _ in range(2):
        w = w - v @ (v.T @ w)
    u, s, _ = np.linalg.svd(w, full_matrices=False)
    keep = s > rank_tol
    if not np.any(keep):
        return v
    new = u[:, keep]
    remaining = v.shape[0] - v.shape[1]
    if remaining <= 0:
        return v
    return np.column_stack((v, new[:, :remaining]))


def run_case(record: dict[str, Any], budgets: list[int],
             preconditioner: str = "gn-diagonal", floor: float = 1e-8,
             rank_tol: float = 1e-11, min_eig_rel: float = 1e-10,
             response_rtol: float = 1e-11) -> dict[str, Any]:
    if record.get("analysis_valid") is not True:
        return {"status": "SKIPPED_ORIGINAL_INVALID", "rows": [],
                "reason": record.get("failure_reason", "analysis_valid is not true")}
    g, h = record["GN_blocks"], record["exact_blocks"]
    gtt, b, gll = (read_matrix(g, key) for key in ("G_tt", "G_tl", "G_ll"))
    hkey = "H_tt_sym" if "H_tt_sym" in h else "H_tt"
    htt, c, hll = (read_matrix(h, key) for key in (hkey, "H_tl", "H_ll"))
    n, p = b.shape
    if gtt.shape != (n, n) or htt.shape != (n, n):
        raise ValueError("inconsistent state dimensions")
    if c.shape != (n, p) or hll.shape != (p, p) or gll.shape != (p, p):
        raise ValueError("inconsistent parameter dimensions")
    for label, matrix in (("G_tt", gtt), ("H_tt", htt), ("G_ll", gll), ("H_ll", hll)):
        check_symmetry(matrix, label)
    for blocks, name, expected in ((g, "G_lt", b.T), (h, "H_lt", c.T)):
        if name in blocks:
            stored = read_matrix(blocks, name)
            mismatch = np.linalg.norm(stored - expected) / max(np.linalg.norm(expected), 1e-30)
            if mismatch > 1e-8:
                raise ValueError(f"{name}: cross-block transpose mismatch {mismatch:.3e}")
    gamma = float(record["gamma"])
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError("gamma must be finite and positive")
    gtt, htt, gll, hll = map(symmetric, (gtt, htt, gll, hll))
    m = gtt + gamma * np.eye(n)
    a = htt + gamma * np.eye(n)
    eigenvalues = np.linalg.eigvalsh(a)
    spectral_scale = max(float(np.max(np.abs(eigenvalues))), np.finfo(float).tiny)
    minimum = float(eigenvalues[0])
    if minimum <= 0 or minimum / spectral_scale <= min_eig_rel:
        raise ValueError("damped exact state block fails the requested positive-definiteness gate")
    np.linalg.cholesky(m)
    np.linalg.cholesky(a)
    z0 = np.linalg.solve(m, b)
    zstar = np.linalg.solve(a, c)  # REFERENCE ONLY; never used to construct a candidate.
    reference = symmetric(hll - c.T @ zstar)
    gn = symmetric(gll - b.T @ z0)
    k0 = quadratic_curvature(hll, c, a, z0)
    d0 = c - a @ z0
    stt, stl, sll = htt - gtt, c - b, hll - gll
    first = symmetric(sll - stl.T @ z0 - z0.T @ stl + z0.T @ stt @ z0)
    denominator = float(np.linalg.norm(reference, "fro")) + floor
    gn_error = float(np.linalg.norm(gn - reference, "fro")) / denominator
    raw_error = float(np.linalg.norm(gll - reference, "fro")) / denominator
    original_saeps = record.get("rerun", {}).get("F_SAEPS")
    reproduction_error = None
    if p == 1 and isinstance(original_saeps, (int, float)):
        reproduction_error = abs(float(gn[0, 0]) - float(original_saeps)) / (abs(float(original_saeps)) + floor)
    diag = np.diag(m)
    if np.any(diag <= 0):
        raise ValueError("nonpositive GN preconditioner diagonal")

    def precondition(d: np.ndarray) -> np.ndarray:
        if preconditioner == "identity":
            return d.copy()
        if preconditioner == "gn-exact":
            return np.linalg.solve(m, d)  # Dense optimistic development control, not scalable evidence.
        return d / diag[:, None]

    rows: list[dict[str, Any]] = []
    v = np.empty((n, 0), dtype=np.float64)
    z = z0.copy()
    previous_k = k0.copy()
    max_positive_increment = 0.0
    stalled = False
    cscale = max(float(np.linalg.norm(c)), floor)
    for step in range(max(budgets) + 1):
        if step:
            defect = c - a @ z
            if np.linalg.norm(defect) <= response_rtol * cscale:
                stalled = True
            if not stalled:
                new_v = extend_basis(v, precondition(defect), rank_tol)
                if new_v.shape[1] == v.shape[1]:
                    stalled = True
                else:
                    v = new_v
                    projected_a = symmetric(v.T @ a @ v)
                    np.linalg.cholesky(projected_a)
                    y = np.linalg.solve(projected_a, v.T @ d0)
                    z = z0 + v @ y
        k = quadratic_curvature(hll, c, a, z)
        if step:
            max_positive_increment = max(max_positive_increment,
                                         float(np.linalg.eigvalsh(symmetric(k - previous_k))[-1]))
        previous_k = k
        if step not in budgets:
            continue
        defect = c - a @ z
        defect_energy = symmetric(defect.T @ np.linalg.solve(a, defect))  # Validation oracle only.
        gap = symmetric(k - reference)
        identity_residual = np.linalg.norm(gap - defect_energy, "fro")
        identity_scale = max(np.linalg.norm(k, "fro"), np.linalg.norm(reference, "fro"), floor)
        k_error = float(np.linalg.norm(gap, "fro")) / denominator
        rows.append({
            "step_budget": step, "basis_dimension": v.shape[1],
            "raw_relative_error": raw_error, "gn_relative_error": gn_error,
            "corrected_relative_error": k_error,
            "improved_over_gn": bool(k_error < gn_error),
            "gn_to_corrected_error_ratio": gn_error / max(k_error, np.finfo(float).tiny),
            "defect_relative_norm": float(np.linalg.norm(defect)) / cscale,
            "identity_relative_residual": float(identity_residual / identity_scale),
            "minimum_gap_eigenvalue": float(np.linalg.eigvalsh(gap)[0]),
            "maximum_positive_nested_increment_so_far": max_positive_increment,
            "dense_oracle_gap_spectral_norm": float(np.linalg.norm(defect_energy, 2)),
            "floating_point_mu_bound": float(np.linalg.norm(defect, 2)**2 / minimum),
            "reference_minimum_eigenvalue": float(np.linalg.eigvalsh(reference)[0]),
            "subspace_stalled_or_response_converged": stalled,
            "reference_scalar": float(reference[0, 0]) if p == 1 else None,
            "gn_scalar": float(gn[0, 0]) if p == 1 else None,
            "corrected_scalar": float(k[0, 0]) if p == 1 else None,
        })
    return {
        "status": "PILOT_COMPUTED", "rows": rows, "n_theta": n, "p": p,
        "gamma": gamma, "minimum_A_eigenvalue": minimum,
        "minimum_A_eigenvalue_relative": minimum / spectral_scale,
        "first_correction_identity_residual": float(np.linalg.norm(k0 - gn - first)),
        "gn_vs_archived_saeps_relative_difference": reproduction_error,
        "notes": ["Dense development pilot, not matrix-free timing evidence.",
                  "The spectral minimum and defect-energy oracle are validation-only.",
                  "p>1 errors here are unwhitened Frobenius errors, not manuscript Eq.37.",
                  "A new historical-data analysis is exploratory, not a fresh held-out result."]
    }


def synthetic_record(n: int, p: int, seed: int, affine: bool = False) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    j = rng.normal(size=(n + p + 5, n + p))
    g = j.T @ j + np.eye(n + p)
    h = g.copy()
    if not affine:
        q = rng.normal(size=(n + p, n + p))
        h = g + 0.06 * (q + q.T)
    return {"analysis_valid": True, "benchmark": "SYNTHETIC_TEST_ONLY", "seed": seed,
            "gamma": 0.2,
            "GN_blocks": {"G_tt": g[:n, :n].tolist(), "G_tl": g[:n, n:].tolist(), "G_ll": g[n:, n:].tolist()},
            "exact_blocks": {"H_tt_sym": h[:n, :n].tolist(), "H_tl": h[:n, n:].tolist(), "H_ll": h[n:, n:].tolist()}}


def self_test() -> dict[str, Any]:
    cases = 0
    for p in (1, 3):
        for seed in range(8):
            result = run_case(synthetic_record(12, p, seed), [0, 1, 3, 6, 12], "gn-exact")
            assert result["first_correction_identity_residual"] < 1e-9
            for row in result["rows"]:
                assert row["identity_relative_residual"] < 1e-10
                assert row["minimum_gap_eigenvalue"] > -1e-9
                assert row["maximum_positive_nested_increment_so_far"] < 1e-9
            assert result["rows"][-1]["corrected_relative_error"] < 1e-9
            cases += 1
    affine = run_case(synthetic_record(8, 2, 42, True), [0, 1, 3])
    assert affine["rows"][0]["gn_relative_error"] < 1e-12
    assert affine["rows"][0]["corrected_relative_error"] < 1e-12
    bad = synthetic_record(8, 1, 43)
    bad["exact_blocks"]["H_tt_sym"] = (-np.eye(8)).tolist()
    try:
        run_case(bad, [0])
    except ValueError:
        pass
    else:
        raise AssertionError("indefinite state block was not rejected")
    assert run_case({"analysis_valid": False}, [0])["status"] == "SKIPPED_ORIGINAL_INVALID"
    return {"status": "SYNTHETIC_TESTS_PASSED", "random_spd_cases": cases,
            "additional_checks": ["affine case", "indefinite-block rejection", "invalid-record retention"],
            "PINN_archive_executed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="Local SAEPS repository root")
    parser.add_argument("--output", type=Path, help="NEW output directory; must not already exist")
    parser.add_argument("--steps", default="0,1,3,5,10")
    parser.add_argument("--preconditioner", choices=("identity", "gn-diagonal", "gn-exact"), default="gn-diagonal")
    parser.add_argument("--min-eig-rel", type=float, default=1e-10)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        if args.repo is None:
            return 0
    if args.repo is None or args.output is None:
        parser.error("--repo and --output are required for archive analysis")
    budgets = sorted(set(int(x) for x in args.steps.split(",")) | {0})
    if min(budgets) < 0:
        parser.error("steps must be nonnegative")
    repo = args.repo.resolve()
    input_root = repo / "outputs/posthoc/exact_fixed_state_v3"
    inputs = sorted(input_root.glob("*/seed_*.json"))
    if not inputs:
        parser.error(f"No archive records found under {input_root}")
    output = args.output.resolve()
    if output == input_root or input_root in output.parents:
        parser.error("Output must not be inside the frozen input archive")
    if output.exists():
        parser.error("Output directory already exists; choose a new path to avoid overwriting evidence")
    output.mkdir(parents=True)
    all_records: list[dict[str, Any]] = []
    flat_rows: list[dict[str, Any]] = []
    input_hashes: dict[str, str] = {}
    for path in inputs:
        relative = str(path.relative_to(repo))
        payload = path.read_bytes()
        input_hashes[relative] = hashlib.sha256(payload).hexdigest()
        record: dict[str, Any] = {}
        try:
            record = json.loads(payload)
            result = run_case(record, budgets, args.preconditioner, min_eig_rel=args.min_eig_rel)
        except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as exc:
            result = {"status": "PILOT_FAILED", "reason": str(exc), "rows": []}
        result.update({"source": relative, "seed": record.get("seed"), "benchmark": record.get("benchmark", path.parent.name)})
        all_records.append(result)
        for row in result["rows"]:
            flat_rows.append({"source": relative, "benchmark": result["benchmark"], "seed": result["seed"], **row})
    summary: dict[str, Any] = {
        "planned_records": len(inputs),
        "computed_records": sum(r["status"] == "PILOT_COMPUTED" for r in all_records),
        "retained_skipped_or_failed_records": sum(r["status"] != "PILOT_COMPUTED" for r in all_records),
        "by_benchmark_and_budget": [],
        "classification": "EXPLORATORY_MATRIX_ONLY_DEVELOPMENT_PILOT"
    }
    for benchmark in sorted({r["benchmark"] for r in all_records}):
        for step in budgets:
            selected = [r for r in flat_rows if r["benchmark"] == benchmark and r["step_budget"] == step]
            if not selected:
                continue
            summary["by_benchmark_and_budget"].append({
                "benchmark": benchmark, "step_budget": step, "computed_n": len(selected),
                "median_gn_error": float(np.median([r["gn_relative_error"] for r in selected])),
                "median_corrected_error": float(np.median([r["corrected_relative_error"] for r in selected])),
                "improved_over_gn_n": sum(r["improved_over_gn"] for r in selected),
                "maximum_corrected_error": max(r["corrected_relative_error"] for r in selected)
            })
    manifest = {"script_version": VERSION, "python": platform.python_version(), "numpy": np.__version__,
                "preconditioner": args.preconditioner, "steps": budgets, "min_eig_rel": args.min_eig_rel,
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input_sha256": input_hashes,
                "warning": "No retraining; no production HVP timing; dense reference calculations are validation oracles."}
    for name, data in (("records.json", all_records), ("summary.json", summary), ("manifest.json", manifest)):
        (output / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    if flat_rows:
        with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flat_rows[0]))
            writer.writeheader()
            writer.writerows(flat_rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"New output written to: {output}")
    return 2 if any(r["status"] == "PILOT_FAILED" for r in all_records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
