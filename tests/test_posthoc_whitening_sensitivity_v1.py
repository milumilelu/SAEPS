import numpy as np, torch
from scripts.posthoc_whitening_sensitivity_v1 import direction, metrics, whiten

def mats():
    return np.array([[2.,.2],[.2,1.]]),np.array([[1.5,.1],[.1,.8]]),np.array([[1.4,.05],[.05,.7]])

def test_b2_construction_each_c():
    raw,fse,exact=mats()
    for c in (1e-8,1e-10,1e-12):
        z=metrics(raw,fse,exact,c,1e-30); assert np.isclose(z['tau'],c*1.5) and z['lambda_min_B2']>0

def test_cholesky_reconstruction_float64():
    z=metrics(*mats(),1e-10,1e-30); assert z['cholesky_relative_reconstruction_error']<1e-14

def test_triangular_whitening_matches_linear_solve():
    raw,_,_=mats(); b=torch.tensor(raw,dtype=torch.float64); l=torch.linalg.cholesky(b); m=torch.tensor([[1.,2.],[3.,4.]],dtype=torch.float64)
    left=torch.linalg.solve(l,m); expected=torch.linalg.solve(l,left.T).T; assert torch.allclose(whiten(m,l),expected)

def test_manual_metric_path():
    raw,fse,exact=mats(); z=metrics(raw,fse,exact,1e-10,1e-30); tau=1e-10*1.5; l=np.linalg.cholesky(raw+tau*np.eye(2)); w=lambda m:np.linalg.solve(l,np.linalg.solve(l,m).T).T; den=np.linalg.norm(w(exact))+1e-30
    assert np.isclose(z['E_raw'],np.linalg.norm(w(raw-exact))/den) and np.isclose(z['E_SAEPS'],np.linalg.norm(w(fse-exact))/den)

def test_direction_roundoff_tolerance():
    tol={'atol':1e-12,'rtol':1e-10}; assert direction(2.,1.,tol)[0]=='SAEPS_BETTER'; assert direction(1.,2.,tol)[0]=='RAW_BETTER'; assert direction(1.,1.+1e-13,tol)[0]=='NUMERICAL_TIE'
