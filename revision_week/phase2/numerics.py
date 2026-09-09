"""Fixed Phase 2 numerical definitions, state corrector and inverse forms."""
from __future__ import annotations
import contextlib,sys,time
import numpy as np
import torch
from common import quadratic,numerical_mu,sym,norm,native,Deadline,read,SPEC

def matrices(g,h,n,gamma,cfg=None):
    cfg=cfg or read(SPEC)['numerics'];t=time.perf_counter();p=len(g)-n
    a=h[:n,:n]+gamma*np.eye(n);m=g[:n,:n]+gamma*np.eye(n);b=h[:n,n:];c=h[n:,n:]
    z=np.linalg.solve(m,g[:n,n:]);mu=numerical_mu(a)
    fields=dict(G=g,H=h,Z_G=z,A=a,B=b,C=c,gamma=gamma,n_state=n,n_parameter=p,state_SPD=mu,
        F_RAW=g[n:,n:],F_GN=quadratic(g[n:,n:],g[:n,n:],m,z),F_SO=quadratic(c,b,a,z),
        GN_normal_residual=norm(m@z-g[:n,n:])/max(norm(g[:n,n:]),1e-30))
    if mu['mu_value'] is None:return dict(**fields,status='CHECKPOINT_INVALID',binding_valid=False,failure_reason='state_'+mu['spd_status'],seconds=time.perf_counter()-t)
    ch=np.linalg.cholesky(a);refsolve=np.linalg.solve(ch.T,np.linalg.solve(ch,b));fst=sym(c-b.T@refsolve)
    vals,vecs=np.linalg.eigh(sym(a));independent=vecs@((vecs.T@b)/vals[:,None]);fst2=sym(c-b.T@independent)
    scale=max(1.,*[float(np.linalg.norm(fields[key],2)) for key in ['F_RAW','F_GN','F_SO']],float(np.linalg.norm(fst,2)))
    eta=max(cfg['curvature_floor_relative']*scale,cfg['reference_disagreement_factor']*norm(fst-fst2))
    d=b-a@z;q=d.T@np.linalg.solve(a,d);identity=norm(fields['F_SO']-fst-q)/max(norm(fst),norm(q),1.)
    residual=norm(a@refsolve-b)/max(norm(b),1e-30)
    valid=bool(residual<=cfg['reference_solve_residual'] and fields['GN_normal_residual']<=cfg['gn_verified_residual'] and
        identity<=cfg['operator_tolerance'] and eta<=cfg['reference_unresolved_relative']*scale and norm(fst)>eta)
    errors={};metrics={}
    for method in ['RAW','GN','SO']:
        errors[method]={kind:float(np.linalg.norm(fields['F_'+method]-fst,ord=ord_)) for kind,ord_ in [('fro','fro'),('spectral',2)]}
    for kind in ['fro','spectral']:
        eg,es=errors['GN'][kind],errors['SO'][kind];metrics[kind]=dict(error_GN=eg,error_SO=es,
            strict_SO_win=bool(valid and eg-es>cfg['strict_win_margin_factor']*eta),strict_GN_win=bool(valid and es-eg>cfg['strict_win_margin_factor']*eta),
            logR_floor=float(np.log(max(eg,eta)/max(es,eta))),logR=float(np.log(eg/es)) if min(eg,es)>eta else None,
            relative_GN=eg/max(norm(fst),eta),relative_SO=es/max(norm(fst),eta),reference_resolved=norm(fst)>eta)
    return dict(**fields,F_star=fst,Z_exact=refsolve,D=d,defect_energy=q,identity_error=identity,reference_residual=residual,
        reference_disagreement=norm(fst-fst2),eta_F=eta,reference_scale=scale,errors=errors,metrics=metrics,
        status='PASS' if valid else 'NUMERICAL_FAILURE',binding_valid=valid,failure_reason=None if valid else 'reference_or_solver_unresolved',seconds=time.perf_counter()-t)

