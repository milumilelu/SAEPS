from pathlib import Path

from saeps.v44.result_validation import PLANNED_SEEDS, build_manifest_rows


ROOT = Path(__file__).resolve().parents[1]


def test_v44_result_layout_uses_actual_architecture_directory() -> None:
    rows, records = build_manifest_rows(ROOT)
    assert [row["seed"] for row in rows] == PLANNED_SEEDS
    assert [record["seed"] for record in records] == PLANNED_SEEDS
    assert all(row["path"] == f"architecture_w8/seed_{row['seed']}/result.json" for row in rows)
