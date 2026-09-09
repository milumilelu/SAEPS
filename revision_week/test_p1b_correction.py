"""Regression checks for reviewed failure paths; no historical writes/training."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import numpy as np
import pytest
import torch
from p1b_correct import bounded_command, load_center
from p1b_onestep import profile_solve
from core import numerical_mu


def test_process_hard_timeout():
    r=bounded_command([sys.executable,'-c','import time; time.sleep(10)'],.1)
    assert r['status']=='budget_exhausted' and r['wall_seconds']<5


def test_inner_timeout_never_converged():
    residual=lambda th,lp:th-lp
    r=profile_solve(residual,torch.zeros(2),1.,.1,torch.zeros(2),1e-6,cap_s=0.)
    assert r.hit_cap and not r.converged


def test_anchored_profile_gradient_and_counts():
    residual=lambda th,lp:th-lp
    r=profile_solve(residual,torch.zeros(2),1.,.1,torch.zeros(2),1e-8)
    np.testing.assert_allclose(r.theta.numpy(),np.ones(2)/1.1,rtol=1e-7)
    assert r.converged and not r.hit_cap
    assert r.objective_evals>=r.optimizer_evals+2 and r.gradient_evals>=r.optimizer_evals+1


def test_parameter_curvature_does_not_prove_state_SPD():
    a=np.diag([-1.,2.]);b=np.zeros((2,1));c=np.array([[1.]])
    assert (c-b.T@np.linalg.solve(a,b))[0,0]>0
    assert numerical_mu(a)['mu_value'] is None


@pytest.mark.parametrize('name',['p1b_a','p1b_recover','p1b_hvp','p1b_onestep','p1b_finalize'])
def test_archival_runner_cannot_overwrite(name):
    import importlib
    with pytest.raises(RuntimeError):importlib.import_module(name).main()


@pytest.mark.parametrize('cid',['burgers_59','burgers_67','burgers_55','allen_cahn_84'])
def test_saved_data_replay(cid):
    ck,prov,residual,seconds=load_center(cid)
    got=residual(torch.from_numpy(ck['theta']),torch.from_numpy(ck['log_parameter'])).numpy()
    np.testing.assert_allclose(got,ck['residual_at_center'],rtol=0,atol=1e-14)
    assert seconds>0
