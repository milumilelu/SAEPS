"""Execute the separately locked v4.2 confirmation exactly once."""

from pathlib import Path

from saeps.v42.pipeline import run_v42_confirmation


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run_v42_confirmation(
        root / "configs/v4_2/locked_corrected_confirmation.yaml",
        root / "outputs/runs/v4_2_corrected_confirmation",
        root,
        root / "configs/v4_2/EXECUTION_AUTHORIZATION.json",
        root / "docs/evidence/V4_2_PRE_CONFIRMATION_AUDIT.json",
    )

