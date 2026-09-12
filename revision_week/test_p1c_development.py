import numpy as np
import torch
from p1c_development import polish, energy_interval, read, CONFIG

def test_newton_known_ill_conditioned_quadratic():
    a=torch.diag(torch.tensor([.01,2.,1e6]));truth=torch.tensor([2.,-1.,.5])
    obj=lambda t:.5*(t-truth)@a@(t-truth)
    theta,result=polish(obj,torch.zeros(3),1,read(CONFIG))
    assert result['status']=='PASS'
    np.testing.assert_allclose(theta.numpy(),truth.numpy(),atol=1e-10)

def test_non_spd_is_not_polished_into_validity():
    _,r=polish(lambda t:-t.square().sum(),torch.ones(2),1,read(CONFIG))
    assert r['status']=='PROFILE_FAILURE' and r['failure_reason']=='state_not_SPD'

def test_energy_identity_and_interval():
    rng=np.random.default_rng(7);q,_=np.linalg.qr(rng.normal(size=(20,20)))
    a=(q*np.geomspace(.1,100,20))@q.T;d=rng.normal(size=20)
    r=energy_interval(a,d,.099,8);exact=d@np.linalg.solve(a,d)
    assert r['lower']<=exact<=r['upper']
    assert r['A_matvec_count']==9

def test_diagonal_energy_estimator_exact_without_oracle():
    a=np.diag([.01,1.,100.]);d=np.array([1.,2.,3.])
    r=energy_interval(a,d,.009,8)
    np.testing.assert_allclose(r['upper'],d@np.linalg.solve(a,d),rtol=1e-12)

def test_zero_defect():
    r=energy_interval(np.eye(3),np.zeros(3),.9,8)
    assert r['upper']==0 and r['iterations']==0
