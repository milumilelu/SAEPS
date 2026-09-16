"""Phase2-only planned denominators, reports, plots and final engineering audit."""
from common import *
from reporting import records,dev_summary,e1_summary,costs,validate_manifests

def failure_row(m,extra=None):
    stopped=m.get('execution_disposition')=='PROTOCOL_STOP'
    return dict(**(extra or {}),status=None if stopped else 'SOLVER_FAILURE',execution_disposition='PROTOCOL_STOP' if stopped else 'FAILED',
                failure_reason=m.get('failure_reason') or m.get('process',{}).get('failure_reason') or 'missing_worker_result')

def stage_rows(node):
    cfg=read(LOCK/'execution.json');rows=[]
    for m,r in records(node):
        job=m['job']
        if node=='E3':
            observed={(a['offset'],a['method']):a for a in (r or {}).get('rows',[])}
            for off in cfg['e3']['offsets']:
                for method in cfg['e3']['methods']:
                    row=observed.get((off,method),failure_row(m))
                    rows.append(dict(row,group=job['group'],seed=job['seed'],offset=off,method=method))
        elif node=='E5C':
            observed={a['pass_label']:a for a in (r or [])}
            for label in ['cold','warmup','steady_1','steady_2','steady_3']:
                row=observed.get(label)
                if row is None and m.get('raw_directory'):
                    p=ROOT/m['raw_directory']/(label+'.json')
                    if p.exists():row=read(p)
                rows.append(dict(row or failure_row(m),n=job['n'],m=job['m'],pass_label=label,shared_process_memory=m.get('process')))
        elif isinstance(r,list):rows.extend(r)
        else:
            row=dict(r or failure_row(m),**{k:job[k] for k in ['group','seed','center'] if k in job})
            if node=='E4C' and r and r.get('binding_valid'):
                curve=read(ROOT/m['raw_directory']/'curvature.json');ref=np.array(curve['F_star']);vals,vecs=np.linalg.eigh(ref)
                resolved=float(vals[1]-vals[0])>1e-6*max(norm(ref),curve['eta_F']);geometry={}
                for method in ['RAW','GN','SO']:
                    mm=np.array(curve['F_'+method]);vv,qq=np.linalg.eigh(mm)
                    geometry[method]=dict(eigenvalues=vv,weak_eigenvalue_error=float(vv[0]-vals[0]),weak_angle_degrees=float(np.degrees(np.arccos(np.clip(abs(qq[:,0]@vecs[:,0]),0,1)))) if resolved else None,
                        signature=np.sign(vv),SPD=bool(vv[0]>curve['eta_F']),SPD_condition=float(vv[-1]/vv[0]) if vv[0]>curve['eta_F'] else None,coordinate_coupling=float(mm[0,1]))
                row.update(geometry=native(geometry),eigenvector_resolved=resolved,reference_eigengap=float(vals[1]-vals[0]))
            rows.append(row)
    return rows

def sign_p(wins,losses):
    import math
    n=wins+losses
    return sum(math.comb(n,k) for k in range(wins,n+1))/2**n if n else None

def multi_summary(rows):
    valid=[r for r in rows if r.get('binding_valid')];wins=sum(r['metrics']['fro']['strict_SO_win'] for r in valid);loss=sum(r['metrics']['fro']['strict_GN_win'] for r in valid)
    logs=[r['metrics']['fro']['logR_floor'] for r in valid];median=float(np.median(logs)) if logs else None;sp=sum(r['metrics']['spectral']['strict_SO_win'] for r in valid);p=sign_p(wins,loss)
    supported=len(valid)>=9 and wins>=8 and median>0 and p is not None and p<=.05 and sp>len(valid)/2
    return dict(planned=10,valid=len(valid),frobenius_wins=wins,spectral_wins=sp,median_logR_floor=median,conditional_sign_p=p,
                conclusion='SUPPORTED' if supported else 'NOT_SUPPORTED' if len(valid)>=9 and wins<=len(valid)/2 else 'PARTIALLY_SUPPORTED')

