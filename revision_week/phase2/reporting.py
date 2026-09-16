"""Aggregation reads run manifests; numerical prose and figures share this source."""
from common import *
from gates import e1_conclusion,e4_fresh_allowed,e6_practical_allowed

def records(node):
    result=[]
    for p in sorted((ROOT/'revision_week/outputs/phase2_v1/run_manifests'/node).glob('*/manifest.json')):
        m=read(p)
        if 'raw_directory' in m:
            rp=ROOT/m['raw_directory']/'result.json'
            if rp.exists():
                raw=read(rp)
                if isinstance(raw,dict) and 'binding_valid' in raw and m['process']['status']!='PASS':raw=dict(raw,binding_valid=False,process_failure_retained=True)
                result.append((m,raw))
            else:result.append((m,None))
        else:result.append((m,None))
    return result

def dev_summary():
    cfg=read(SPEC);selected=read(OUT/'preflight/DEVELOPMENT_SELECTION.json') if (OUT/'preflight/DEVELOPMENT_SELECTION.json').exists() else {}
    selection=selected.get('historical',{'E0':'dev02','E4D':'dev01','E6D':'dev03'});raw={}
    for node,name in selection.items():
        matches=[(m,r) for m,r in records(node) if m['name']==name]
        assert len(matches)==1 and matches[0][0]['process']['status']=='PASS';raw[node]=matches[0][1]
    multi=[r for r in raw['E4D'] if r['status']=='PASS']
    e4=dict(all_original_valid_reloaded=all(r['reload_pass'] for r in multi),available=len(multi),
        joint_frobenius_spectral_wins=sum(all(r['metrics'][k]['strict_SO_win'] for k in ['fro','spectral']) for r in multi),
        median_logR_frobenius=float(np.median([r['metrics']['fro']['logR_floor'] for r in multi])),median_logR_spectral=float(np.median([r['metrics']['spectral']['logR_floor'] for r in multi])))
    terminal=[r for r in raw['E6D'] if r.get('defect')=='terminal' and r.get('k')==8];eff=[r['effectivity'] for r in terminal if r.get('effectivity') is not None]
    e6=dict(k=8,defect='terminal',coverage=sum(r['coverage'] for r in terminal),finite_intervals=len(eff),median_effectivity=float(np.median(eff)),q90_effectivity=float(np.quantile(eff,.9)))
    checks=[]
    for cid in cfg['e5']['compact_centers']:
        rr={m['name']:r for m,r in records('E5AB')};mf=rr[cid+'_compact_mf_'+selected.get('MF','dev03')];ex=rr[cid+'_compact_explicit_'+selected.get('explicit','dev01')];h=np.array(ex['H'])
        difference=norm(np.array(mf['F_SO'])-np.array(ex['F_SO']));relative=difference/max(norm(ex['F_SO']),1e-30)
        hv=[norm(np.array(row['Hv'])-h@np.array(row['direction']))/max(norm(h@np.array(row['direction'])),1e-30) for row in mf['directions']]
        checks.append(dict(center=cid,MF_status=mf['status'],curvature_absolute_error=difference,curvature_relative_error=relative,
            HVP_relative_errors=hv,adjoint_errors=[r['adjoint_error'] for r in mf['directions']],CG=mf['solves'],
            JVP_VJP_adjoint_errors=[r['JVP_VJP_adjoint_error'] for r in mf['directions']],
            passed=bool(mf['status']=='PASS' and relative<=1e-6 and max(hv)<=1e-8 and max(r['adjoint_error'] for r in mf['directions'])<=1e-8 and max(r['JVP_VJP_adjoint_error'] for r in mf['directions'])<=1e-8 and not mf['forbidden_entry_attempts'])))
    for row in checks:row.update(status='PASS' if row['passed'] else 'NUMERICAL_FAILURE',failure_reason=None if row['passed'] else 'operator_or_MF_parity_failure')
    solver=[r for m,r in records('PREFLIGHT') if m['job']['kind']=='solver_audit' and (not selected or m['name'].endswith(selected['solver']))]
    e0=raw['E0'];assert len(e0['mechanism'])==25 and len(e0['gamma_sweep'])==150 and len(e0['robustness'])==14
    out=dict(selection=selection,development_attempt_selection_reason='Only engineering-corrected attempts; all earlier attempts and costs retained.',
        E0=dict(planned=25,available=sum(r['status']=='PASS' for r in e0['mechanism']),classes={c:sum(r.get('classification')==c for r in e0['mechanism']) for c in ['appropriate','wrong_direction','overshoot','unresolved']},
            gamma_cells=len(e0['gamma_sweep']),robustness_planned=14,robustness_available=0),
        E4D=e4,E4C_allowed=e4_fresh_allowed(e4,cfg['e4']),E6D=e6,E6P_allowed=e6_practical_allowed(e6,cfg['e6']),E5AB=checks,
        E5AB_engineering_pass=all(r['passed'] for r in checks),solver_development_records=len(solver),
        solver_development_pass=len(solver)>=2 and all(r and r['engineering_accept'] for r in solver))
    write(OUT/'DEVELOPMENT_SUMMARY.json',out);return out

