"""No dense state Jacobian/Hessian production path; guarded AD entrypoints."""
from __future__ import annotations
import contextlib,time
import numpy as np
import torch
from common import norm,native
from saeps.autodiff import ResidualLinearization
from saeps.core import MatrixFreeEliminator

def stable_cg(operator,rhs,tolerance,max_iterations):
    """CG with two-pass A-conjugacy restoration and verified residuals.

    In exact arithmetic these are the same unpreconditioned CG directions.
    Stored Krylov vectors are n-vectors, never Jacobian/Hessian columns.
    No diagonal, spectral reference, or dense state solve is used.
    """
    from saeps.solvers import CGResult
    x=torch.zeros_like(rhs);den=float(torch.linalg.vector_norm(rhs))
    if den==0:return CGResult(x,True,0,0.,0.)
    r=rhs-operator(x);directions=[];images=[];energies=[];converged=False;iteration=0
    for iteration in range(1,max_iterations+1):
        p=r.clone();ap=operator(p)
        for _ in range(2):
            for old,aold,energy in zip(directions,images,energies):
                coefficient=torch.dot(old,ap)/energy;p=p-coefficient*old;ap=ap-coefficient*aold
        energy=torch.dot(p,ap)
        if not torch.isfinite(energy) or float(energy)<=torch.finfo(rhs.dtype).tiny:break
        alpha=torch.dot(p,r)/energy;x=x+alpha*p
        directions.append(p);images.append(ap);energies.append(energy)
        # Recompute the true residual; do not accept the recursively propagated one.
        r=rhs-operator(x);absolute=float(torch.linalg.vector_norm(r))
        if absolute/den<=tolerance:converged=True;break
        if len(directions)>=len(rhs):
            # A finite-precision restart discards only search vectors, never the solution.
            directions.clear();images.clear();energies.clear()
    verified=operator(x)-rhs;absolute=float(torch.linalg.vector_norm(verified));relative=absolute/den
    return CGResult(x,converged and relative<=tolerance,iteration,absolute,relative)

@contextlib.contextmanager
def forbid_dense():
    originals=[];attempts=[]
    def forbidden(*a,**kw):attempts.append('forbidden_dense_entry');raise RuntimeError('dense derivative called inside MF route')
    for obj,key in [(torch.func,'jacrev'),(torch.func,'jacfwd'),(torch.func,'hessian'),(torch.autograd.functional,'jacobian'),(torch.autograd.functional,'hessian'),(ResidualLinearization,'explicit_jacobians')]:
        originals.append((obj,key,getattr(obj,key)));setattr(obj,key,forbidden)
    try:yield attempts
    finally:
        for obj,key,value in originals:setattr(obj,key,value)

def mf_so(residual,theta,coordinate,gamma,cfg):
    start=time.perf_counter();n=len(theta);p=len(coordinate)
    with forbid_dense() as attempts:
        lin=ResidualLinearization(residual,theta,coordinate);jl=lin.parameter_columns_matrix_free()
        eliminator=MatrixFreeEliminator(lin,gamma,1e-10,cfg['cg_max_iterations'])
        gnstart=time.perf_counter();solves=[];zs=[];matvecs=0
        def operator(v):
            nonlocal matvecs
            matvecs+=1
            return eliminator.normal_operator(v)
        for column in jl.T:
            rhs=lin.vjp_theta(column);sol=stable_cg(operator,rhs,tolerance=1e-10,max_iterations=cfg['cg_max_iterations'])
            solves.append(dict(iterations=sol.iterations,verified_relative_residual=sol.relative_residual,target_converged=sol.converged));zs.append(sol.solution)
        z=torch.stack(zs,dim=1);gnseconds=time.perf_counter()-gnstart
        v=torch.cat((-z,torch.eye(p)),dim=0);joint=torch.cat((theta,coordinate))
        ell=lambda w:.5*residual(w[:n],w[n:]).square().sum()
        incstart=time.perf_counter();hvs=[]
        for col in v.T:hvs.append(torch.autograd.functional.hvp(ell,joint,col)[1])
        hv=torch.stack(hvs,dim=1);f=v.T@hv+gamma*z.T@z;increment=time.perf_counter()-incstart
        qstart=time.perf_counter();jv=jl-torch.stack([lin.jvp_theta(col) for col in z.T],dim=1);q=jv.T@jv+gamma*z.T@z
        qseconds=time.perf_counter()-qstart
    valid=all(s['verified_relative_residual']<=1e-8 for s in solves) and bool(torch.isfinite(f).all())
    return dict(status='PASS' if valid else 'SOLVER_FAILURE',failure_reason=None if valid else 'GN_verified_residual_failed',F_SO=f,F_GN=q,F_RAW=jl.T@jl,Z_G=z,
        solves=solves,GN_seconds=gnseconds,SO_increment_seconds=increment,GN_quadratic_diagnostic_seconds=qseconds,total_seconds=time.perf_counter()-start,
        operation_counts=dict(lin.operation_counts),HVP_count=p,A_matvec_count=matvecs,
        explicit_jacobians=0,explicit_hessians=0,forbidden_entry_attempts=attempts,route='true_MF_GN_plus_AD_HVP',
        CG_stability='two_pass_A_conjugacy_reorthogonalization_true_residual_each_iteration')