def dense_curvature(residual,theta,coordinate,gamma=None):
    start=time.perf_counter();n=len(theta);joint=torch.cat((theta,coordinate))
    r=lambda v:residual(v[:n],v[n:]);ell=lambda v:.5*r(v).square().sum()
    j=torch.func.jacrev(r)(joint).detach().numpy();g=j.T@j;h=torch.func.hessian(ell)(joint).detach().numpy()
    if gamma is None:gamma=1e-8*float(np.linalg.eigvalsh(g[:n,:n])[-1])
    if not np.isfinite(gamma) or gamma<=0:raise ValueError('zero or nonfinite nominal gamma')
    result=matrices(g,h,n,gamma);grad=torch.func.grad(ell)(joint).detach().numpy()
    result.update(gradient_sum=grad,residual=residual(theta,coordinate).detach().numpy(),explicit_jacobians=1,explicit_hessians=1,
        all_seconds=time.perf_counter()-start)
    return result

class Objective:
    def __init__(self,residual,coordinate,anchor,gamma,deadline=None):
        self.residual=residual;self.coordinate=coordinate.detach();self.anchor=anchor.detach();self.gamma=float(gamma)
        self.deadline=deadline;self.m=int(residual(anchor,coordinate).numel());self.counts=dict(objective=0,gradient=0,hessian=0)
    def check(self):
        if self.deadline:self.deadline.check()
    def tensor(self,t):return .5*self.residual(t,self.coordinate).square().sum()+.5*self.gamma*(t-self.anchor).square().sum()
    def value(self,t):self.check();self.counts['objective']+=1;return float(self.tensor(t))
    def grad(self,t):self.check();self.counts['gradient']+=1;return torch.func.grad(self.tensor)(t).detach().numpy()
    def hess(self,t):self.check();self.counts['hessian']+=1;return torch.func.hessian(self.tensor)(t).detach().numpy()
    def diagnostic(self,t):
        loss=self.value(t);g=self.grad(t);a=self.hess(t);mu=numerical_mu(a)
        return dict(loss=loss,gradient=norm(g)/self.m/max(norm(t.numpy()),1.),gradient_sum_norm=norm(g),g=g,A=a,SPD=mu,
            energy=float(g@np.linalg.solve(a,g)/2) if mu['mu_value'] else None)

def lbfgs_root(obj,theta,cfg,save_state=None):
    """Trace actual installed LBFGS branch exit via Python line tracing, without algorithm edits."""
    th=theta.detach().clone().requires_grad_(True);opt=torch.optim.LBFGS([th],max_iter=cfg['root_lbfgs_max_iter'],
        max_eval=cfg['root_lbfgs_max_eval'],history_size=cfg['history_size'],tolerance_grad=cfg['tol_grad'],
        tolerance_change=cfg['tol_change'],line_search_fn='strong_wolfe')
    import inspect
    function=torch.optim.LBFGS.step.__wrapped__;source_lines,line0=inspect.getsourcelines(function)
    reasons={}
    for i,line in enumerate(source_lines):
        if line.strip()=='break':reasons[line0+i]=source_lines[i-1].strip()
    traced=[];oldtrace=sys.gettrace()
    def trace(frame,event,arg):
        if frame.f_code==function.__code__ and event=='line' and frame.f_lineno in reasons:traced.append(reasons[frame.f_lineno])
        return trace if frame.f_code==function.__code__ else None
    def closure():
        obj.check();opt.zero_grad(set_to_none=True);obj.counts['objective']+=1;obj.counts['gradient']+=1
        loss=obj.tensor(th)/obj.m;loss.backward();return loss
    start=time.perf_counter()
    try:
        sys.settrace(trace);opt.step(closure)
    finally:sys.settrace(oldtrace)
    if save_state:save_state(opt.state_dict())
    state=opt.state[th]
    reason=traced[-1] if traced else 'initial_gradient_condition_or_return'
    return th.detach(),dict(iterations=int(state.get('n_iter',0)),function_evals=int(state.get('func_evals',0)),termination_branch=reason,seconds=time.perf_counter()-start)

