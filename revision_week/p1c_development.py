"""Bounded, prospective development; original experiments remain immutable."""
from __future__ import annotations
import argparse, sys, time, platform
from pathlib import Path
import numpy as np
import torch
from p1b_correct import ROOT, OUT as PREVIOUS, read, write, sha, git, csvout, load_center, bounded_command, norm
from p1b_onestep import profile_solve
from core import numerical_mu, quadratic, refine

OUT=ROOT/'revision_week/outputs/phase1c_development_v1'
CONFIG=ROOT/'revision_week/config/phase1c_development.json'
METHODS=['RAW','SAEPS-GN','SO','EXACT-REDUCED-ORACLE']

def polish(objective, initial, m, cfg):
    """SPD Newton with fixed line search. No Hessian regularization or gate change."""
    theta=initial.detach().clone(); trace=[]; evals=0; grads=0; hessians=0
    start=time.perf_counter(); reason='iteration_limit'
    for k in range(cfg['newton_iterations']+1):
        value=float(objective(theta)); g=torch.func.grad(objective)(theta).numpy(); evals+=2;grads+=1
        a=torch.func.hessian(objective)(theta).numpy(); hessians+=1
        mu=numerical_mu(a); gn=norm(g)/m/max(norm(theta.numpy()),1.)
        energy=float(g@np.linalg.solve(a,g)/2) if mu['mu_value'] else None
        row=dict(iteration=k,loss=value,gradient_sum=norm(g),gradient_mean_normalized=gn,
                 gradient_energy=energy,mu=mu['mu_value']);trace.append(row)
        if not mu['mu_value']: reason='state_not_SPD';break
        if gn<=cfg['newton_target']: reason='target_reached';break
        if k==cfg['newton_iterations']:break
        direction=np.linalg.solve(a,-g); accepted=False
        floor=64*np.finfo(float).eps*max(1.,abs(value))
        for bt in range(cfg['newton_backtracks']):
            alpha=2.**(-bt); trial=theta+torch.from_numpy(alpha*direction)
            fv=float(objective(trial));evals+=1
            # At objective roundoff, also demand a strict gradient decrease.
            if fv<=value+cfg['armijo']*alpha*float(g@direction):
                accepted=True
            elif abs(fv-value)<=floor:
                gt=torch.func.grad(objective)(trial).numpy();evals+=1;grads+=1
                accepted=norm(gt)<.5*norm(g)
            if accepted:
                row.update(alpha=alpha,objective_change=fv-value,roundoff_floor=floor)
                theta=trial.detach();break
        if not accepted:reason='line_search_failed';break
    ok=bool(mu['mu_value'] and gn<=cfg['gradient_gate'])
    return theta,dict(status='PASS' if ok else 'PROFILE_FAILURE',failure_reason=None if ok else reason,
        termination=reason,trace=trace,loss=value,gradient=gn,energy=energy,SPD=bool(mu['mu_value']),
        objective_evals=evals,gradient_evals=grads,explicit_hessians=hessians,seconds=time.perf_counter()-start)

def energy_interval(a,d,mu,iterations):
    """q = 2 d'w - w'Aw + r'A^-1 r; only final scalar energy is bounded."""
    d=np.asarray(d).reshape(-1);w=np.zeros_like(d);r=d.copy();z=r/np.diag(a);p=z.copy();rz=float(r@z)
    count=0;used=0
    for k in range(iterations):
        if rz<=np.finfo(float).tiny:break
        ap=a@p;count+=1;den=float(p@ap)
        if den<=0:raise ValueError('non-SPD estimator direction')
        alpha=rz/den;w+=alpha*p;r-=alpha*ap;z=r/np.diag(a);new=float(r@z)
        p=z+(new/rz)*p;rz=new;used=k+1
    aw=a@w;count+=1;r=d-aw
    lower=float(2*d@w-w@aw);upper=lower+float(r@r)/mu
    return dict(lower=lower,upper=upper,iterations=used,A_matvec_count=count,residual_norm=norm(r))

