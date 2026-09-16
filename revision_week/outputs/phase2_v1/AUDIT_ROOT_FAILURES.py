"""Read-only post-run diagnostics. Never trains, refines or changes locked files."""
import csv,hashlib,json,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def main():
    started=time.perf_counter();rows=[]
    for node in ['E1','E4C']:
        for mp in sorted((OUT/'run_manifests'/node).glob('*/manifest.json')):
            manifest=read(mp)
            if not manifest.get('raw_directory'):continue
            dest=ROOT/manifest['raw_directory'].replace('\\','/');r=read(dest/'result.json');lb=read(dest/'root_lbfgs.json');tr=read(dest/'root_solver.json')
            initial=read(dest/'initial_state_diagnostic.json');spd=r['anchored_state_SPD'];gradient=r['state_gradient'];claim=read(dest/'claim.json');curve=read(dest/'curvature.json')
            training=read(dest/'training.json')['checkpoint'];locked=read(ROOT/'revision_week/protocols/phase2_locked_v1/execution.json')
            rows.append(dict(node=node,group=r['group'],seed=r['seed'],status=r['status'],initial_gradient=initial['gradient'],final_gradient=gradient,
                gradient_pass=gradient<=1e-8,A_SPD_pass=spd['mu_value'] is not None,lambda_min_A=spd['lambda_min_A_numeric'],A_numerical_margin=spd['numerical_margin'],
                root_LBFGS_iterations=lb['iterations'],root_LBFGS_function_evals=lb['function_evals'],root_LBFGS_iteration_cap_observed=lb['iterations']>=1200,
                original_LBFGS_termination_label=lb['termination_branch'],TR_trials=len(tr['trace']),TR_accepted_steps=tr['accepted_steps'],
                failure_reason=r['failure_reason'],process_wall_seconds=manifest['process']['wall_seconds'],process_timeout_seconds=read(dest/'claim.json')['timeout_seconds'],
                original_checkpoint_sha256=r['checkpoint_sha256'],source_result=str((dest/'result.json').relative_to(ROOT)).replace('\\','/'),source_result_sha256=digest(dest/'result.json'),
                implementation_commit=manifest['git_commit'],protocol_hash=manifest['config_hash'],dtype=claim['environment']['dtype'],device=claim['environment']['device'],threads=claim['environment']['threads'],
                n_state=curve['n_state'],m_residual=len(curve['residual']),n_parameter=curve['n_parameter'],coordinate=training.get('coordinate',training.get('log_parameter')),
                gamma=r['gamma'],loss_weights=locked['resolved_runtime'][r['group']]['loss_weights'],objective=locked['numerics']['objective'],
                CG_iterations=r['CG_iterations'],explicit_JVP_VJP_counts=r['explicit_JVP_VJP_counts'],explicit_jacobians=r['explicit_jacobians'],
                explicit_hessians=r['explicit_hessians'],HVP_count=read(dest/'HVP.json')['HVP_count'],hardware=claim['environment']['processor']))
    if len(rows)!=30:raise RuntimeError('requires all 30 originally planned fresh root records; no partial scientific report')
    summary={}
    for group in ['burgers','allen_cahn','multi']:
        rr=[r for r in rows if r['group']==group]
        summary[group]=dict(planned=10,valid=sum(r['status']=='PASS' for r in rr),gradient_pass=sum(r['gradient_pass'] for r in rr),A_SPD_pass=sum(r['A_SPD_pass'] for r in rr),
            both_gradient_and_SPD_failed=sum(not r['gradient_pass'] and not r['A_SPD_pass'] for r in rr),
            gradient_range=[min(r['final_gradient'] for r in rr),max(r['final_gradient'] for r in rr)],
            iteration_cap_observed=sum(r['root_LBFGS_iteration_cap_observed'] for r in rr),worker_wall_seconds=sum(r['process_wall_seconds'] for r in rr))
    result=dict(scope='read_only_failure_diagnosis_no_new_solve',summary=summary,rows=rows,source_commit='read each immutable run manifest',
        interpretation='Availability-limited PARTIALLY_SUPPORTED labels must not be read as independent evidence of SO superiority. Algorithmic iteration caps and wall-clock caps are different.',
        audit_seconds=time.perf_counter()-started)
    dest=OUT/'final';dest.mkdir(exist_ok=True)
    (dest/'ROOT_FAILURE_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (dest/'ROOT_FAILURE_AUDIT.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    parts=['# 新训练根中心失效审计','本审计只读取保存的结果，没有重训、追加精化或修改本轮科学协议。']
    for group,s in summary.items():
        parts.append(f"{group}：有效 {s['valid']}/10；梯度门通过 {s['gradient_pass']}/10，A-SPD 门通过 {s['A_SPD_pass']}/10；末态梯度范围 {s['gradient_range']}，已达到 LBFGS 迭代上限的记录 {s['iteration_cap_observed']}/10。")
    parts += ['逐中心同时保留 LBFGS 原始停止标签和可直接核验的迭代计数；不能把迭代上限耗尽写成墙钟预算耗尽。',
        '若独立中心全部无效，PARTIALLY_SUPPORTED 仅为预注册函数对可用性不足的标签，不表示 SO 获得任何独立胜出证据。',
        '历史已恢复中心上的开发通过，不证明一次新训练得到的状态一定可被相同有界流程精化到严格驻点。下一轮若研究求解器可达性，须使用新的开发/确认划分，不得调参后覆盖或替换本批结果。']
    (dest/'ROOT_FAILURE_AUDIT.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    plot_start=time.perf_counter()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(1,2,figsize=(12,8),gridspec_kw={'width_ratios':[1,2]})
    ordered=sorted(rows,key=lambda r:(['burgers','allen_cahn','multi'].index(r['group']),r['seed']))
    heat=np.array([[r['gradient_pass'],r['A_SPD_pass'],r['status']=='PASS'] for r in ordered],dtype=int)
    axes[0].imshow(heat,aspect='auto',vmin=0,vmax=1,cmap='RdYlGn');axes[0].set(xticks=[0,1,2],xticklabels=['gradient','A-SPD','valid'],yticks=range(len(ordered)),yticklabels=[f"{r['group']} {r['seed']}" for r in ordered],title='All planned roots: red=fail, green=pass')
    for group,color in [('burgers','tab:blue'),('allen_cahn','tab:orange'),('multi','tab:green')]:
        rr=[r for r in ordered if r['group']==group];axes[1].semilogy([r['seed'] for r in rr],[r['final_gradient'] for r in rr],'o',color=color,label=group)
    axes[1].axhline(locked['numerics']['gradient_gate'],color='black',ls='--',label='frozen gradient gate');axes[1].legend();axes[1].set(xlabel='seed',ylabel='normalized state gradient',title='Every fresh root retained')
    fig.tight_layout();figdir=dest/'figures';figdir.mkdir(exist_ok=True)
    fig.savefig(figdir/'ROOT_AVAILABILITY.svg');fig.savefig(figdir/'ROOT_AVAILABILITY.png',dpi=150);plt.close(fig)
    (dest/'ROOT_AVAILABILITY_PROVENANCE.json').write_text(json.dumps(dict(source_sha256=digest(dest/'ROOT_FAILURE_AUDIT.json'),plot_seconds=time.perf_counter()-plot_start,read_only=True),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
