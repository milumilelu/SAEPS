from saeps.v45.confirmation import aggregate_v45_confirmation


def _record(seed: int, valid: bool = True) -> dict:
    eta = [0.02, 0.06, 0.10, 0.15, 0.20]
    return {"seed": seed, "status": "PASS" if valid else "CHECKPOINT_INVALID", "binding_valid": valid, "alpha_evaluations": [{"status": "PASS" if valid else "CHECKPOINT_INVALID", "eta": value if valid else None} for value in eta]}


def test_v45_confirmation_planned_denominator() -> None:
    specification = {"phase": "test", "planned_seeds": list(range(90, 100)), "alpha_values": [0, 0.25, 0.5, 0.75, 1], "primary": {"monotonic_absolute_tolerance": 1e-8, "monotonic_planned_seeds_required": 8, "median_valid_seed_spearman_min": 0.9}}
    supported = aggregate_v45_confirmation([_record(seed) for seed in range(90, 100)], specification)
    assert supported["scientific_status"] == "SUPPORTED"
    invalid = aggregate_v45_confirmation([_record(seed, seed != 90) for seed in range(90, 100)], specification)
    assert invalid["scientific_status"] == "NOT_SUPPORTED"
