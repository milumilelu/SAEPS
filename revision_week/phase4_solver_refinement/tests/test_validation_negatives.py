"""Negative controls for the Phase 4 evidence audit.

Each test constructs a task directory that satisfies the cosmetic surface of a
result but violates one evidence requirement; the audit must fail on it. A
positive control confirms that a directory with no violation produces none.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from common import load_payload, write
import finalize
from objective_adapter import source_dir

PROTOCOL = finalize.read(Path(finalize.__file__).with_name('protocol.json'))
PROTOCOL_SHA = finalize.sha256_file(Path(finalize.__file__).with_name('protocol.json'))


def base_task(tmp_path, center='burgers_1006', **overrides):
    task = tmp_path / f'{center}_raw'
    task.mkdir(parents=True, exist_ok=True)
    claim = dict(scope='PHASE4_SOLVER_REFINEMENT', center=center, route='raw',
                 terminal_status='PASS',
                 labels=dict(reference_gradient_pass=True,
                             finite_damped_or_proximal_stability_pass=True,
                             curvature_stability='UNRESOLVED',
                             physical_fit_preserved=True,
                             raw_gradient_pass=True,
                             raw_local_minimum=False,
                             REFERENCE_CAPABLE=True),
                 curvature=dict(K10_saved=False), loss_raw_after=1.0)
    claim.update(overrides)
    write(task / 'claim.json', claim)
    write(task / 'process.json', dict(scope='PHASE4_SOLVER_REFINEMENT', status='PASS',
                                      failure_reason=None, wall_seconds=1.0,
                                      sampled_peak_rss_bytes=1, exit_code=0))
    write(task / 'code_hashes.json', dict(code_hashes={'protocol.json': PROTOCOL_SHA}))
    return task


def kinds(task):
    return {violation['kind'] for violation in finalize.audit_task_dir(task, PROTOCOL)}


def test_positive_control_is_clean(tmp_path):
    task = base_task(tmp_path)
    assert finalize.audit_task_dir(task, PROTOCOL) == []


def test_identical_k8_k10_states_marked_stable_is_rejected(tmp_path):
    task = base_task(tmp_path, labels=dict(reference_gradient_pass=True,
                                           finite_damped_or_proximal_stability_pass=True,
                                           curvature_stability='STABLE',
                                           physical_fit_preserved=True,
                                           raw_gradient_pass=True,
                                           raw_local_minimum=False,
                                           REFERENCE_CAPABLE=True),
                     curvature=dict(K10_saved=True))
    shared = dict(state_theta_sha256='deadbeef', separable_from_previous=True)
    write(task / 'curvature_K8.json', shared)
    write(task / 'curvature_K10.json', shared)
    assert 'vacuous_curvature_stability' in kinds(task)


def test_raw_local_minimum_without_raw_stationarity_is_rejected(tmp_path):
    task = base_task(tmp_path, labels=dict(reference_gradient_pass=True,
                                           finite_damped_or_proximal_stability_pass=True,
                                           curvature_stability='UNRESOLVED',
                                           physical_fit_preserved=True,
                                           raw_gradient_pass=False,
                                           raw_local_minimum=True,
                                           REFERENCE_CAPABLE=True))
    write(task / 'diagnostics_after.json', dict(m=10, theta_norm=1.0,
                                                raw_gradient_sum_norm=1e-3))
    assert 'raw_local_minimum_without_raw_stationarity' in kinds(task)


def test_tampered_protocol_hash_is_rejected(tmp_path):
    task = base_task(tmp_path)
    write(task / 'code_hashes.json', dict(code_hashes={'protocol.json': '0' * 64}))
    assert 'protocol_hash_mismatch' in kinds(task)


def test_missing_process_record_is_rejected(tmp_path):
    task = base_task(tmp_path)
    (task / 'process.json').unlink()
    assert 'missing_process_record' in kinds(task)


def test_failed_process_with_terminal_claim_is_rejected(tmp_path):
    task = base_task(tmp_path)
    write(task / 'process.json', dict(scope='PHASE4_SOLVER_REFINEMENT', status='SOLVER_FAILURE',
                                      failure_reason='resource_limit', wall_seconds=1.0,
                                      sampled_peak_rss_bytes=1, exit_code=-9))
    assert 'process_failure_with_terminal_claim' in kinds(task)


def test_tampered_gamma_rule_is_rejected(tmp_path):
    task = base_task(tmp_path, route='proximal')
    write(task / 'claim.json', dict(finalize.read(task / 'claim.json'), route='proximal'))
    write(task / 'gamma_computation.json', dict(nominal_alpha=1e-8,
                                                lambda_max_state_block=1.0,
                                                gamma=1e-8))
    assert 'lambda_max_mismatch' in kinds(task)


def test_label_status_inconsistency_is_rejected(tmp_path):
    task = base_task(tmp_path, terminal_status='RESOURCE_LIMIT')
    assert 'label_status_inconsistent' in kinds(task)
