"""Isolated numerical workers. Every invocation has a parent-owned immutable claim."""
from __future__ import annotations
import argparse,contextlib,dataclasses,math,random,time,traceback
from pathlib import Path
from common import *
from numerics import *

def compact_export(cid,dest):
    from p1b_correct import load_center
    from saeps.scalar import ScalarPoints
    ck,prov,residual,seconds=load_center(cid);bench='Burgers' if cid.startswith('burgers') else 'Allen-Cahn'
    cfg=prov['data_recipe']['runtime_config']
    payload=dict(benchmark=bench,runtime=cfg,theta=torch.from_numpy(ck['theta']),coordinate=torch.from_numpy(ck['log_parameter']),gamma=float(ck['gamma']),
        points={k:torch.from_numpy(ck[k]) for k in ScalarPoints.__dataclass_fields__},
        truth=dict(values=torch.from_numpy(ck['truth_values']),spatial_points=int(ck['truth_spatial_points']),time_steps=int(ck['truth_time_steps']),
                   final_time=float(ck['truth_final_time']),benchmark=bench,parameter=float(cfg['benchmarks'][bench]['truth_parameter'])))
    save_payload(dest/'state.pt',payload);write(dest/'export.json',dict(center=cid,load_seconds=seconds,source=prov,state_sha256=sha(dest/'state.pt'),contains_dense_derivatives=False))

def compact(dest,job,cfg):
    from matrix_free import mf_so,forbid_dense
    from saeps.autodiff import ResidualLinearization
    payload=load_payload(job['input']);r=residual_from_payload(payload);t=payload['theta'];l=payload['coordinate'];n=len(t)
    assert not any(k in payload for k in ['G','H','A','B','Z_G','Z'])
    if job['kind']=='compact_explicit':
        result=dense_curvature(r,t,l,payload['gamma']);write(dest/'result.json',result);return
    result=mf_so(r,t,l,payload['gamma'],cfg['e5']);gen=torch.Generator().manual_seed(stream('compact/'+job['center']))
    dirs=[torch.randn(n+len(l),generator=gen) for _ in range(cfg['e5']['random_directions_per_center'])]
    dirs+=[torch.cat((-result['Z_G'][:,0],torch.ones(1)))];joint=torch.cat((t,l));ell=lambda w:.5*r(w[:n],w[n:]).square().sum()
    records=[];start=time.perf_counter()
    lin=ResidualLinearization(r,t,l)
    with forbid_dense() as attempts:
        for v in dirs:
            v=v/torch.linalg.vector_norm(v);hv=torch.autograd.functional.hvp(ell,joint,v)[1]
            u=torch.randn(n+len(l),generator=gen);u/=torch.linalg.vector_norm(u);hu=torch.autograd.functional.hvp(ell,joint,u)[1]
            w=torch.randn(len(r(t,l)),generator=gen);jv=lin.jvp_theta(v[:n])+lin.jvp_parameter(v[n:])
            left=float(w@jv);right=float(v[:n]@lin.vjp_theta(w)+v[n:]@lin.vjp_parameter(w))
            records.append(dict(direction=v,Hv=hv,adjoint_error=float(abs(u@hv-v@hu))/max(float(torch.linalg.vector_norm(hv)),float(torch.linalg.vector_norm(hu)),1.),
                JVP_VJP_adjoint_error=abs(left-right)/max(abs(left),abs(right),1.)))
    result.update(directions=records,direction_audit_seconds=time.perf_counter()-start,direction_audit_HVP_count=2*len(records),audit_forbidden_attempts=attempts,
        direction_JVP_VJP_counts=lin.operation_counts)
    write(dest/'result.json',result)

@contextlib.contextmanager
def capture_optimizers():
    """Capture final real optimizer state; preserve the original optimizer classes."""
    originals=[];instances=[]
    for cls in [torch.optim.Adam,torch.optim.LBFGS]:
        original=cls.__init__;originals.append((cls,original))
        def init(self,*a,_original=original,**kw):_original(self,*a,**kw);instances.append(self)
        cls.__init__=init
    try:yield instances
    finally:
        for cls,original in originals:cls.__init__=original