def curvature(residual,theta,lam,gamma):
    start=time.perf_counter();n=len(theta);joint=torch.cat((theta,torch.tensor([lam])))
    r=lambda v:residual(v[:n],v[n:]);ell=lambda v:.5*r(v).square().sum()
    j=torch.func.jacrev(r)(joint).numpy();g=j.T@j;h=torch.func.hessian(ell)(joint).numpy()
    z=np.linalg.solve(g[:n,:n]+gamma*np.eye(n),g[:n,n:]);a=h[:n,:n]+gamma*np.eye(n)
    f=[float(g[-1,-1]),float(quadratic(g[n:,n:],g[:n,n:],g[:n,:n]+gamma*np.eye(n),z)[0,0]),
       float(quadratic(h[n:,n:],h[:n,n:],a,z)[0,0]),float(h[-1,-1]-(h[n:,:n]@np.linalg.solve(a,h[:n,n:]))[0,0])]
    grad=float(torch.func.grad(ell)(joint)[-1])
    return dict(zip(METHODS,f)),z[:,0],grad,time.perf_counter()-start

def root_worker(cid,dest,cfg):
    ck,prov,residual,load_seconds=load_center(cid);anchor=torch.from_numpy(ck['theta']);gamma=float(ck['gamma'])
    m=len(ck['residual_at_center']);lam0=float(ck['log_parameter'][0]);diagnostics=[];rows=[]
    bench='Burgers' if cid.startswith('burgers') else 'Allen-Cahn'
    truth=prov['data_recipe']['runtime_config']['benchmarks'][bench]['truth_parameter']
    for off in cfg['offsets']:
        tag=f'{cid}_{"plus" if off>0 else "minus"}';lam=lam0+off;states={}
        # Diagnose every old strict state, including unfavorable candidate records.
        for old in sorted((PREVIOUS/'tasks').glob(tag+'_*_strict')):
            lp=read(old/'claim.json')['payload']['lambda'];init=torch.from_numpy(np.load(old/'state.npz')['theta'])
            obj=lambda t:.5*residual(t,torch.tensor([lp])).square().sum()+.5*gamma*(t-anchor).square().sum()
            th,result=polish(obj,init,m,cfg);result.update(task=old.name,old_result=read(old/'result.json'),lambda_value=lp)
            diagnostics.append(result);states[old.name]=(th,result)
            np.savez_compressed(dest/(old.name+'.npz'),theta=th.numpy())
            write(dest/'stationarity.json',diagnostics)
        theta,start_result=states[tag+'_start_strict']
        if start_result['status']!='PASS':
            rows.extend(dict(root=cid,offset=off,method=method,status='PROFILE_FAILURE',failure_reason='common_start_failed') for method in METHODS)
            write(dest/'steps.json',rows);continue
        f,z,gradient,curv_seconds=curvature(residual,theta,lam,gamma)
        beta=cfg['shift_beta_scale']*max(f['RAW'],1e-8)
        write(dest/(tag+'_curvature.json'),dict(curvatures=f,gradient=gradient,beta=beta,seconds=curv_seconds,
            route='dense Jacobian and Hessian validation route',explicit_jacobians=1,explicit_hessians=1))
        for method in METHODS:
            if f[method]+beta<=0:
                rows.append(dict(root=cid,offset=off,method=method,status='NUMERICAL_FAILURE',failure_reason='nonpositive_shifted_curvature'));continue
            raw=-gradient/(f[method]+beta);scaled=cfg['step_fraction']*raw
            step=float(np.clip(scaled,-cfg['trust_radius'],cfg['trust_radius']));lp=lam+step
            candidate=profile_solve(residual,anchor,lp,gamma,theta-torch.from_numpy(z*step),cfg['gradient_gate'],
                cap_s=60,max_iter=300,tolerance_grad=1e-12,tolerance_change=1e-18)
            obj=lambda t:.5*residual(t,torch.tensor([lp])).square().sum()+.5*gamma*(t-anchor).square().sum()
            if candidate.hit_cap:
                rows.append(dict(root=cid,offset=off,method=method,status='SOLVER_FAILURE',failure_reason='candidate_budget_exhausted',solve_seconds=candidate.solve_seconds));continue
            th,result=polish(obj,candidate.theta,m,cfg)
            np.savez_compressed(dest/(tag+'_'+method+'_candidate.npz'),theta=th.numpy())
            write(dest/(tag+'_'+method+'_solve.json'),dict(lbfgs={k:v for k,v in vars(candidate).items() if k!='theta'},newton=result))
            actual=start_result['loss']-result['loss'];pred=-(gradient*step+.5*f[method]*step*step)
            err=10*(abs(start_result['energy'] or 0)+abs(result['energy'] or 0))+64*np.finfo(float).eps*max(1.,abs(start_result['loss']))
            valid=result['status']=='PASS';accepted=bool(valid and pred>0 and actual-cfg['armijo']*pred>err)
            rows.append(dict(root=cid,offset=off,method=method,status='PASS' if valid else 'PROFILE_FAILURE',
                failure_reason=result['failure_reason'],raw_step=raw,step=step,trust_radius_active=bool(abs(scaled)>cfg['trust_radius']),
                predicted=pred,actual=actual,error_estimate=err,error_status='local_gradient_energy_diagnostic_not_certificate',
                accepted=accepted,start_gradient=start_result['gradient'],candidate_gradient=result['gradient'],
                parameter_error_before=abs(np.exp(lam)-truth)/truth,parameter_error_after=abs(np.exp(lp)-truth)/truth,
                candidate_cost_seconds=candidate.solve_seconds+result['seconds']))
            write(dest/'steps.json',rows)
    write(dest/'result.json',dict(root=cid,load_seconds=load_seconds,stationarity=diagnostics,steps=rows))

