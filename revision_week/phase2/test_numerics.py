import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pytest
import torch
from common import read,SPEC,process_memory
from numerics import matrices,dense_curvature,Objective,correct,lanczos_inverse,fd_record,lbfgs_root
from matrix_free import mf_so,forbid_dense

@pytest.mark.parametrize('p',[1,2])
def test_full_form_identity(p):
    rng=np.random.default_rng(827);j=rng.normal(size=(12,5+p));g=j.T@j
    h=g.copy();h[:5,:5]+=np.eye(5);h[5:,5:]+=2*np.eye(p)
    r=matrices(g,h,5,.2)
    assert r['binding_valid'] and r['identity_error']<1e-12
    assert np.linalg.eigvalsh(r['F_SO']-r['F_star']).min()>-1e-12

@pytest.mark.parametrize('p',[1,2])
def test_real_nonlinear_mf_and_counts(p):
    t=torch.tensor([.2,-.1,.3]);l=torch.ones(p)*.15
    def residual(t,l):
        return torch.cat((t+t.square()/3+l.sum(),torch.sin(t)-l.sum(),l*2))
    r=dense_curvature(residual,t,l,.7);m=mf_so(residual,t,l,.7,{'cg_max_iterations':500})
    assert m['status']=='PASS'
    assert np.allclose(m['F_SO'].numpy(),r['F_SO'],atol=1e-10,rtol=1e-10)
    assert m['A_matvec_count']==sum(2*s['iterations']+2 for s in m['solves'])
    assert m['explicit_jacobians']==m['explicit_hessians']==0
    with forbid_dense(),pytest.raises(RuntimeError):torch.func.jacrev(residual)

@pytest.mark.parametrize('spectrum',[np.ones(20),np.geomspace(.01,1e4,20),np.arange(1,21)])
def test_lanczos_enclosure(spectrum):
    a=np.diag(spectrum);d=np.random.default_rng(3).normal(size=20)
    r=lanczos_inverse(a,d,float(spectrum.min())*.999)
    q=d@np.linalg.solve(a,d)
    for row in r['rows']:
        assert row['lower']<=q+1e-9*abs(q)
        assert row['upper']>=q-1e-9*abs(q)
        assert row['lanczos_relative_residual']<1e-10
        assert row['orthogonality']<1e-10
    assert r['matvecs']<=16

def test_strict_solver_mean_sum_and_real_lbfgs():
    residual=lambda t,l:torch.cat((t-torch.tensor([.3,-.2]),l))
    obj=Objective(residual,torch.zeros(1),torch.zeros(2),.2)
    t,r=correct(obj,torch.zeros(2))
    assert r['status']=='PASS'
    assert np.allclose(t.numpy(),np.array([.3,-.2])/1.2,atol=1e-9)
    t,b=lbfgs_root(obj,torch.zeros(2),read(SPEC)['strict_solver'])
    assert b['function_evals']>0 and obj.diagnostic(t)['gradient']<1e-8

def test_saddle_is_not_accepted():
    residual=lambda t,l:torch.cat((t.square()-1,l))
    obj=Objective(residual,torch.zeros(1),torch.zeros(1),0)
    _,r=correct(obj,torch.zeros(1),branch=True)
    assert r['status']!='PASS' and not r['diagnostic']['SPD']['mu_value']

def test_fd_floor_censors_cancellation():
    zero={'loss':1.,'eta_phi':1e-14,'precision_valid':True}
    delta=.01;side=dict(zero,loss=1+delta**2)
    assert fd_record(delta,side,zero,side,2.,1e-10)['resolved']
    assert not fd_record(1e-8,zero,zero,zero,2.,1e-10)['resolved']

def test_native_memory_counter():
    if os.name=='nt':assert process_memory(os.getpid())['rss']>0

def test_real_continuation_reverse_and_fixed_anchor(tmp_path):
    from common import Deadline
    from locality import follow,audit
    residual=lambda t,l:torch.stack((t[0]-l[0],t[1]-.1*l[0]**2,2*l[0]))
    payload=dict(theta=torch.zeros(2),coordinate=torch.zeros(1),anchor=torch.zeros(2),gamma=.1)
    obj=Objective(residual,payload['coordinate'],payload['anchor'],.1)
    zero=audit(obj,payload['theta'],tmp_path/'zero')
    r=follow(residual,payload,.01,tmp_path/'forward',read(SPEC),Deadline(30),zero)
    assert r['reached_target'] and len(r['accepted'])==2 and r['reverse_valid']
    assert r['final_audit']['precision_valid']
    assert torch.equal(payload['anchor'],torch.zeros(2))

def test_multiple_minima_does_not_switch_branch(tmp_path):
    from common import Deadline
    from locality import follow,audit
    residual=lambda t,l:torch.stack((t[0]**2-1-l[0],2*l[0]))
    payload=dict(theta=torch.ones(1),coordinate=torch.zeros(1),anchor=torch.ones(1),gamma=.01)
    zero=audit(Objective(residual,payload['coordinate'],payload['anchor'],.01),payload['theta'],tmp_path/'zero')
    r=follow(residual,payload,.005,tmp_path/'positive_branch',read(SPEC),Deadline(30),zero)
    from common import load_payload
    assert r['reached_target'] and load_payload(tmp_path/'positive_branch/endpoint_state.pt')['theta'][0]>0
