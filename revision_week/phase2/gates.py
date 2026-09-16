"""Prospective Phase 2 decision functions. No experiment execution or file writes."""
from __future__ import annotations
import math

def e1_conclusion(pdes, cfg):
    if len(pdes)!=2:raise ValueError('two PDE records required')
    for r in pdes:
        if not 0<=r['wins']<=r['valid']<=cfg['planned_per_pde']:raise ValueError('invalid denominator')
    enough=all(r['valid']>=cfg['minimum_valid_per_pde'] for r in pdes)
    wins=sum(r['wins'] for r in pdes);valid=sum(r['valid'] for r in pdes)
    # The pooled median is supplied explicitly; a mean of PDE medians is invalid.
    logs=[x for r in pdes for x in r['pair_logs']]
    if len(logs)!=valid or any(not math.isfinite(x) for x in logs):raise ValueError('one finite floor-log per valid pair required')
    logs=sorted(logs);median=(logs[(len(logs)-1)//2]+logs[len(logs)//2])/2 if logs else None
    if enough and wins>=cfg['minimum_planned_wins'] and all(r['wins']>r['valid']/2 for r in pdes) and median>0:return 'SUPPORTED'
    if enough and wins<=valid/2:return 'NOT_SUPPORTED'
    return 'PARTIALLY_SUPPORTED'

def e3_allowed(e1_pde, e2_pde, cfg):
    """Per-PDE gate; validity count refers to BOTH sides of the SAME root."""
    return bool(e1_pde['valid']>=cfg['minimum_e1_valid_per_pde']
        and e1_pde['wins']>=cfg['minimum_e1_wins_per_pde']
        and e1_pde['median_logR_floor']>0
        and e2_pde['roots_with_both_sides_micro_and_reverse_valid']>=cfg['minimum_ready_roots_per_pde']
        and e2_pde['verified_bidirectional_offset']>=cfg['required_bidirectional_reach']
        and not e2_pde.get('shared_reference_implementation_failure',False))

def e4_fresh_allowed(dev,cfg):
    return bool(dev['all_original_valid_reloaded'] and dev['available']==cfg['development_expected_valid']
        and dev['joint_frobenius_spectral_wins']>=cfg['development_min_joint_norm_wins']
        and dev['median_logR_frobenius']>0 and dev['median_logR_spectral']>0)

def e6_practical_allowed(dev,cfg):
    return bool(dev['k']==cfg['gate_k'] and dev['defect']==cfg['primary_defect']
        and dev['coverage']==cfg['gate_min_coverage'] and dev['finite_intervals']==cfg['expected_usable']
        and dev['median_effectivity']<=cfg['gate_median_effectivity_max']
        and dev['q90_effectivity']<=cfg['gate_q90_effectivity_max'])

def topological_order(nodes):
    ids=[n['id'] for n in nodes]
    if len(set(ids))!=len(ids):raise ValueError('duplicate node')
    remaining={n['id']:set(n['depends_on']) for n in nodes};order=[]
    if any(not deps<=set(ids) for deps in remaining.values()):raise ValueError('missing dependency')
    while remaining:
        ready=[n for n,deps in remaining.items() if deps<=set(order)]
        if not ready:raise ValueError('cyclic dependency')
        for node in ready:order.append(node);del remaining[node]
    return order

def radius_prefix(rows,threshold):
    """Ordered positive deltas; unknown middle points censor rather than disappear."""
    rows=sorted(rows,key=lambda r:r['delta']);last=None;started=False
    for r in rows:
        if not r['resolved']:
            if started:return dict(last_valid=last,disposition='resolution_censored')
            continue
        started=True
        if not r['branch_valid']:return dict(last_valid=last,disposition='branch_limited')
        if r['relative_error']>threshold:return dict(last_valid=last,disposition='below_min_resolved_delta' if last is None else 'first_error_failure')
        last=r['delta']
    return dict(last_valid=last,disposition='right_censored' if started else 'unresolved')
