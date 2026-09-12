#!/usr/bin/env python3
"""Independent algebraic checks for the SAEPS identifiability audit.

Requires NumPy only. This does NOT import SAEPS or train a PINN. These examples
check interpretations of finite-damping curvature and analytic heat-equation
sensitivities; they are not replacements for repository reproduction.

Run:
    python verify_identifiability_counterexamples.py --output counterexample_checks.json
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_COMMIT = "71fd3b025824f59146851f2ebfb5068e8cc9addb"


def reduced_curvature(a: np.ndarray, b: np.ndarray, gamma: float) -> np.ndarray:
    """B.T [I - A(A.T A + gamma I)^(-1)A.T] B, evaluated via a solve."""
    if a.ndim != 2 or b.ndim != 2 or a.shape[0] != b.shape[0]:
        raise ValueError("A and B must be matrices with equal row counts")
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError("gamma must be finite and strictly positive")
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise ValueError("All matrix entries must be finite")
    m = a.T @ a + gamma * np.eye(a.shape[1])
    f = b.T @ b - (b.T @ a) @ np.linalg.solve(m, a.T @ b)
    return 0.5 * (f + f.T)


def numerical_rank(matrix: np.ndarray, relative_tolerance: float = 1e-10) -> int:
    s = np.linalg.svd(matrix, compute_uv=False)
    if not len(s) or s[0] == 0:
        return 0
    return int(np.count_nonzero(s > relative_tolerance * s[0]))


def heat_observations(k: float, capacity: float, x: np.ndarray,
                      t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """C*T_t=k*T_xx; T(x,0)=sin(pi*x); T(0,t)=T(1,t)=0."""
    if k <= 0 or capacity <= 0:
        raise ValueError("k and heat capacity must be strictly positive")
    z = (k / capacity) * np.pi**2 * t
    decay = np.exp(-z)
    temperature = np.sin(np.pi * x) * decay
    flux = -k * np.pi * np.cos(np.pi * x) * decay
    return temperature, flux


def run_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    a = b = np.ones((1, 1), dtype=np.float64)

    # A perfectly flat *unanchored* parameter profile nevertheless has positive
    # finite-damping curvature. Here GN and exact anchored Hessian coincide.
    rows = []
    displacements = np.array([-2.0, -0.5, 0.0, 0.5, 2.0])
    for gamma in [1e-6, 1e-2, 1.0, 100.0]:
        computed = float(reduced_curvature(a, b, gamma)[0, 0])
        expected = gamma / (1.0 + gamma)
        np.testing.assert_allclose(computed, expected, rtol=1e-9, atol=1e-14)
        w = -displacements / (1.0 + gamma)
        profiled_anchor_loss = 0.5 * (w + displacements)**2 + 0.5 * gamma * w**2
        np.testing.assert_allclose(profiled_anchor_loss,
                                   0.5 * expected * displacements**2, atol=1e-14)
        assert computed > 0
        rows.append({"gamma": gamma, "finite_damping_curvature": computed,
                     "exact_anchored_curvature": expected,
                     "unanchored_profile_curvature": 0.0})
    checks["flat_profile_positive_damped_curvature"] = {"passed": True, "rows": rows}

    # Identical sets of representable functions; a fixed Euclidean anchor on
    # different nuisance coordinates defines a different regularization metric.
    gamma = 0.01
    rescaled = []
    for c in [0.1, 1.0, 10.0]:
        f = float(reduced_curvature(np.array([[c]]), b, gamma)[0, 0])
        np.testing.assert_allclose(f, gamma / (c*c + gamma), rtol=1e-9)
        # A covariantly transformed metric has gamma_z = gamma_w*c^2.
        covariant = float(reduced_curvature(np.array([[c]]), b, gamma*c*c)[0, 0])
        np.testing.assert_allclose(covariant, gamma / (1.0 + gamma), rtol=1e-9)
        rescaled.append({"coordinate_scale_c": c, "fixed_gamma_F": f,
                         "covariant_metric_F": covariant})
    checks["state_coordinate_dependence"] = {"passed": True, "rows": rescaled}

    # Positive diagonal entries and eta=1 do not identify individual parameters.
    correlated_b = np.array([[1.0, 1.0]])
    raw = correlated_b.T @ correlated_b
    f = reduced_curvature(np.zeros((1, 1)), correlated_b, 1.0)
    eta = np.diag(f) / np.diag(raw)
    assert numerical_rank(f) == 1
    np.testing.assert_allclose(eta, [1.0, 1.0])
    checks["diagonal_retention_does_not_imply_joint_identifiability"] = {
        "passed": True, "F": f.tolist(), "eta": eta.tolist(),
        "rank": numerical_rank(f), "null_direction": [1.0, -1.0]}

    # For gamma>0, P_gamma is positive definite, so ker(F_gamma)=ker(B).
    # Here B is entirely in the range of A: the undamped projected curvature is 0.
    rng = np.random.default_rng(20260912)
    a = rng.normal(size=(7, 3))
    c = rng.normal(size=(3, 2))
    b = a @ c
    p0 = np.eye(7) - a @ np.linalg.pinv(a)
    f0 = b.T @ p0 @ b
    assert np.linalg.norm(f0) < 1e-11
    ranks = []
    for gamma in [0.01, 1.0, 10.0]:
        f = reduced_curvature(a, b, gamma)
        assert numerical_rank(f) == numerical_rank(b) == 2
        assert np.min(np.linalg.eigvalsh(f)) > 0
        ranks.append({"gamma": gamma, "rank_B": numerical_rank(b),
                      "rank_F_gamma": numerical_rank(f),
                      "eigenvalues_F_gamma": np.linalg.eigvalsh(f).tolist()})
    checks["finite_damping_kernel_identity"] = {
        "passed": True, "undamped_F_frobenius_norm": float(np.linalg.norm(f0)),
        "rows": ranks}

    # Duplicating quadrature nodes with halved weights is not a new observation.
    f = reduced_curvature(a, b, 0.1)
    ad = np.vstack([a, a]) / np.sqrt(2.0)
    bd = np.vstack([b, b]) / np.sqrt(2.0)
    fd = reduced_curvature(ad, bd, 0.1)
    error = float(np.linalg.norm(f-fd))
    np.testing.assert_allclose(fd, f, rtol=1e-10, atol=1e-12)
    checks["normalized_collocation_duplication"] = {"passed": True, "F_difference_norm": error}

    # Analytic PDE case: temperature-only observations determine k/C, not k,C.
    k, capacity = 0.6, 1.2
    x, t = np.meshgrid(np.array([0.2, 0.4, 0.7]), np.array([0.02, 0.2, 0.5]))
    x, t = x.ravel(), t.ravel()
    temperature, flux = heat_observations(k, capacity, x, t)
    scaled_temperature, scaled_flux = heat_observations(2*k, 2*capacity, x, t)
    np.testing.assert_allclose(scaled_temperature, temperature, atol=1e-14)
    np.testing.assert_allclose(scaled_flux, 2*flux, atol=1e-14)
    z = (k/capacity)*np.pi**2*t
    st = np.column_stack([-z*temperature, z*temperature]) / 0.01
    sq = np.column_stack([flux*(1-z), flux*z]) / 0.05
    combined = np.vstack([st, sq])
    assert numerical_rank(st) == 1
    assert numerical_rank(combined) == 2
    np.testing.assert_allclose(st @ np.ones(2), 0.0, atol=1e-12)
    # Check analytic log-coordinate sensitivities with centered finite differences.
    h = 1e-6
    numeric_t, numeric_q = [], []
    for d in np.eye(2):
        plus = np.exp(np.log([k, capacity]) + h*d)
        minus = np.exp(np.log([k, capacity]) - h*d)
        tp, qp = heat_observations(*plus, x, t)
        tm, qm = heat_observations(*minus, x, t)
        numeric_t.append((tp-tm)/(2*h)/0.01)
        numeric_q.append((qp-qm)/(2*h)/0.05)
    np.testing.assert_allclose(np.array(numeric_t).T, st, rtol=1e-7, atol=1e-7)
    np.testing.assert_allclose(np.array(numeric_q).T, sq, rtol=1e-7, atol=1e-7)
    checks["heat_temperature_scale_symmetry_and_flux_intervention"] = {
        "passed": True, "k": k, "C": capacity, "alpha": k/capacity,
        "temperature_max_difference_under_common_scaling": float(np.max(np.abs(temperature-scaled_temperature))),
        "temperature_sensitivity_rank": numerical_rank(st),
        "temperature_plus_flux_sensitivity_rank": numerical_rank(combined),
        "temperature_singular_values": np.linalg.svd(st, compute_uv=False).tolist(),
        "temperature_plus_flux_singular_values": np.linalg.svd(combined, compute_uv=False).tolist(),
        "temperature_log_parameter_null_direction": (np.ones(2)/np.sqrt(2.0)).tolist(),
        "temperature_sigma": 0.01, "flux_sigma": 0.05,
        "scope": "Analytic observation-map check, not trained PINN results; known temperature BC/IC, no source."}

    # A complementary PDE case isolates STATE/parameter confounding: C is
    # known, but the initial sine amplitude is an unknown nuisance. At one
    # snapshot, a change in k is exactly compensated by a change in amplitude.
    xs = np.array([0.2, 0.4, 0.7])
    ts = np.full_like(xs, 0.2)
    temp_s, _ = heat_observations(k, capacity, xs, ts)
    zs = (k/capacity)*np.pi**2*ts
    single = np.column_stack([-zs*temp_s, temp_s])  # log k, log amplitude
    x2 = np.tile(xs, 2)
    t2 = np.repeat([0.08, 0.2], len(xs))
    temp_2, _ = heat_observations(k, capacity, x2, t2)
    z2 = (k/capacity)*np.pi**2*t2
    two = np.column_stack([-z2*temp_2, temp_2])
    assert numerical_rank(single) == 1
    assert numerical_rank(two) == 2
    alternate_k = 1.2
    alternate_amplitude = np.exp(((alternate_k-k)/capacity)*np.pi**2*0.2)
    alternate_temp, _ = heat_observations(alternate_k, capacity, xs, ts)
    np.testing.assert_allclose(alternate_amplitude*alternate_temp, temp_s, atol=1e-14)
    checks["heat_temperature_scale_symmetry_and_flux_intervention"]["unknown_initial_amplitude_subcase"] = {
        "single_snapshot_joint_sensitivity_rank": numerical_rank(single),
        "two_snapshot_joint_sensitivity_rank": numerical_rank(two),
        "alternative_k": alternate_k,
        "compensating_initial_amplitude": float(alternate_amplitude),
        "interpretation": "C known; initial amplitude is a profiled nuisance. One temperature snapshot cannot identify k; two distinct nondegenerate times can."}

    p1, p2 = 2.0, -2.0
    assert p1 != p2 and p1*p1 == p2*p2
    assert (2*p1)**2 > 0 and (2*p2)**2 > 0
    checks["local_information_does_not_rule_out_global_aliases"] = {
        "passed": True, "parameter_domain": "real numbers", "forward_map": "p**2",
        "parameter_pair": [p1, p2], "same_output": p1*p1,
        "local_GN_curvatures": [(2*p1)**2, (2*p2)**2]}

    return {"audit_date": "2026-09-12", "repository_commit_under_review": REPOSITORY_COMMIT,
            "execution_scope": "Independent NumPy algebra and analytic PDE checks; no repository tests or PINN training rerun.",
            "environment": {"python": platform.python_version(), "numpy": np.__version__},
            "number_of_checks": len(checks), "all_passed": all(v["passed"] for v in checks.values()),
            "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("counterexample_checks.json"))
    args = parser.parse_args()
    result = run_checks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"all_passed": result["all_passed"],
                      "number_of_checks": result["number_of_checks"],
                      "output": str(args.output.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
