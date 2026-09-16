"""Fixed-anchor exact-tangent continuation with reverse and precision sidecars."""
from common import *
from numerics import Objective,correct,precision,dense_curvature,fd_record
from gates import radius_prefix

def audit(obj,theta,dest):
    th,r=precision(obj,theta,trace_path=dest/'precision_trace.json');save_payload(dest/'audit_state.pt',dict(theta=th,coordinate=obj.coordinate))
    write(dest/'precision.json',r)
    return dict(loss=r['diagnostic']['loss'],eta_phi=r['eta_phi'],precision_valid=r['precision_valid'],status=r['status'])

def follow(residual,payload,target,dest,cfg,deadline,root_audit,micro=False):
    ec=cfg['e2'];theta=payload['theta'].clone();coordinate=payload['coordinate'];anchor=payload['anchor'];gamma=payload['gamma'];scale=max(norm(anchor),1.)
    sign=1 if target>0 else -1;offset=0.;step=ec['step'];accepted=[];trials=[];previous_audit=root_audit
    maxtrials=ec['micro_trials_per_target'] if micro else ec['forward_trials_per_side'];correctors=0;reverse_attempts=0;reason='right_censored_at_max_offset';firstfailed=None
    final_audit=root_audit;endtheta=theta;firstmu=None;reverse_valid=True
    try:
        while abs(target-offset)>1e-12:
            deadline.check()
            if len(accepted)>=ec['accepted_steps_per_side'] or len(trials)>=maxtrials or (micro and correctors+4>maxtrials) or reverse_attempts>=ec['reverse_checks_per_side']:reason='budget_exhausted';break
            curve=dense_curvature(residual,theta,coordinate+offset,gamma)
            if not curve['binding_valid']:reason='branch_reference_unresolved';break
            if firstmu is None:firstmu=curve['state_SPD']['lambda_min_A_numeric']
            distance=min(step,abs(target-offset));h=sign*distance;nextoff=offset+h
            pred=theta-torch.from_numpy(curve['Z_exact'][:,0])*h;trialdest=dest/f'trial_{len(trials):03d}'
            obj=Objective(residual,coordinate+nextoff,anchor,gamma,deadline)
            candidate,r=correct(obj,pred,cfg['strict_solver'],branch=True,trace_path=trialdest/'corrector_trace.json');correctors+=1
            cand_distance=norm(candidate-pred)/scale
            forward_ok=r['status']=='PASS' and cand_distance<=ec.get('predictor_distance_max',.01)
            record=dict(trial=len(trials),from_offset=offset,target_offset=nextoff,step=h,forward_status=r['status'],forward_failure=r['failure_reason'],
                candidate_SPD=r['diagnostic']['SPD'],predictor_distance=cand_distance,accepted=False,forward_seconds=r['seconds'],forward_counts=r['counts'],
                starting_curvature_seconds=curve['all_seconds'],candidate_gradient=r['diagnostic']['gradient'])
            save_payload(trialdest/'baseline_state.pt',dict(theta=candidate,coordinate=coordinate+nextoff))
            if forward_ok:
                cc=dense_curvature(residual,candidate,coordinate+nextoff,gamma)
                if cc['binding_valid']:
                    backpred=candidate+torch.from_numpy(cc['Z_exact'][:,0])*h
                    backobj=Objective(residual,coordinate+offset,anchor,gamma,deadline)
                    back,br=correct(backobj,backpred,cfg['strict_solver'],branch=True,trace_path=trialdest/'reverse_trace.json');correctors+=1;reverse_attempts+=1
                    save_payload(trialdest/'reverse_state.pt',dict(theta=back,coordinate=coordinate+offset))
                    backaudit=audit(backobj,back,trialdest/'reverse_audit');correctors+=1
                    endpoint_audit=audit(obj,candidate,trialdest/'forward_audit');correctors+=1
                    state_error=norm(back-theta)/scale;objerror=abs(backaudit['loss']-previous_audit['loss'])
                    reverse_ok=bool(br['status']=='PASS' and backaudit['precision_valid'] and previous_audit['precision_valid'] and state_error<=ec['reverse_state_tolerance'] and objerror<=backaudit['eta_phi']+previous_audit['eta_phi'])
                    record.update(reverse_valid=reverse_ok,reverse_state_error=state_error,reverse_objective_error=objerror,
                        reverse_objective_tolerance=backaudit['eta_phi']+previous_audit['eta_phi'],precision=endpoint_audit,
                        reverse_seconds=br['seconds'],reverse_counts=br['counts'],candidate_curvature_seconds=cc['all_seconds'])
                    if reverse_ok:
                        accepted.append(dict(offset=nextoff,state_path=str(trialdest/'baseline_state.pt'),loss=r['diagnostic']['loss'],gradient=r['diagnostic']['gradient'],
                            lambda_min_A=cc['state_SPD']['lambda_min_A_numeric'],lambda_min_Htt=float(np.linalg.eigvalsh(cc['H'][:len(theta),:len(theta)])[0]),
                            exact_tangent_norm=norm(cc['Z_exact']),predictor_distance=cand_distance,relative_root_displacement=norm(candidate-anchor)/scale,
                            precision=endpoint_audit,reverse_valid=True))
                        offset=nextoff;theta=candidate;previous_audit=endpoint_audit;final_audit=endpoint_audit;endtheta=candidate;record['accepted']=True
                    else:record['failure_class']='branch_consistency_unresolved';reverse_valid=False
                else:record['failure_class']='branch_reference_unresolved'
            trials.append(record);write(dest/'trials.json',trials);write(dest/'accepted.json',accepted)
            if record['accepted']:continue
            if firstfailed is None:firstfailed=nextoff
            if distance<ec['min_step']+1e-12:
                negative=any(t.get('candidate_SPD',{}).get('spd_status')=='not_SPD' for t in r['trace']) or r['diagnostic']['SPD']['spd_status']=='not_SPD'
                eig=[a['lambda_min_A'] for a in accepted[-3:]]
                stability=negative and len(eig)==3 and eig[0]>=eig[1]>=eig[2] and eig[2]<=.1*firstmu and reverse_valid
                reason='stability_boundary_evidence' if stability else 'observed_nonSPD_state' if negative else record.get('failure_class','solver_limited');break
            step=distance/2
    except TimeoutError:reason='budget_exhausted'
    reached=abs(target-offset)<=1e-12
    result=dict(target=target,last_valid_offset=offset,first_failed_trial=firstfailed,reached_target=reached,termination=reason,
        reverse_valid=all(a['reverse_valid'] for a in accepted) and (reached or bool(accepted)),accepted=accepted,trials=trials,corrector_attempts=correctors,
        final_audit=final_audit if reached else dict(loss=None,eta_phi=None,precision_valid=False),status='PASS' if reached else 'PROFILE_FAILURE',failure_reason=None if reached else reason)
    save_payload(dest/'endpoint_state.pt',dict(theta=endtheta,coordinate=coordinate+offset));write(dest/'result.json',result);return result

