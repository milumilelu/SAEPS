import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pytest
from common import *
from finalize_phase2 import step_summary,multi_summary

def test_actual_watchdog_kills_child(tmp_path):
    sentinel=tmp_path/'must_not_exist.txt'
    child='import time; from pathlib import Path; time.sleep(1); Path('+repr(str(sentinel))+').write_text("orphan")'
    parent='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(5)'
    r=bounded_process([sys.executable,'-c',parent],tmp_path,.3)
    assert r['failure_reason']=='budget_exhausted' and r['exit_code']!=0
    assert r['wall_seconds']<2
    time.sleep(1.1)
    assert not sentinel.exists() and r['process_tree_kill_enforced']
    assert len(r['observed_process_ids'])>=2

def test_interrupted_claim_is_terminal_without_retraining(tmp_path,monkeypatch):
    import execution
    monkeypatch.setattr(execution,'ROOT',tmp_path);monkeypatch.setattr(execution,'OUT',tmp_path/'revision_week/outputs/phase2_v1')
    config=tmp_path/'config.json';write(config,read(SPEC));job=dict(kind='fresh',group='burgers',seed=1000007)
    dest=execution.OUT/'tasks/E1/test';write(dest/'claim.json',dict(job=job,config_sha256=canon_sha(config),timeout_seconds=7,source_commit='unit_test'))
    before=sha(dest/'claim.json')
    def forbidden(*a,**k):raise AssertionError('interrupted run must not spawn')
    monkeypatch.setattr(execution,'bounded_process',forbidden)
    _,r=execution.task('E1','test',job,config)
    assert r['execution_disposition']=='INTERRUPTED' and r['timing_kind']=='conservative_upper_bound_not_measured'
    assert sha(dest/'claim.json')==before
    _,again=execution.task('E1','test',job,config)
    assert again==r
    with (dest/'claim.json').open('a') as f:f.write(' ')
    with pytest.raises(RuntimeError,match='hash changed'):execution.task('E1','test',job,config)

def test_partial_root_is_not_promoted_to_independent_pair():
    rows=[]
    for method,actual in [('SO',2.),('SAEPS-GN',1.)]:
        rows.append(dict(group='burgers',seed=1000007,offset=.05,method=method,status='PASS',actual=actual,error_estimate=.01,step=.01))
    result=step_summary(rows)
    assert result['complete_roots']==0 and result['root_wins']==0
    assert result['roots'][0]['mean_SO_minus_GN'] is None
    rows += [dict(r,offset=-.05) for r in rows]
    assert step_summary(rows)['complete_roots']==1

def test_two_parameter_gate_keeps_invalid_in_denominator():
    win=dict(binding_valid=True,metrics={k:dict(strict_SO_win=True,strict_GN_win=False,logR_floor=1.) for k in ['fro','spectral']})
    r=multi_summary([win]*8+[dict(binding_valid=False)]*2)
    assert r['planned']==10 and r['valid']==8 and r['conclusion']=='PARTIALLY_SUPPORTED'

def test_near_zero_reference_is_not_resolved():
    from numerics import matrices
    g=np.eye(3);h=np.diag([1.,1.,0.]);r=matrices(g,h,2,.1)
    assert not r['binding_valid'] and r['status']=='NUMERICAL_FAILURE'

def test_mean_sum_scaling_includes_gamma():
    from numerics import matrices
    rng=np.random.default_rng(42);j=rng.normal(size=(8,4));g=j.T@j;h=g+np.eye(4)
    a=matrices(g,h,3,.2);b=matrices(g/8,h/8,3,.2/8)
    for k in ['F_RAW','F_GN','F_SO','F_star']:assert np.allclose(a[k]/8,b[k],atol=1e-12)

def test_quartic_fd_and_reference_tie():
    from numerics import fd_record,matrices
    delta=.01;zero=dict(loss=0.,eta_phi=1e-15,precision_valid=True);side=dict(zero,loss=delta**2+3*delta**4)
    assert abs(fd_record(delta,side,zero,side,2.,1e-10)['K_FD']-(2+6*delta**2))<1e-12
    r=matrices(np.eye(3),np.eye(3),2,.1)
    assert not r['metrics']['fro']['strict_SO_win'] and r['metrics']['fro']['logR_floor']==0

def test_all_future_handlers_import_without_fresh_inputs():
    import workers,locality,one_step,run_all,finalize_phase2
    assert all(callable(f) for f in [workers.fresh,workers.scale,locality.run,one_step.run,run_all.freeze,finalize_phase2.finalize])

def test_figures_handle_all_future_runs_unavailable(tmp_path,monkeypatch):
    import finalize_phase2 as f
    actual=OUT
    monkeypatch.setattr(f,'OUT',tmp_path)
    data=dict(E0=read(actual/'tasks/E0/dev02/result.json'),E4D=read(actual/'tasks/E4D/dev01/result.json'),
              E6D=read(actual/'tasks/E6D/dev03/result.json'),E2=[],E4C=[],E5C=[])
    f.plots(data,dict(E1=dict(rows=[]),E3=dict(roots=[],attempted_candidates=0,valid_candidates=0,accepted=0)))
    assert len(list((tmp_path/'final/figures').glob('*.svg')))>=9