def matrix_worker(dest,cfg):
    rows=[]
    for path in sorted((ROOT/'revision_week/outputs/day1/raw').glob('*.json')):
        start=time.perf_counter();old=read(path)
        if old['status']!='PASS':rows.append(dict(center=old['center_id'],status=old['status'],failure_reason=old['failure_reason']));continue
        archive=read(old['input_path']);gg=archive['GN_blocks'];hh=archive['exact_blocks'];n=old['n_state'];gamma=old['gamma']
        a=np.array(hh['H_tt_sym'])+gamma*np.eye(n);b=np.array(hh['H_tl']);c=np.array(hh['H_ll'])
        z=np.linalg.solve(np.array(gg['G_tt'])+gamma*np.eye(n),np.array(gg['G_tl']))
        terminal=refine(a,b,c,z,old['mu_value'],.1,100);z=terminal['Z']
        f=float(quadratic(c,b,a,z)[0,0]);d=b-a@z
        replay_seconds=time.perf_counter()-start
        t=time.perf_counter();mu=numerical_mu(a);spectrum_seconds=time.perf_counter()-t
        t=time.perf_counter();interval=energy_interval(a,d,mu['mu_value'],cfg['estimator_iterations']);estimate_seconds=time.perf_counter()-t
        t=time.perf_counter();q=float((d.T@np.linalg.solve(a,d))[0,0]);oracle_seconds=time.perf_counter()-t
        upper=interval['upper'];rel=upper/(abs(f)-upper) if abs(f)>upper else None
        true=q/abs(f-q);passed=bool(rel is not None and rel<=.1)
        assert abs(abs(f-old['F_star'])-old['adaptive_absolute_error'])<1e-8*max(1.,abs(old['F_star']))
        rows.append(dict(center=old['center_id'],status='PASS',terminal_F=f,true_error_energy=q,true_relative=true,
            old_estimated_pass=terminal['status']=='numerical_tolerance_met',new_estimated_pass=passed,
            quadrant='Q1' if passed and true<=.1 else 'Q2' if true<=.1 else 'Q4' if passed else 'Q3',
            upper_effectivity=upper/q,old_upper_effectivity=(norm(d)**2/old['mu_value'])/q,
            relative_estimate=rel,interval_contains_reference=bool(interval['lower']-1e-10*max(1.,q)<=q<=upper+1e-10*max(1.,q)),
            **interval,replay_seconds=replay_seconds,spectrum_seconds=spectrum_seconds,estimate_seconds=estimate_seconds,
            oracle_seconds=oracle_seconds,bound_status='dense_assisted_numerical_estimate_not_certificate'))
        write(dest/'result.json',rows)