def run(dest,job,cfg,deadline):
    source=Path(job['input']);payload=load_payload(source/'state.pt');residual=residual_from_payload(payload);curve=read(source/'curvature.json')
    obj=Objective(residual,payload['coordinate'],payload['anchor'],payload['gamma'],deadline);zero=audit(obj,payload['theta'],dest/'root_audit')
    sides={}
    for label,sign in [('plus',1),('minus',-1)]:
        sides[label]=follow(residual,payload,sign*cfg['e2']['offset_max'],dest/label,cfg,deadline,zero)
    micros={};fds=[]
    for delta in cfg['e2']['micro_deltas']:
        pair={}
        for label,sign in [('plus',1),('minus',-1)]:
            local=Deadline(min(deadline.remaining(),cfg['e2']['micro_target_seconds']))
            pair[label]=follow(residual,payload,sign*delta,dest/'micro'/f'{delta}_{label}',cfg,local,zero,True)
        micros[str(delta)]=pair
        if all(pair[s]['reached_target'] for s in pair):
            fd=fd_record(delta,pair['plus']['final_audit'],zero,pair['minus']['final_audit'],float(curve['F_star'][0][0]),curve['eta_F'])
        else:fd=dict(delta=delta,resolved=False,branch_valid=False,K_FD=None,eta_K=None,relative_reference_difference=None)
        fd.update(curvature_approximation_error={m:abs(curve['F_'+m][0][0]-curve['F_star'][0][0]) for m in ['RAW','GN','SO']},
            finite_displacement_difference=abs(curve['F_star'][0][0]-fd['K_FD']) if fd['K_FD'] is not None else None)
        fds.append(fd);write(dest/'FD.json',fds)
    smallest=[r for r in fds if r['resolved'] and r['delta']<=cfg['e2']['micro_selection_max_delta']][:3]
    scale=max(abs(curve['F_star'][0][0]),curve['eta_F'])
    gate=len(smallest)==3 and all(r['relative_reference_difference']<=.05 for r in smallest) and abs(smallest[0]['K_FD']-smallest[1]['K_FD'])<=.05*scale
    radii={}
    for method in ['RAW','GN','SO','star']:
        rows=[dict(r,relative_error=abs(curve['F_'+method][0][0]-r['K_FD'])/abs(r['K_FD']) if r['resolved'] else None) for r in fds]
        radii[method]=radius_prefix(rows,.1)
    ready=bool(gate and all(abs(sides[s]['last_valid_offset'])>=.05-1e-12 and sides[s]['reverse_valid'] for s in sides))
    write(dest/'result.json',dict(group=job['group'],seed=job['seed'],status='PASS',failure_reason=None,gate_C=bool(gate),
        gate_C_reason='local_reference_consistent' if gate else 'resolution_limited' if len(smallest)<3 else 'resolved_reference_mismatch',
        E3_ready=ready,bidirectional_reach=min(abs(sides[s]['last_valid_offset']) for s in sides),sides=sides,FD=fds,radii=radii,
        root_precision=zero,source_checkpoint_sha256=sha(source/'state.pt'),evidence_role='preregistered_secondary_on_E1_roots'))
