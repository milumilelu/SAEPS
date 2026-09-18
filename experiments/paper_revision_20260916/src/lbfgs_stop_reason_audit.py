"""L-BFGS stop-reason audit.

Why this exists
---------------
PyTorch's L-BFGS runs two budgets, not one.  ``max_iter`` bounds accepted iterations and
``max_eval`` bounds function evaluations, and when ``max_eval`` is not passed it defaults
to ``max_iter * 5 // 4``.  The loop breaks on whichever is reached first, and that check
sits *before* the gradient and change tolerances.

The E2 refinement records therefore contain two different counters: ``inner_iterations_to_*``
(accepted iterations, ``n_iter``) and ``closure_calls_to_*`` (function evaluations).  A budget
flag derived only from ``n_iter >= max_iter`` reports "not exhausted" even when the
evaluation budget was the binding constraint and the run stopped there.

This script reconstructs, from the recorded counters and the installed source semantics,
which budget actually bound each run.  Where the records are insufficient it reports
UNKNOWN rather than guessing.  It also runs one instrumented reproduction of the current
configuration so the present-day behaviour is measured rather than assumed; that
reproduction is a new measurement and is labelled as such.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

E2_PATH = "outputs/posthoc/e2/e2_stationarity_path.csv"
E3_HELDOUT = "outputs/heldout/e3/e3_all_fits.csv"
E6_PATH = "outputs/development/e6/e6_architecture_accuracy.csv"
E7_PATH = "outputs/heldout/e7/e7_profile_resolution.csv"

LEVELS = ("1e-06", "1e-08", "1e-10")


def max_eval_for(max_iter: int) -> int:
    """The installed torch default: max_iter * 5 // 4."""
    return max_iter * 5 // 4


def classify(n_iter: int | None, closure_calls: int | None, max_iter: int) -> tuple[str, str]:
    """Return (binding_budget, stop_reason) from the recorded counters."""
    limit = max_eval_for(max_iter)
    if n_iter is None or closure_calls is None:
        return "UNKNOWN", "UNKNOWN"
    if closure_calls >= limit:
        return (
            "function_evaluation_budget",
            f"max_eval reached: {closure_calls} closure calls against max_eval={limit}, "
            f"while n_iter={n_iter} < max_iter={max_iter}",
        )
    if n_iter >= max_iter:
        return (
            "iteration_budget",
            f"max_iter reached: n_iter={n_iter} against max_iter={max_iter}",
        )
    return (
        "neither",
        f"stopped below both budgets (n_iter={n_iter} of {max_iter}, "
        f"closure calls={closure_calls} of {limit}); a tolerance or line-search condition "
        "terminated the run, which the records do not identify",
    )


def audit_e2(namespace: Path, max_iter: int) -> list[dict]:
    path = namespace / E2_PATH
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for level in LEVELS:
                n_iter = row.get(f"inner_iterations_to_{level}")
                closure = row.get(f"closure_calls_to_{level}")
                n_iter = int(n_iter) if n_iter not in (None, "") else None
                closure = int(closure) if closure not in (None, "") else None
                binding, reason = classify(n_iter, closure, max_iter)
                flagged = row.get(f"budget_exhausted_at_{level}")
                rows.append(
                    {
                        "task": "E2",
                        "unit": row.get("seed"),
                        "level": level,
                        "max_iter": max_iter,
                        "max_eval": max_eval_for(max_iter),
                        "recorded_n_iter": n_iter,
                        "recorded_closure_calls": closure,
                        "recorded_budget_exhausted_flag": flagged,
                        "binding_budget": binding,
                        "stop_reason": reason,
                        "flag_was_misleading": (
                            str(flagged).lower() == "false" and binding != "neither"
                        ),
                        "source_path": E2_PATH,
                    }
                )
    return rows


def audit_single_counter(namespace: Path, task: str, relative: str, column: str, max_iter: int) -> list[dict]:
    """Cohorts that recorded only accepted iterations cannot be classified."""
    path = namespace / relative
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            n_iter = row.get(column)
            n_iter = int(n_iter) if n_iter not in (None, "") else None
            rows.append(
                {
                    "task": task,
                    "unit": "|".join(
                        str(row.get(k, "")) for k in ("data_seed", "initialization_seed", "noise_level")
                    ),
                    "level": "",
                    "max_iter": max_iter,
                    "max_eval": max_eval_for(max_iter),
                    "recorded_n_iter": n_iter,
                    "recorded_closure_calls": None,
                    "recorded_budget_exhausted_flag": "",
                    "binding_budget": "UNKNOWN",
                    "stop_reason": (
                        "UNKNOWN: only accepted iterations were recorded, so the eval budget "
                        "cannot be checked against max_eval. Not reconstructed by re-running."
                    ),
                    "flag_was_misleading": False,
                    "source_path": relative,
                }
            )
    return rows


