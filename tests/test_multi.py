from __future__ import annotations
import torch
from saeps.multi import truth_channels, truth_derivatives


def test_multi_truth_derivatives_match_autodiff() -> None:
    x=torch.tensor([0.2,0.7],dtype=torch.float64,requires_grad=True)
    t=torch.tensor([0.1,0.3],dtype=torch.float64,requires_grad=True)
    u,v=truth_channels(x,t)
    ut=torch.autograd.grad(u.sum(),t,create_graph=True)[0]
    vt=torch.autograd.grad(v.sum(),t,create_graph=True)[0]
    ux=torch.autograd.grad(u.sum(),x,create_graph=True)[0]
    vx=torch.autograd.grad(v.sum(),x,create_graph=True)[0]
    uxx=torch.autograd.grad(ux.sum(),x)[0]; vxx=torch.autograd.grad(vx.sum(),x)[0]
    values=truth_derivatives(x,t)
    assert torch.allclose(ut,values[2],atol=1e-13,rtol=1e-13)
    assert torch.allclose(vt,values[3],atol=1e-13,rtol=1e-13)
    assert torch.allclose(uxx,values[4],atol=1e-13,rtol=1e-13)
    assert torch.allclose(vxx,values[5],atol=1e-13,rtol=1e-13)

