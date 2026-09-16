"""Analytic ingredients for E3. No training is performed by this module.

The fitted residual is nonlinear in the physical saturation coefficient kappa.
All forcing values must be detached at the true coefficients before inference.
"""
from __future__ import annotations
import math
import torch


def truth(x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    return 1 + 0.2*torch.exp(-t)*torch.cos(2*math.pi*x) + 0.1*torch.exp(-2*t)*torch.sin(4*math.pi*x)


def truth_derivatives(x: torch.Tensor, t: torch.Tensor) -> tuple[torch.Tensor, ...]:
    u = truth(x,t)
    ut = -0.2*torch.exp(-t)*torch.cos(2*math.pi*x) - 0.2*torch.exp(-2*t)*torch.sin(4*math.pi*x)
    uxx = -0.2*(2*math.pi)**2*torch.exp(-t)*torch.cos(2*math.pi*x) - 0.1*(4*math.pi)**2*torch.exp(-2*t)*torch.sin(4*math.pi*x)
    return u,ut,uxx


def fixed_source(x: torch.Tensor, t: torch.Tensor, diffusion: float=0.01,
                 rho_true: float=1.0, kappa_true: float=1.2) -> torch.Tensor:
    if diffusion <= 0 or rho_true <= 0 or kappa_true <= 0:
        raise ValueError('Physical coefficients must be positive')
    u,ut,uxx=truth_derivatives(x,t)
    return (ut-diffusion*uxx-rho_true*u/(1+kappa_true*u)).detach()


def pde_residual(u: torch.Tensor, ut: torch.Tensor, uxx: torch.Tensor,
                 log_kappa: torch.Tensor, source: torch.Tensor,
                 diffusion: float=0.01, rho: float=1.0) -> torch.Tensor:
    # Use positive neural fields; do not clip or silently repair a bad denominator.
    return ut-diffusion*uxx-rho*u/(1+torch.exp(log_kappa)*u)-source


def positive_field(raw: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.softplus(raw)+0.05
