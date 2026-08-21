"""Locked planned-denominator aggregation for Allen--Cahn confirmation."""

from __future__ import annotations

import math
import statistics
from typing import Any

import numpy as np

from saeps.v36.pipeline import _spearman


def _sign_tail(wins: int, non_tied: int) -> float | None:
    if non_tied == 0:
        return None
    return sum(math.comb(non_tied, value) for value in range(wins, non_tied + 1)) / (2**non_tied)


def aggregate_allen_confirmation(
    records: list[dict[str, Any]], specification: dict[str, Any]
) -> dict[str, Any]:
    planned_seeds = [int(value) for value in specification["planned_seeds"]]
    if sorted(int(record["seed"]) for record in records) != planned_seeds:
        raise ValueError("record seeds do not match locked planned cohort")
    valid = [record for record in records if record["binding_valid"] and record["status"] == "PASS"]
    tolerance = float(specification["primary"]["tie_tolerance"])
    wins = sum(float(record["D"]) > tolerance for record in valid)
    losses = sum(float(record["D"]) < -tolerance for record in valid)
    ties = len(valid) - wins - losses
    differences = [float(record["D"]) for record in valid]
    sign_p = _sign_tail(wins, wins + losses)
    median_d = statistics.median(differences) if differences else None
    primary = specification["primary"]
    conditions = {
        "minimum_valid_pairs": len(valid) >= int(primary["minimum_valid_pairs"]),
        "planned_seed_wins": wins >= int(primary["planned_strict_wins_required"]),
        "positive_median_D": median_d is not None and median_d > 0.0,
        "exact_sign_test": sign_p is not None and sign_p <= float(primary["alpha"]),
    }
    e_saeps = [float(record["E_SAEPS"]) for record in valid]
    e_raw = [float(record["E_raw"]) for record in valid]
    indicators = [float(record["I_GN"]) for record in valid]
    threshold = float(specification["directional_indicator"]["threshold"])
    predicted = [value <= threshold for value in indicators]
    observed = [value <= threshold for value in e_saeps]
    profile_statuses = [record["statuses"]["profile_status"] for record in records]
    return {
        "schema_version": 1,
        "phase": specification["phase"],
        "scientific_status": "SUPPORTED" if all(conditions.values()) else "NOT_SUPPORTED",
        "primary_conditions": conditions,
        "planned": len(planned_seeds),
        "valid": len(valid),
        "invalid": len(planned_seeds) - len(valid),
        "strict_wins_out_of_planned": wins,
        "strict_losses": losses,
        "ties": ties,
        "sign_test_non_tied_denominator": wins + losses,
        "exact_one_sided_sign_p": sign_p,
        "median_D": median_d,
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in ["PASS", "CHECKPOINT_INVALID", "PROFILE_FAILURE", "SOLVER_FAILURE", "NUMERICAL_FAILURE"]
        },
        "secondary": {
            "E_SAEPS_all_valid": e_saeps,
            "E_SAEPS_median": statistics.median(e_saeps) if e_saeps else None,
            "E_SAEPS_q25": float(np.quantile(e_saeps, 0.25, method="linear")) if e_saeps else None,
            "E_SAEPS_q75": float(np.quantile(e_saeps, 0.75, method="linear")) if e_saeps else None,
            "E_SAEPS_IQR": float(np.quantile(e_saeps, 0.75) - np.quantile(e_saeps, 0.25)) if e_saeps else None,
            "E_SAEPS_range": [min(e_saeps), max(e_saeps)] if e_saeps else None,
            "E_SAEPS_within_5_percent_count": sum(value <= 0.05 for value in e_saeps),
            "E_raw_all_valid": e_raw,
            "profile_bridge_PASS": sum(value == "PASS" for value in profile_statuses),
            "profile_bridge_FAILURE": sum(value != "PASS" for value in profile_statuses),
        },
        "gn_indicator": {
            "threshold": threshold,
            "values": indicators,
            "accuracy": (
                sum(left == right for left, right in zip(predicted, observed)) / len(valid)
                if valid
                else None
            ),
            "spearman_with_E_SAEPS": _spearman(indicators, e_saeps),
            "median_absolute_calibration_error": (
                statistics.median(abs(left - right) for left, right in zip(indicators, e_saeps))
                if valid
                else None
            ),
        },
        "per_seed": [
            {
                "seed": record["seed"],
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "E_raw": record["E_raw"],
                "E_SAEPS": record["E_SAEPS"],
                "D": record["D"],
                "I_GN": record["I_GN"],
                "profile_status": record["statuses"]["profile_status"],
                "failure_reason": record["failure_reason"],
            }
            for record in records
        ],
    }