def run():
    cfg=read(CONFIG)
    if not (OUT/'snapshot.json').exists():
        if git('status','--porcelain'):raise RuntimeError('commit protocol and tested code first')
        OUT.mkdir(parents=True,exist_ok=False)
        hist=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for folder in ['day1','day2','phase1b_correction_v1']
            for p in sorted((ROOT/'revision_week/outputs'/folder).rglob('*')) if p.is_file()]
        code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),CONFIG,ROOT/'revision_week/core.py',ROOT/'revision_week/p1b_correct.py',ROOT/'revision_week/p1b_onestep.py']}
        write(OUT/'snapshot.json',dict(config=cfg,code=code,commit=git('rev-parse','HEAD'),history=hist,
            environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,device='cpu',threads=1,dtype='float64',hardware=platform.platform(),peak_memory=None)))
    snap=read(OUT/'snapshot.json')
    assert all(sha(ROOT/p)==s for p,s in snap['code'].items())
    for name in [*cfg['roots'],'matrix']:
        dest=OUT/name
        if dest.exists():
            if (dest/'process.json').exists():continue
            raise RuntimeError('interrupted attempt retained, no retry')
        used=sum(read(p)['wall_seconds'] for p in OUT.glob('*/process.json'));remaining=cfg['total_worker_seconds']-used
        dest.mkdir();write(dest/'claim.json',dict(name=name,timeout=min(cfg['per_worker_seconds'],remaining),commit=snap['commit']))
        if remaining<=0:proc=dict(status='budget_exhausted',wall_seconds=0,exit_code=None)
        else:proc=bounded_command([sys.executable,__file__,'worker','--name',name],min(cfg['per_worker_seconds'],remaining))
        write(dest/'process.json',proc);print(name,proc['status'],proc['wall_seconds'],flush=True)
    report()

