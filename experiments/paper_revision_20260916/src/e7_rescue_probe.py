"""Bounded E7 rescue probe; never overwrites the locked E7 output.

This probe tests whether the original 1000-iteration budget was the binding
failure mode.  It keeps the original anchor, gamma, independent start and
parameter steps, and writes to a new output namespace.  It is development-only
and cannot change the historical E7 adjudication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import center_cache as C  # noqa: E402
import e3_saturation as E3  # noqa: E402
import e7_profile as E7  # noqa: E402
import repo_adapter as A  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-iterations", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=916101)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument("--steps", type=float, nargs="+", default=[0.01, 0.003, 0.001])
    args = parser.parse_args()
    torch.set_default_dtype(torch.float64)

    repo = A.repo_root().resolve()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    cache = (args.cache or (out / "centres")).resolve()
    protocol_path = HERE.parent / "protocol.yaml"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    e7 = protocol["E7"]
    config = E3.load_config(repo, A.resolve_commit(repo, A.DEFAULT_REF))
    budget = int(protocol["E3"]["optimizer_proposal"]["fixed_parameter_state_polish_max_iterations"])
    E7.MAX_INNER_ITERATIONS = int(args.max_iterations)

    fit = C.load_or_train(
        cache,
        config,
        E7.ARCHITECTURE,
        int(args.seed),
        int(e7["initialization_seed"]),
        float(e7["noise_level"]),
        budget,
    )
    context = E7.anchor_context(fit, config["gamma_alpha"], config["exact_hessian"])
    if context["reference"] is None:
        raise RuntimeError(f"anchor reference unavailable: {context['reference_status']}")

    lam0 = fit["lam"].detach().clone()
    anchor = {
        "theta": fit["theta"],
        "phi": float(E7.penalised(fit, fit["theta"], lam0, context["gamma"]).item()),
    }
    rows = []
    for step in args.steps:
        values = {}
        for sign in (1.0, -1.0):
            lam_value = lam0 + sign * step
            prediction = (anchor["theta"] + sign * step * context["state_direction"]).reshape(-1)
            started = time.perf_counter()
            result = E7.refine(fit, lam_value, prediction, context["gamma"], 1.0e-8)
            elapsed = time.perf_counter() - started
            values["plus" if sign > 0 else "minus"] = result
            rows.append(
                {
                    "seed": int(args.seed),
                    "step": step,
                    "side": "plus" if sign > 0 else "minus",
                    "max_iterations": int(args.max_iterations),
                    "iterations": result["iterations"],
                    "normalized_full_penalty_gradient": result["normalized_full_penalty_gradient"],
                    "max_abs_gradient": result["max_abs_gradient"],
                    "phi": result["phi"],
                    "displacement_from_anchor": result["displacement_from_anchor"],
                    "wall_seconds": elapsed,
                }
            )
        symmetric = (values["plus"]["phi"] - 2.0 * anchor["phi"] + values["minus"]["phi"]) / (step * step)
        relative = abs(symmetric - context["reference"]) / max(abs(context["reference"]), 1.0e-30)
        rows[-2]["symmetric_curvature"] = symmetric
        rows[-2]["reference"] = context["reference"]
        rows[-2]["relative_difference"] = relative
        rows[-1]["symmetric_curvature"] = symmetric
        rows[-1]["reference"] = context["reference"]
        rows[-1]["relative_difference"] = relative

    result = {
        "classification": "DEVELOPMENT_ONLY_RESCUE_PROBE",
        "historical_e7_output_untouched": True,
        "source_protocol_sha256": sha256(protocol_path),
        "source_code_sha256": sha256(HERE / "e7_profile.py"),
        "seed": int(args.seed),
        "steps": [float(step) for step in args.steps],
        "max_inner_iterations": int(args.max_iterations),
        "gradient_tolerance": 1.0e-8,
        "gamma": context["gamma"],
        "reference": context["reference"],
        "rows": rows,
        "claim_boundary": (
            "This probe tests budget sensitivity only. It is not confirmation and cannot "
            "change the original E7 0/21 stationarity verdict."
        ),
    }
    (out / "e7_rescue_probe.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "seed": result["seed"],
        "max_inner_iterations": result["max_inner_iterations"],
        "rows": [
            {
                "step": row["step"],
                "side": row["side"],
                "iterations": row["iterations"],
                "gradient": row["normalized_full_penalty_gradient"],
                "relative_difference": row.get("relative_difference"),
            }
            for row in rows
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
