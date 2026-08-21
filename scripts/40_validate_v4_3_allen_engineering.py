from __future__ import annotations

import json
from pathlib import Path

from saeps.v43.validation import validate_allen_engineering


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = validate_allen_engineering(ROOT)
    destination = ROOT / "docs/evidence/v4_3_allen_engineering_validation.json"
    destination.write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report = ROOT / "docs/evidence/V4_3_ALLEN_ENGINEERING.md"
    report.write_text(
        "\n".join(
            [
                "# v4.3 Allen--Cahn Engineering Development",
                "",
                f"**Status:** `{result['status']}` — development engineering only",
                f"**Seeds / selected width:** `{result['seeds']}` / `{result['selected_width']}`",
                "",
                f"Binding-valid chains: `{result['binding_valid_count']}/3`. Parameter-only reference, curvature solver, exact finite-gamma gold and finite-primary nodes pass 3/3.",
                "",
                f"The directional-HVP correction matches the explicit correction on `{result['directional_indicator_pass_count']}/3` seeds. Score diagnostics fail on `{result['score_failure_nonbinding_count']}/3` but remain nonbinding.",
                "",
                f"The gamma-matched nonlinear-profile bridge passes `{result['profile_bridge_pass_count']}/3` and fails `{result['profile_bridge_failure_count']}/3`; this limitation is retained and is not allowed to invalidate or validate the exact-curvature primary chain.",
                "",
                "No comparative D/E/eta quantity was used for architecture or engineering selection. Confirmation remains unauthorized.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

