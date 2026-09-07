"""Rebuild Phase 1.5 findings exclusively from hashed raw stage manifests."""
from collections import Counter,defaultdict
from pathlib import Path
import csv
import json
import math
import numpy as np
from run_phase15 import context,read,sha,unpack,write


def rankdata(values):
    order=np.argsort(values,kind='stable'); ranks=np.empty(len(values))
    i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]: j+=1
        ranks[order[i:j]]=(i+j-1)/2+1;i=j
    return ranks


def correlation(x,y):
    if len(x)<2 or np.ptp(x)==0 or np.ptp(y)==0:return None
    return float(np.corrcoef(rankdata(np.array(x)),rankdata(np.array(y)))[0,1])


def stage_records(base,stage):
    manifest=read(base/stage/'manifest.json'); result=[]
    assert manifest['status']=='PASSED'
    for item in manifest['records']:
        path=base/stage/item['file']; assert sha(path)==item['sha256'],path
        result.append(unpack(path) if path.suffix=='.gz' else read(path))
    return result


def aggregate():
    config,auth,inventory,base=context()
    a,b,c=(stage_records(base,stage) for stage in 'ABC')
    expected_b=len(inventory)*sum(len(x['ranks'])*(5 if x['randomized'] else 1)*2 for x in config['candidates'])
    assert len(a)==len(inventory) and len(b)==expected_b
    expected_c=len(inventory)*sum(len(x['ranks'])*(5 if x['randomized'] else 1)*(len(x['budgets'])+1) for x in config['candidates'])
    assert len(c)==expected_c
    valid_sources={(r['benchmark'],r['seed']) for r in inventory if r['analysis_valid']}
    groups=defaultdict(list)
    for row in c: groups[(row['candidate'],row['rank_requested'],row['mode'])].append(row)
    gates=[]; flat=[]
    for (name,rank,mode),rows in groups.items():
        per_source=defaultdict(list)
        for row in rows:
            source=row['source']; key=(source['benchmark'],source['seed'])
            if key not in valid_sources:continue
            per_source[key].append(row)
        checkpoint_errors=[]; cold=[]; increment=[]; gv=[]; hv=[]; nonworse=0; success=0
        setup_max=0; max_steps=0; failed=[]; worst_seed=None; worst=-1
        for key in sorted(valid_sources):
            sample=per_source[key]; repeats=5 if name=='nystrom' else 1
            assert len(sample)==repeats
            usable=[r for r in sample if r['status']=='PASS' and r['selected'] is not None]
            if len(usable)!=repeats:
                failed.append({'source':key,'statuses':[r['status'] for r in sample]});continue
            success+=1
            error=max(r['selected']['oracle']['relative_error'] for r in usable)
            checkpoint_errors.append(error)
            if error>worst: worst=error;worst_seed=key
            nonworse+=int(all(r['selected']['oracle']['relative_error']<=r['gn_error']+1e-10 for r in usable))
            cold.append(max(r['selected']['cold_seconds'] for r in usable))
            increment.append(max(r['selected']['incremental_seconds'] for r in usable))
            gv.append(max(r['selected']['counts']['Gv'] for r in usable));hv.append(max(r['selected']['counts']['Hv'] for r in usable))
            setup_max=max(setup_max,max(r['selected']['counts'].get('setup_Gv',0) for r in usable))
            max_steps=max(max_steps,max(r['selected']['step'] for r in usable))
            for r in usable:
                flat.append({'candidate':name,'rank':rank,'mode':mode,'benchmark':key[0],'seed':key[1],
                             'sketch_seed':r['sketch_seed'],'error':r['selected']['oracle']['relative_error'],
                             'gn_error':r['gn_error'],'steps':r['selected']['step'],
                             'cold_seconds':r['selected']['cold_seconds'],'Gv':r['selected']['counts']['Gv'],
                             'Hv':r['selected']['counts']['Hv']})
        med=float(np.median(checkpoint_errors)) if checkpoint_errors else None
        eligible=(name!='exact_gn' and success==len(valid_sources) and med<.005 and worst<.03
                  and nonworse==len(valid_sources) and max_steps<=5 and setup_max<=30)
        gates.append({'candidate':name,'rank':rank,'mode':mode,'planned_records':len(rows),
                      'valid_checkpoint_denominator':len(valid_sources),'computed_checkpoints':success,
                      'median_error':med,'worst_error':worst if worst>=0 else None,'worst_source':worst_seed,
                      'nonworse_checkpoints':nonworse,'failed_checkpoints':failed,'maximum_steps':max_steps,
                      'maximum_additional_setup_Gv':setup_max,'median_cold_seconds':float(np.median(cold)) if cold else None,
                      'worst_cold_seconds':max(cold) if cold else None,
                      'median_incremental_seconds':float(np.median(increment)) if increment else None,
                      'total_Gv':sum(gv),'total_Hv':sum(hv),'entry_gate':eligible})
    selected={}
    for kind in ('fixed','adaptive'):
        passing=[r for r in gates if r['entry_gate'] and (r['mode'].startswith('fixed') if kind=='fixed' else r['mode']=='adaptive')]
        passing.sort(key=lambda r:(r['median_cold_seconds'],r['worst_cold_seconds'],r['total_Hv'],r['total_Gv'],r['rank'],r['candidate'],r['mode']))
        selected[kind]=passing[0] if passing else None
    # Within-checkpoint paired first-hit comparisons, never discard missing targets.
    pairs=defaultdict(dict);pair_summary=defaultdict(list); indicators=[]; worsening=[]
    for row in b:
        s=row['source']; key=(s['benchmark'],s['seed'],row['candidate'],row['rank_requested'],row['sketch_seed'])
        pairs[key][row['start']]=row
        if row.get('rows') and row['start']=='gn':
            positive=[r for r in row['rows'] if r['eta']>0 and r['oracle']['energy_gap']>1e-25]
            indicators.append({'source':s,'candidate':row['candidate'],'rank':row['rank_requested'],'sketch_seed':row['sketch_seed'],
                               'log_spearman':correlation([math.log(r['eta']) for r in positive],[math.log(r['oracle']['energy_gap']) for r in positive]),
                               'minimum_eta_to_gap':min((r['oracle']['indicator_to_gap'] for r in positive),default=None),
                               'maximum_eta_to_gap':max((r['oracle']['indicator_to_gap'] for r in positive),default=None)})
    paired_rows=[]
    for key,starts in pairs.items():
        assert set(starts)=={'zero','gn'}
        for target in config['start_comparison']['oracle_error_targets']:
            zero=starts['zero'].get('target_hits',{}).get(str(target)); warm=starts['gn'].get('target_hits',{}).get(str(target))
            row={'benchmark':key[0],'seed':key[1],'candidate':key[2],'rank':key[3],'sketch_seed':key[4],
                 'target':target,'zero':zero,'gn':warm,'both_reached':zero is not None and warm is not None,
                 'gn_fewer_steps':warm['step']<zero['step'] if zero and warm else None,
                 'gn_less_cold_time':warm['cold_seconds']<zero['cold_seconds'] if zero and warm else None}
            paired_rows.append(row);pair_summary[(key[2],key[3],target)].append(row)
    summaries=[]
    for (name,rank,target),rows in pair_summary.items():
        reached=[r for r in rows if r['both_reached']]
        summaries.append({'candidate':name,'rank':rank,'target':target,'planned_pairs':len(rows),
                          'both_reached':len(reached),'gn_fewer_steps':sum(r['gn_fewer_steps'] for r in reached),
                          'gn_less_cold_time':sum(r['gn_less_cold_time'] for r in reached),
                          'median_zero_steps':float(np.median([r['zero']['step'] for r in reached])) if reached else None,
                          'median_gn_steps':float(np.median([r['gn']['step'] for r in reached])) if reached else None})
    for row in c:
        if row['status']=='PASS' and row['selected']['oracle']['relative_error']>row['gn_error']+1e-10:
            worsening.append({k:row[k] for k in ('source','candidate','rank_requested','sketch_seed','mode','selected','gn_error')})
    adaptive=[r for r in c if r['mode']=='adaptive' and r['source']['analysis_valid']]
    audits={'maximum_identity_error':max((r['oracle']['identity_relative_error'] for run in b for r in run.get('rows',[])),default=None),
            'initial_GN_failures':sum(not r.get('rows') and r['status']=='SOLVER_FAILURE' for r in b),
            'adaptive_valid_source_records':len(adaptive),
            'adaptive_indicator_triggered':sum(r.get('indicator_triggered',False) for r in adaptive),
            'adaptive_not_triggered':sum(not r.get('indicator_triggered',False) for r in adaptive),
            'adaptive_false_early_0p1percent':sum(r.get('indicator_triggered',False) and r['selected']['oracle']['relative_error']>.001 for r in adaptive if r.get('selected')),
            'raw_status_counts':{stage:dict(Counter(r['status'] for r in records)) for stage,records in zip('ABC',(a,b,c))}}
    result={'engineering_status':'PASSED','development_conclusion':'SUPPORTED' if any(selected.values()) else 'NOT_SUPPORTED',
            'scope':'candidate-set historical-development gate only, no general scientific support claim',
            'source_planned':len(inventory),'source_valid':len(valid_sources),'source_invalid':len(inventory)-len(valid_sources),
            'selected':selected,'gates':gates,'spectral_records':a,'paired_start_summary':summaries,
            'paired_start_rows':paired_rows,'indicator_audit':indicators,'worsened_records':worsening,'audits':audits,
            'input_manifests':{stage:sha(base/stage/'manifest.json') for stage in 'ABC'}}
    return base,result,flat


