from pathlib import Path
import json
import hashlib

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
    architecture = development["architecture_engineering"]
    assert architecture["fallback_order"] == [16, 12, 8]
    assert architecture["selected_width"] == 8
    assert "D" in architecture["selection_forbidden_metrics"]


def test_allen_semantic_graph_keeps_profile_and_score_nonbinding() -> None:
    graph = json.loads(
        (ROOT / "docs/v4_3/ALLEN_SEMANTIC_GATE_GRAPH.json").read_text(encoding="utf-8")
    )
    assert "score_solver_status" in graph["nonbinding_nodes"]
    assert "profile_status" in graph["nonbinding_nodes"]
    assert "score_solver_status" not in graph["curvature_gate"]["requires"]
    assert graph["fail_soft_recording"] is True


def test_allen_executable_freeze_matches_all_declared_files() -> None:
    freeze = json.loads(
        (ROOT / "configs/v4_3/ALLEN_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["confirmation_authorized"] is False
    for relative_path, expected in freeze["file_sha256"].items():
        observed = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert observed == expected
