"""Derived interpretation and accuracy/cost figures; no scientific reruns."""
from collections import defaultdict
from html import escape
import json
import math
from pathlib import Path
import numpy as np
from run_phase15 import context,read,sha,unpack,write


def main():
    config,auth,inventory,base=context(); report=read(base/'report/summary.json')
    groups=defaultdict(list)
    for item in read(base/'B/manifest.json')['records']:
        p=base/'B'/item['file'];assert sha(p)==item['sha256'];r=unpack(p)
        if r['start']=='gn' and r.get('oracle_preconditioned_spectrum'):
            e=r['oracle_preconditioned_spectrum'];groups[(r['candidate'],r['rank_requested'])].append(e[-1]/e[0])
    conditions=[{'candidate':k[0],'rank':k[1],'records':len(v),'median_condition':float(np.median(v)),
                 'worst_condition':float(max(v))} for k,v in groups.items()]
    valid=[r for r in report['spectral_records'] if r['status']=='PASS']
    observed={'source_summary_sha256':sha(base/'report/summary.json'),'conditions':conditions,
              'exact_condition_median':float(np.median([r['condition_number'] for r in valid])),
              'exact_condition_min':min(r['condition_number'] for r in valid),
              'exact_condition_max':max(r['condition_number'] for r in valid),
              'median_90pct_energy_directions':float(np.median([r['directions_for_energy']['0.9'] for r in valid])),
              'cancellation_59_67':[{k:r[k] for k in ('source','chi','delta_fix','delta_relax')} for r in valid if r['source']['seed'] in (59,67)],
              'interpretation':'No configured scalable candidate passed. Do not enlarge budgets or start subsequent layers.',
              'script_sha256':sha(Path(__file__))}
    out=base/'findings';out.mkdir(exist_ok=False);write(out/'findings.json',observed)
    lines=['# Phase 1.5 结果解读','',
           f"本候选集合的开发进阶门槛：**{report['development_conclusion']}**。这不改变历史SAEPS结论，也不是整个研究方向无效。",'',
           f"精确GN预处理条件数中位数 {observed['exact_condition_median']:.4g}，范围 {observed['exact_condition_min']:.4g}–{observed['exact_condition_max']:.4g}。",
           f"90% defect能量所需方向数中位数 {observed['median_90pct_energy_directions']:.4g}，不能把快速收敛简化为只有两三个能量方向。",
           '', '## 两个初始修正变差样本','', '|seed|delta_fix|delta_relax|chi|','|---:|---:|---:|---:|']
    for r in observed['cancellation_59_67']:
        lines.append(f"|{r['source']['seed']}|{r['delta_fix']:.6g}|{r['delta_relax']:.6g}|{r['chi']:.6g}|")
    lines+=['','两项同号且在相减时部分抵消；不是用初始误差大小猜测这一机制。','',
            '## 全部预处理条件数','', '|候选|rank|有效轨迹数|中位谱条件数|最差|','|---|---:|---:|---:|---:|']
    for r in conditions:
        lines.append(f"|{r['candidate']}|{r['rank']}|{r['records']}|{r['median_condition']:.6g}|{r['worst_condition']:.6g}|")
    lines+=['','低秩候选与exact GN的条件数差距是本次可检验的诊断，尚不足以证明某一种新的预处理一定能解决问题。',
            '', '## 成本解释','',
            'accuracy_cost.svg 展示所有固定预算/自适应输出的中位cold时间与中位误差；随机方法先取每checkpoint最差sketch。',
            '虚线是所测点的描述性Pareto前沿，不是通过门槛的算法集合。exact GN保留作稠密对照，不参与进阶。',
            'cold时间包含GN初始化。图不证明matrix-free、GPU或大网络效率，且所有候选的最差误差和非劣门槛须同时查看。',
            '', '## 停止决定','',
            '按本轮协议，未选出fixed或adaptive可扩展候选。保留全部失败与变差记录，停止后续层级。',
            '未来若改变预处理形式、rank、停止指标或预算，应作为新的开发协议，不能覆盖本次结果。',
            '', '## 产物','', '../report/REPORT.md：完整预算表、起点对照与失败统计。',
            '../report/summary.json：全部自动聚合数据及逐条变差记录。',
            '../RESULT_VALIDATION_V2.json：独立hash、成本计数、代数、谱界与重聚合核验。']
    (out/'FINDINGS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    rows=[r for r in report['gates'] if r['median_error'] is not None and r['median_cold_seconds']>0]
    xs=[math.log10(r['median_cold_seconds']*1000) for r in rows];ys=[math.log10(max(r['median_error'],1e-16)) for r in rows]
    xmin,xmax=math.floor(min(xs)),math.ceil(max(xs));ymin,ymax=math.floor(min(ys)),math.ceil(max(ys))
    def x(v):return 100+760*(v-xmin)/max(xmax-xmin,1)
    def y(v):return 530-430*(v-ymin)/max(ymax-ymin,1)
    palette={'diagonal':'#666666','nystrom':'#2166ac','recycled_ritz':'#1b9e77','hybrid_defect':'#d95f02','exact_gn':'#8e44ad'}
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="630" viewBox="0 0 1050 630">',
         '<rect width="1050" height="630" fill="white"/>',
         '<text x="40" y="35" font-size="21">Historical matrix accuracy vs complete cold diagnostic time</text>',
         '<text x="40" y="60" font-size="13">All configured outputs; worst sketch per checkpoint; exact GN is a dense control</text>']
    for value in range(xmin,xmax+1):
        svg.append(f'<path d="M{x(value)} 100 V530" stroke="#ddd"/><text x="{x(value)-12}" y="555" font-size="12">1e{value}</text>')
    for value in range(ymin,ymax+1):
        svg.append(f'<path d="M100 {y(value)} H860" stroke="#ddd"/><text x="45" y="{y(value)+4}" font-size="12">1e{value}</text>')
    svg.append('<text x="320" y="595" font-size="15">Median cold time (milliseconds, logarithmic)</text>')
    svg.append('<text x="16" y="400" font-size="14" transform="rotate(-90 16 400)">Median relative curvature error</text>')
    points=sorted(zip(xs,ys,rows),key=lambda t:(t[0],t[1]));front=[];best=float('inf')
    for px,py,r in points:
        if py<best:front.append((x(px),y(py)));best=py
    svg.append('<polyline fill="none" stroke="#333" stroke-dasharray="5 4" points="'+' '.join(f'{a:.2f},{b:.2f}' for a,b in front)+'"/>')
    for px,py,r in points:
        label=escape(f"{r['candidate']} rank={r['rank']} {r['mode']}; median={r['median_error']:.6g}, worst={r['worst_error']:.6g}; gate={r['entry_gate']}")
        svg.append(f'<circle cx="{x(px):.3f}" cy="{y(py):.3f}" r="4" fill="{palette[r["candidate"]]}" opacity="0.7"><title>{label}</title></circle>')
    for i,(name,color) in enumerate(palette.items()):
        svg.append(f'<circle cx="885" cy="{115+i*25}" r="4" fill="{color}"/><text x="896" y="{119+i*25}" font-size="12">{name}</text>')
    svg.append('</svg>');(out/'accuracy_cost.svg').write_text('\n'.join(svg),encoding='utf-8',newline='\n')
    write(out/'manifest.json',{'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(observed,indent=2))


if __name__=='__main__':main()
