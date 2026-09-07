"""Fully reorthogonalized Lanczos/Galerkin initialization with reusable products."""
import numpy as np


def initialize(ops,b,rtol=1e-10):
    n=len(b); scale=max(np.linalg.norm(b),1e-8)
    if np.linalg.norm(b)==0:
        return {'status':'PASS','z':np.zeros(n),'Q':np.empty((n,0)), 'GQ':np.empty((n,0)), 'history':[0.]}
    q=b/np.linalg.norm(b); Q=np.empty((n,0)); GQ=Q.copy(); history=[]
    z=np.zeros(n)
    for _ in range(n):
        Q=np.column_stack((Q,q)); gq=ops.G(q,'initial_GN'); GQ=np.column_stack((GQ,gq))
        t=Q.T@GQ+ops.gamma*(Q.T@Q); t=(t+t.T)/2
        y=np.linalg.solve(t,Q.T@b); z=Q@y
        residual=b-ops.G(z,'initial_GN_verify')-ops.gamma*z
        rr=float(np.linalg.norm(residual)/scale); history.append(rr)
        if rr <= rtol:
            return {'status':'PASS','z':z,'Q':Q,'GQ':GQ,'history':history}
        w=gq+ops.gamma*q
        for _ in range(2):
            w-=Q@(Q.T@w)
        norm=np.linalg.norm(w)
        if norm <= np.finfo(float).eps*max(np.linalg.norm(gq),1e-30):
            break
        q=w/norm
    return {'status':'SOLVER_FAILURE','z':z,'Q':Q,'GQ':GQ,'history':history,
            'failure_reason':'GN verified residual not attained before Lanczos termination'}
