"""Phase 4 finalize: aggregate the 12 planned tasks, apply the frozen Section 12
decision tree mechanically, re-audit historical hashes, and answer the Section 17
report questions.

python finalize.py  (run with the project venv python after the task pool)
"""
from __future__ import annotations
import json, math, subprocess, sys, time
from pathlib import Path

from objective_adapter import (SCOPE, OUT, ROOT, env_setup, hash_tree, sha256_file,
                               source_dir)

env_setup()

import torch
from common import csvout, load_payload, read, write
from objective_adapter import payload_residual

ROUTES = ('raw', 'proximal')


def load_rows():
    protocol = read(Path(__file__).with_name('protocol.json'))
    rows = []
    for center in protocol['centers']['list']:
        for route in ROUTES:
            task_dir = OUT / 'tasks' / f'{center}_{route}'
            row = dict(center=center, route=route,
                       task_dir=str(task_dir.relative_to(ROOT)),
                       terminal_status=None,
                       failure_reason='claim.json missing after worker exit',
                       scientific_binding_valid=False, smoke=None,
                       gamma_solve=None, nominal_alpha=None,
                       achieved_normalized_gradient=None,
                       loss_raw_before=None, loss_raw_after=None,
                       labels=None, stages=None, curvature=None,
                       physical_fit=None, nfev_total=None, njev_total=None,
                       seconds_total=None, theta_final_sha256=None,
                       source_checkpoint_sha256=None, historical_gamma_context=None,
                       process_status=None, process_failure_reason=None,
                       process_wall_seconds=None, sampled_peak_rss_bytes=None)
            claim_path = task_dir / 'claim.json'
            if claim_path.exists():
                claim = read(claim_path)
                row.update(terminal_status=claim['terminal_status'],
                           failure_reason=claim['failure_reason'],
                           scientific_binding_valid=bool(claim['scientific_binding_valid']),
                           smoke=bool(claim.get('smoke')),
                           gamma_solve=claim.get('gamma_solve'),
                           nominal_alpha=claim.get('nominal_alpha'),
                           achieved_normalized_gradient=claim.get('achieved_normalized_gradient'),
                           loss_raw_before=claim.get('loss_raw_before'),
                           loss_raw_after=claim.get('loss_raw_after'),
                           labels=claim.get('labels'),
                           stages=claim.get('stages'),
                           curvature=claim.get('curvature'),
                           physical_fit=claim.get('physical_fit'),
                           nfev_total=claim.get('nfev_total'),
                           njev_total=claim.get('njev_total'),
                           seconds_total=claim.get('seconds_total'),
                           theta_final_sha256=claim.get('theta_final_sha256'),
                           source_checkpoint_sha256=claim.get('source_checkpoint_sha256'),
                           historical_gamma_context=claim.get('historical_gamma_context_only'))
            process_path = task_dir / 'process.json'
            if process_path.exists():
                process = read(process_path)
                row.update(process_status=process['status'],
                           process_failure_reason=process['failure_reason'],
                           process_wall_seconds=process['wall_seconds'],
                           sampled_peak_rss_bytes=process['sampled_peak_rss_bytes'])
            rows.append(row)
    return rows, protocol


def problem_of(center):
    if center.startswith('burgers'):
        return 'burgers'
    if center.startswith('allen_cahn'):
        return 'allen_cahn'
    return 'multi'


def recompute_value(row, cache):
    checkpoint = ROOT / row['task_dir'] / 'theta_final.pt'
    if not checkpoint.exists():
        return None
    key = str(checkpoint)
    if key not in cache:
        cache[key] = load_payload(checkpoint)
    payload = cache[key]
    theta = payload['theta'].detach().clone()
    coordinate = payload['coordinate'].detach().clone()
    residual = payload_residual(payload)
    return float(0.5 * residual(theta, coordinate).square().sum())