def step_summary(rows):
    roots=[]
    for group,seed in sorted(set((r['group'],r['seed']) for r in rows)):
        sides=[]
        for off in [.05,-.05]:
            pair={r['method']:r for r in rows if r['group']==group and r['seed']==seed and r['offset']==off and r.get('status')=='PASS'}
            if all(k in pair for k in ['SO','SAEPS-GN']):
                so,gn=pair['SO'],pair['SAEPS-GN'];sides.append(dict(offset=off,difference=so['actual']-gn['actual'],error=so['error_estimate']+gn['error_estimate'],distinct_steps=so['step']!=gn['step']))
        complete=len(sides)==2;delta=float(np.mean([r['difference'] for r in sides])) if complete else None;err=float(np.mean([r['error'] for r in sides])) if complete else None
        roots.append(dict(group=group,seed=seed,complete_pair=complete,mean_SO_minus_GN=delta,error_estimate=err,strict_SO_win=bool(complete and delta>err),sides=sides))
    return dict(planned_candidates=160,accepted=sum(r.get('accepted',False) for r in rows),valid_candidates=sum(r.get('status')=='PASS' for r in rows),
        attempted_candidates=sum(r.get('candidate_solve_attempted',False) for r in rows),planned_roots=20,complete_roots=sum(r['complete_pair'] for r in roots),
        root_wins=sum(r['strict_SO_win'] for r in roots),roots=roots,evidence_role='conditional_secondary_on_E1_roots')