def fresh(dest,job,cfg,deadline):
    from saeps.scalar import solve_truth,train_scalar_checkpoint
    from saeps.multi import train_multi_checkpoint
    group=job['group'];seed=job['seed'];rt=cfg['resolved_runtime'][group];bench={'burgers':'Burgers','allen_cahn':'Allen-Cahn','multi':'multi'}[group]
    start=time.perf_counter();truth=None
    if group!='multi':truth=solve_truth(rt,bench)
    with capture_optimizers() as optimizers:
        ck,points=train_multi_checkpoint(rt,seed) if group=='multi' else train_scalar_checkpoint(rt,bench,seed,truth)
    deadline.check();training=dataclasses.asdict(ck)
    payload=dict(benchmark=bench,group=group,seed=seed,runtime=rt,theta=ck.theta,coordinate=ck.coordinate if group=='multi' else ck.log_parameter,
        points=dataclasses.asdict(points),truth=dataclasses.asdict(truth) if truth is not None else None)
    save_payload(dest/'trained_state.pt',payload)
    save_payload(dest/'training_optimizers.pt',{str(i):opt.state_dict() for i,opt in enumerate(optimizers)})
    save_payload(dest/'rng_state.pt',dict(torch=torch.get_rng_state(),python=random.getstate(),numpy=native(np.random.get_state())))
    write(dest/'training.json',dict(checkpoint=training,truth_and_training_seconds=time.perf_counter()-start))
    residual=residual_from_payload(payload);obj=Objective(residual,payload['coordinate'],payload['theta'],0,deadline)
    write(dest/'initial_state_diagnostic.json',obj.diagnostic(payload['theta']))
    theta,lb=lbfgs_root(obj,payload['theta'],cfg['strict_solver'],lambda s:save_payload(dest/'root_lbfgs_optimizer.pt',s))
    save_payload(dest/'lbfgs_state.pt',dict(payload,theta=theta));write(dest/'root_lbfgs.json',lb)
    theta,tr=correct(obj,theta,cfg['strict_solver'],trace_path=dest/'root_TR_trace.json',require_spd=False)
    # Gamma is chosen ONCE at this fixed-lambda unanchored refinement endpoint.
    curve=dense_curvature(residual,theta,payload['coordinate']);payload.update(theta=theta,anchor=theta.clone(),gamma=curve['gamma'])
    save_payload(dest/'state.pt',payload);write(dest/'curvature.json',curve);write(dest/'root_solver.json',tr)
    joint=torch.cat((theta,payload['coordinate']));n=len(theta);v=torch.cat((-torch.from_numpy(curve['Z_G']),torch.eye(len(payload['coordinate']))))
    hvs=torch.stack([torch.autograd.functional.hvp(lambda w:.5*residual(w[:n],w[n:]).square().sum(),joint,col)[1] for col in v.T],dim=1)
    hvp_error=norm(hvs.numpy()-curve['H']@v.numpy())/max(norm(curve['H']@v.numpy()),1e-30)
    write(dest/'HVP.json',dict(directions=v,HVP=hvs,relative_error=hvp_error,HVP_count=len(payload['coordinate'])))
    reloaded=load_payload(dest/'state.pt');rr=residual_from_payload(reloaded)
    reload_equal=bool(torch.equal(rr(reloaded['theta'],reloaded['coordinate']),residual(theta,payload['coordinate'])))
    valid=bool(tr['status']=='PASS' and curve['binding_valid'] and reload_equal and hvp_error<=1e-8)
    write(dest/'result.json',dict(group=group,seed=seed,status='PASS' if valid else 'CHECKPOINT_INVALID',binding_valid=valid,
        failure_reason=None if valid else ('reload_mismatch' if not reload_equal else 'HVP_reference_mismatch' if hvp_error>1e-8 else tr['failure_reason'] or curve['failure_reason']),
        state_gradient=tr['diagnostic']['gradient'],unanchored_state_SPD=tr['diagnostic']['SPD'],anchored_state_SPD=curve['state_SPD'],
        reload_bitwise=reload_equal,metrics=curve.get('metrics'),gamma=payload['gamma'],checkpoint_sha256=sha(dest/'state.pt'),
        training_seconds=training['elapsed_seconds'],root_lbfgs_seconds=lb['seconds'],root_corrector_seconds=tr['seconds'],curvature_seconds=curve['all_seconds'],
        counts=tr['counts'],explicit_JVP_VJP_counts=0,explicit_jacobians=1,explicit_hessians=1+tr['counts']['hessian'],CG_iterations=0))

