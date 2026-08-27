import numpy as np
from scripts.posthoc_variable_projection_v1 import _summary, analyze_blocks

def calc(g, b, gamma=1e-6, h=None):
    h=g if h is None else h
    return analyze_blocks(g,b,b.T,[[2.]],h,b,b.T,[[2.]],gamma,2.,1.,tsvd_cutoffs=(1e-8,1e-10,1e-12))

def test_rank_deficient_psd():
    z=calc(np.diag([2.,0.]),np.array([[1.],[0.]])); assert z["numerical_rank"]==1 and z["nullity"]==1

def test_full_rank_psd():
    z=calc(np.diag([2.,1.]),np.array([[1.],[1.]])); assert z["numerical_rank"]==2

def test_pseudoinverse_schur_identity():
    g=np.diag([2.,0.]); b=np.array([[1.],[0.]]); z=calc(g,b); assert np.isclose(z["F_VP0"],2-(b.T@np.linalg.pinv(g)@b)[0,0])

def test_gamma_zero_continuity():
    g=np.diag([2.,1.]); b=np.array([[.2],[.3]]); z=calc(g,b,1e-12); finite=2-(b.T@np.linalg.solve(g+1e-12*np.eye(2),b))[0,0]; assert abs(z["F_VP0"]-finite)<1e-10

def test_h_admissibility():
    assert calc(np.eye(2),np.ones((2,1)),h=np.eye(2))["exact_gamma0"]["status"]=="ADMISSIBLE_CLASSICAL"
    assert calc(np.eye(2),np.ones((2,1)),h=np.diag([1.,-1.]))["exact_gamma0"]["status"]=="NOT_CLASSICALLY_ADMISSIBLE"

def test_tsvd_consistency():
    z=calc(np.diag([1.,1e-11]),np.array([[.1],[.1]])); assert z["tsvd"]["1e-08"]["rank"]==1 and z["tsvd"]["1e-12"]["rank"]==2

def test_scalar_normalization():
    z=calc(np.eye(1),np.array([[.5]])); assert np.isfinite(z["relative_finite_vs_undamped"])

def test_deterministic_aggregation():
    assert _summary([3.,1.,2.])==_summary([3.,1.,2.]) and _summary([1.,2.,3.])["median"]==2.
