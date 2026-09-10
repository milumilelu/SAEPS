"""Phase 4 single-task worker: one center, one route, one isolated process.

python worker.py <center> <route> <dest> [--smoke <json>]

Route P freezes gamma = nominal_alpha * lambda_max(J_theta(theta0)^T J_theta
(theta0)) in gamma_computation.json before any solve; theta0 is never updated.
All outputs are atomic; terminal statuses follow the frozen protocol
precedence. Historical inputs are read-only.
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path

import numpy as np

from objective_adapter import (SCOPE, ROOT, ResidualEvaluator, env_setup, load_source,
                               lambda_max_state_block, payload_residual, state_objective,
                               sha256_file)

env_setup()

import torch
from common import Deadline, read, save_payload, write
import least_squares_solver as solver
import diagnostics


def run(center, route, dest, smoke=None, alpha_override=None):
    started = time.perf_counter()
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    protocol = read(Path(__file__).with_name('protocol.json'))
    alpha = float(protocol['routes']['P']['nominal_alpha'])
    alpha_source = 'protocol_nominal'
    if alpha_override is not None:
        alpha = float(alpha_override)
        alpha_source = 'alpha_grid'
    record = dict(scope=SCOPE, center=center, route=route, smoke=bool(smoke),
                  smoke_override=smoke, alpha_source=alpha_source,
                  alpha_override=alpha_override)
    gates = protocol['gates']['physical_fit']
    stage_spec = protocol['stages']
    if smoke is None:
        wall_total = float(protocol['resources']['wall_seconds_per_task'])
        wall_caps = [float(v) for v in stage_spec['wall_caps_seconds']]
        nfev_pool_total = int(stage_spec['nfev_pool_total'])
    else:
        wall_total = float(smoke.get('wall_seconds', protocol['resources']['wall_seconds_per_task']))
        wall_caps = [float(v) for v in smoke.get('wall_caps', stage_spec['wall_caps_seconds'])]
        nfev_pool_total = int(smoke.get('nfev_total', stage_spec['nfev_pool_total']))
    chunk = int(protocol['solver']['chunk_nfev'])
    tol = float(protocol['solver']['ftol'])
    deadline = Deadline(wall_total)
    code_hashes = {path.name: sha256_file(path) for path in sorted(Path(__file__).parent.glob('*.py'))}
    protocol_path = Path(__file__).with_name('protocol.json')
    code_hashes['protocol.json'] = sha256_file(protocol_path)
    record['protocol_sha256'] = code_hashes['protocol.json']
    write(dest / 'code_hashes.json',
          dict(scope=SCOPE, center=center, route=route, code_hashes=code_hashes))

    def claim_now(status, failure_reason):
        write(dest / 'claim.json', {**record, 'terminal_status': status,
                                    'failure_reason': failure_reason})

    try:
        source = load_source(center)
    except FileNotFoundError as error:
        claim_now('MISSING_INPUT', str(error))
        return
    payload = source['payload']
    residual = payload_residual(payload)
    theta0 = payload['theta'].detach().clone()
    coordinate0 = payload['coordinate'].detach().clone()
    anchor = theta0.detach().clone()

    if route == 'proximal':
        try:
            lambda_max, _, _ = lambda_max_state_block(residual, theta0, coordinate0)
        except TimeoutError:
            claim_now('RESOURCE_LIMIT', 'gamma computation exceeded task deadline')
            return
        gamma = alpha * lambda_max
        write(dest / 'gamma_computation.json', dict(
            scope=SCOPE, center=center, route=route, nominal_alpha=alpha,
            lambda_max_state_block=lambda_max, gamma=gamma,
            gamma_rule=protocol['routes']['P']['gamma_rule'],
            frozen_before_solve=True, frozen_at_state='theta0',
            source_checkpoint_sha256=source['hashes']['lbfgs_state.pt'],
            source_hashes=source['hashes'],
            historical_gamma_context_only=source['historical_gamma'],
            note='historical state.pt gamma is recorded as context only and is never used by Phase 4 objectives'))
    elif route == 'raw':
        gamma = 0.0
    else:
        claim_now('MISSING_INPUT', f'unknown route {route}')
        return

    obj = state_objective(payload, theta0, gamma)
    ev = ResidualEvaluator(residual, coordinate0, theta0, gamma, deadline)
    diag_before, _ = diagnostics.state_diagnostics(residual, theta0, coordinate0, gamma, theta0, route, alpha)
    if not math.isfinite(diag_before['loss_raw_sum']):
        claim_now('NUMERICAL_FAILURE', 'non-finite diagnostics at theta0')
        return
    blocks_before = diagnostics.residual_blocks(residual, theta0, coordinate0, payload)
    write(dest / 'diagnostics_before.json', {**record, 'state': 'theta0', **diag_before})
    write(dest / 'residual_blocks_before.json', {**record, **blocks_before})

    names = ['K8', 'K10', 'K12']
    targets = [float(stage_spec['binding_target'])] + [float(v) for v in stage_spec['polish_targets']]
    x = theta0.numpy().astype(np.float64).copy()
    pool_remaining = nfev_pool_total
    stages = {}
    checkpoints = {}
    milestone_hash = {}
    reached = []
    trajectory = []
    for index, (name, target, wall_cap) in enumerate(zip(names, targets, wall_caps)):
        previous = names[index - 1] if index > 0 else None
        if index > 0 and not stages[previous]['target_reached']:
            stages[name] = dict(target=target, target_reached=False,
                                termination='not_attempted', seconds=0.0,
                                nfev_used=0, njev_used=0)
            continue
        if index > 0:
            # Pre-declared overshoot policy (protocol v3): an identical state is
            # never re-run to manufacture a milestone. If the previous milestone
            # state already satisfies this target, the pair is not separable at
            # the declared resolution and no stability claim is made.
            previous_gate = stages[previous].get('last_gate') or {}
            previous_value = previous_gate.get('normalized_gradient')
            if previous_value is not None and float(previous_value) <= float(target):
                inherited = milestone_hash.get(previous)
                stages[name] = dict(target=target, target_reached=True,
                                    termination='milestone_not_separable', seconds=0.0,
                                    nfev_used=0, njev_used=0, last_gate=previous_gate,
                                    milestone_overshoot=True,
                                    gate_at_start=float(previous_value))
                milestone_hash[name] = inherited
                write(dest / f'curvature_{name}.json',
                      {**record, 'stage': name, 'target': target, 'reached': True,
                       'milestone_overshoot': True, 'separable_from_previous': False,
                       'state_theta_sha256': inherited,
                       'normalized_gradient_route': float(previous_value),
                       'evidence': ('previous milestone state already satisfies this target; '
                                    'the pair is not separable at the declared resolution; '
                                    'curvature stability is UNRESOLVED')})
                continue
        offset = nfev_pool_total - pool_remaining
        stage = solver.solve_stage(ev, x, target, obj, name, deadline, wall_cap,
                                   pool_remaining, chunk, tol)
        pool_remaining -= int(stage['nfev_used'])
        stages[name] = dict(target=target, target_reached=stage['target_reached'],
                            termination=stage['termination'], scipy_stop=stage['scipy_stop'],
                            seconds=stage['seconds'], nfev_used=int(stage['nfev_used']),
                            njev_used=int(stage['njev_used']), last_gate=stage['last_gate'],
                            stage_wall_cap=stage['stage_wall_cap'])
        for row in stage['rows']:
            entry = {**row, 'nfev_task_cum': offset + row['nfev_cum']}
            trajectory.append(entry)
            with (dest / 'trajectory.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + '\n')
        x = stage['x'].astype(np.float64).copy()
        if not stage['target_reached']:
            if name == 'K8':
                write(dest / 'curvature_K8.json', {**record, 'reached': False,
                                                   'termination': stage['termination']})
            continue
        state_theta = torch.from_numpy(stage['x'].copy())
        diag_check, matrices_check = diagnostics.state_diagnostics(
            residual, state_theta, coordinate0, gamma, theta0, route, alpha)
        prev_K = (checkpoints[previous][1] if (previous in checkpoints) else None)
        record_K, K_matrix = diagnostics.curvature_record(
            center, route, name, state_theta, matrices_check, diag_check, prev_K,
            stage['seconds'], target)
        next_target = targets[index + 1] if index + 1 < len(targets) else None
        gate_value = float(stage['last_gate']['normalized_gradient'])
        record_K['milestone_overshoot'] = bool(next_target is not None and gate_value <= float(next_target))
        separable = bool(prev_K is not None and
                         record_K['state_theta_sha256'] != checkpoints[previous][0]['state_theta_sha256'])
        record_K['separable_from_previous'] = separable if prev_K is not None else True
        write(dest / f'curvature_{name}.json', {**record, **record_K})
        milestone_hash[name] = record_K['state_theta_sha256']
        if name in ('K8', 'K10'):
            checkpoints[name] = (record_K, K_matrix, diag_check, separable)
        reached.append((name, stage['x'].copy(), diag_check))

    reached = {entry[0]: (entry[1], entry[2]) for entry in reached}
    binding_name = None
    for candidate in ('K10', 'K8'):
        if candidate in checkpoints and checkpoints[candidate][3] and candidate in reached:
            binding_name = candidate
            break
    if binding_name is not None:
        final_name = binding_name
        final_x, diag_after = reached[binding_name]
    else:
        final_name, final_x, diag_after = 'stage_end', x, None
    final_theta = torch.from_numpy(final_x.copy())
    save_payload(dest / 'theta_final.pt', dict(payload, theta=final_theta))
    if diag_after is None:
        diag_after, _ = diagnostics.state_diagnostics(residual, final_theta, coordinate0, gamma, theta0, route, alpha)
    blocks_after = diagnostics.residual_blocks(residual, final_theta, coordinate0, payload)
    write(dest / 'diagnostics_after.json', {**record, 'state': final_name, **diag_after})
    write(dest / 'residual_blocks_after.json', {**record, **blocks_after})

    fit = diagnostics.physical_fit(diag_before, diag_after, blocks_before, blocks_after, gates, route)
    write(dest / 'physical_fit.json', {**record, **fit})

    k8 = checkpoints.get('K8')
    k10 = checkpoints.get('K10')
    k12_reached = bool(stages.get('K12', {}).get('target_reached'))
    curvature_summary = dict(
        K8_saved=bool(k8 and k8[3]),
        K10_saved=bool(k10 and k10[3]),
        K12_saved=k12_reached,
        K8_reached=bool(k8), K10_reached=bool(k10), K12_milestone_reached=k12_reached,
        milestone_separable=dict(K8=bool(k8 and k8[3]), K10=bool(k10 and k10[3])),
        milestone_not_separable=[name for name in ('K8', 'K10', 'K12')
                                 if stages.get(name, {}).get('termination') == 'milestone_not_separable'],
        binding_state=final_name,
        drift_pass=(k10[0].get('K_drift_vs_previous', {}).get('stability_pass')
                    if (k10 and k10[3]) else None),
        lambda_min_H_raw_at_final=diag_after['H_raw']['lambda_min_H_raw'],
                             H_raw_spd_status=diag_after['H_raw']['H_raw_spd'],
                             lambda_min_A_fd_at_final=diag_after['H_raw']['lambda_min_A_fd'],
                             A_fd_spd_status=diag_after['H_raw']['A_fd_spd'],
                             lambda_min_H_prox_at_final=diag_after['H_prox']['lambda_min_H_prox'],
                             H_prox_spd_status=diag_after['H_prox']['H_prox_spd'],
                             relative_theta_displacement=diag_after['relative_theta_displacement'],
                             proximal_term=diag_after['proximal_term'])
    verdict = diagnostics.decide_terminal(
        route, stages['K8'], diag_after, curvature_summary, fit,
        solver_abort=(ev.failure if not stages['K8']['target_reached'] else None))
    failure_reason = verdict['failure_reason']
    for name in ('K10', 'K12'):
        stage = stages.get(name, {})
        if stage.get('target_reached'):
            continue
        if stage.get('termination') not in (None, 'not_attempted'):
            if failure_reason is None and name == 'K10':
                failure_reason = f'polish attempt {name} terminated: {stage["termination"]}'
    write(dest / 'claim.json', {**record,
                                'terminal_status': verdict['status'],
                                'failure_reason': failure_reason,
                                'labels': verdict['labels'],
                                'scientific_binding_valid': verdict['scientific_binding_valid'],
                                'solver_abort': ev.failure,
                                'gamma_solve': gamma,
                                'nominal_alpha': alpha,
                                'binding_gradient_target': targets[0],
                                'achieved_normalized_gradient': diag_after['normalized_gradient_route'],
                                'loss_raw_before': diag_before['loss_raw_sum'],
                                'loss_raw_after': diag_after['loss_raw_sum'],
                                'physical_fit': fit,
                                'curvature': curvature_summary,
                                'stages': stages,
                                'theta_final_sha256': sha256_file(dest / 'theta_final.pt'),
                                'theta_final_state': final_name,
                                'source_checkpoint_sha256': source['hashes']['lbfgs_state.pt'],
                                'source_state_dir': str(source['source_dir']),
                                'source_hashes': source['hashes'],
                                'historical_gamma_context_only': source['historical_gamma'],
                                'seconds_total': time.perf_counter() - started,
                                'nfev_total': ev.nfev, 'njev_total': ev.njev,
                                'counts': dict(obj.counts),
                                'deadline_seconds': wall_total})

    solver_result = dict(scope=SCOPE, center=center, route=route,
                         method='scipy_least_squares_trf', x_scale='jac', loss='linear',
                         nfev=ev.nfev, njev=ev.njev,
                         cost=None, optimality=None,
                         scipy_status=None, scipy_success=None, message=None,
                         wall_seconds=time.perf_counter() - started,
                         dtype='float64', device='cpu', threads=1,
                         CUDA_VISIBLE_DEVICES='', source_checkpoint_sha256=source['hashes']['lbfgs_state.pt'],
                         scientific_binding_valid=False,
                         note='scipy_success != scientific_binding_valid; usability decided by repository diagnostics')
    for stage_record in stages.values():
        gate = stage_record.get('last_gate') if isinstance(stage_record, dict) else None
        if gate is not None:
            solver_result['scipy_status'] = gate['scipy_status']
            solver_result['scipy_success'] = bool(gate['scipy_success'])
            solver_result['message'] = gate['scipy_message']
            solver_result['cost'] = gate['scipy_cost']
            solver_result['optimality'] = gate['scipy_optimality']
    write(dest / 'solver_result.json', solver_result)


def main(argv):
    alpha_override = None
    args = list(argv)
    if '--alpha' in args:
        index = args.index('--alpha')
        alpha_override = float(args[index + 1])
        del args[index:index + 2]
    smoke = None
    if '--smoke' in args:
        index = args.index('--smoke')
        smoke = json.loads(args[index + 1])
        del args[index:index + 2]
    run(args[0], args[1], args[2], smoke=smoke, alpha_override=alpha_override)


if __name__ == '__main__':
    main(sys.argv[1:])
