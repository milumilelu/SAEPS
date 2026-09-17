"""Aggregate an E3 cohort at the protocol's statistical unit.

The independent unit is the observation data set, not the fit: two initializations of one
data seed are repeats inside that unit and must not be counted as two pieces of evidence.
This script therefore reports the per-fit rows first, then the median within each data
seed, then a summary across data seeds.  Denominators are printed with every rate and no
fit is dropped.

Both improvement ratios are reported, because they are different numbers:
    R1 = median E_raw / median E_SAEPS        (ratio of medians)
    R2 = median (E_raw / E_SAEPS)             (median of paired ratios)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

METRICS = ("E_raw", "E_SAEPS", "E_fix", "E_GN_fix", "E_relax")


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sign_test(wins: int, non_ties: int) -> float | None:
    if non_ties == 0:
        return None
    return sum(math.comb(non_ties, i) for i in range(wins, non_ties + 1)) / 2**non_ties


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fits", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)

    rows = load(args.fits)

    per_fit = []
    for row in rows:
        entry = {
            "data_seed": int(row["data_seed"]),
            "initialization_seed": int(row["initialization_seed"]),
            "noise_level": float(row["noise_level"]),
            "status": row["status"],
            "kappa_estimate": number(row.get("kappa_estimate")),
            "kappa_relative_error": number(row.get("parameter_relative_error")),
            "normalized_state_gradient": number(
                row.get("normalized_state_gradient_after_polish")
            ),
        }
        for metric in METRICS:
            entry[metric] = number(row.get(metric))
        if entry["E_raw"] is not None and entry["E_SAEPS"]:
            entry["paired_ratio"] = entry["E_raw"] / entry["E_SAEPS"]
            entry["SAEPS_wins"] = entry["E_SAEPS"] < entry["E_raw"]
        per_fit.append(entry)

    # Every later block must read the typed rows, not the raw CSV strings, or the
    # noise-level comparison and the win counts silently come out empty.
    valid = [e for e in per_fit if e["status"] == "PASS"]

    by_seed = {}
    for entry in per_fit:
        by_seed.setdefault(entry["data_seed"], []).append(entry)

    within = []
    for seed in sorted(by_seed):
        group = [e for e in by_seed[seed] if e["status"] == "PASS"]
        complete = len(group) == len(by_seed[seed])
        within.append(
            {
                "data_seed": seed,
                "fits_planned": len(by_seed[seed]),
                "fits_valid": len(group),
                "complete": complete,
                **{
                    f"median_{m}": statistics.median([e[m] for e in group])
                    if group and all(e[m] is not None for e in group)
                    else None
                    for m in METRICS
                },
                "wins": sum(1 for e in group if e.get("SAEPS_wins")),
                "median_kappa_relative_error": statistics.median(
                    [e["kappa_relative_error"] for e in group if e["kappa_relative_error"] is not None]
                )
                if group
                else None,
            }
        )

    complete_within = [w for w in within if w["complete"]]

    def across(metric: str):
        values = [w[f"median_{metric}"] for w in complete_within if w[f"median_{metric}"] is not None]
        return statistics.median(values) if values else None

    median_raw = across("E_raw")
    median_saeps = across("E_SAEPS")
    paired = [e["paired_ratio"] for e in valid if e.get("paired_ratio")]
    wins = sum(1 for e in valid if e.get("SAEPS_wins"))
    non_ties = sum(1 for e in valid if e["E_raw"] is not None and e["E_SAEPS"] is not None and e["E_raw"] != e["E_SAEPS"])

    by_noise = {}
    for level in sorted({e["noise_level"] for e in per_fit}):
        group = [e for e in valid if e["noise_level"] == level]
        by_noise[str(level)] = {
            "fits_valid": len(group),
            "median_E_raw": statistics.median([e["E_raw"] for e in group]),
            "median_E_SAEPS": statistics.median([e["E_SAEPS"] for e in group]),
            "wins": sum(1 for e in group if e.get("SAEPS_wins")),
        }

    document = {
        "classification": "NEW_EXPERIMENT_AGGREGATE",
        "task": "E3_aggregate",
        "cohort": args.label,
        "statistical_unit": "data_seed",
        "initializer_aggregation": "median_within_data_seed",
        "fits_planned": len(rows),
        "fits_valid": len(valid),
        "invalid_fits": [f"{e['data_seed']}/{e['initialization_seed']}/{e['noise_level']}" for e in per_fit if e["status"] != "PASS"],
        "data_seeds_planned": len(by_seed),
        "data_seeds_complete": len(complete_within),
        "across_data_seeds": {
            "median_E_raw": median_raw,
            "median_E_SAEPS": median_saeps,
            "median_E_fix": across("E_fix"),
            "median_E_GN_fix": across("E_GN_fix"),
            "median_E_relax": across("E_relax"),
            "ratio_of_medians_R1": (median_raw / median_saeps) if median_saeps else None,
            "median_paired_ratio_R2": statistics.median(paired) if paired else None,
            "wins": wins,
            "non_ties": non_ties,
            "one_sided_sign_test_p": sign_test(wins, non_ties),
            "median_kappa_relative_error": statistics.median(
                [w["median_kappa_relative_error"] for w in complete_within if w["median_kappa_relative_error"] is not None]
            ),
        },
        "by_noise_level": by_noise,
        "within_data_seed": within,
        "per_fit": per_fit,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, allow_nan=False)
        handle.write("\n")

    across_block = document["across_data_seeds"]
    print(f"{args.label}: {len(valid)}/{len(rows)} fits valid, {len(complete_within)}/{len(by_seed)} data seeds complete")
    print(f"  median E_raw  = {across_block['median_E_raw']:.6g}")
    print(f"  median E_SAEPS= {across_block['median_E_SAEPS']:.6g}")
    print(f"  R1 (ratio of medians)     = {across_block['ratio_of_medians_R1']:.6g}")
    print(f"  R2 (median paired ratio)  = {across_block['median_paired_ratio_R2']:.6g}")
    print(f"  wins {wins}/{non_ties}  sign-test p = {across_block['one_sided_sign_test_p']:.6g}")


if __name__ == "__main__":
    main()
