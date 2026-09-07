"""Scalar PCG with explicit residual audit and costed per-step snapshots."""
from time import perf_counter
import numpy as np
from .curvature import curvature


def trajectory(ops,c,hll,z,precondition,maximum_steps,rtol=1e-10):
    started=perf_counter(); verify_seconds=0.; rows=[]
    z=z.copy(); scale=max(np.linalg.norm(c),1e-8)
    tick=perf_counter()
    az=ops.A(z,'initial_defect') if np.any(z) else np.zeros_like(z)
    initial_seconds=perf_counter()-tick
    r=c-az; w=precondition(r); p=w.copy(); rz=float(r@w)
    for step in range(maximum_steps+1):
        tick=perf_counter()
        explicit=c-ops.A(z,'verification')
        discrepancy=float(np.linalg.norm(explicit-r)/scale)
        eta=float(explicit@precondition(explicit))
        verify_seconds+=perf_counter()-tick
        k=curvature(hll,c,z,az)
        rows.append({'step':step,'z':z.tolist(),'K':k,'eta':eta,
                     'indicator_relative':eta/(abs(k)+1e-8),
                     'defect_relative':float(np.linalg.norm(explicit)/scale),
                     'recursive_defect_relative':float(np.linalg.norm(r)/scale),
                     'residual_discrepancy':discrepancy,'counts':ops.snapshot(),
                     'elapsed_seconds':perf_counter()-started,
                     'initial_defect_seconds':initial_seconds,'verification_seconds':verify_seconds})
        if not np.isfinite([k,eta,rz]).all() or eta<0 or discrepancy>1e-8:
            return {'status':'NUMERICAL_FAILURE','failure_reason':'nonfinite/negative indicator or residual drift','rows':rows}
        if np.linalg.norm(explicit)/scale <= rtol:
            return {'status':'PASS','stop_reason':'VERIFIED_RESIDUAL','rows':rows}
        if step==maximum_steps:
            return {'status':'SOLVER_FAILURE','failure_reason':'maximum steps before residual tolerance','stop_reason':'MAX_BUDGET','rows':rows}
        ap=ops.A(p,'outer'); pap=float(p@ap)
        if pap<=0 or rz<=0 or not np.isfinite(pap):
            return {'status':'NUMERICAL_FAILURE','failure_reason':'PCG nonpositive energy','rows':rows}
        alpha=rz/pap; z+=alpha*p; az+=alpha*ap; r-=alpha*ap
        w=precondition(r); new_rz=float(r@w)
        p=w+(new_rz/rz)*p; rz=new_rz
