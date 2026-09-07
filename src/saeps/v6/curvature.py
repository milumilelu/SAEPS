"""Candidate curvature and separately invoked validation oracles."""
import numpy as np


def curvature(hll, c, z, az):
    return float(hll-2*c@z+z@az)


def oracle(g,h,b,c,gll,hll,gamma):
    m=g+gamma*np.eye(len(g)); a=h+gamma*np.eye(len(g))
    z0=np.linalg.solve(m,b); zs=np.linalg.solve(a,c)
    ref=float(hll-c@zs); gn=float(gll-b@z0)
    return {'z0':z0, 'zstar':zs, 'A':a, 'M':m, 'reference':ref, 'gn':gn,
            'gn_error':abs(gn-ref)/(abs(ref)+1e-8)}
