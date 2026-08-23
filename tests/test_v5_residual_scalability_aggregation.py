import json
import statistics
from pathlib import Path

from saeps.v5.residual_scalability_aggregation import build_residual_scalability


ROOT = Path(__file__).resolve().parents[1]


def test_v5_residual_scalability_aggregate_is_complete_and_source_derived() -> None:
    aggregate = build_residual_scalability(ROOT)
    assert aggregate["engineering_status"] == "PASSED"
    assert aggregate["terminal_count"] == aggregate["pass_count"] == 27
    assert aggregate["training_or_reconstruction_runs"] == 0
    assert aggregate["synthetic_residual_padding"] is False
    assert aggregate["complexity_exponent_fitted"] is False
    assert len(aggregate["conditions"]) == 9
    condition = aggregate["conditions"][0]
    raw = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "outputs/runs/v5/residual_scalability/n_1001/m_213").rglob("result.json"))
    ]
    assert condition["wall_seconds"]["median"] == statistics.median(row["wall_seconds"] for row in raw)
