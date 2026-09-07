import inspect
import json
from pathlib import Path
import numpy as np
import pytest
from saeps.v6.operators import DenseOperators, load_blocks
from saeps.v6.defect_response import initialize
from saeps.v6.preconditioners import build, Exact, LowRank
from saeps.v6.pcg import trajectory
from saeps.v6.curvature import curvature
from saeps.v6.stopping import indicator_stop


@pytest.mark.parametrize('seed',range(8))
def test_spd_response_and_defect(seed):
    rng=np.random.default_rng(seed); n=12
    j=rng.normal(size=(20,n)); g=j.T@j+np.eye(n)
    h=g+np.eye(n)*0.3; gamma=.2; b=rng.normal(size=n); c=b+rng.normal(size=n)*.1
    ops=DenseOperators(g,h,gamma); init=initialize(ops,b)
    assert init['status']=='PASS'
    a=h+gamma*np.eye(n); m=g+gamma*np.eye(n)
    z0=init['z']; zs=np.linalg.solve(a,c)
    assert np.linalg.norm(z0-np.linalg.solve(m,b))<1e-9
    assert np.allclose(c-a@z0,(c-b)-(h-g)@z0+b-m@z0)
    for name,rank in [('diagonal',0),('nystrom',8),('recycled_ritz',8),('hybrid_defect',8),('exact_gn',-1)]:
        p=build(name,rank,seed,ops,init,c-a@z0)
        d=rng.normal(size=n)
        assert np.allclose(p(d),np.linalg.solve(p.matrix(),d),rtol=1e-8,atol=1e-8)
        if isinstance(p,LowRank): assert np.allclose(p(d),p.woodbury(d),atol=1e-8)
        result=trajectory(ops,c,2.,z0,p,n)
        old=float('inf')
        for row in result['rows']:
            z=np.array(row['z']); gap=(z-zs)@a@(z-zs)
            assert abs((row['K']-(2-c@zs))-gap)<1e-8
            assert gap<=old+1e-8
            old=gap
    direct=trajectory(ops,c,2.,np.zeros(n),Exact(m),n)
    warm=trajectory(ops,c,2.,z0,Exact(m),n)
    assert np.allclose(direct['rows'][-1]['z'],warm['rows'][-1]['z'],atol=1e-8)


def test_counts_and_no_oracle_signature():
    ops=DenseOperators(np.eye(3),np.eye(3),1.)
    ops.G(np.ones((3,2)),'setup'); ops.A(np.ones(3),'outer')
    assert ops.snapshot()['Gv']==2 and ops.snapshot()['Hv']==1
    assert ops.snapshot()['HVP_actual']==0
    assert 'oracle' not in inspect.signature(trajectory).parameters
    assert indicator_stop(1e-5,1.) and not indicator_stop(1.,1.)


def test_rank_zero_and_negative_curvature():
    ops=DenseOperators(np.zeros((3,3)),np.eye(3),1.)
    cache=initialize(ops,np.ones(3))
    p=build('nystrom',2,0,ops,cache,np.ones(3))
    assert p.rank==0 and np.allclose(p(np.ones(3)),1.)
    bad=DenseOperators(np.eye(3),-2*np.eye(3),1.)
    result=trajectory(bad,np.ones(3),1.,np.zeros(3),p,3)
    assert result['status']=='NUMERICAL_FAILURE'


def test_actual_archive_algebra():
    root=Path(__file__).resolve().parents[2]
    record=json.loads((root/'outputs/posthoc/exact_fixed_state_v3/burgers/seed_55.json').read_text())
    g,h,b,c,gll,hll,gamma=load_blocks(record)
    m=g+gamma*np.eye(len(g)); a=h+gamma*np.eye(len(g))
    z=np.linalg.solve(m,b); ref=hll-c@np.linalg.solve(a,c)
    assert abs(ref-record['rerun']['H_red_exact'])/(abs(ref)+1e-8)<1e-6
    d=c-a@z
    assert abs(curvature(hll,c,z,a@z)-ref-d@np.linalg.solve(a,d))/(abs(ref)+1e-8)<1e-8


def test_timed_runner_serialization_and_prefix_policy():
    import importlib.util
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('phase15_runner',root/'scripts/v6/run_phase15.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    config=json.loads((root/'configs/v6/development/phase15.json').read_text())
    rng=np.random.default_rng(94);j=rng.normal(size=(15,8));g=j.T@j+np.eye(8)
    b=rng.normal(size=8);blocks=(g,g+.1*np.eye(8),b,b+.1,2.,2.1,.2)
    candidate=config['candidates'][1]
    result=module.measured_case(blocks,candidate,4,0,'gn',config)
    json.dumps(result,allow_nan=False)
    assert len(result['component_timing_repeats']['initial_GN_seconds'])==5
    assert module.prefix(result,budget=0)['selected']['step']==0
    adaptive=module.prefix(result,adaptive=True)
    assert adaptive['selected']['step']<=5
    if adaptive.get('indicator_triggered'):
        assert adaptive['selected']['indicator_relative']<.001
    # Counter-costed rows are available even when full residual convergence fails.
    assert result['rows'][0]['counts']['Hv']>=2
    assert all(r['oracle']['identity_relative_error']<1e-8 for r in result['rows'])
    assert module.prefix({'status':'CHECKPOINT_INVALID','rows':[]},budget=0)['status']=='CHECKPOINT_INVALID'
