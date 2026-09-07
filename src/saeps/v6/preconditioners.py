"""Fixed SPD diagonal, Nyström, recycled and defect-enriched preconditioners."""
import numpy as np


class LowRank:
    def __init__(self,u,values,gamma):
        self.u,self.values,self.gamma=u,values,gamma
        self.rank=len(values)

    def __call__(self,d):
        coordinates=self.u.T@d
        perpendicular=d-self.u@coordinates
        # Reproject to reduce cancellation in a nearly full-rank basis.
        leakage=self.u.T@perpendicular
        perpendicular-=self.u@leakage
        coordinates+=leakage
        return perpendicular/self.gamma+self.u@(coordinates/(self.gamma+self.values))

    def woodbury(self,d):
        return d/self.gamma-self.u@((self.values/(self.gamma*(self.gamma+self.values)))*(self.u.T@d))

    def matrix(self):
        return self.gamma*np.eye(self.u.shape[0])+(self.u*self.values)@self.u.T


class Diagonal:
    def __init__(self,d):
        if np.min(d)<=0: raise ValueError('nonpositive diagonal')
        self.d=d; self.rank=0
    def __call__(self,x): return x/self.d
    def matrix(self): return np.diag(self.d)


class Exact:
    def __init__(self,m): self.l=np.linalg.cholesky(m); self.rank=len(m)
    def __call__(self,x): return np.linalg.solve(self.l.T,np.linalg.solve(self.l,x))
    def matrix(self): return self.l@self.l.T


def eig_psd(t):
    values,vectors=np.linalg.eigh((t+t.T)/2)
    scale=max(float(np.max(abs(values))),1e-30) if len(values) else 1e-30
    if len(values) and min(values)<-1e-11*scale: raise ValueError('significant negative Ritz eigenvalue')
    return np.maximum(values,0),vectors


def ritz(cache,rank):
    q,gq=cache['Q'],cache['GQ']
    if q.shape[1]==0: return q,gq
    values,v=eig_psd(q.T@gq)
    take=np.argsort(values)[::-1][:rank]; transform=v[:,take]
    return q@transform,gq@transform


def build(name,rank,seed,ops,cache,defect):
    n=len(ops.g); gamma=ops.gamma
    if name=='diagonal': return Diagonal(np.diag(ops.g)+gamma)
    if name=='exact_gn': return Exact(ops.g+gamma*np.eye(n))
    if name=='nystrom':
        sketch=np.random.Generator(np.random.PCG64(seed)).standard_normal((n,32))
        omega=np.linalg.qr(sketch[:,:rank],mode='reduced')[0]
        y=ops.G(omega,'setup'); t=omega.T@y
        val,v=eig_psd(t); keep=val>1e-11*max(float(max(val)),1e-30)
        f=y@v[:,keep]/np.sqrt(val[keep])[None,:]
        u,s,_=np.linalg.svd(f,full_matrices=False)
        return LowRank(u,s*s,gamma)
    q,gq=ritz(cache,rank if name=='recycled_ritz' else rank-1)
    if name=='hybrid_defect' and np.linalg.norm(defect)>0:
        w=defect/np.linalg.norm(defect)
        for _ in range(2): w-=q@(q.T@w)
        if np.linalg.norm(w)>1e-11:
            w/=np.linalg.norm(w)
            q=np.column_stack((q,w)); gq=np.column_stack((gq,ops.G(w,'setup')))
    values,v=eig_psd(q.T@gq)
    return LowRank(q@v,values,gamma)
