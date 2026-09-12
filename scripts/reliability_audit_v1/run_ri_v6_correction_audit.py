#!/usr/bin/env python3
"""Create the non-destructive RI-v6 P0 correction audit.

This audit exercises only deterministic algebra and interface checks.  It does
not retrain archived PINNs or alter outputs/reliability_audit_v1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from saeps.reliability_audit_v1.corrections import (
    SaepsOnlyInput,
    evaluate_refinement,
    normalized_heat_residual_from_parameters,
    normalized_quadrature_weights,
    weighted_residual_mean_square,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/ri_v6_correction_audit_v1"))
    args = parser.parse_args()
    out = args.output
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty audit directory: {out}")
    out.mkdir(parents=True, exist_ok=True)

    payload = {
        "observation": [1.0],
        "known_constants": {"pi": 3.141592653589793},
        "checkpoint": "development-only",
        "noise_sigma": 0.01,
        "residual_weights": {"data": 1.0, "pde": 1.0},
        "numerical_config": {"dtype": "float64"},
    }
    isolated = SaepsOnlyInput.from_mapping(payload)
    truth_rejected = False
    try:
        SaepsOnlyInput.from_mapping({**payload, "physical_truth": {"k": 0.6}})
    except TypeError:
        truth_rejected = True

    ut = torch.tensor([0.8, -0.3, 1.4], dtype=torch.float64)
    uxx = torch.tensor([-1.2, 0.9, -0.1], dtype=torch.float64)
    r1 = normalized_heat_residual_from_parameters(ut, uxx, 0.6, 1.2)
    r2 = normalized_heat_residual_from_parameters(ut, uxx, 0.006, 0.012)
    scale_invariant = bool(torch.allclose(r1, r2, rtol=1e-12, atol=1e-14))
    base = torch.tensor([1.0, 2.0], dtype=torch.float64)
    repeated = base.repeat_interleave(4)
    quadrature_invariant = bool(torch.isclose(
        weighted_residual_mean_square(base, normalized_quadrature_weights(2)),
        weighted_residual_mean_square(repeated, normalized_quadrature_weights(repeated.numel())),
    ))
    refinement = evaluate_refinement(0.1, 0.10015798093922381, noise_scale=0.01)

    # Independent finite-dimensional projection check for the F0 expression.
    rng = np.random.default_rng(20260912)
    jw = rng.normal(size=(4, 8))
    jp = rng.normal(size=(4, 1))
    u, _, _ = np.linalg.svd(jw, full_matrices=False)
    projected = jp - u @ (u.T @ jp)
    f0 = projected.T @ projected

    result = {
        "schema_version": 1,
        "audit_id": "ri_v6_correction_audit_v1",
        "baseline_commit": "ebdb494f9c9ff3f0c1c821d4723c28249fe4dcfd",
        "config_path": "configs/ri_v6_correction.yaml",
        "config_sha256": hashlib.sha256(Path("configs/ri_v6_correction.yaml").read_bytes()).hexdigest(),
        "scope": "P0 deterministic correction checks; no PINN retraining or confirmation",
        "old_output_namespace_preserved": True,
        "checks": {
            "saeps_only_truth_rejected": truth_rejected,
            "saeps_only_mode": isolated.mode.value,
            "common_scale_residual_invariant": scale_invariant,
            "normalized_quadrature_mass_invariant": quadrature_invariant,
            "f0_projection_norm": float(np.linalg.norm(projected)),
            "f0_value": float(f0[0, 0]),
            "refinement": refinement,
            "profile_status": "PROFILE_NOT_IMPLEMENTED",
        },
        "classification": {
            "oracle_input_defect": "CONFIRMED_IMPLEMENTATION_DEFECT",
            "bounded_closure_defect": "CONFIRMED_IMPLEMENTATION_DEFECT",
            "physical_residual_scale": "CONFIRMED_IMPLEMENTATION_DEFECT",
            "nonlinear_profile": "UNTESTED",
            "scientific_incremental_value": "INCONCLUSIVE",
        },
    }
    result["audit_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    (out / "RI_V6_CORRECTION_AUDIT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