def e1_summary():
    cfg=read(LOCK/'execution.json');rows=[]
    for m,r in records('E1'):
        rows.append(dict(r or {},group=m['job']['group'],seed=m['job']['seed'],binding_valid=bool(r and r.get('binding_valid')),process=m.get('process'),failure_reason=(r or {}).get('failure_reason') or (m.get('process') or {}).get('failure_reason')))
    pdes=[]
    for group in ['burgers','allen_cahn']:
        valid=[r for r in rows if r['group']==group and r['binding_valid']];logs=[r['metrics']['fro']['logR_floor'] for r in valid]
        pdes.append(dict(group=group,planned=10,valid=len(valid),wins=sum(r['metrics']['fro']['strict_SO_win'] for r in valid),pair_logs=logs,median_logR_floor=float(np.median(logs)) if logs else None))
    interval=None
    if all(p['valid'] for p in pdes):
        rng=np.random.default_rng(stream(cfg['e1']['bootstrap_stream']));boot=[]
        for _ in range(cfg['e1']['bootstrap_resamples']):boot.append(np.median(np.concatenate([rng.choice(p['pair_logs'],size=p['valid'],replace=True) for p in pdes])))
        interval=np.quantile(boot,[.025,.975]).tolist()
    out=dict(planned=20,terminal_records=len(rows),pdes=pdes,conclusion=e1_conclusion(pdes,cfg['e1']),bootstrap95=interval,bootstrap_role='descriptive_not_binding',rows=rows)
    write(OUT/'E1_SUMMARY.json',out);return out

def costs():
    processes=[]
    for p in (OUT/'tasks').glob('*/*/process.json'):
        processes.append(dict(node=p.parent.parent.name,task=p.parent.name,**read(p)))
    audit=read(OUT/'preflight/SEED_AUDIT.json')['wall_seconds'];review=read(OUT/'preflight/ROBUSTNESS_INPUT_AUDIT.json')['seconds']
    engineering=read(OUT/'preflight/ENGINEERING_COMMAND_COSTS.json') if (OUT/'preflight/ENGINEERING_COMMAND_COSTS.json').exists() else []
    engineering_seconds=sum(r['wall_seconds'] for r in engineering)
    prior=read(ROOT/'revision_week/outputs/phase1c_development_v1/CLOSEOUT.json')
    measured=sum(r['wall_seconds'] for r in processes if r.get('timing_kind','measured')=='measured');estimated=sum(r['wall_seconds'] for r in processes if r.get('timing_kind','measured')!='measured')
    out=dict(worker_processes=processes,worker_seconds=measured,estimated_interruption_upper_bound_seconds=estimated,preflight_seed_scan_seconds=audit,
        preflight_source_review_seconds=review,measured_activity_seconds=measured+audit+review+engineering_seconds,
        instrumented_engineering_command_seconds=engineering_seconds,
        accounting='Measured process walls including startup, failed development, warmups and reference work; recorded engineering commands are separate. Early uninstrumented shell/test commands, dependency network wait, and model reasoning are not included. Shared trajectory fields are not summed twice.',
        estimated_seconds=None,historical_costs={k:v for k,v in prior.items() if 'seconds' in k or 'cumulative' in k},
        cumulative_accounted_excluding_historical_reconstruction_and_estimated_failures=prior['cumulative_accounted_excluding_historical_reconstruction_and_estimated_failures']+measured+audit+review+engineering_seconds)
    write(OUT/'COST_LEDGER.json',out);return out

def validate_manifests():
    count=0
    for mpath in (ROOT/'revision_week/outputs/phase2_v1/run_manifests').glob('*/*/manifest.json'):
        m=read(mpath)
        for entry in m.get('files',[]):
            p=ROOT/entry['path'];actual=canon_sha(p) if p.suffix in ['.json','.log','.csv'] else sha(p)
            if actual!=entry['sha256']:raise AssertionError('raw manifest mismatch '+str(p))
        count+=1
    return count

def development_report():
    s=dev_summary();c=costs();v=validate_manifests()
    paragraphs=['# Phase 2 开发验收实测报告','本文仅报告开发数据；独立 confirmation 尚未开始。',
        f"E0：{s['E0']['available']}/{s['E0']['planned']} 历史中心可用，机制分类 {s['E0']['classes']}。gamma 计划格 {s['E0']['gamma_cells']}。E0-C 14 个原始状态缺失，未补算。",
        f"二维开发：{s['E4D']['joint_frobenius_spectral_wins']}/{s['E4D']['available']} 同时改善 Frobenius 和 spectral 误差；E4-C 放行={s['E4C_allowed']}。",
        f"Lanczos 终点 k=8：覆盖 {s['E6D']['coverage']}/21，有效度中位数 {s['E6D']['median_effectivity']:.6g}，90%分位 {s['E6D']['q90_effectivity']:.6g}；E6-P 放行={s['E6P_allowed']}。",
        f"MF 完整链工程通过={s['E5AB_engineering_pass']}；逐中心 AD HVP、曲率与算子计数见 DEVELOPMENT_SUMMARY.json。",
        f"真实旧状态求解器开发记录 {s['solver_development_records']}，正确分类检查={s['solver_development_pass']}。不能把开发精化后的状态当作历史原状态。",
        f"已核验 {v} 个 run manifests；累计实测活动 {c['measured_activity_seconds']:.3f} 秒。失败开发尝试包含在 COST_LEDGER.json，未删除或覆盖。",
        '新 seed 与下游配置仍待实现完整性验收后一次冻结。']
    (OUT/'DEVELOPMENT_REPORT.md').write_text('\n\n'.join(paragraphs)+'\n',encoding='utf-8');return s

if __name__=='__main__':development_report()