def report():
    snap=read(OUT/'snapshot.json');assert all(sha(ROOT/x['path'])==x['sha256'] for x in snap['history'])
    stationarity=[];steps=[];mat=[];processes=[]
    for name in [*snap['config']['roots'],'matrix']:
        p=OUT/name;proc=read(p/'process.json');processes.append(dict(name=name,**proc))
        if (p/'result.json').exists():
            result=read(p/'result.json')
            if name=='matrix':mat=result
            else:stationarity+=result['stationarity'];steps+=result['steps']
        elif name!='matrix':
            for off in snap['config']['offsets']:
                for method in METHODS:steps.append(dict(root=name,offset=off,method=method,status='SOLVER_FAILURE',failure_reason=proc['status']))
    valid=[r for r in mat if r['status']=='PASS'];good=[r for r in steps if r['status']=='PASS'];pairs=[]
    for root in snap['config']['roots']:
        for off in snap['config']['offsets']:
            by={r['method']:r for r in good if r['root']==root and r['offset']==off}
            if 'SO' in by and 'SAEPS-GN' in by:
                so,gn=by['SO'],by['SAEPS-GN'];diff=so['actual']-gn['actual'];margin=so['error_estimate']+gn['error_estimate']
                pairs.append(dict(root=root,offset=off,SO_minus_GN_actual=diff,comparison_error_estimate=margin,
                    resolved=abs(diff)>margin,SO_better=diff>margin,distinct_steps=so['step']!=gn['step']))
    summary=dict(stationarity_total=len(stationarity),stationarity_pass=sum(r['status']=='PASS' for r in stationarity),
        planned_steps=16,step_records=len(steps),valid_steps=len(good),accepted_steps=sum(r.get('accepted',False) for r in steps),
        parameter_error_improved=sum(r['parameter_error_after']<r['parameter_error_before'] for r in good),
        paired_branches=pairs,independent_roots=2,adapt_planned=25,adapt_valid=len(valid),
        old_estimated_pass=sum(r['old_estimated_pass'] for r in valid),new_estimated_pass=sum(r['new_estimated_pass'] for r in valid),
        quadrants={q:sum(r['quadrant']==q for r in valid) for q in ['Q1','Q2','Q3','Q4']},
        median_new_effectivity=float(np.median([r['upper_effectivity'] for r in valid])) if valid else None,
        interval_checks=all(r['interval_contains_reference'] for r in valid),
        worker_seconds=sum(p['wall_seconds'] for p in processes),historical_hashes_preserved=len(snap['history']),
        source_commit=snap['commit'],training=0,new_seeds=0,
        scientific_scope='development only; no strict certificate, efficiency or general SO superiority claim')
    write(OUT/'SUMMARY.json',summary);csvout(OUT/'ONE_STEP.csv',steps);csvout(OUT/'ADAPT_ESTIMATOR.csv',mat);csvout(OUT/'SO_GN_PAIRED.csv',pairs)
    write(OUT/'STATIONARITY.json',stationarity)
    text=['# Phase 1C 开发试验实测报告','', '本轮为用户授权的补充开发，旧协议与失败结果保持不变。', '',
        f"驻点校正：{summary['stationarity_pass']}/{summary['stationarity_total']} 达到原定 1e-8 门槛。",
        f"新一步比较：{summary['valid_steps']}/16 状态有效；{summary['accepted_steps']}/16 接受。",
        f"合成真值参数误差改善：{summary['parameter_error_improved']}/{len(good)}，与目标下降独立报告。",'',
        'SO 与 GN 的逐分支实际下降差及误差分辨率：', '```json',__import__('json').dumps(pairs,ensure_ascii=False,indent=2),'```',
        f"SO-ADAPT 终点固定，旧估计通过 {summary['old_estimated_pass']}/{len(valid)}；新估计通过 {summary['new_estimated_pass']}/{len(valid)}。",
        f"四格表：{summary['quadrants']}；新界有效度中位数 {summary['median_new_effectivity']}。",'',
        f"新增 worker 活动墙钟 {summary['worker_seconds']:.3f} 秒（含进程启动）；工程检查另列。历史 {summary['historical_hashes_preserved']} 文件哈希不变。",'',
        '驻点修复使用稠密精确 Hessian Newton，仅证明小网络上的数值可行性；不建立大规模求解效率。',
        '新步长为运行前固定的统一 0.1 倍原始步，再应用 0.1 安全半径；只覆盖两个标量根中心，不是多参数独立验证。',
        '新估计利用固定 8 步对角 PCG 和已有数值谱下界；原 SO-ADAPT 迭代终点不变。这不是严格证书，也不是端到端 matrix-free 优势。',
        '历史重复恢复和原协议冻结时序偏差保留；本轮不启动独立确认或下游实验。']
    (OUT/'REPORT.md').write_text('\n\n'.join(text),encoding='utf-8')
    print(summary,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','worker','report']);p.add_argument('--name');args=p.parse_args()
    if args.action=='run':run()
    elif args.action=='report':report()
    elif args.name=='matrix':matrix_worker(OUT/args.name,read(CONFIG))
    else:root_worker(args.name,OUT/args.name,read(CONFIG))