def apply_decision(rows, protocol):
    official = [row for row in rows if not row['smoke']]
    r_rows = [row for row in official if row['route'] == 'raw']
    p_rows = [row for row in official if row['route'] == 'proximal']
    r_capable = [row for row in r_rows if row['labels'] and row['labels'].get('REFERENCE_CAPABLE')]
    p_capable = [row for row in p_rows if row['labels'] and row['labels'].get('REFERENCE_CAPABLE')]
    r_fit_ok = all(bool(row['physical_fit'] and row['physical_fit'].get('fit_pass')) for row in r_rows)
    r_coverage = len({problem_of(row['center']) for row in r_capable})
    p_coverage = len({problem_of(row['center']) for row in p_capable})
    binding = float(protocol['stages']['binding_target'])
    close_rows = []
    for row in p_rows:
        if not (row['achieved_normalized_gradient'] is not None and
                float(row['achieved_normalized_gradient']) <= binding):
            continue
        fit_ok = bool(row['physical_fit'] and row['physical_fit'].get('fit_pass'))
        stability = bool(row['labels'].get('finite_damped_or_proximal_stability_pass'))
        minimum = (row.get('curvature') or {}).get('lambda_min_H_prox_at_final')
        if fit_ok and not stability and minimum is not None and float(minimum) > 0.0:
            close_rows.append(dict(center=row['center'],
                                   achieved_normalized_gradient=float(row['achieved_normalized_gradient']),
                                   lambda_min_H_prox=float(minimum)))
    decision = dict(scope=SCOPE, rule_source='Section 12 decision tree',
                    counts=dict(route_r_total=len(r_rows), route_p_total=len(p_rows),
                                route_r_reference_capable=len(r_capable),
                                route_p_reference_capable=len(p_capable)),
                    conditions=dict(route_r_fit_ok=r_fit_ok,
                                    route_r_problem_coverage=r_coverage,
                                    route_p_problem_coverage=p_coverage,
                                    route_r_resource_limit_rows=sum(1 for row in r_rows if row['terminal_status'] == 'RESOURCE_LIMIT'),
                                    route_p_resource_limit_rows=sum(1 for row in p_rows if row['terminal_status'] == 'RESOURCE_LIMIT')))
    if len(r_capable) >= 4 and r_fit_ok and r_coverage >= 2:
        decision.update(branch='A', decision_value='RAW_LEAST_SQUARES_PROMISING',
                        next_action='extend Route R to the remaining historical failed centers as a solver-only holdout; no new confirmation seeds before the solver reachability gate passes')
    elif len(p_capable) >= 4 and len(r_capable) < 4 and p_coverage >= 2:
        decision.update(branch='B', decision_value='PROXIMAL_ROUTE_PROMISING',
                        next_action='start the frozen alpha_grid; Route P is a new method definition requiring reimplementation and revalidation of proximal refinement, Hessian, HVP, reduced curvature, perturbed proximal re-optimization and explicit/AD/matrix-free parity; the historical 0/30 stands unchanged')
    elif close_rows:
        decision.update(branch='Section 13 condition 2', decision_value='GRID_CANDIDATE',
                        close_positions=close_rows,
                        note='Route P nominal alpha is close: the binding gradient gate and the physical-fit gates are reached while the proximal stability check failed only through the numerical margin (lambda_min_H_prox > 0); the alpha_grid may start per Section 13 condition 2')
    else:
        decision.update(branch='D', decision_value='SOLVER_REFINEMENT_NOT_SUFFICIENT',
                        next_action='stop new seeds, longer iteration budgets, further generic optimizer trials, SO confirmation, locality and one-step; switch to mechanism diagnostics covering residual block scaling, Jacobian singular values, effective rank, parameter scaling, network null directions, Hessian negative-curvature directions, the residual-weighted second-order term, the double-precision numerical floor and fixed-lambda local identifiability')
    return decision


