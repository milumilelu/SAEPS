from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_v43_seed_namespaces_are_disjoint_and_confirmation_is_inactive() -> None:
    config = yaml.safe_load((ROOT / "configs/v4_3/supported_branch.yaml").read_text(encoding="utf-8"))

    assert config["confirmation_authorized"] is False
    external = config["external_scalar"]
    groups = [
        external["development_seeds"],
        external["inactive_confirmation_seeds"],
        *config["future_reserved_seeds"].values(),
    ]
    flattened = [seed for group in groups for seed in group]
    assert len(flattened) == len(set(flattened))
    assert external["benchmark"] == "Allen-Cahn"
    assert external["screening_forbidden"] is True
    assert config["candidate_external_confirmation_rule"]["state"] == "NOT_LOCKED_NOT_AUTHORIZED"


def test_v43_preserves_permanently_closed_confirmation_records() -> None:
    config = yaml.safe_load((ROOT / "configs/v4_3/supported_branch.yaml").read_text(encoding="utf-8"))
    for relative_path in config["immutable_history"].values():
        assert (ROOT / relative_path).is_file()


def test_allen_development_uses_only_reserved_development_seeds() -> None:
    branch = yaml.safe_load((ROOT / "configs/v4_3/supported_branch.yaml").read_text(encoding="utf-8"))
    development = yaml.safe_load(
        (ROOT / "configs/v4_3/allen_cahn_development.yaml").read_text(encoding="utf-8")
    )
    assert development["development_seeds"] == branch["external_scalar"]["development_seeds"]
    assert development["inactive_confirmation_seeds"] == branch["external_scalar"]["inactive_confirmation_seeds"]
    assert development["confirmation_authorized"] is False
    assert development["scientific_gate"] == "NONE_DEVELOPMENT_ONLY"
    assert development["engineering_seeds"] == [70, 71, 72]
    assert development["heldout_development_seeds"] == [73, 74]