def main():
    base,data,flat=aggregate(); output=base/'report';output.mkdir(exist_ok=False)
    write(output/'summary.json',data)
    with (output/'per_checkpoint.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat[0]) if flat else ['candidate']);writer.writeheader();writer.writerows(flat)
    lines=['# Phase 1.5 历史矩阵方法定型报告','',
           f"工程执行：{data['engineering_status']}；开发候选门槛：{data['development_conclusion']}。",
           f"历史输入 {data['source_planned']}，源有效 {data['source_valid']}，原无效 {data['source_invalid']}。",
           '所有数值从A/B/C raw manifest自动聚合。以下误差为无量纲相对误差，0.005代表0.5%。',
           '随机候选按每checkpoint最差sketch判门槛。迭代数据不是独立统计样本。', '',
           '## 完整终态','', '```json',json.dumps(data['audits'],indent=2),'```','',
           '## 谱与误差抵消','',
           '|问题|seed|状态|条件数|偏离1>0.1|偏离1>0.5|90%能量方向数|chi|',
           '|---|---:|---|---:|---:|---:|---:|---:|']
    for r in data['spectral_records']:
        s=r['source']
        if r['status']=='PASS':
            lines.append(f"|{s['benchmark']}|{s['seed']}|PASS|{r['condition_number']:.5g}|{r['outliers']['0.1']['count']}|{r['outliers']['0.5']['count']}|{r['directions_for_energy']['0.9']}|{r['chi']:.5g}|")
        else:lines.append(f"|{s['benchmark']}|{s['seed']}|{r['status']}|—|—|—|—|—|")
    lines+=['','## 全部候选与预算','',
            '|候选|rank|输出|成功checkpoint|中位误差|最差误差|非劣数|中位cold秒|额外setup Gv|进阶|',
            '|---|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for r in data['gates']:
        fmt=lambda x:'null' if x is None else f'{x:.5g}'
        lines.append(f"|{r['candidate']}|{r['rank']}|{r['mode']}|{r['computed_checkpoints']}/{r['valid_checkpoint_denominator']}|{fmt(r['median_error'])}|{fmt(r['worst_error'])}|{r['nonworse_checkpoints']}|{fmt(r['median_cold_seconds'])}|{r['maximum_additional_setup_Gv']}|{r['entry_gate']}|")
    lines+=['','## 选择','', '```json',json.dumps(data['selected'],indent=2),'```',
            '若没有合格候选，按协议停止，不增加rank、预算或替换检查点。若有合格候选，也仅说明历史开发可行，未授权进入训练。',
            '', '## Zero-start 与 GN-start','',
            '|候选|rank|目标误差|双侧达到/计划配对|GN步数更少|GN cold更快|zero中位步数|GN中位步数|',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in data['paired_start_summary']:
        lines.append(f"|{r['candidate']}|{r['rank']}|{r['target']}|{r['both_reached']}/{r['planned_pairs']}|{r['gn_fewer_steps']}|{r['gn_less_cold_time']}|{r['median_zero_steps']}|{r['median_gn_steps']}|")
    lines+=['','## 审计与限制','',
            f"变差的有效输出共 {len(data['worsened_records'])} 条（含预算及sketch重复，不是独立checkpoint数量）；完整逐条数据见summary.json。",
            'B的SOLVER_FAILURE可能是n_theta步内未达到严格响应残差；C在既定预算获得有限、通过核验的输出仍可PASS，但不保证曲率精度。',
            'cold时间包含GN初始化；incremental时间扣除已完成的GN初始化。exact GN和diagonal的稠密访问性质明确保留。',
            '所有Gv/Hv为已归档矩阵乘法。真实JVP/VJP/HVP调用为0；不能外推GPU/matrix-free速度。完整native峰值内存未测。',
            'eta是indicator；存在过早停止时按原阈值保留，不用oracle补算或回退挑结果。',
            '历史文件缺失导致的legacy validator失败单独记录。本阶段不恢复原有删除文件，不声称全仓库通过。']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    # Standalone scientific SVG: all checkpoints, no representative selection.
    valid=[r for r in data['spectral_records'] if r['status']=='PASS'];svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="680" viewBox="0 0 1000 680">',
        '<rect width="1000" height="680" fill="white"/><text x="40" y="30" font-size="20">GN-preconditioned spectrum: all valid historical checkpoints</text>']
    for i,r in enumerate(valid):
        y=60+i*27;svg.append(f'<text x="10" y="{y+4}" font-size="11">{r["source"]["benchmark"]} {r["source"]["seed"]}</text>')
        for ev,energy in zip(r['eigenvalues'],r['energy_weights'] or [0]*len(r['eigenvalues'])):
            x=160+min(780,max(0,(math.log10(ev)+2)*195))
            svg.append(f'<circle cx="{x:.3f}" cy="{y}" r="{2+7*math.sqrt(energy):.3f}" fill="#2266aa" opacity="0.55"/>')
    svg+=['<text x="160" y="655" font-size="13">x: log10 eigenvalue, range [0.01,100]; circle area indicates defect energy weight</text>','</svg>']
    (output/'spectrum.svg').write_text('\n'.join(svg),encoding='utf-8',newline='\n')
    write(output/'manifest.json',{'status':'PASSED','files':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}})
    print(json.dumps({'status':data['engineering_status'],'conclusion':data['development_conclusion'],'selected':data['selected'],'audits':data['audits']},indent=2))


if __name__=='__main__':main()