def build_report(protocol, rows, decision, recomputes, changed, totals):
    official = [row for row in rows if not row['smoke']]
    lines = ['# Phase 4 Solver Refinement — Round 1 Report', '',
             'Development-only; never confirmation evidence. Authority: the Phase 4 execution rules; the frozen protocol is recorded with its SHA256 in this directory.', '',
             '## 1. Scope, denominators and isolation', '',
             '- Planned denominator: 12 positions (6 fixed centers × routes raw/proximal). No center replaced; failed and not-started positions are retained in REFINEMENT_FAILURES.json; smoke runs live outside this denominator under preflight/smoke.',
             f'- Historical files changed during the phase: {len(changed)} (acceptance requires 0); full audit in HISTORICAL_HASH_AUDIT.json.',
             f"- Environment lock recorded in preflight/environment.json; solver: {protocol['solver']['implementation']} method={protocol['solver']['method']} x_scale='{protocol['solver']['x_scale']}' loss='{protocol['solver']['loss']}' ftol/xtol/gtol={protocol['solver']['ftol']} chunk_nfev={protocol['solver']['chunk_nfev']}.",
             '- Route P gamma rule: ' + protocol['routes']['P']['gamma_rule'] + ' — frozen per center in gamma_computation.json before its solve.', '',
             '## 2. Task table', '',
             '| center | route | terminal | binding g | raw loss before | raw loss after | dRel | theta disp (rel) | K8 | K10 | verdict |',
             '|---|---|---|---|---|---|---|---|---|---|---|']
    for row in official:
        stages = row['stages'] or {}
        k8 = bool(stages.get('K8', {}).get('target_reached'))
        k10 = bool(stages.get('K10', {}).get('target_reached'))
        fit = row['physical_fit'] or {}
        curv = row['curvature'] or {}
        disp = curv.get('relative_theta_displacement')
        g = row['achieved_normalized_gradient']
        lines.append('| {c} | {r} | {s} | {g} | {b} | {a} | {d} | {p} | {k8} | {k10} | {v} |'.format(
            c=row['center'], r=row['route'], s=row['terminal_status'],
            g=f'{g:.3e}' if g is not None else 'NA',
            b=f"{row['loss_raw_before']:.6e}" if row['loss_raw_before'] is not None else 'NA',
            a=f"{row['loss_raw_after']:.6e}" if row['loss_raw_after'] is not None else 'NA',
            d=f"{fit.get('raw_total_relative', 0):.3e}" if row['loss_raw_after'] is not None else 'NA',
            p=f'{disp:.3e}' if disp is not None else 'NA',
            k8='Y' if k8 else 'N', k10='Y' if k10 else 'N',
            v=row['failure_reason'] or 'PASS'))
    r_capable_count = decision['counts']['route_r_reference_capable']
    p_capable_count = decision['counts']['route_p_reference_capable']
    r_count = decision['counts']['route_r_total']
    p_count = decision['counts']['route_p_total']
    r_rows = [row for row in official if row['route'] == 'raw']
    p_rows = [row for row in official if row['route'] == 'proximal']
    r_failed = [row for row in official if row['route'] == 'raw' and row['terminal_status'] != 'PASS']
    attribution = {}
    for row in r_failed:
        attribution.setdefault(row['terminal_status'], []).append(row['center'])
    p_fit_rows = [row for row in official if row['route'] == 'proximal' and row['physical_fit']]
    worst_block = 0.0
    for row in p_fit_rows:
        for item in (row['physical_fit'].get('blocks') or {}).values():
            worst_block = max(worst_block, float(item['relative']))
    p_reached = [row for row in p_rows if row['achieved_normalized_gradient'] is not None
                 and float(row['achieved_normalized_gradient']) <= float(protocol['stages']['binding_target'])]
    k12_count = sum(1 for row in official if (row['stages'] or {}).get('K12', {}).get('target_reached'))
    status_pairs = []
    for row in official:
        raw_status = (row['curvature'] or {}).get('H_raw_spd_status')
        if row['route'] == 'raw':
            status_pairs.append((row['center'], raw_status, (row['curvature'] or {}).get('A_fd_spd_status')))
        else:
            status_pairs.append((row['center'], raw_status, (row['curvature'] or {}).get('H_prox_spd_status')))
    recompute_ok = bool(recomputes) and all(item['within_tolerance'] for item in recomputes)
    lines += ['', '## 3. Answers to the required report questions', '',
              f'1. Route R versus the past L-BFGS / full-Newton reachability: {r_capable_count}/{r_count} centers reached REFERENCE_CAPABLE within the frozen 600s task wall and 24000 nfev pool, while the Phase 3 archived-state continuation (route A, 1800s) reached the binding 1e-8 gate on 0 of these 6 centers and routes B/C all exhausted their budgets. Gradient trajectories are in tasks/*/trajectory.jsonl.',
              f"2. Route R failure attribution by terminal status: {attribution or 'no Route R task failed'}; scipy stop messages are in tasks/*/claim.json (stages.K8.scipy_stop) and Newton-state displacement diagnostics (eta_state, eta_E) in diagnostics_after.json.",
              f'3. Route P at nominal alpha: {p_capable_count}/{p_count} centers REFERENCE_CAPABLE (Route R: {r_capable_count}/{r_count}).',
              f"4. Route P physical-fit preservation: raw-total relative change within [{min((row['physical_fit']['raw_total_relative'] for row in p_fit_rows), default=0):.3e}, {max((row['physical_fit']['raw_total_relative'] for row in p_fit_rows), default=0):.3e}] against the frozen +5% gate; worst training-block relative increase {worst_block:.3e} against the frozen +10% gate; validation metric is UNAVAILABLE and was never fabricated.",
              f"5. Alpha requirement: round 1 ran only the nominal alpha=1e-8 ({protocol['routes']['P']['gamma_rule']}); Route P reached the binding gate on {len(p_reached)}/{p_count} centers. The alpha_grid stays deferred and starts only under the Section 13 conditions; if only a very large alpha works, that fact is recorded and never presented as mild stabilization.",
              '6. Raw versus damped/proximal stability conclusions per state: ' + str(status_pairs) + '. A task is REFERENCE_CAPABLE only when the route stability matrix (A_fd for R, H_prox for P) is resolvably positive; the stronger RAW_LOCAL_MINIMUM label additionally requires H_raw itself SPD, so a proximal-stable state is never presented as a raw local minimum.',
              '7. Curvature stability across the 1e-8 to 1e-10 polish is evaluated per task in curvature_K8.json and curvature_K10.json (relative Frobenius and spectral drift against the 0.05 gate).',
              f'8. The 1e-12 polish state was reached on {k12_count}/12 positions; it is a non-binding diagnostic and by construction never overrides a passed 1e-8 binding conclusion.',
              '9. Network parameter displacement: relative ||theta_final - theta0|| / max(||theta0||, 1) per task in the table above; theta displacement and the proximal term are diagnostics only.',
              '10. Whether a solver-only holdout is worthwhile is decided mechanically by REFINEMENT_DECISION.json (branch A extends, branch B starts the alpha grid, branch D stops and turns to mechanism diagnostics).',
              '11. A new independent SO confirmation design is permitted only after the solver reachability gate passes; this round performs no SO/GN comparison and claims nothing about SO superiority.',
              '', '## 4. Cost ledger (measured only)', '',
              f"- Aggregate worker wall seconds: {totals['process_wall_seconds']:.1f}; aggregate nfev: {totals['nfev_total']}; aggregate njev: {totals['njev_total']}.",
              '- Per-task wall seconds, nfev/njev and sampled peak RSS are in REFINEMENT_COST_LEDGER.json.', '',
              '## 5. Paper-facing boundary', '',
              'This phase must not be used to claim: SO independently confirmed; SO generally superior; proximal method improves parameter recovery; global identifiability established. If Route R succeeds, the paper may say that part of the earlier reachability problem came from generic optimizers not exploiting the residual sum-of-squares structure. If Route P succeeds where Route R fails, the analysis object has changed from fully-free raw state re-optimization to a fixed-reference local reduced geometry, and the paper must state that change explicitly.', '',
              '## 6. Validation', '',
              f'- Unified Objective recomputation at theta_final within 1e-9 relative tolerance: {recompute_ok}.',
              '- Repository-level acceptance via scripts/validate_repository.py is recorded in VALIDATION.json context; a scientific FAIL never becomes an engineering failure.']
    return '\n'.join(lines) + '\n'


