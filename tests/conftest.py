"""Phase-aware handling for the immutable V5.0 pre-execution assertion."""

from pathlib import Path

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    root = Path(__file__).resolve().parents[1]
    execution_started = (root / "configs/v5/V5_EXECUTION_AUTHORIZATION.json").is_file() and (
        root / "outputs/runs/v5"
    ).is_dir()
    if not execution_started:
        return
    historical_node = "tests/test_v5_governance.py::test_v5_governance_freeze_passes_without_scientific_output"
    for item in items:
        if item.nodeid == historical_node:
            item.add_marker(
                pytest.mark.skip(
                    reason="immutable V5.0 empty-output assertion is historical after authorized execution; post-execution validator is binding"
                )
            )