def correct(obj,theta,cfg=None,branch=False,target=1e-10,trace_path=None,require_spd=True):
    """One fixed TR pipeline. No multistart or spectral shift in the scientific objective."""
    from common import write
    cfg=cfg or read(SPEC)['strict_solver'];start=time.perf_counter();th=theta.detach().clone();scale=max(norm(obj.anchor.numpy() if branch else th.numpy()),1.)
    predictor=th.numpy().copy();radius=cfg['initial_relative_radius']*scale;changes=[];trace=[];reason='trial_budget_exhausted';status='PROFILE_FAILURE'
    for trial in range(cfg['newton_trials']):
        obj.check();d0=obj.diagnostic(th);a=d0['A']/obj.m;g=d0['g']/obj.m
        record=dict(trial=trial,loss=d0['loss'],gradient=d0['gradient'],radius=radius,SPD=d0['SPD'],accepted=False)
        # A state already at the target must not be forced to move away merely to
        # manufacture two accepted steps. Two same-state validations have zero change.
        if d0['gradient']<=target and (d0['SPD']['mu_value'] or not require_spd):
            validations=[obj.diagnostic(th) for _ in range(cfg['plateau_accepted_steps'])]
            stationary_changes=[abs(d['loss']-d0['loss'])/max(1.,abs(d0['loss'])) for d in validations]
            if all(d['gradient']<=min(target,1e-8) and (d['SPD']['mu_value'] or not require_spd) for d in validations) and max(stationary_changes)<=cfg['plateau_relative']:
                record.update(accepted=True,stationary_revalidation=True,objective_changes=stationary_changes);trace.append(record);status='PASS';reason='stationary_and_plateau_verified';break
        vals=np.linalg.eigvalsh(sym(a));shift=max(0.,cfg['direction_shift_relative']*max(float(np.max(abs(vals))),1.)-float(vals[0]))
        direction=np.linalg.solve(a+shift*np.eye(len(a)),-g);dn=norm(direction)
        if dn>radius:direction*=radius/dn
        pred=-float(g@direction+.5*direction@a@direction);candidate=th+torch.from_numpy(direction)
        record.update(direction_shift=shift,predicted_mean=pred,step_norm=norm(direction))
        if pred<=0 or not np.isfinite(pred):radius*=.5;record['rejection']='nonpositive_prediction'
        else:
            dt=obj.diagnostic(candidate);actual=(d0['loss']-dt['loss'])/obj.m;rho=actual/pred
            floor=64*np.finfo(float).eps*max(1.,abs(d0['loss']))
            roundoff=abs(d0['loss']-dt['loss'])<=floor and norm(dt['g'])<.5*norm(d0['g'])
            numerical_accept=(actual>0 and rho>=cfg['rho_accept']) or roundoff
            branch_accept=(not branch) or (bool(dt['SPD']['mu_value']) and norm(candidate.numpy()-predictor)<=cfg['branch_predictor_distance_max_relative']*scale)
            finite=bool(np.isfinite(dt['loss']) and np.isfinite(dt['gradient']))
            accept=bool(numerical_accept and branch_accept and finite)
            record.update(candidate_loss=dt['loss'],candidate_gradient=dt['gradient'],candidate_SPD=dt['SPD'],rho=rho,
                roundoff_accept=bool(roundoff),accepted=accept,branch_accept=bool(branch_accept))
            if accept:
                changes.append(abs(dt['loss']-d0['loss'])/max(1.,abs(d0['loss'])));th=candidate.detach()
            if not accept or rho<cfg['rho_shrink']:radius*=.5
            elif rho>cfg['rho_expand'] and norm(direction)>=.99*radius:radius=min(radius*2,cfg['max_relative_radius']*scale)
        trace.append(record)
        if trace_path:write(trace_path,trace)
        if radius<cfg['min_relative_radius']*scale:reason='trust_radius_exhausted';break
    final=obj.diagnostic(th)
    if status=='PASS' and ((require_spd and not final['SPD']['mu_value']) or final['gradient']>1e-8):raise AssertionError('invalid solver acceptance')
    if trace_path:write(trace_path,trace)
    return th,dict(status=status,failure_reason=None if status=='PASS' else reason,termination=reason,diagnostic=final,trace=trace,
        accepted_steps=sum(r['accepted'] and not r.get('stationary_revalidation',False) for r in trace),counts=dict(obj.counts),seconds=time.perf_counter()-start)

