"""Synthetic tests only; none trains or accesses confirmation samples."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).parent))
from core import evaluate, quadratic, reference, update, numerical_mu, error_control, refine, directional_operators


@pytest.mark.parametrize('p',[1,2,3])
@pytest.mark.parametrize('seed',range(8))
def test_arbitrary_response_identities(p,seed):
    rng=np.random.default_rng(seed); n=9; gamma=.3
    j=rng.normal(size=(n+p+5,n+p)); g=j.T@j
    x=rng.normal(size=(n,n)); a=x.T@x+2*np.eye(n)
    b=rng.normal(size=(n,p)); c=-np.eye(p)  # indefinite/negative reduced Hessian allowed
    h=np.block([[a-gamma*np.eye(n),b],[b.T,c]])
    z=rng.normal(size=(n,p)); e=evaluate(g,h,n,gamma,z)
    fg=reference(g,n,gamma); fs=reference(h,n,gamma)
    m=g[:n,:n]+gamma*np.eye(n); r=e['R_G']; d=e['D']
    np.testing.assert_allclose(e['F_SO'],e['Q_G']+e['correction'],rtol=1e-10,atol=1e-10)
    np.testing.assert_allclose(e['Q_G']-fg,r.T@np.linalg.solve(m,r),rtol=1e-10,atol=1e-10)
    gap=e['F_SO']-fs
    np.testing.assert_allclose(gap,d.T@np.linalg.solve(a,d),rtol=1e-10,atol=1e-10)
    w=.03*rng.normal(size=(n,p))
    np.testing.assert_allclose(update(e['F_SO'],d,w,a@w),quadratic(c,b,a,z+w),rtol=1e-10,atol=1e-10)
    # Known exact-arithmetic construction lower bound A >= 2 I.
    assert np.linalg.eigvalsh(d.T@d/2-gap).min() >= -1e-10
    y=rng.normal(size=(p,p)); l=np.linalg.cholesky(y@y.T+np.eye(p))
    t=np.linalg.solve(l.T,np.eye(p)); dg=d@t
    np.testing.assert_allclose(t.T@gap@t,dg.T@np.linalg.solve(a,dg),rtol=1e-10,atol=1e-10)
    assert np.linalg.eigvalsh(dg.T@dg/2-t.T@gap@t).min() >= -1e-10


def test_failure_and_resolution_paths():
    assert numerical_mu(-np.eye(3))['spd_status']=='not_SPD'
    assert numerical_mu(np.diag([1.,1e-16]))['spd_status']=='spd_unresolved'
    assert numerical_mu(np.full((2,2),np.nan))['spd_status']=='nonfinite'
    assert error_control(np.zeros((1,1)),np.ones((2,1)),1)['U_relative_if_available'] is None
    assert error_control(np.eye(1),np.ones((2,1)),None)['relative_status']=='mu_unresolved'
    assert refine(np.eye(2),np.ones((2,1)),np.eye(1),np.zeros((2,1)),1,.01,0)['status']=='tolerance_not_met'
    assert refine(np.eye(2),np.ones((2,1)),np.eye(1),np.zeros((2,1)),None,.01,5)['status']=='mu_unresolved'
    assert numerical_mu(np.eye(3))['bound_status']=='numerical_bound_estimate' # repeated eigenvalues
    with pytest.raises(ValueError): evaluate(np.full((3,3),np.nan),np.eye(3),2,.1,np.zeros((2,1)))
    with pytest.raises(FileNotFoundError): Path('__missing_historical_center__.json').read_text()
    g=np.eye(3); z=np.ones((2,1)); e=evaluate(g,g,2,.1,z)
    assert np.linalg.norm(e['R_G'])>1 # inexact solve not labelled converged
    assert e['Q_G'][0,0] != (g[2:,2:]-g[:2,2:].T@z)[0,0]


def test_real_scalar_network_operator_and_log_identity():
    from saeps.scalar import scalar_network
    torch.set_default_dtype(torch.float64)
    gen=torch.Generator().manual_seed(950)
    n=9; x=torch.linspace(0,1,7); t=x*.3
    joint=torch.randn(n+1,generator=gen)*.2
    weights=torch.linspace(.5,2.,7).sqrt()
    def residual(v):
        u,ut,ux,uxx=scalar_network(v[:n],x,t,2)
        return weights*(ut+u*ux-torch.exp(v[n])*uxx)
    objective=lambda v:.5*(residual(v)**2).sum()
    jac=torch.func.jacrev(residual)(joint); hes=torch.func.hessian(objective)(joint)
    grad=torch.func.grad(objective)(joint)
    v=torch.randn(n+1,generator=gen); y=torch.randn(7,generator=gen)
    torch.testing.assert_close(torch.func.jvp(residual,(joint,),(v,))[1],jac@v,rtol=1e-8,atol=1e-10)
    torch.testing.assert_close(torch.func.vjp(residual,joint)[1](y)[0],jac.T@y,rtol=1e-8,atol=1e-10)
    torch.testing.assert_close(torch.func.jvp(torch.func.grad(objective),(joint,),(v,))[1],hes@v,rtol=1e-8,atol=1e-10)
    torch.testing.assert_close(hes[-1,-1]-(jac.T@jac)[-1,-1],grad[-1],rtol=1e-8,atol=1e-10)
    physical=joint[-1].exp()
    def physical_obj(mu):
        return objective(torch.cat((joint[:-1],mu.log().reshape(1))))
    gm=torch.func.grad(physical_obj)(physical); hm=torch.func.hessian(physical_obj)(physical)
    torch.testing.assert_close(hes[-1,-1],physical**2*hm+physical*gm,rtol=1e-8,atol=1e-10)
    errors=[]
    for step in [1e-2,1e-3,1e-4,1e-5,1e-6]:
        fd=(objective(joint+step*v)-objective(joint-step*v))/(2*step)
        errors.append(float(abs(fd-grad@v)))
    assert errors[2]<errors[0] and sum(e<1e-7 for e in errors)>=2
    z=np.random.default_rng(4).normal(size=(n,1)); gamma=.05
    op=directional_operators(
        lambda u:torch.func.jvp(residual,(joint,),(torch.tensor(u),))[1].numpy(),
        lambda u:torch.func.jvp(torch.func.grad(objective),(joint,),(torch.tensor(u),))[1].numpy(),z,gamma)
    dense=evaluate((jac.T@jac).numpy(),hes.numpy(),n,gamma,z)
    for key in ['Q_G','F_SO','D']:
        np.testing.assert_allclose(op[key],dense[key],rtol=1e-8,atol=1e-10)


def test_indefinite_algebra_without_profile_claim():
    h=np.diag([-2.,3.,-.1]); g=np.eye(3); z=np.ones((2,1)); gamma=.1
    e=evaluate(g,h,2,gamma,z); a=h[:2,:2]+gamma*np.eye(2)
    np.testing.assert_allclose(e['F_SO']-reference(h,2,gamma),e['D'].T@np.linalg.solve(a,e['D']))
    assert numerical_mu(a)['bound_status']=='indicator_only'
