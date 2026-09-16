"""Synthetic checks only. Passing these tests is not a SAEPS repository reproduction."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import numpy as np
import pytest
import torch
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from numerics import objective_blocks,reduced_matrices,log_affine_identity,save_blocks,load_blocks
from benchmark_saturation import truth,truth_derivatives,fixed_source,pde_residual,positive_field
from plan_jobs import make_plan
from audit_repository import summarize,audit

DT=torch.float64


def log_residual(theta,param):
    a=torch.exp(param[0])
    return torch.stack([theta[0]**2+a*theta[0]-1.0,
                        theta[1]+2*a-0.3,
                        2*theta[0]+theta[1]-0.2])


def sample_blocks():
    return objective_blocks(log_residual,torch.tensor([.7,.2],dtype=DT),torch.tensor([-.3],dtype=DT))


def test_tikhonov_energy_and_loewner():
    rng=np.random.default_rng(5);j=rng.normal(size=(7,3));jp=rng.normal(size=(7,2));gamma=.3
    z=np.linalg.solve(j.T@j+gamma*np.eye(3),j.T@jp)
    a=np.eye(7)-j@np.linalg.solve(j.T@j+gamma*np.eye(3),j.T)
    np.testing.assert_allclose(jp.T@a@jp,(a@jp).T@(a@jp)+gamma*z.T@z,rtol=1e-12,atol=1e-12)
    assert np.linalg.eigvalsh(jp.T@j@z).min()>-1e-12
    assert not np.allclose(a@a,a)


def test_scalar_log_identity():
    assert log_affine_identity(sample_blocks())['identity_pass']


def test_vector_log_identity():
    def residual(t,p):
        a,b=torch.exp(p)
        return torch.stack([t[0]+a*t[0]-b,2*t[0]+2*a+b,1-t[0]])
    b=objective_blocks(residual,torch.tensor([.4],dtype=DT),torch.tensor([.2,-.1],dtype=DT))
    assert log_affine_identity(b)['identity_pass']


def test_physical_coefficient_has_zero_fixed_remainder():
    def residual(t,a):
        return torch.stack([t[0]**2+a[0]*t[0]-1,t[1]+2*a[0]-.3,2*t[0]+t[1]-.2])
    b=objective_blocks(residual,torch.tensor([.7,.2],dtype=DT),torch.tensor([.8],dtype=DT))
    np.testing.assert_allclose(b['H_parameter_parameter'],b['J_parameter'].T@b['J_parameter'],atol=1e-12)


def test_exact_coordinate_transformation_includes_score():
    th=torch.tensor([.7,.2],dtype=DT);a=torch.tensor([.8],dtype=DT)
    def physical(t,q):return log_residual(t,torch.log(q))
    bp=objective_blocks(physical,th,a);bl=objective_blocks(log_residual,th,torch.log(a))
    rp=reduced_matrices(bp,10);rl=reduced_matrices(bl,10)
    np.testing.assert_allclose(rl['F_SAEPS'],float(a[0])**2*rp['F_SAEPS'],atol=1e-12)
    predicted=float(a[0])**2*rp['H_reduced']+float(a[0])*bp['gradient_parameter'][0]
    np.testing.assert_allclose(rl['H_reduced'],predicted,atol=1e-12)
    assert not np.allclose(rl['H_reduced'],float(a[0])**2*rp['H_reduced'])


def test_preserved_state_metric_is_invariant():
    b=sample_blocks();T=np.diag([.1,10.]);gamma=10
    bt={**b,'J_theta':b['J_theta']@T,'H_theta_theta':T.T@b['H_theta_theta']@T,
        'H_theta_parameter':T.T@b['H_theta_parameter'],'gradient_theta':T.T@b['gradient_theta']}
    r=reduced_matrices(b,gamma);rt=reduced_matrices(bt,gamma,T.T@T)
    for k in ['F_SAEPS','H_reduced','F_SO']:np.testing.assert_allclose(r[k],rt[k],rtol=1e-11,atol=1e-11)
    naive=reduced_matrices(bt,gamma)
    assert not np.allclose(r['F_SAEPS'],naive['F_SAEPS'])


def test_mean_normalization_requires_scaled_gamma():
    b=sample_blocks();m=float(b['residual_count']);c=1/m
    scaled={k:(v*np.sqrt(c) if k.startswith('J_') else v*c if k.startswith(('H_','gradient_')) else v) for k,v in b.items()}
    r=reduced_matrices(b,10);s=reduced_matrices(scaled,10*c)
    np.testing.assert_allclose(s['F_SAEPS'],c*r['F_SAEPS'],atol=1e-12)
    np.testing.assert_allclose(s['H_reduced'],c*r['H_reduced'],atol=1e-12)


def test_inadmissible_state_block_is_not_repaired():
    b=sample_blocks();b['H_theta_theta']=-100*np.eye(2)
    r=reduced_matrices(b,.1)
    assert not r['exact_valid'] and r['H_reduced'] is None
    assert r['C_exact'] is None and np.isfinite(r['F_SAEPS']).all()


def test_spd_does_not_certify_stationarity():
    r=reduced_matrices(sample_blocks(),10)
    assert r['exact_state_block_admissible']
    assert not r['stationarity_certified']
    assert np.linalg.norm(r['newton_response'])>1e-6


def test_penalty_gradient_is_used_after_refinement():
    b=sample_blocks();b['penalty_gradient_theta']=np.zeros(2)
    r=reduced_matrices(b,10)
    np.testing.assert_allclose(r['newton_response'],0,atol=1e-15)


def test_first_order_remainder_formula():
    b=sample_blocks();j=b['J_theta'];q=b['J_parameter'];gtt=j.T@j;gtp=j.T@q;gpp=q.T@q
    stt=b['H_theta_theta']-gtt;stp=b['H_theta_parameter']-gtp;spp=b['H_parameter_parameter']-gpp
    h=1e-5;gamma=10
    def exact_at(t):
        return gpp+t*spp-(gtp+t*stp).T@np.linalg.solve(gtt+gamma*np.eye(2)+t*stt,gtp+t*stp)
    derivative=(exact_at(h)-exact_at(-h))/(2*h)
    r=reduced_matrices(b,gamma)
    np.testing.assert_allclose(r['F_SO']-r['F_SAEPS'],derivative,rtol=1e-8,atol=1e-8)


def test_manufactured_source_at_truth():
    x=torch.linspace(0,1,31,dtype=DT);t=torch.linspace(0,.4,31,dtype=DT)
    u,ut,uxx=truth_derivatives(x,t)
    r=pde_residual(u,ut,uxx,torch.tensor(np.log(1.2),dtype=DT),fixed_source(x,t))
    torch.testing.assert_close(r,torch.zeros_like(r),rtol=0,atol=1e-14)
    assert float(u.min())>=.7


def test_analytic_field_derivatives():
    x=torch.tensor([.17,.36],dtype=DT,requires_grad=True);t=torch.tensor([.11,.28],dtype=DT,requires_grad=True)
    u=truth(x,t);ux=torch.autograd.grad(u.sum(),x,create_graph=True)[0]
    uxx=torch.autograd.grad(ux.sum(),x,retain_graph=True)[0]
    ut=torch.autograd.grad(u.sum(),t)[0]
    _,at,axx=truth_derivatives(x,t)
    torch.testing.assert_close(ut,at);torch.testing.assert_close(uxx,axx)


def test_nonlinear_physical_parameter_second_derivative_nonzero():
    u=torch.tensor([.7,1.1,1.3],dtype=DT)
    q=torch.tensor(1.2,dtype=DT,requires_grad=True)
    def response(k):return -u/(1+k*u)
    h=torch.func.jacfwd(torch.func.jacrev(response))(q)
    assert bool((h.abs()>1e-3).all())
    jac=torch.func.jacrev(response)(q)
    assert not torch.allclose(h/jac,torch.ones_like(h)*(h[0]/jac[0]))


def test_positive_field_and_fixed_source():
    raw=torch.tensor([-100.,0,100.],dtype=DT)
    assert bool((positive_field(raw)>=.05).all())
    x=torch.tensor([.1],dtype=DT,requires_grad=True);t=torch.tensor([.2],dtype=DT,requires_grad=True)
    assert not fixed_source(x,t).requires_grad


def test_archive_roundtrip_and_no_overwrite(tmp_path):
    b=sample_blocks();path=tmp_path/'b.npz';save_blocks(path,b,10)
    got,gamma=load_blocks(path);assert gamma==10
    np.testing.assert_array_equal(got['J_theta'],b['J_theta'])
    with pytest.raises(FileExistsError):save_blocks(path,b,10)


def test_input_validation():
    with pytest.raises(ValueError):objective_blocks(log_residual,torch.tensor([.7,.2]),torch.tensor([-.3]))
    with pytest.raises(ValueError):reduced_matrices(sample_blocks(),0)
    with pytest.raises(ValueError):reduced_matrices(sample_blocks(),float('nan'))


def test_plan_counts_and_no_execution():
    cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'configs/protocol.yaml').read_text())
    base=make_plan(cfg);full=make_plan(cfg,True)
    assert len(base)==32 and len(full)==44
    assert sum(r['split']=='development' for r in base)==8
    assert all(r['status']=='NOT_RUN' for r in full)
    assert len({r['job_id'] for r in full})==44


def test_statistics_preserve_invalid_missing_and_ratio_definitions():
    records={1:dict(binding_valid=True,E_raw=8.,E_SAEPS=1.,status='PASS'),
             2:dict(binding_valid=True,E_raw=2.,E_SAEPS=2.,status='PASS'),
             3:dict(binding_valid=False,status='CHECKPOINT_INVALID')}
    r=summarize(records,[1,2,3,4])
    assert r['planned']==4 and r['valid']==2 and r['missing']==1
    assert r['planned_wins']==1 and r['ratio_of_median_errors']==5/1.5
    assert r['median_paired_ratio']==4.5 and r['one_sided_sign_p_valid_non_ties']==.5


def test_git_audit_fixture_reads_tag_not_current_files(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True)
    git('init');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
    path=repo/'outputs/runs/v4_2_corrected_confirmation/records/seed_55.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dict(seed=55,binding_valid=True,E_raw=2.,E_SAEPS=.1,F_raw=1,status='PASS')))
    git('add','.');git('commit','-m','synthetic fixture');git('tag','fixture-v1')
    path.write_text('{}')
    r=audit(repo,'fixture-v1')
    assert r['cohorts']['Burgers']['valid']==1
    assert r['cohorts']['Burgers']['missing']==14
    assert path.read_text()=='{}'