def instrumented_reproduction(repo: Path, config: dict, budget: int) -> dict:
    """Measure the present configuration's binding budget on a real centre.

    This is a new measurement, not a reconstruction of any past run.
    """
    import center_cache as C
    import torch

    cache = Path(__file__).resolve().parents[1] / "outputs/development/e6/centres"
    fit = C.load_or_train(cache, config, [2, 16, 1], 916101, 926001, 0.02, budget)
    theta = fit["theta"].detach().clone().requires_grad_(True)
    lam = fit["lam"].detach().clone()
    counter = {"calls": 0}
    optimizer = torch.optim.LBFGS(
        [theta], max_iter=budget, history_size=50,
        tolerance_grad=0.0, tolerance_change=0.0, line_search_fn="strong_wolfe",
    )

    def closure():
        counter["calls"] += 1
        optimizer.zero_grad(set_to_none=True)
        value = C.objective(theta, lam, fit["points"], fit["local"], fit["architecture"])
        value.backward()
        return value

    optimizer.step(closure)
    n_iter = int(optimizer.state[theta].get("n_iter", 0))
    func_evals = int(optimizer.state[theta].get("func_evals", 0))
    binding, reason = classify(n_iter, counter["calls"], budget)
    return {
        "label": "instrumented reproduction (new measurement, not a reconstruction)",
        "budget": budget,
        "max_eval": max_eval_for(budget),
        "n_iter": n_iter,
        "closure_calls": counter["calls"],
        "state_func_evals": func_evals,
        "binding_budget": binding,
        "stop_reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--instrument", action="store_true",
                        help="also run one instrumented reproduction (~1 h at the frozen budget)")
    args = parser.parse_args()

    import torch

    torch.set_default_dtype(torch.float64)
    repo = args.repo.resolve()
    namespace = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    e2_max_iter = 1000
    rows = audit_e2(namespace, e2_max_iter)
    rows += audit_single_counter(namespace, "E3", E3_HELDOUT, "polish_lbfgs_iterations", 100000)
    rows += audit_single_counter(namespace, "E6", E6_PATH, "polish_iterations", 100000)
    rows += audit_single_counter(namespace, "E7", E7_PATH, "iterations", 1000)

    fields = ["task", "unit", "level", "max_iter", "max_eval", "recorded_n_iter",
              "recorded_closure_calls", "recorded_budget_exhausted_flag",
              "binding_budget", "stop_reason", "flag_was_misleading", "source_path"]
    with (out / "lbfgs_stop_reason_audit.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    e2_rows = [r for r in rows if r["task"] == "E2"]
    reproduction = None
    if args.instrument:
        import e3_saturation as E3

        config = E3.load_config(repo, A.resolve_commit(repo))
        reproduction = instrumented_reproduction(repo, config, 1000)

    summary = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "lbfgs_stop_reason_audit",
        "torch_version": torch.__version__,
        "max_eval_rule": "torch LBFGS default max_eval = max_iter * 5 // 4 when not passed",
        "break_order": [
            "n_iter == max_iter",
            "current_evals >= max_eval",
            "gradient tolerance",
            "step/change tolerance",
            "function-change tolerance",
        ],
        "E2": {
            "records": len(e2_rows),
            "binding_function_evaluation_budget": sum(
                1 for r in e2_rows if r["binding_budget"] == "function_evaluation_budget"
            ),
            "binding_iteration_budget": sum(
                1 for r in e2_rows if r["binding_budget"] == "iteration_budget"
            ),
            "flags_misleading": sum(1 for r in e2_rows if r["flag_was_misleading"]),
        },
        "E3_E6_E7": {
            "records": sum(1 for r in rows if r["task"] != "E2"),
            "stop_reason": "UNKNOWN",
            "why": (
                "these cohorts recorded only accepted iterations, so the evaluation budget "
                "cannot be checked against max_eval from the saved output"
            ),
        },
        "instrumented_reproduction": reproduction,
        "correction": (
            "The E2 'budget_exhausted' flag was derived from n_iter >= max_iter only. It "
            "reported False while the evaluation budget was in fact the binding constraint, "
            "so the field must not be read as 'the optimisation converged'."
        ),
    }
    (out / "lbfgs_stop_reason_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(out)


if __name__ == "__main__":
    main()
