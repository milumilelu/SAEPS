import json
from pathlib import Path
import pytest
from gates import e1_conclusion,e3_allowed,e4_fresh_allowed,e6_practical_allowed,topological_order,radius_prefix
S=json.loads((Path(__file__).resolve().parents[1]/'protocols/phase2/phase2_spec.json').read_text(encoding='utf-8'))

def pde(valid=10,wins=8):return dict(valid=valid,wins=wins,pair_logs=[1.]*valid)

def test_e1_supported():assert e1_conclusion([pde(),pde(wins=7)],S['e1'])=='SUPPORTED'
def test_no_pde_reversal():assert e1_conclusion([pde(wins=10),pde(wins=5)],S['e1'])=='PARTIALLY_SUPPORTED'
def test_availability_not_silent_drop():assert e1_conclusion([pde(valid=7,wins=7),pde(wins=10)],S['e1'])=='PARTIALLY_SUPPORTED'
def test_negative_science():assert e1_conclusion([pde(wins=4),pde(wins=4)],S['e1'])=='NOT_SUPPORTED'
def test_all_invalid_is_availability_limited():assert e1_conclusion([pde(0,0),pde(0,0)],S['e1'])=='PARTIALLY_SUPPORTED'
def test_bad_denominator():
    with pytest.raises(ValueError):e1_conclusion([pde(4,8),pde()],S['e1'])

def step_inputs():return dict(valid=8,wins=6,median_logR_floor=.1),dict(roots_with_both_sides_micro_and_reverse_valid=8,verified_bidirectional_offset=.05)
def test_e3_both_sides():
    a,b=step_inputs();assert e3_allowed(a,b,S['e3'])
    b['verified_bidirectional_offset']=.025;assert not e3_allowed(a,b,S['e3'])
def test_e3_reference_failure():
    a,b=step_inputs();b['shared_reference_implementation_failure']=True;assert not e3_allowed(a,b,S['e3'])
def test_e3_no_root_doubling():
    a,b=step_inputs();b['roots_with_both_sides_micro_and_reverse_valid']=4;assert not e3_allowed(a,b,S['e3'])
def test_multi_gate_requires_both_norms():
    d=dict(all_original_valid_reloaded=True,available=8,joint_frobenius_spectral_wins=6,median_logR_frobenius=.2,median_logR_spectral=-.1)
    assert not e4_fresh_allowed(d,S['e4']);d['median_logR_spectral']=.1;assert e4_fresh_allowed(d,S['e4'])
def test_kill_test_cannot_use_k16():
    d=dict(k=8,defect='terminal',coverage=21,finite_intervals=21,median_effectivity=3,q90_effectivity=10)
    assert e6_practical_allowed(d,S['e6']);d['k']=16;assert not e6_practical_allowed(d,S['e6'])
def test_kill_test_no_missing_coverage():
    d=dict(k=8,defect='terminal',coverage=20,finite_intervals=21,median_effectivity=2,q90_effectivity=5)
    assert not e6_practical_allowed(d,S['e6'])
def test_dag_complete():assert len(topological_order(S['nodes']))==len(S['nodes'])
def test_cycle_rejected():
    with pytest.raises(ValueError):topological_order([dict(id='a',depends_on=['b']),dict(id='b',depends_on=['a'])])
def test_missing_dependency_rejected():
    with pytest.raises(ValueError):topological_order([dict(id='a',depends_on=['b'])])
def test_radius_no_far_isolated_success():
    rows=[dict(delta=d,resolved=True,branch_valid=True,relative_error=e) for d,e in [(0.001,.05),(.002,.2),(.005,.01)]]
    assert radius_prefix(rows,.1)['last_valid']==.001
def test_radius_unknown_censors():
    rows=[dict(delta=d,resolved=r,branch_valid=True,relative_error=.05) for d,r in [(0.001,True),(.002,False),(.005,True)]]
    assert radius_prefix(rows,.1)==dict(last_valid=.001,disposition='resolution_censored')
def test_radius_all_unresolved_null():
    assert radius_prefix([dict(delta=.001,resolved=False)],.1)['last_valid'] is None