def scale(dest,job,cfg,deadline):
    from saeps.config import load_config
    from saeps.v5.residual_scalability import _load_base,_runtime_for_condition
    from saeps.v48.pipeline import _widen
    from saeps.controlled import make_diagnostic_points,base_residual,fourier_library
    from saeps.autodiff import ResidualLinearization
    from matrix_free import mf_so,forbid_dense
    start=time.perf_counter();base,manifest=_load_base(ROOT);n,m=job['n'],job['m']
    rt=_runtime_for_condition(ROOT,load_config(ROOT/'configs/v5/residual_scalability_execution.yaml'),n,m)
    theta=_widen(base,25,int(rt['network']['hidden_width']),120);points=make_diagnostic_points(rt);lib=fourier_library(rt,points)
    source=lib[rt['selected_sources']['q_parallel']];pdec=len(points.pde_x);weight=math.sqrt(rt['training']['loss_weights']['pde']);l=torch.zeros(1)
    def residual(t,q):
        value=base_residual(t,points,rt).clone();value[:pdec]-=weight*q[0]*source;return value
    assert len(theta)==n and len(residual(theta,l))==m
    with forbid_dense():
        lin=ResidualLinearization(residual,theta,l);v=torch.randn(n,generator=torch.Generator().manual_seed(stream(f'scale/{n}/{m}')));v/=torch.linalg.vector_norm(v)
        for _ in range(cfg['e5']['power_iterations']):
            deadline.check();v=lin.vjp_theta(lin.jvp_theta(v));v/=torch.linalg.vector_norm(v).clamp_min(1e-30)
        av=lin.vjp_theta(lin.jvp_theta(v));estimate=float(v@av);gamma=cfg['e5']['scale_gamma_alpha']*max(estimate,1e-12)
    write(dest/'setup.json',dict(n=n,m=m,runtime=rt,gamma=gamma,lambda_estimate=estimate,seconds=time.perf_counter()-start,
        counts=lin.operation_counts,power_matvecs=cfg['e5']['power_iterations']+1,base_manifest=manifest,claim='cost_only_function_preserving_widening'))
    rows=[]
    for label in ['cold','warmup','steady_1','steady_2','steady_3']:
        deadline.check();r=mf_so(residual,theta,l,gamma,cfg['e5']);r.pop('Z_G');r.update(pass_label=label,n=n,m=m)
        write(dest/(label+'.json'),r);rows.append(r)
    write(dest/'result.json',rows)

def solver_audit(dest,job,cfg,deadline):
    payload=load_payload(job['input']);residual=residual_from_payload(payload);theta=payload['theta']
    coordinate=payload['coordinate']
    if job.get('old_state'):
        old=Path(job['old_state']);theta=torch.from_numpy(np.load(old/'state.npz')['theta'])
        coordinate=torch.tensor([read(old/'claim.json')['payload']['lambda']])
    obj=Objective(residual,coordinate,payload['theta'],payload['gamma'],deadline);initial=obj.diagnostic(theta)
    theta,lb=lbfgs_root(obj,theta,cfg['strict_solver']);theta,tr=correct(obj,theta,cfg['strict_solver'],trace_path=dest/'trace.json')
    save_payload(dest/'state.pt',dict(payload,theta=theta,coordinate=coordinate));write(dest/'result.json',dict(initial=initial,lbfgs=lb,TR=tr,
        engineering_accept=bool(tr['status']!='PASS' or (tr['diagnostic']['gradient']<=1e-8 and tr['diagnostic']['SPD']['mu_value'])),
        purpose='real_saved_state_solver_development_not_confirmation'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('dest');args=ap.parse_args();dest=Path(args.dest);claim=read(dest/'claim.json');job=claim['job'];cfg=read(claim['config'])
    deadline=Deadline(max(.01,claim['timeout_seconds']-2));start=time.perf_counter()
    try:
        kind=job['kind']
        if kind in ['scalar_history','multi_history','lanczos_history','lanczos_practical']:
            import historical
            {'scalar_history':historical.scalar,'multi_history':historical.multi,'lanczos_history':historical.lanczos,'lanczos_practical':lambda d,c:historical.lanczos(d,c,True)}[kind](dest,cfg)
        elif kind=='compact_export':compact_export(job['center'],dest)
        elif kind.startswith('compact_'):compact(dest,job,cfg)
        elif kind=='fresh':fresh(dest,job,cfg,deadline)
        elif kind=='scale':scale(dest,job,cfg,deadline)
        elif kind=='solver_audit':solver_audit(dest,job,cfg,deadline)
        elif kind=='locality':
            from locality import run
            run(dest,job,cfg,deadline)
        elif kind=='one_step':
            from one_step import run
            run(dest,job,cfg,deadline)
        else:raise ValueError('unknown worker '+kind)
        write(dest/'worker_terminal.json',dict(status='PASS',seconds=time.perf_counter()-start))
    except Exception as exc:
        write(dest/'worker_terminal.json',dict(status='SOLVER_FAILURE' if isinstance(exc,TimeoutError) else 'NUMERICAL_FAILURE',failure_reason=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc(),seconds=time.perf_counter()-start))
        raise

if __name__=='__main__':main()