def precision(obj,theta,trace_path=None):
    base=obj.diagnostic(theta);th,result=correct(obj,theta,branch=True,target=1e-12,trace_path=trace_path);d=result['diagnostic']
    consistent=norm(th.numpy()-theta.numpy())/max(norm(theta.numpy()),1.)<=1e-5
    eta=10*abs(d['loss']-base['loss'])+10*abs(d['energy'] or 0)+64*np.finfo(float).eps*max(1.,abs(d['loss']))
    return th,dict(**result,eta_phi=eta,baseline_loss=base['loss'],consistent=consistent,precision_valid=bool(result['status']=='PASS' and consistent))

def lanczos_inverse(a,d,endpoint,ks=(2,4,8,16)):
    """Unpreconditioned Lanczos, two full reorthogonalization passes; Gauss/Radau."""
    start=time.perf_counter();d=np.asarray(d).ravel();weight=float(d@d)
    if endpoint<=0:return dict(status='endpoint_unavailable',rows=[],matvecs=0,seconds=time.perf_counter()-start)
    if weight==0:return dict(status='zero_defect',rows=[dict(k=k,lower=0.,upper=0.,zero_defect=True) for k in ks],matvecs=0,seconds=time.perf_counter()-start)
    v=d/np.sqrt(weight);vectors=[];products=[];alpha=[];beta=[];rows=[];count=0;breakdown=False
    for k in range(1,min(max(ks),len(a))+1):
        vectors.append(v);av=a@v;products.append(av.copy());count+=1;w=av-(beta[-1]*vectors[-2] if k>1 else 0);aa=float(v@w);alpha.append(aa);w-=aa*v
        vv=np.column_stack(vectors)
        for _ in range(2):w-=vv@(vv.T@w)
        bb=norm(w);T=np.diag(alpha)+np.diag(beta,1)+np.diag(beta,-1)
        eps=100*np.finfo(float).eps*max(norm(av),1.);breakdown=bb<=eps
        if k in ks or breakdown or k==len(a):
            e=np.eye(k)[:,0];lower=weight*float(e@np.linalg.solve(T,e));upper=None;failure=None
            if breakdown:upper=lower
            else:
                try:
                    ek=np.eye(k)[:,-1];tail=endpoint+bb**2*float(ek@np.linalg.solve(T-endpoint*np.eye(k),ek))
                    R=np.zeros((k+1,k+1));R[:k,:k]=T;R[-1,-1]=tail;R[-1,-2]=R[-2,-1]=bb
                    er=np.eye(k+1)[:,0];upper=weight*float(er@np.linalg.solve(R,er))
                    if not np.isfinite(upper) or upper<lower:failure='radau_interval_unresolved'
                except np.linalg.LinAlgError:failure='radau_shift_singular'
            avv=np.column_stack(products)
            residual=norm(avv-vv@T-(np.outer(w,np.eye(k)[:,-1]) if not breakdown else 0))/max(norm(avv),1.)
            row=dict(k=k,lower=lower,upper=upper,breakdown=breakdown,tail_beta=bb,orthogonality=norm(vv.T@vv-np.eye(k)),
                lanczos_relative_residual=residual,failure_reason=failure,endpoint=endpoint,matvec_count=count)
            rows.append(row)
            if breakdown:
                for target in ks:
                    if target>k:rows.append(dict(row,k=target,actual_iterations=k))
                break
        beta.append(bb);v=w/bb
    return dict(status='PASS',rows=[r for r in rows if r['k'] in ks],matvecs=count,seconds=time.perf_counter()-start)

def fd_record(delta,plus,zero,minus,reference,eta_F):
    k=(plus['loss']-2*zero['loss']+minus['loss'])/delta**2
    floor=(plus['eta_phi']+2*zero['eta_phi']+minus['eta_phi'])/delta**2
    floor+=64*np.finfo(float).eps*(abs(plus['loss'])+2*abs(zero['loss'])+abs(minus['loss']))/delta**2
    valid=all(r['precision_valid'] for r in (plus,zero,minus))
    resolved=bool(valid and floor<=.01*max(abs(reference),eta_F) and abs(k)>10*floor)
    return dict(delta=delta,K_FD=k,eta_K=floor,resolved=resolved,branch_valid=valid,relative_reference_difference=abs(k-reference)/max(abs(reference),eta_F))
