from saeps.provenance import environment_provenance, make_run_id


def test_environment_provenance_has_required_p0_fields() -> None:
    payload = environment_provenance(".", dtype="float64", device="cpu")
    required = {
        "timestamp",
        "python_version",
        "python_executable",
        "platform",
        "machine",
        "dtype",
        "device",
        "packages",
        "git_branch",
        "git_dirty",
    }
    assert required <= payload.keys()
    assert payload["dtype"] == "float64"
    assert payload["device"] == "cpu"


def test_run_id_changes_with_seed() -> None:
    first = make_run_id("P0", 1, "a" * 64, "2026-08-19T00:00:00+00:00")
    second = make_run_id("P0", 2, "a" * 64, "2026-08-19T00:00:00+00:00")
    assert first != second
    assert first.startswith("p0-s1-")

