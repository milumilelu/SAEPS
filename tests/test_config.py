from pathlib import Path

import pytest

from saeps.config import ConfigError, canonical_json, config_hash, load_config


def test_config_hash_is_order_independent() -> None:
    first = {"schema_version": 1, "nested": {"b": 2, "a": 1}}
    second = {"nested": {"a": 1, "b": 2}, "schema_version": 1}
    assert canonical_json(first) == canonical_json(second)
    assert config_hash(first) == config_hash(second)


def test_config_hash_changes_with_value() -> None:
    first = {"schema_version": 1, "seed": 0}
    second = {"schema_version": 1, "seed": 1}
    assert config_hash(first) != config_hash(second)


def test_load_config_rejects_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("schema_version: 2\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="schema_version"):
        load_config(path)

