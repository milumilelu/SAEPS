"""Corrective evidence audit. No training, new seeds, or historical overwrites.

Reuses the existing residual, directional core and LBFGS profile solver. Every
numerical task runs in a hard-timeout subprocess with an immutable attempt claim.
Historical errors remain historical errors; this is supplemental development.
"""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'): os.environ[key]='1'
import argparse, csv, hashlib, json, subprocess, sys, time
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from saeps.scalar import scalar_residual, ScalarPoints
from saeps.forward import ForwardSolution
from core import evaluate, numerical_mu, refine, quadratic
from p1b_onestep import profile_solve

OLD=ROOT/'revision_week/outputs/day2'
OUT=ROOT/'revision_week/outputs/phase1b_correction_v1'
CONFIG=ROOT/'revision_week/config/phase1b_correction.json'
torch.set_default_dtype(torch.float64); torch.set_num_threads(1)

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8',newline='\n'); t.replace(p)
def csvout(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def git(*a): return subprocess.check_output(['git','-C',str(ROOT),*a]).decode('utf-8').strip()
def norm(x): return float(np.linalg.norm(x))

def load_center(cid):
    """Load saved tensors/data; no regeneration from seeds and no training."""
    start=time.perf_counter()
    p=OLD/'recovery'/cid/'state_checkpoint.npz'; prov=read(p.parent/'provenance.json')
    if sha(p)!=prov['checkpoint_npz_sha256']: raise ValueError('checkpoint hash mismatch')
    with np.load(p,allow_pickle=False) as z: ck={k:z[k].copy() for k in z.files}
    runtime=prov['data_recipe']['runtime_config']; bench='Burgers' if cid.startswith('burgers') else 'Allen-Cahn'
    points=ScalarPoints(**{k:torch.from_numpy(ck[k]) for k in ScalarPoints.__dataclass_fields__})
    truth=ForwardSolution(torch.from_numpy(ck['truth_values']),int(ck['truth_spatial_points']),int(ck['truth_time_steps']),
                          float(ck['truth_final_time']),bench,float(runtime['benchmarks'][bench]['truth_parameter']))
    residual=lambda th,lp:scalar_residual(th,lp,bench,points,truth,runtime)
    return ck,prov,residual,time.perf_counter()-start

def bounded_command(command,timeout):
    """Hard wall limit, including import/startup. No automatic restart."""
    t=time.perf_counter()
    p=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
    try:
        stdout,stderr=p.communicate(timeout=max(.001,timeout))
        status='PASS' if p.returncode==0 else 'FAILED'
    except subprocess.TimeoutExpired:
        p.kill(); stdout,stderr=p.communicate(); status='budget_exhausted'
    return dict(status=status,wall_seconds=time.perf_counter()-t,exit_code=p.returncode,stdout=stdout,stderr=stderr)

def task(task_id,payload):
    cfg=read(CONFIG); dest=OUT/'tasks'/task_id; claim=dest/'claim.json'; result=dest/'process.json'
    identity=dict(payload=payload,config_sha256=sha(CONFIG),code_sha256=sha(__file__),solver_sha256=sha(ROOT/'revision_week/p1b_onestep.py'))
    if claim.exists():
        old=read(claim)
        if any(old.get(k)!=v for k,v in identity.items()): raise RuntimeError('task identity mismatch; do not overwrite')
        if result.exists(): return dest,read(result)
        raise RuntimeError('Interrupted claimed task is retained; no automatic retry')
    used=sum(read(p)['wall_seconds'] for p in (OUT/'tasks').glob('*/process.json'))
    remaining=cfg['total_new_process_seconds']-used
    timeout=min(cfg['per_solve_process_seconds'] if payload['kind']=='profile' else 120,remaining)
    dest.mkdir(parents=True,exist_ok=False)
    write(claim,dict(**identity,source_commit=git('rev-parse','HEAD'),timeout_seconds=timeout))
    if timeout<=0:
        r=dict(status='budget_exhausted',wall_seconds=0.,exit_code=None,stdout='',stderr='cumulative budget exhausted')
    else:
        r=bounded_command([sys.executable,str(Path(__file__).resolve()),'worker','--task',str(dest)],timeout)
    write(result,r)
    print(task_id,r['status'],f"{r['wall_seconds']:.2f}s",flush=True)
    return dest,r

def worker(dest):
    claim=read(dest/'claim.json'); payload=claim['payload']; cfg=read(CONFIG)
    start=time.perf_counter(); ck,prov,residual,load_s=load_center(payload['center'])
    th=torch.from_numpy(ck['theta']); lp=torch.from_numpy(ck['log_parameter']); gamma=float(ck['gamma']); n=len(th)
    if payload['kind']=='profile':
        init=np.load(payload['init_path'],allow_pickle=False)['theta']
        strict=payload['strict']
        # Parent process enforces an actual hard limit even if a tensor call stalls.
        solve=profile_solve(residual,th,payload['lambda'],gamma,torch.from_numpy(init),
            cfg['profile_gate_mean_normalized'] if strict else payload['historical_gate'],
            cap_s=max(.001,claim['timeout_seconds']-(time.perf_counter()-start)-.5),
            max_iter=cfg['strict_max_iter'] if strict else 300,
            tolerance_grad=cfg['strict_gradient_tolerance'] if strict else 1e-10,
            tolerance_change=cfg['strict_change_tolerance'] if strict else 1e-16)
        if solve.hit_cap: raise TimeoutError('profile solve exceeded its budget')
        np.savez_compressed(dest/'state.npz',theta=solve.theta.numpy())
        lam=torch.tensor([payload['lambda']])
        anchored=lambda t:.5*residual(t,lam).square().sum()+.5*gamma*(t-th).square().sum()
        diag_start=time.perf_counter(); a=torch.func.hessian(anchored)(solve.theta).numpy(); mu=numerical_mu(a)
        g=torch.func.grad(anchored)(solve.theta).numpy()
        # Local gradient-based error estimate is diagnostic, not a global certificate.
        energy=float(g@np.linalg.solve(a,g)/2) if mu['mu_value'] else None
        row={k:v for k,v in vars(solve).items() if k!='theta'}
        row.update(load_seconds=load_s,diagnostic_seconds=time.perf_counter()-diag_start,
                   gradient_energy_estimate=energy,state_SPD=mu,strict=strict,lambda_value=payload['lambda'],
                   reference_scope='local numerical stationary solve; not global minimum')
        write(dest/'result.json',row)
    elif payload['kind']=='hvp':
        joint=torch.cat((th,lp)); r=lambda v:residual(v[:n],v[n:]); ell=lambda v:.5*r(v).square().sum()
        # Fixed explicit-GN response route, labelled dense-assisted and charged.
        gstart=time.perf_counter(); j=torch.func.jacrev(r)(joint).numpy(); g=j.T@j
        z=np.linalg.solve(g[:n,:n]+gamma*np.eye(n),g[:n,n:]); gn_s=time.perf_counter()-gstart
        v=np.vstack((-z,np.eye(1))); vt=torch.from_numpy(v[:,0])
        times=[]; values=[]
        for label in ['cold','warmup','steady1','steady2','steady3']:
            t=time.perf_counter(); hv=torch.autograd.functional.hvp(ell,joint,v=vt)[1].numpy()
            f=float((v.T@hv[:,None]+gamma*z.T@z)[0,0]); d=hv[:n,None]-gamma*z
            times.append(dict(label=label,seconds=time.perf_counter()-t,hvp_count=1))
            values.append(hv)
        t=time.perf_counter(); h=torch.func.hessian(ell)(joint).numpy(); hessian_s=time.perf_counter()-t
        t=time.perf_counter(); mu=numerical_mu(h[:n,:n]+gamma*np.eye(n)); spectrum_s=time.perf_counter()-t
        t=time.perf_counter(); jv=torch.func.jvp(r,(joint,),(vt,))[1]
        y=torch.linspace(-1,1,len(jv)); jt_y=torch.func.vjp(r,joint)[1](y)[0]
        gradient=torch.func.grad(ell)(joint).numpy(); diag_s=time.perf_counter()-t
        expected=h@v[:,0]; ev=evaluate(g,h,n,gamma,z)
        parity=dict(hvp_relative=norm(hv-expected)/max(norm(expected),1e-30),
            SO_relative=abs(f-ev['F_SO'][0,0])/max(abs(ev['F_SO'][0,0]),1e-12),
            D_relative=norm(d-ev['D'])/max(norm(ev['D']),1e-12),
            adjoint_relative=abs(float(y@jv-jt_y@vt))/max(abs(float(y@jv)),1e-12),
            gradient_identity_relative=abs(h[-1,-1]-g[-1,-1]-gradient[-1])/max(abs(gradient[-1]),1e-12),
            gn_residual=norm(ev['R_G'])/max(norm(g[:n,n:]),1e-30))
        allpass=all(v<=cfg['operator_tolerance'] for v in parity.values())
        write(dest/'result.json',dict(center=payload['center'],all_checks_pass=allpass,parity=parity,
            route='explicit Jacobian GN + true AD directional HVP; dense-assisted, not end-to-end matrix-free',
            load_seconds=load_s,GN_jacobian_and_solve_seconds=gn_s,HVP_calls=times,
            SO_increment_cold_seconds=times[0]['seconds'],SO_increment_steady_median_seconds=float(np.median([r['seconds'] for r in times[2:]])),
            checkpoint_to_SO_cold_seconds=load_s+gn_s+times[0]['seconds'],
            validation_hessian_seconds=hessian_s,validation_spectrum_seconds=spectrum_s,validation_other_seconds=diag_s,
            hvp_count=5,jvp_count=1,vjp_count=1,explicit_jacobians=1,explicit_hessians=1,
            implicit_internal_AD_operation_counts=None,mu=mu,peak_native_memory=None,
            environment=dict(torch=torch.__version__,numpy=np.__version__,device='cpu',threads=1,sync='CPU synchronous perf_counter')))
    else: raise ValueError('unknown worker kind')

def initialize():
    if (OUT/'protocol_snapshot.json').exists():
        frozen=read(OUT/'protocol_snapshot.json')
        assert frozen['config_sha256']==sha(CONFIG)
        assert frozen['code_sha256']==sha(__file__)
        return
    if git('status','--porcelain'): raise RuntimeError('Commit tested correction code before starting validation')
    OUT.mkdir(parents=True,exist_ok=True)
    history=[dict(path=str(p),sha256=sha(p)) for folder in ['day1','day2'] for p in sorted((ROOT/'revision_week/outputs'/folder).rglob('*')) if p.is_file()]
    write(OUT/'protocol_snapshot.json',dict(config=read(CONFIG),config_sha256=sha(CONFIG),code_sha256=sha(__file__),
        solver_sha256=sha(ROOT/'revision_week/p1b_onestep.py'),source_commit=git('rev-parse','HEAD'),
        historical_artifacts=history,created_unix=time.time()))

def matrix_audit():
    rows=[]; recovery=[]; start=time.perf_counter()
    for path in sorted((ROOT/'revision_week/outputs/day1/raw').glob('*.json')):
        old=read(path)
        if old['status']!='PASS':
            rows.append(dict(center=old['center_id'],status=old['status'],failure_reason=old['failure_reason']));continue
        archive=read(old['input_path']); gg=archive['GN_blocks']; hh=archive['exact_blocks']
        g=np.block([[np.array(gg['G_tt']),np.array(gg['G_tl'])],[np.array(gg['G_tl']).T,np.array(gg['G_ll'])]])
        h=np.block([[np.array(hh['H_tt_sym']),np.array(hh['H_tl'])],[np.array(hh['H_tl']).T,np.array(hh['H_ll'])]])
        n=old['n_state']; gamma=old['gamma']; a=h[:n,:n]+gamma*np.eye(n)
        z=np.linalg.solve(g[:n,:n]+gamma*np.eye(n),g[:n,n:])
        # Exact original algorithm/budget; validate endpoint against saved trace.
        ad=refine(a,h[:n,n:],h[n:,n:],z,old['mu_value'],.1,100)
        err=norm(quadratic(h[n:,n:],h[:n,n:],a,ad['Z'])-old['F_star'])
        assert abs(err-old['adaptive_absolute_error'])<=1e-8*max(abs(old['F_star']),1.)
        assert ad['status']==old['adaptive']['status'] and len(ad['trace'])==len(old['adaptive']['trace'])
        vals,vecs=np.linalg.eigh(a); phases={}
        for label,zz in [('initial',z),('terminal',ad['Z'])]:
            d=h[:n,n:]-a@zz; q=float((d.T@np.linalg.solve(a,d))[0,0]); rotated=vecs.T@d
            u=norm(d)**2/old['mu_value']
            phases[label]=dict(q=q,U=u,effectivity=u/q if q>0 else None,
                mu_effective=norm(d)**2/q if q>0 else None,
                min_eigen_energy_fraction=float(rotated[0,0]**2/vals[0]/q) if q>0 else None)
        true=err/(abs(old['F_star'])+1e-8); estimated=ad['status']=='numerical_tolerance_met'
        rows.append(dict(center=old['center_id'],status='PASS',true_relative_error=true,estimated_pass=estimated,
            quadrant='Q1' if estimated and true<=.1 else 'Q2' if true<=.1 else 'Q4' if estimated else 'Q3',
            **{f'{label}_{k}':v for label,values in phases.items() for k,v in values.items()}))
    for cid in read(CONFIG)['centers']:
        ck,prov,residual,_=load_center(cid); old=read(ROOT/'revision_week/outputs/day1/raw'/f'{cid}.json'); arc=read(old['input_path'])
        errors={k:norm(ck[k]-np.array(arc[group][k]))/max(norm(arc[group][k]),1e-30)
                for group,keys in [('GN_blocks',['G_tt','G_tl','G_ll']),('exact_blocks',['H_tt_sym','H_tl','H_ll'])] for k in keys}
        r=residual(torch.from_numpy(ck['theta']),torch.from_numpy(ck['log_parameter'])).numpy()
        assert all(v<=1e-6 for v in errors.values())
        recovery.append(dict(center=cid,full_blocks_pass=True,max_block_relative_error=max(errors.values()),
            residual_replay_max_abs=float(np.max(abs(r-ck['residual_at_center']))),
            checkpoint_sha256=sha(OLD/'recovery'/cid/'state_checkpoint.npz'),new_training_attempts=0))
    write(OUT/'matrix_audit.json',dict(rows=rows,recovery=recovery,seconds=time.perf_counter()-start))
    csvout(OUT/'ADAPT_TERMINAL_ANALYSIS.csv',rows);csvout(OUT/'RECOVERY_BLOCK_VALIDATION.csv',recovery)

def profile_task(cid,task_id,lam,init,strict,gate):
    p=OUT/'initial_states'/f'{task_id}.npz';p.parent.mkdir(exist_ok=True)
    if not p.exists():np.savez_compressed(p,theta=init)
    else:np.testing.assert_array_equal(np.load(p)['theta'],init)
    if sum(1 for c in (OUT/'tasks').glob('*/claim.json') if read(c)['payload']['kind']=='profile')>=read(CONFIG)['max_profile_solves'] and not (OUT/'tasks'/task_id/'claim.json').exists():
        raise RuntimeError('profile validation solve budget exhausted')
    dest,process=task(task_id,dict(kind='profile',center=cid,lambda_=lam,**{'lambda':lam},init_path=str(p),
                                init_sha256=sha(p),strict=strict,historical_gate=gate))
    if process['status']!='PASS':return None,None,task_id
    return read(dest/'result.json'),np.load(dest/'state.npz')['theta'].copy(),task_id

def profiles():
    cfg=read(CONFIG); oldrows=list(csv.DictReader((OLD/'ONE_STEP_PILOT.csv').open(encoding='utf-8')))
    oldsummary=read(OLD/'p1b_d_summary.json'); result=[]
    for cid in cfg['roots']:
        if not read(OUT/'tasks'/f'hvp_{cid}'/'result.json')['all_checks_pass']:raise RuntimeError('HVP gate failed')
        ck,prov,residual,_=load_center(cid); th=ck['theta']; lp=float(ck['log_parameter'][0]);gamma=float(ck['gamma']);n=len(th)
        rootmu=numerical_mu(ck['H_tt_sym']+gamma*np.eye(n))
        gate=next(x['gate'] for x in oldsummary['cost_notes'] if x['root_id']==cid and x['kind']=='root_qualification')
        rootgrad=norm(ck['gradient_theta_sum_objective'])/len(ck['residual_at_center'])/max(norm(th),1.)
        if rootmu['mu_value'] is None or rootgrad>gate:
            for off in cfg['offsets']:
                for method in ['RAW','SAEPS-GN','SO','EXACT-REDUCED-ORACLE']:
                    result.append(dict(root=cid,offset=off,method=method,status='root_not_qualified'))
            write(OUT/'profile_audit.json',result)
            continue
        for off in cfg['offsets']:
            tag=f'{cid}_{"plus" if off>0 else "minus"}';lam=lp+off
            initial=th-ck['gn_response_Z'][:,0]*off
            base,theta,baseid=profile_task(cid,tag+'_start',lam,initial,False,gate)
            if base is None:result.append(dict(root=cid,offset=off,status='budget_exhausted_or_failed'));continue
            strict,theta_strict,sid=profile_task(cid,tag+'_start_strict',lam,theta,True,gate)
            if strict is None:result.append(dict(root=cid,offset=off,status='strict_start_failed'));continue
            # Reconstruct shared GN initialization at the original replayed start.
            joint=torch.cat((torch.from_numpy(theta),torch.tensor([lam])))
            r=lambda v:residual(v[:n],v[n:]);j=torch.func.jacrev(r)(joint).numpy();g=j.T@j
            z=np.linalg.solve(g[:n,:n]+gamma*np.eye(n),g[:n,n:])[:,0]
            branch=[r for r in oldrows if r['root_id']==cid and float(r['offset_id'])==off]
            cached={}
            for row in branch:
                trial=float(row['trial_lambda']); step=trial-lam
                if trial not in cached:
                    k=len(cached);b,t,bid=profile_task(cid,f'{tag}_candidate{k}',trial,theta-z*step,False,gate)
                    s,ts,ssid=profile_task(cid,f'{tag}_candidate{k}_strict',trial,t,True,gate) if b else (None,None,None)
                    cached[trial]=(b,s,bid,ssid)
                cand,strictcand,cid_task,csid=cached[trial]
                if cand is None or strictcand is None:result.append(dict(root=cid,offset=off,method=row['method'],status='candidate_validation_failed'));continue
                oldactual=float(row['actual_profile_decrease']); oldpred=float(row['predicted_decrease'])
                replayactual=base['final_loss']-cand['final_loss']; strictactual=strict['final_loss']-strictcand['final_loss']
                change=abs(base['final_loss']-strict['final_loss'])+abs(cand['final_loss']-strictcand['final_loss'])
                energies=sum(abs(x.get('gradient_energy_estimate') or 0) for x in [strict,strictcand])
                floor=64*np.finfo(float).eps*max(abs(base['final_loss']),abs(cand['final_loss']),1.)
                error_estimate=cfg['resolution_safety_factor']*(change+energies)+floor
                stationary=all(x['converged'] for x in [strict,strictcand])
                spd=all(x['state_SPD']['mu_value'] is not None for x in [base,strict,cand,strictcand]) and rootmu['mu_value'] is not None
                resolved=stationary and spd and strictactual>error_estimate and strictactual-1e-4*oldpred>error_estimate
                result.append(dict(root=cid,offset=off,method=row['method'],status='PASS' if resolved else 'UNRESOLVED',
                    replay_actual=replayactual,historical_actual=oldactual,replay_absolute_difference=abs(replayactual-oldactual),
                    strict_actual=strictactual,predicted=oldpred,objective_precision_change=change,
                    local_remaining_gradient_energy=energies,error_estimate=error_estimate,
                    error_estimate_status='numerical_precision_audit_not_rigorous_bound',stationarity_pass=stationary,SPD_pass=spd,
                    root_min_eigen=rootmu['lambda_min_A_numeric'],root_normalized_gradient=rootgrad,
                    start_grad=strict['final_grad_normalized'],candidate_grad=strictcand['final_grad_normalized'],
                    branch_consistency_status='precision_stable_local_minimum' if resolved else 'unresolved_precision_or_local_branch',
                    numerical_descent_resolved=resolved,parameter_error_improved=float(row['parameter_error_after'])<float(row['parameter_error_before']),
                    start_task=baseid,strict_start_task=sid,candidate_task=cid_task,strict_candidate_task=csid))
                write(OUT/'profile_audit.json',result)
    csvout(OUT/'ONE_STEP_PRECISION_AUDIT.csv',result)
    write(OUT/'profile_complete.json',dict(rows=len(result)))

def run_all():
    initialize()
    if not (OUT/'matrix_audit.json').exists():matrix_audit()
    for cid in read(CONFIG)['centers']:task('hvp_'+cid,dict(kind='hvp',center=cid))
    if not (OUT/'profile_complete.json').exists():profiles()
    report()

def report():
    frozen=read(OUT/'protocol_snapshot.json')
    for row in frozen['historical_artifacts']:
        if sha(row['path'])!=row['sha256']:raise RuntimeError('Historical output changed')
    matrix=read(OUT/'matrix_audit.json'); profiles_=read(OUT/'profile_audit.json')
    workers=[read(p) for p in sorted((OUT/'tasks').glob('*/process.json'))]
    hvp=[read(OUT/'tasks'/f'hvp_{cid}'/'result.json') for cid in read(CONFIG)['centers']]
    costs=read(OLD/'p1b_cost_ledger.json');b=read(OLD/'p1b_b_cost.json')
    measured=sum(costs['p1b_new_measured'].values())
    # Include full successful recovery activity, not just its training interval.
    measured_full=measured-costs['p1b_new_measured']['recovery_P1B_B_successful_replay_seconds']+b['wall_seconds']
    quadrants={q:sum(r.get('quadrant')==q for r in matrix['rows']) for q in ['Q1','Q2','Q3','Q4']}
    valid=[r for r in matrix['rows'] if r['status']=='PASS']
    ledger=dict(historical_successful_activity_measured_seconds=measured_full,
        historical_measured_parts=costs['p1b_new_measured'],historical_recovery_full_wall_seconds=b['wall_seconds'],
        historical_failed_compute_estimates=costs['failed_development_attempts_non_production'],
        historical_recovery_budget_usage='successful measured activity + failed replay estimates; exact cumulative total unavailable',
        original_recovery_attempt_rule='VIOLATED: multiple executed replay rounds, including export failures; no retroactive success-only reinterpretation',
        original_freeze_timing='UNVERIFIED: protocol first committed with results; supplied summaries do not prove pre-run byte freeze',
        new_training_attempts=0,new_validation_process_seconds=sum(w['wall_seconds'] for w in workers),
        new_matrix_analysis_seconds=matrix['seconds'],new_profile_solves=sum(read(p)['payload']['kind']=='profile' for p in (OUT/'tasks').glob('*/claim.json')),
        new_budget_seconds=read(CONFIG)['total_new_process_seconds'],historical_failures_charged=True,
        stage1_cost_unchanged=read(ROOT/'revision_week/outputs/day1/cumulative_costs.json'),
        costs_scope='process wall time includes all new successful/failed/timeout workers; Python AD primitive counts do not include hidden framework operations')
    write(OUT/'COST_LEDGER.json',ledger)
    outcome=dict(historical_outputs_unchanged=True,recovery_blocks_pass=all(r['full_blocks_pass'] for r in matrix['recovery']),
        hvp_pass=sum(r['all_checks_pass'] for r in hvp),hvp_attempted=len(hvp),quadrants=quadrants,
        profile_rows=len(profiles_),profile_numerically_resolved=sum(r.get('numerical_descent_resolved',False) for r in profiles_),
        process_failures=sum(w['status']!='PASS' for w in workers),
        original_protocol_compliance='NOT_ESTABLISHED_WITH_RETAINED_DEVIATIONS',
        independent_freeze_readiness='DEFER: new protocol must explicitly acknowledge historical deviations and supplemental development scope',
        terminal_median_effectivity=float(np.median([r['terminal_effectivity'] for r in valid])),
        initial_median_effectivity=float(np.median([r['initial_effectivity'] for r in valid])),
        source_commit=frozen['source_commit'])
    write(OUT/'VALIDATION.json',outcome)
    csvout(OUT/'HVP_COST_AND_PARITY.csv',[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in hvp])
    report_text=f'''# Phase 1B 审查修复报告

本目录是新的补充开发验证；day1/day2 原始产物逐文件 SHA256 保持不变。
没有新增训练、替换种子、调 gamma 或重新选择候选步。来源提交 {frozen['source_commit']}。

机器验收结果：

```json
{json.dumps(outcome,indent=2,ensure_ascii=False)}
```

## 修复与可保留结论

恢复检查现在比较全部六个G/H块和保存数据生成的残差；不再只比较曲率标量。
HVP路径从保存的真实状态/数据构建，完整收费：加载、显式GN Jacobian/求解、冷HVP、
独立预热、三次稳态HVP、验证Hessian和谱分解。该路线明确为dense-assisted，未声称全流程矩阵无关。
每条HVP结果检查全部算子/二次型/伴随/梯度恒等式，而非只检查H@v。

ADAPT保留原算法停止点与100次迭代预算，只重放矩阵算法以恢复最终Z，核对保存终点。
初始与最终缺陷的谱机制分开保存于ADAPT_TERMINAL_ANALYSIS.csv，不再混用。

一步补验只重放原保存的候选坐标，完全相同坐标去重。共同起点和候选均做一次固定精化，
保存状态、带锚定目标、梯度、状态块SPD和精化前后目标变化。数值可分辨要求下降与接受余量
超过10倍精化变化和剩余局部梯度能量估计；这仍是数值精度审计，不是严格全局误差界。
GN/SO/ORACLE原候选被信赖半径截到同一点，所以不能推导SO相对GN的实际一步增益。

## 不可被事后修复的历史偏差

历史多次重放与导出失败确实发生，违反每中心一次流程限制；计入失败计算估计，不能称421秒为总用量。
历史失败的精确计时和尝试原始日志未完整保存，只有原台账估计，本轮无法追溯补造。
历史协议与结果同提交，缺少可独立验证的运行前冻结证据，不反向认证原冻结。
新的24次上限精度补验是本次修复授权下的补充验证，不并入原16次试验或称原预算执行完全合规。

已测历史成功活动 {measured_full:.6f} 秒；原HVP实测 {costs['p1b_new_measured']['hvp_P1B_C_seconds']:.6f} 秒。
新工作进程墙钟合计 {ledger['new_validation_process_seconds']:.6f} 秒，矩阵复核 {matrix['seconds']:.6f} 秒。
完整失败估计、第一阶段历史成本与新成本分别见COST_LEDGER.json；未知总量不伪造单一精确值。

结论：保留有证据的局部代数、恢复、HVP和精度审计结果；撤回原报告“全部合规、冻结条件全部满足”。
可以据本轮证据讨论新的独立协议，但不自动冻结或启动。所有输出由机器结果生成；未使用硬编码成功数。
'''
    (OUT/'PHASE1B_CORRECTED_REPORT.md').write_text(report_text,encoding='utf-8',newline='\n')
    claims=[dict(claim='SO pointwise increment over GN in actual update',status='NOT_SUPPORTED',reason='identical clipped trial coordinates'),
            dict(claim='Strict low-cost error certification',status='NOT_SUPPORTED',reason='ordinary eigensolve; dense-assisted route'),
            dict(claim='Original one-replay protocol compliant',status='NOT_SUPPORTED',reason=ledger['original_recovery_attempt_rule']),
            dict(claim='Supplemental real HVP parity',status='SUPPORTED' if outcome['hvp_pass']==4 else 'NOT_SUPPORTED',evidence='tasks/hvp_*/result.json'),
            dict(claim='Numerically resolved local decrease on saved candidates',status='SUPPORTED' if outcome['profile_numerically_resolved']==16 else 'PARTIALLY_SUPPORTED' if outcome['profile_numerically_resolved'] else 'NOT_SUPPORTED',evidence='ONE_STEP_PRECISION_AUDIT.csv')]
    write(OUT/'CLAIM_LEDGER.json',claims)
    print(json.dumps(outcome,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','report','worker']);parser.add_argument('--task')
    args=parser.parse_args()
    if args.action=='worker':worker(Path(args.task))
    elif args.action=='run':run_all()
    else:report()
