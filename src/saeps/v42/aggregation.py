"""Frozen v4.2 paired aggregation."""

from __future__ import annotations

from typing import Any

from saeps.v36.pipeline import _aggregate


def aggregate_v42(records: list[dict[str, Any]], v42: dict[str, Any], v36: dict[str, Any]) -> dict[str, Any]:
    merged = dict(v36)
    merged["primary"] = v42["primary"]
    merged["secondary"] = v42["secondary"]
    merged["gn_indicator"] = {
        **v36["gn_indicator"],
        **v42["gn_indicator"],
    }
    result = _aggregate(records, merged)
    result["phase"] = "V4_2_CORRECTED_UNTOUCHED_CONFIRMATION"
    result["v3_6_result_modified"] = False
    return result