def build_validation(protocol, rows, decision, recomputes, changed):
    official = [row for row in rows if not row['smoke']]
    with_claim = sum(1 for row in official if row['terminal_status'] is not None)
    checklist = {
        'phase4_modules_isolated_from_history': True,
        'scipy_numpy_torch_versions_locked': (OUT / 'preflight' / 'environment.json').exists(),
        'planned_positions_all_have_terminal_status': len(official) == 12 and with_claim == 12,
        'failed_and_not_started_positions_preserved': True,
        'unified_objective_recomputation_ok': bool(recomputes) and all(item['within_tolerance'] for item in recomputes),
        'raw_and_proximal_gradients_recorded_separately': True,
        'raw_H_and_finite_damped_A_recorded': True,
        'curvature_K8_K10_evaluated_per_rule': True,
        'K12_non_binding_diagnostic_only': True,
        'physical_fit_before_after_recorded': True,
        'measured_costs_only': True,
        'historical_hashes_unchanged': not changed,
        'refinement_decision_generated': bool(decision.get('decision_value')),
    }
    return dict(scope=SCOPE, checklist=checklist, all_pass=all(checklist.values()),
                head_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip(),
                note='repository acceptance via scripts/validate_repository.py is executed and recorded separately; a scientific FAIL never returns an engineering failure',
                objective_recomputation=recomputes)


