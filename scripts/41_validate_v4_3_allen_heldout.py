from __future__ import annotations

import json
from pathlib import Path

from saeps.v43.heldout_validation import validate_allen_heldout


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = validate_allen_heldout(ROOT)
    (ROOT / "docs/evidence/v4_3_allen_heldout_validation.json").write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (ROOT / "docs/evidence/V4_3_ALLEN_HELDOUT.md").write_text(
        "\n".join(
            [
                "# v4.3 Allen--Cahn Held-Out Development",
                "",
                f"**Status:** `{result['status']}` — frozen development executable",
                "",
                f"Seeds `{result['seeds']}` are binding-valid `{result['binding_valid_count']}/2`; directional-HVP agreement passes `{result['directional_indicator_pass_count']}/2`.",
                "",
                f"Score diagnostics fail `{result['score_failure_nonbinding_count']}/2` and remain nonbinding. The gamma-matched nonlinear-profile bridge passes `{result['profile_bridge_pass_count']}/2`.",
                "",
                "No D/E/eta quantity entered the held-out acceptance. This result permits drafting a separate confirmation lock but does not authorize seeds 75--84.",
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

