"""Dense archived operators with explicit vector-column accounting."""
from collections import Counter
import numpy as np


class DenseOperators:
    def __init__(self, g, h, gamma):
        self.g, self.h, self.gamma = g, h, gamma
        self.counts = Counter()

    def _apply(self, matrix, x, kind, purpose):
        columns = 1 if x.ndim == 1 else x.shape[1]
        self.counts[kind] += columns
        self.counts[f'{purpose}_{kind}'] += columns
        return matrix @ x

    def G(self, x, purpose):
        return self._apply(self.g, x, 'Gv', purpose)

    def A(self, x, purpose):
        self.counts['gamma_axpy'] += 1 if x.ndim == 1 else x.shape[1]
        return self._apply(self.h, x, 'Hv', purpose) + self.gamma * x

    def snapshot(self):
        return {'Gv': 0, 'Hv': 0, 'JVP': 0, 'VJP': 0, 'HVP_actual': 0, **dict(self.counts)}


def load_blocks(record):
    g, h = record['GN_blocks'], record['exact_blocks']
    G, H = np.array(g['G_tt']), np.array(h.get('H_tt_sym', h['H_tt']))
    B, C = np.array(g['G_tl']), np.array(h['H_tl'])
    Gll, Hll = np.array(g['G_ll']), np.array(h['H_ll'])
    n = len(G)
    if G.shape != (n,n) or H.shape != (n,n) or B.shape != (n,1) or C.shape != (n,1):
        raise ValueError('scalar block dimensions required')
    if Gll.shape != (1,1) or Hll.shape != (1,1):
        raise ValueError('physical block dimensions')
    for matrix in (G,H,B,C,Gll,Hll):
        if not np.isfinite(matrix).all():
            raise ValueError('nonfinite block')
    for matrix in (G,H):
        if np.linalg.norm(matrix-matrix.T) > 1e-8 * max(np.linalg.norm(matrix),1e-30):
            raise ValueError('asymmetric state block')
    for blocks, name, transpose in ((g,'G_lt',B.T),(h,'H_lt',C.T)):
        if name in blocks and np.linalg.norm(np.asarray(blocks[name])-transpose) > 1e-8*max(np.linalg.norm(transpose),1e-30):
            raise ValueError('cross transpose mismatch')
    gamma = float(record['gamma'])
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError('invalid gamma')
    G,H = (G+G.T)/2, (H+H.T)/2
    M,A = G+gamma*np.eye(n), H+gamma*np.eye(n)
    np.linalg.cholesky(M)
    ev = np.linalg.eigvalsh(A)
    if ev[0] <= 1e-10*max(abs(ev)):
        raise ValueError('A positive-definiteness gate')
    return G,H,B[:,0],C[:,0],float(Gll[0,0]),float(Hll[0,0]),gamma