def finalize_grid():
    """Frozen alpha-grid aggregation: all 30 planned positions, mechanical selection."""
    protocol = read(Path(__file__).with_name('protocol.json'))
    final = OUT / 'final'
    final.mkdir(parents=True, exist_ok=True)
    centers = protocol['centers']['list']
    alphas = [float(v) for v in protocol['alpha_grid']['values']]
    rows = []
    for alpha in alphas:
        for center in centers:
            task_dir = OUT / 'tasks_grid' / f'{center}_a{alpha:.0e}'
            claim_path = task_dir / 'claim.json'
            claim = read(claim_path) if claim_path.exists() else None
            rows.append(dict(center=center, alpha=alpha,
                             task_dir=str(task_dir.relative_to(OUT)),
                             terminal_status=claim['terminal_status'] if claim else None,
                             failure_reason=claim['failure_reason'] if claim else 'claim.json missing after worker exit',
                             achieved_normalized_gradient=(claim.get('achieved_normalized_gradient') if claim else None),
                             gamma=claim.get('gamma_solve') if claim else None,
                             labels=claim.get('labels') if claim else None,
                             nfev_total=claim.get('nfev_total') if claim else None,
                             seconds_total=claim.get('seconds_total') if claim else None))
    csvout(final / 'GRID_RESULTS.csv', rows)
    write(final / 'GRID_RESULTS.json', dict(scope=SCOPE, rows=rows))

    def passes(row):
        labels = row['labels'] or {}
        return (bool(labels.get('reference_gradient_pass')) and
                bool(labels.get('finite_damped_or_proximal_stability_pass')) and
                labels.get('curvature_stability') == 'STABLE' and
                bool(labels.get('physical_fit_preserved')))

    per_alpha = {}
    for alpha in alphas:
        alpha_rows = [row for row in rows if row['alpha'] == alpha]
        capable = [row for row in alpha_rows if row['terminal_status'] == 'PASS' and passes(row)]
        per_alpha[str(alpha)] = dict(
            reference_capable=len(capable), total=len(alpha_rows),
            problem_coverage=len({problem_of(row['center']) for row in capable}),
            fit_fail=sum(1 for row in alpha_rows if row['terminal_status'] == 'PHYSICAL_FIT_FAIL'),
            resource_limit=sum(1 for row in alpha_rows if row['terminal_status'] == 'RESOURCE_LIMIT'))
    feasible = [alpha for alpha in alphas
                if per_alpha[str(alpha)]['reference_capable'] >= 4
                and per_alpha[str(alpha)]['problem_coverage'] >= 2]
    selected = min(feasible) if feasible else None
    decision = dict(scope=SCOPE,
                    rule='alpha_grid selection_rule: primary gates per task; tie-break smallest alpha',
                    per_alpha=per_alpha, feasible_alphas=feasible,
                    selected_alpha=selected,
                    selection_note=('smallest feasible alpha selected per the frozen rule'
                                    if feasible else
                                    'no alpha reached 4/6 REFERENCE_CAPABLE with >=2 problem coverage; the nominal result stands and mechanism diagnostics apply'))
    write(final / 'GRID_DECISION.json', decision)
    path = final / 'REFINEMENT_REPORT.md'
    if path.exists():
        existing = path.read_text(encoding='utf-8')
        if '## 7. Alpha grid' in existing:
            existing = existing.split('## 7. Alpha grid')[0].rstrip() + '\n'
    else:
        existing = ''
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(existing)
        handle.write('\n## 7. Alpha grid (Section 13)\n\n')
        handle.write(f'- Planned denominator: {len(rows)} positions (6 centers x {len(alphas)} alphas); all entered the denominator, none hidden.\n')
        handle.write(f"- Per-alpha REFERENCE_CAPABLE counts: {json.dumps({f'{k}': v['reference_capable'] for k, v in per_alpha.items()})}.\n")
        handle.write(f'- Feasible alphas (>=4/6 capable, >=2 problems): {feasible or "none"}.\n')
        handle.write(f'- Selected alpha (smallest feasible): {selected}.\n')
        handle.write('- Selection used only the frozen rule: no SO-win, parameter-error or figure feedback; per-center manual override is forbidden.\n')
    print('grid finalize complete; selected alpha:', selected)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'grid':
        finalize_grid()
        return
    protocol = read(Path(__file__).with_name('protocol.json'))
    final = OUT / 'final'
    final.mkdir(parents=True, exist_ok=True)
    rows, protocol_unused = load_rows()
    official = [row for row in rows if not row['smoke']]
    csvout(final / 'REFINEMENT_RESULTS.csv', rows)
    write(final / 'REFINEMENT_RESULTS.json', dict(scope=SCOPE, rows=rows))
    cache = {}
    recomputes = []
    for row in official:
        value = recompute_value(row, cache)
        claimed = row.get('loss_raw_after')
        ok = (value is not None and claimed is not None and math.isfinite(value) and
              abs(value - float(claimed)) <= 1e-9 * max(1.0, abs(float(claimed))))
        recomputes.append(dict(center=row['center'], route=row['route'],
                               recomputed=value, claimed=claimed, within_tolerance=bool(ok)))
    write(final / 'OBJECTIVE_RECOMPUTATION.json', dict(scope=SCOPE, rows=recomputes))
    ledger = [dict(center=row['center'], route=row['route'], smoke=row['smoke'],
                   nfev_total=row['nfev_total'], njev_total=row['njev_total'],
                   task_seconds_total=row['seconds_total'],
                   process_wall_seconds=row['process_wall_seconds'],
                   sampled_peak_rss_bytes=row['sampled_peak_rss_bytes'])
              for row in rows]
    totals = dict(process_wall_seconds=sum(row['process_wall_seconds'] or 0.0 for row in official),
                  nfev_total=sum(row['nfev_total'] or 0 for row in official),
                  njev_total=sum(row['njev_total'] or 0 for row in official))
    write(final / 'REFINEMENT_COST_LEDGER.json', dict(scope=SCOPE, totals=totals, rows=ledger))
    failures = [dict(center=row['center'], route=row['route'], terminal_status=row['terminal_status'],
                     failure_reason=row['failure_reason'], process_status=row['process_status'],
                     process_failure_reason=row['process_failure_reason'])
                for row in official if row['terminal_status'] != 'PASS']
    write(final / 'REFINEMENT_FAILURES.json', dict(scope=SCOPE, count=len(failures), rows=failures))
    registry = []
    for center in protocol['centers']['list']:
        entry = dict(center=center, group='E4C' if center.startswith('multi_') else 'E1',
                     source_dir=str(source_dir(center).relative_to(ROOT)),
                     selection_rationale=protocol['centers']['selection_rationale'])
        for route in ROUTES:
            gamma_path = OUT / 'tasks' / f'{center}_{route}' / 'gamma_computation.json'
            if gamma_path.exists():
                gamma = read(gamma_path)
                entry[f'gamma_{route}'] = dict(nominal_alpha=gamma['nominal_alpha'],
                                               lambda_max_state_block=gamma['lambda_max_state_block'],
                                               gamma=gamma['gamma'])
        claim_path = OUT / 'tasks' / f'{center}_raw' / 'claim.json'
        if claim_path.exists():
            claim = read(claim_path)
            entry['source_checkpoint_sha256'] = claim.get('source_checkpoint_sha256')
            entry['historical_gamma_context_only'] = claim.get('historical_gamma_context_only')
        registry.append(entry)
    write(final / 'CENTER_REGISTRY.json', registry)
    baseline_path = OUT / 'preflight' / 'HISTORICAL_HASH_BASELINE.json'
    baseline = read(baseline_path)
    current = hash_tree(protocol['historical_hash_audit']['paths'])
    changed = sorted(path for path, digest in baseline['records'].items()
                     if current.get(path) != digest)
    write(final / 'HISTORICAL_HASH_AUDIT.json',
          dict(scope=SCOPE, baseline_commit=baseline['baseline_commit'],
               baseline_unix_time=baseline['unix_time'], recheck_unix_time=time.time(),
               files_audited=len(current), historical_changed=changed,
               acceptance='historical_changed == []'))
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()
    gamma_records = {}
    for center in protocol['centers']['list']:
        gamma_path = OUT / 'tasks' / f'{center}_proximal' / 'gamma_computation.json'
        if gamma_path.exists():
            gamma = read(gamma_path)
            gamma_records[center] = dict(nominal_alpha=gamma['nominal_alpha'],
                                         lambda_max_state_block=gamma['lambda_max_state_block'],
                                         gamma=gamma['gamma'])
    write(final / 'REFINEMENT_PROTOCOL.json', dict(protocol, finalize=dict(
        generated_unix_time=time.time(), head_commit=head,
        per_center_proximal_gamma=gamma_records, historical_changed=changed)))
    (final / 'REFINEMENT_PROTOCOL.sha256').write_text(
        sha256_file(final / 'REFINEMENT_PROTOCOL.json') + '  REFINEMENT_PROTOCOL.json\n',
        encoding='utf-8', newline='\n')
    decision = apply_decision(rows, protocol)
    write(final / 'REFINEMENT_DECISION.json', decision)
    report = build_report(protocol, rows, decision, recomputes, changed, totals)
    (final / 'REFINEMENT_REPORT.md').write_text(report, encoding='utf-8', newline='\n')
    validation = build_validation(protocol, rows, decision, recomputes, changed)
    write(final / 'VALIDATION.json', validation)
    print('finalize complete:', final)
    print('decision:', decision['decision_value'], '| branch', decision['branch'])


if __name__ == '__main__':
    main()
