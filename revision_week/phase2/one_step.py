"""Conditional Phase 1C-rule candidates, fixed E1 anchor, explicit error audit."""
from common import *
from numerics import Objective,dense_curvature,correct
from locality import audit

def run(dest,job,cfg,deadline):
    from p1b_onestep import profile_solve
    from p1c_development import polish
    root=Path(job['input']);local=Path(job['locality']);payload=load_payload(root/'state.pt');lr=read(local/'result.json')
    residual=residual_from_payload(payload);anchor=payload['anchor'];gamma=payload['gamma'];l0=float(payload['coordinate'][0]);scale=max(norm(anchor),1.)
    oldcfg=read(ROOT/'revision_week/config/phase1c_development.json');rows=[]
    bounds=[lr['sides']['minus']['last_valid_offset'],lr['sides']['plus']['last_valid_offset']]
    for off in cfg['e3']['offsets']:
        label='plus' if off>0 else 'minus';points=lr['sides'][label]['accepted'];match=next((p for p in points if abs(p['offset']-off)<1e-12),None)
        if match is None:
            rows.extend(dict(offset=off,method=m,status='PROFILE_FAILURE',failure_reason='common_start_unavailable') for m in cfg['e3']['methods']);continue
        theta=load_payload(match['state_path'])['theta'];lam=l0+off;startobj=Objective(residual,torch.tensor([lam]),anchor,gamma,deadline)
        start_audit=audit(startobj,theta,dest/f'{label}_start_audit');cv=dense_curvature(residual,theta,torch.tensor([lam]),gamma)
        write(dest/f'{label}_curvature.json',cv)
        if not cv['binding_valid'] or not start_audit['precision_valid']:
            rows.extend(dict(offset=off,method=m,status='PROFILE_FAILURE',failure_reason='common_start_reference_or_precision_failure') for m in cfg['e3']['methods']);continue
        gradient=float(cv['gradient_sum'][-1]);beta=cfg['e3']['shift_beta_scale']*max(float(cv['F_RAW'][0,0]),1e-8)
        for method,key in zip(cfg['e3']['methods'],['RAW','GN','SO','star']):
            cd=dest/f'{label}_{key}';row=dict(offset=off,method=method,status='PROFILE_FAILURE',failure_reason=None,candidate_solve_attempted=False)
            try:
                deadline.check();candidate_started=time.perf_counter();budget=Deadline(min(deadline.remaining(),cfg['e3']['candidate_seconds']));f=float(cv['F_'+key][0,0])
                if f+beta<=0:row['failure_reason']='nonpositive_shifted_curvature';rows.append(row);continue
                raw=-gradient/(f+beta);scaled=cfg['e3']['step_fraction']*raw;step=float(np.clip(scaled,-.1,.1));newlam=lam+step
                row.update(raw_step=raw,step=step,trust_radius_active=abs(scaled)>.1,lambda_value=newlam)
                if off+step<bounds[0]-1e-12 or off+step>bounds[1]+1e-12:
                    row['failure_reason']='outside_observed_branch_domain';rows.append(row);continue
                init=theta-torch.from_numpy(cv['Z_G'][:,0])*step;row['candidate_solve_attempted']=True
                candidate=profile_solve(residual,anchor,newlam,gamma,init,1e-8,cap_s=budget.remaining(),max_iter=300,tolerance_grad=1e-12,tolerance_change=1e-18)
                save_payload(cd/'lbfgs_state.pt',dict(theta=candidate.theta,coordinate=torch.tensor([newlam])))
                write(cd/'lbfgs.json',{k:v for k,v in vars(candidate).items() if k!='theta'})
                if candidate.hit_cap:raise TimeoutError('candidate_budget_exhausted')
                obj=Objective(residual,torch.tensor([newlam]),anchor,gamma,budget)
                def objective(t):obj.check();return obj.tensor(t)
                th,pr=polish(objective,candidate.theta,obj.m,oldcfg)
                save_payload(cd/'candidate_state.pt',dict(theta=th,coordinate=torch.tensor([newlam])));write(cd/'newton.json',pr)
                pa=audit(obj,th,cd/'candidate_audit')
                ccurve=dense_curvature(residual,th,torch.tensor([newlam]),gamma);write(cd/'curvature.json',ccurve)
                branch_ok=False
                if ccurve['binding_valid']:
                    backpred=th+torch.from_numpy(ccurve['Z_exact'][:,0])*step
                    backobj=Objective(residual,torch.tensor([lam]),anchor,gamma,budget)
                    back,br=correct(backobj,backpred,cfg['strict_solver'],branch=True,trace_path=cd/'reverse_trace.json')
                    save_payload(cd/'reverse_state.pt',dict(theta=back,coordinate=torch.tensor([lam])));ba=audit(backobj,back,cd/'reverse_audit')
                    branch_ok=bool(br['status']=='PASS' and ba['precision_valid'] and norm(back-theta)/scale<=1e-5 and abs(ba['loss']-start_audit['loss'])<=ba['eta_phi']+start_audit['eta_phi'])
                actual=start_audit['loss']-pa['loss'];pred=-(gradient*step+.5*f*step**2);error=start_audit['eta_phi']+pa['eta_phi']
                valid=bool(pr['status']=='PASS' and pa['precision_valid'] and branch_ok and norm(th-init)/scale<=.01)
                accepted=bool(valid and pred>0 and actual-cfg['e3']['armijo']*pred>error)
                truth=payload['runtime']['benchmarks'][payload['benchmark']]['truth_parameter']
                row.update(status='PASS' if valid else 'PROFILE_FAILURE',failure_reason=None if valid else 'candidate_stationarity_precision_or_branch_failure',
                    predicted=pred,actual=actual,error_estimate=error,rho=actual/pred if pred>error else None,accepted=accepted,
                    branch_consistent=branch_ok,gradient=pr['gradient'],parameter_relative_error_before=abs(np.exp(lam)-truth)/truth,
                    parameter_relative_error_after=abs(np.exp(newlam)-truth)/truth,parameter_error_role='synthetic_validation_only',
                    candidate_seconds=time.perf_counter()-candidate_started)
            except TimeoutError:row.update(status='SOLVER_FAILURE',failure_reason='budget_exhausted')
            rows.append(row);write(dest/'rows.json',rows)
    write(dest/'result.json',dict(group=job['group'],seed=job['seed'],rows=rows,evidence_role='conditional_secondary_not_independent_confirmation'))
