from pathlib import Path

from saeps.v5.reconstruction_audit import build_reconstruction_audit


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_reconstruction_inventory_is_complete_and_reloadable() -> None:
    audit = build_reconstruction_audit(ROOT)
    assert audit["attempted_count"] == 9
    assert audit["total_v5_checkpoint_inventory_at_audit"] >= 9
    assert audit["pass_count"] == 9
    assert audit["retry_count"] == 0
    assert audit["replacement_count"] == 0
    assert len({row["seed"] for row in audit["records"]}) == 9
    assert audit["historical_outputs_file_count"] == 441
    assert audit["historical_outputs_tree_sha256"] == (
        "d9d270695dae57108da9a28fa7c57835dc8155be8dd46fb5f39ba749d2c829b2"
    )