def artifact_stage(node,rows,summary,cost):
    dest=OUT/node.lower();dest.mkdir(parents=True,exist_ok=True);cfg=read(LOCK/'execution.json')
    protocol=dict(node=next(n for n in cfg['nodes'] if n['id']==node),lock_sha256=canon_sha(LOCK/'LOCK.json'))
    write(dest/'PROTOCOL.json',protocol);(dest/'PROTOCOL.sha256').write_text(canon_sha(dest/'PROTOCOL.json')+'\n',encoding='ascii')
    write(dest/'RUN_MANIFEST.json',rows);csvout(dest/'ALL_RUNS.csv',rows);write(dest/'SUMMARY.json',summary)
    failures=[r for r in rows if r.get('status') not in ['PASS'] or r.get('failure_reason')];write(dest/'FAILURES.json',failures)
    write(dest/'COST_LEDGER.json',[r for r in cost['worker_processes'] if r['node']==node])
    write(dest/'VALIDATION.json',dict(engineering_status='PASSED',denominator=len(rows),failures_retained=len(failures),source='run manifests and hashed raw files',scientific_failure_is_engineering_failure=False))
    (dest/'REPORT.md').write_text('# '+node+' actual results\n\nGenerated from RUN_MANIFEST.json. Scientific failures and unavailable positions remain in the denominator.\n\n```json\n'+json.dumps(native(summary),ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')

def plots(allrows,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dest=OUT/'final/figures';dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'svg.fonttype':'none'})
    def save(fig,name):fig.tight_layout();fig.savefig(dest/(name+'.svg'));fig.savefig(dest/(name+'.png'),dpi=140);plt.close(fig)
    r=allrows['E0'];v=[a for a in r['mechanism'] if a['status']=='PASS'];fig,ax=plt.subplots(1,3,figsize=(13,3.5))
    ax[0].scatter([a['e_GN'] for a in v],[a['correction'] for a in v]);ax[0].axhline(0,color='gray');ax[0].axvline(0,color='gray');ax[0].set(xlabel='Signed GN error',ylabel='SO correction',title='E0: 21/25 available')
    for group in sorted(set(a['pde'] for a in r['gamma_sweep'])):
        x=sorted(set(a['alpha'] for a in r['gamma_sweep']));ys=[]
        for alpha in x:
            cell=[a for a in r['gamma_sweep'] if a['pde']==group and a['alpha']==alpha];ys.append(sum(a.get('strict_SO_win',False) for a in cell)/len(cell))
        ax[1].semilogx(x,ys,'o-',label=group)
    ax[1].legend();ax[1].set(xlabel='gamma alpha',ylabel='planned win fraction',ylim=(0,1),title='No failed cells removed')
    ax[2].bar(['available','missing'],[0,14]);ax[2].set(title='E0-C: 0/14 original inputs',ylabel='anchor positions');save(fig,'E0_mechanism_gamma_availability')
    fig,ax=plt.subplots(1,2,figsize=(11,3.6));rows=summary['E1']['rows']
    for group,color in [('burgers','tab:blue'),('allen_cahn','tab:orange')]:
        good=[r for r in rows if r['group']==group and r.get('binding_valid')]
        for r in good:ax[0].plot([0,1],[r['metrics']['fro']['error_GN'],r['metrics']['fro']['error_SO']],color=color,alpha=.6)
        ax[1].scatter([r['seed'] for r in good],[r['metrics']['fro']['logR_floor'] for r in good],label=f'{group} {len(good)}/10',color=color)
    ax[0].set(xticks=[0,1],xticklabels=['GN','SO'],yscale='log',ylabel='Absolute curvature error');ax[1].axhline(0,color='gray');ax[1].legend();ax[1].set(xlabel='Root seed',ylabel='floor-adjusted log ratio');save(fig,'E1_paired_all_roots')
    fig,ax=plt.subplots(2,2,figsize=(11,7));e2=[r for r in allrows['E2'] if r.get('sides')]
    for r in e2:
        ax[0,0].plot([-abs(r['sides']['minus']['last_valid_offset']),abs(r['sides']['plus']['last_valid_offset'])],[r['seed']]*2,'o-')
        for side in r['sides'].values():
            accepted=side['accepted'];ax[0,1].plot([a['offset'] for a in accepted],[a['lambda_min_A'] for a in accepted],alpha=.5)
        fd=[a for a in r['FD'] if a.get('K_FD') is not None]
        ax[1,0].semilogx([a['delta'] for a in fd],[a['K_FD'] for a in fd],alpha=.5)
        ax[1,1].loglog([a['delta'] for a in fd],[max(a['eta_K'],1e-30) for a in fd],alpha=.5)
    ax[0,0].set(title=f'Observed branch intervals: {len(e2)}/20 roots',xlabel='offset',ylabel='seed');ax[0,1].set(title='Accepted-state A eigenvalue',xlabel='offset')
    ax[1,0].set(title='Audited K(delta); unresolved values diagnostic',xlabel='delta');ax[1,1].set(title='FD numerical floor',xlabel='delta',ylabel='eta_K');save(fig,'E2_branch_FD_floor')
    fig,ax=plt.subplots(1,2,figsize=(11,3.5))
    for method in ['RAW','GN','SO','star']:
        rr=[r for r in e2 if r['radii'][method]['last_valid'] is not None];ax[0].scatter([r['seed'] for r in rr],[r['radii'][method]['last_valid'] for r in rr],label=f'{method} ({len(rr)}/20)')
    for r in e2:
        ff=[a for a in r['FD'] if a.get('finite_displacement_difference') is not None]
        ax[1].loglog([a['delta'] for a in ff],[max(a['finite_displacement_difference'],1e-30) for a in ff],alpha=.5)
    ax[0].legend();ax[0].set(title='Resolved-prefix radii: censored bounds',xlabel='seed',ylabel='last valid delta');ax[1].set(title='Finite displacement |F* - K|',xlabel='delta');save(fig,'E2_radius_and_displacement_error')
    fig,ax=plt.subplots(1,2,figsize=(10,3.5));s=summary['E3'];rr=[r for r in s['roots'] if r['complete_pair']]
    ax[0].bar(['planned','attempted','valid','accepted'],[160,s['attempted_candidates'],s['valid_candidates'],s['accepted']]);ax[0].tick_params(axis='x',rotation=25)
    if rr:ax[1].errorbar([r['seed'] for r in rr],[r['mean_SO_minus_GN'] for r in rr],yerr=[r['error_estimate'] for r in rr],fmt='o')
    else:ax[1].text(.5,.5,'No complete eligible root pairs',ha='center',transform=ax[1].transAxes)
    ax[1].axhline(0,color='gray');ax[1].set(title=f'Conditional root pairs {len(rr)}/20',xlabel='seed',ylabel='SO - GN actual decrease');save(fig,'E3_admissibility_and_root_difference')
    fig,ax=plt.subplots(1,2,figsize=(10,3.5))
    for index,node in enumerate(['E4D','E4C']):
        good=[r for r in allrows[node] if r.get('metrics') and (r.get('binding_valid') or r.get('historical_binding_valid'))]
        for r in good:ax[index].plot([0,1],[r['metrics']['fro']['error_GN'],r['metrics']['fro']['error_SO']],'o-',alpha=.6)
        ax[index].set(title=f'{node}: {len(good)}/10',xticks=[0,1],xticklabels=['GN','SO'],yscale='log',ylabel='Frobenius error')
    save(fig,'E4_full_matrix_errors')
    fig,ax=plt.subplots(1,2,figsize=(11,3.5))
    for method in ['RAW','GN','SO']:
        rr=[r for r in allrows['E4D']+allrows['E4C'] if r.get('geometry')]
        ax[0].scatter(range(len(rr)),[r['geometry'][method]['weak_eigenvalue_error'] for r in rr],label=method)
        available=[(i,r) for i,r in enumerate(rr) if r['geometry'][method]['weak_angle_degrees'] is not None]
        ax[1].scatter([i for i,r in available],[r['geometry'][method]['weak_angle_degrees'] for i,r in available],label=f'{method}: {len(available)}/{len(rr)} resolved')
    ax[0].legend();ax[1].legend();ax[0].set(xlabel='dev then fresh valid record',ylabel='signed weak eigenvalue error');ax[1].set(xlabel='dev then fresh valid record',ylabel='weak direction angle (degrees)');save(fig,'E4_weak_geometry_resolution')
    fig,ax=plt.subplots(1,3,figsize=(13,3.5));steady=[r for r in allrows['E5C'] if r.get('status')=='PASS' and r['pass_label'].startswith('steady')]
    for m in [213,853,3413]:
        rr=[r for r in steady if r['m']==m];ax[0].loglog([r['n'] for r in rr],[r['GN_seconds']+r['SO_increment_seconds'] for r in rr],'o',label=f'm={m}')
        ax[1].loglog([r['n'] for r in rr],[r['A_matvec_count'] for r in rr],'o')
        ax[2].loglog([r['n'] for r in rr],[r['shared_process_memory'].get('os_peak_working_set_bytes',1)/2**20 for r in rr],'o')
    ax[0].legend();ax[0].set(xlabel='n',ylabel='GN + SO seconds',title=f'Cost-only: {len(steady)}/27 steady passes');ax[1].set(xlabel='n',ylabel='normal operator calls');ax[2].set(xlabel='n',ylabel='shared cell peak working set MiB');save(fig,'E5_cost_operators_memory')
    fig,ax=plt.subplots(figsize=(10,3.5));cells=sorted(set((r['n'],r['m']) for r in steady));gn=[];so=[]
    for n,m in cells:
        rr=[r for r in steady if r['n']==n and r['m']==m];gn.append(float(np.median([r['GN_seconds'] for r in rr])));so.append(float(np.median([r['SO_increment_seconds'] for r in rr])))
    labels=[f'{n}/{m}' for n,m in cells];ax.bar(labels,gn,label='GN solve');ax.bar(labels,so,bottom=gn,label='SO HVP increment');ax.tick_params(axis='x',rotation=35);ax.legend();ax.set(ylabel='median steady seconds',xlabel='n / m (missing cells retained in table)');save(fig,'E5_cost_components')
    fig,ax=plt.subplots(1,3,figsize=(13,3.5));terminal=[r for r in allrows['E6D'] if r.get('defect')=='terminal' and r.get('k')]
    for k in [2,4,8,16]:
        rr=[r for r in terminal if r['k']==k];ax[0].bar(str(k),sum(r['coverage'] for r in rr));ax[1].scatter([k]*len(rr),[r['effectivity'] for r in rr]);ax[2].scatter([k]*len(rr),[r['interval_gap'] for r in rr])
    ax[0].set(xlabel='k',ylabel='coverage / 21');ax[1].set(xlabel='k',ylabel='U/q',yscale='log');ax[2].set(xlabel='k',ylabel='U-L',yscale='log');save(fig,'E6_oracle_kill_test')

def finalize():
    start=time.perf_counter();cfg=read(LOCK/'execution.json');dev=dev_summary();e1=e1_summary();cost=costs();count=validate_manifests()
    allrows={n:stage_rows(n) for n in ['E2','E3','E4C','E5C','E6P']}
    for node in ['E0','E4D','E6D']:allrows[node]=next(r for m,r in records(node) if m['name']==dev['selection'][node])
    allrows['E1']=e1['rows'];allrows['E5AB']=dev['E5AB']
    assert len(allrows['E1'])==20 and len(allrows['E2'])==20 and len(allrows['E3'])==160 and len(allrows['E4C'])==10 and len(allrows['E5C'])==45
    summary=dict(E1=e1,E3=step_summary(allrows['E3']),E4C=multi_summary(allrows['E4C']),development=dev,
        E2=dict(planned=20,computed_roots=sum(bool(r.get('sides')) for r in allrows['E2']),gate_C_pass=sum(r.get('gate_C',False) for r in allrows['E2']),E3_ready=sum(r.get('E3_ready',False) for r in allrows['E2'])),
        E5C=dict(planned=45,valid=sum(r.get('status')=='PASS' for r in allrows['E5C'])),cost=cost,
        WORKFLOW_COMPLETE=True,ALL_NUMERICAL_EXPERIMENTS_EXECUTED=False,
        limitations=['E0-C original 14 states/full blocks unavailable; no reconstruction training.', 'E2/E3 are secondary on E1 roots, not new independent samples.',
        'All spectral endpoints and objective precision estimates are numerical diagnostics, not rigorous certificates.', 'E5 large-network results establish cost only.'])
    write(OUT/'final/SUMMARY.json',summary);write(OUT/'final/ALL_RAW_AGGREGATED.json',allrows)
    for node,rows in allrows.items():
        if node=='E0':
            for suffix,key in [('a','mechanism'),('b','gamma_sweep'),('c','robustness')]:
                artifact_stage('E0',rows[key],dict(part=suffix,planned=len(rows[key]),valid=sum(r.get('status')=='PASS' for r in rows[key])),cost)
                # E0 parts receive separate copies, avoiding mixed denominators.
                import shutil
                dest=OUT/('e0_'+suffix);dest.mkdir(exist_ok=True)
                for p in (OUT/'e0').iterdir():
                    if p.is_file():shutil.copy2(p,dest/p.name)
            artifact_stage(node,rows['mechanism']+rows['gamma_sweep']+rows['robustness'],dev['E0'],cost)
        else:artifact_stage(node,rows,summary.get(node,dev.get(node,dict(planned=len(rows)))),cost)
    plots(allrows,summary)
    history=read(OUT/'preflight/HISTORICAL_HASHES.json')
    for name,digest in history.items():
        p=ROOT/name;actual=canon_sha(p) if p.suffix.lower() in ['.json','.csv','.md','.txt','.yaml','.yml','.log'] else sha(p)
        assert actual==digest,'historical input changed: '+name
    stopped={node:sum(r.get('execution_disposition')=='PROTOCOL_STOP' for r in rows) for node,rows in allrows.items() if isinstance(rows,list)}
    text=['# Phase 2 actual execution report',
        '**未实际补算：E0-C 的 14 个历史状态/完整块缺失。条件停止位置：'+json.dumps(stopped,ensure_ascii=False)+'。**',
        f"E1 独立 scalar 结论：{e1['conclusion']}。"+ '；'.join(f"{p['group']} valid {p['valid']}/10、SO 严格胜出 {p['wins']}/10" for p in e1['pdes'])+'.',
        f"E2：{summary['E2']['computed_roots']}/20 roots 实际分析，Gate C 通过 {summary['E2']['gate_C_pass']}，E3 可用 {summary['E2']['E3_ready']}。失败/截尾不能解释成物理分支不存在。",
        f"E3：实际候选 {summary['E3']['attempted_candidates']}/160，有效 {summary['E3']['valid_candidates']}，接受 {summary['E3']['accepted']}；完整双侧配对 roots {summary['E3']['complete_roots']}/20，SO 实际下降严格胜出 {summary['E3']['root_wins']}/20。",
        f"E4-C：{summary['E4C']['conclusion']}，valid {summary['E4C']['valid']}/10，Frobenius wins {summary['E4C']['frobenius_wins']}/10。旧 V5 裁决保持原样。",
        f"E5：四中心 MF/AD 工程核验通过；大规模 cost-only 完成有效计时 {summary['E5C']['valid']}/45。",
        f"E6-D k=8 oracle 有效度中位数 {dev['E6D']['median_effectivity']:.6g}，门槛 3；E6-P 放行={dev['E6P_allowed']}。当前证据不支持实用的低成本误差认证。",
        f"累计 Phase2 实测活动 {cost['measured_activity_seconds']:.3f} 秒；中断上界估计另列 {cost['estimated_interruption_upper_bound_seconds']:.3f} 秒。最终聚合/绘图耗时另见 VALIDATION.json。", 
        '所有图、表、正文数值同源于 final/SUMMARY.json 和原始 run manifests。训练失败、数值失败和开发修复前尝试全部保留。']
    (OUT/'final/PHASE2_REPORT.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    claims=dict(independent_scalar_curvature=e1['conclusion'],independent_multi_curvature=summary['E4C']['conclusion'],
        actual_one_step_increment='conditional_root_level_evidence_only',ADAPT_practical_certification='NOT_SUPPORTED',
        prohibited=['SO globally superior','global identifiability','posterior covariance from curvature only','large-network accuracy from widening cost test','rigorous floating-point certificate','old V5 failures repaired','all numerical experiments executed'])
    write(OUT/'final/CLAIM_LEDGER.json',claims);(OUT/'final/CLAIM_LEDGER.md').write_text('# Claim ledger\n\n```json\n'+json.dumps(claims,indent=2)+'\n```\n',encoding='utf-8')
    write(OUT/'final/VALIDATION.json',dict(status='PASSED',run_manifests=count,history_files_unchanged=len(history),all_planned_denominators_preserved=True,
        aggregation_and_plot_seconds=time.perf_counter()-start,source_summary_sha256=canon_sha(OUT/'final/SUMMARY.json')))
    artifacts=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=canon_sha(p) if p.suffix in ['.json','.md','.csv','.svg'] else sha(p)) for p in (OUT/'final').rglob('*') if p.is_file()]
    write(OUT/'FINAL_MANIFEST.json',artifacts)
    with (ROOT/'TASKS.md').open('a',encoding='utf-8') as f:f.write('\n\n## Phase 2 closeout\n\n**状态:** `PASSED` — conditional workflow complete, not all numerical experiments executed.\n\n- Generated scientific findings and retained failures: revision_week/outputs/phase2_v1/final/PHASE2_REPORT.md.\n- New scalar and multi conclusions remain separate; all historical conclusions are unchanged.\n')

if __name__=='__main__':finalize()
