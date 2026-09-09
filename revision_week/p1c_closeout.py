"""Read-only numerical audit and generated closeout of the fixed Phase 1C run."""
import json, sys, time
import numpy as np
import torch
from p1c_development import OUT, PREVIOUS, ROOT, read, write, sha, load_center, numerical_mu, norm, bounded_command

def main():
    start=time.perf_counter();snap=read(OUT/'snapshot.json');summary=read(OUT/'SUMMARY.json')
    assert all(sha(ROOT/p)==s for p,s in snap['code'].items())
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in snap['history'])
    assert summary['step_records']==16 and summary['adapt_valid']==21
    checks=[];details=[]
    for cid in snap['config']['roots']:
        ck,prov,residual,_=load_center(cid);anchor=torch.from_numpy(ck['theta']);gamma=float(ck['gamma'])
        m=len(ck['residual_at_center'])
        for row in read(OUT/cid/'stationarity.json'):
            theta=torch.from_numpy(np.load(OUT/cid/(row['task']+'.npz'))['theta']);lp=torch.tensor([row['lambda_value']])
            obj=lambda t:.5*residual(t,lp).square().sum()+.5*gamma*(t-anchor).square().sum()
            g=torch.func.grad(obj)(theta).numpy();a=torch.func.hessian(obj)(theta).numpy();mu=numerical_mu(a)
            gradient=norm(g)/m/max(norm(theta.numpy()),1.)
            assert abs(float(obj(theta))-row['loss'])<1e-10*max(1.,abs(row['loss']))
            assert abs(gradient-row['gradient'])<1e-12
            assert (row['status']=='PASS')==bool(mu['mu_value'] and gradient<=snap['config']['gradient_gate'])
            old=row['old_result'];cap='max_eval_reached' if old['optimizer_evals']>=1500 else 'max_iter_reached' if old['optimizer_iterations']>=1200 else 'other_LBFGS_termination_not_logged'
            details.append(dict(task=row['task'],status=row['status'],failure_reason=row['failure_reason'],
                old_termination_evidence=cap,old_gradient=old['final_grad_normalized'],new_gradient=gradient,
                accepted_newton_steps=sum('alpha' in t for t in row['trace']),
                final_min_eigen=mu['lambda_min_A_numeric'],final_SPD_status=mu['spd_status'],
                newton_step_norm=norm(theta.numpy()-np.load(PREVIOUS/'tasks'/row['task']/'state.npz')['theta']),
                objective_change=row['loss']-old['final_loss']))
        for row in read(OUT/cid/'steps.json'):
            if row['status']!='PASS':continue
            tag=f'{cid}_{"plus" if row["offset"]>0 else "minus"}';lam=float(ck['log_parameter'][0])+row['offset']+row['step']
            theta=torch.from_numpy(np.load(OUT/cid/(tag+'_'+row['method']+'_candidate.npz'))['theta'])
            obj=lambda t:.5*residual(t,torch.tensor([lam])).square().sum()+.5*gamma*(t-anchor).square().sum()
            g=torch.func.grad(obj)(theta).numpy();a=torch.func.hessian(obj)(theta).numpy()
            grad=norm(g)/m/max(norm(theta.numpy()),1.)
            assert grad<=snap['config']['gradient_gate'] and numerical_mu(a)['mu_value']
            sr=next(r for r in read(OUT/cid/'stationarity.json') if r['task']==tag+'_start_strict')
            assert abs(sr['loss']-float(obj(theta))-row['actual'])<1e-10
            checks.append(dict(root=cid,offset=row['offset'],method=row['method'],gradient=grad))
    matrix=read(OUT/'matrix/result.json');valid=[r for r in matrix if r['status']=='PASS']
    assert len(matrix)==25 and all(r['interval_contains_reference'] for r in valid)
    assert sum(r['quadrant']=='Q4' for r in valid)==0
    verify_s=time.perf_counter()-start
    engineering=[]
    for name,command in [('tests',[sys.executable,'-m','pytest','-q','revision_week/test_p1c_development.py','revision_week/test_p1b_correction.py','revision_week/test_core.py']),
                         ('repository',[sys.executable,'scripts/validate_repository.py'])]:
        path=OUT/(name+'_validation.json')
        if path.exists():r=read(path)
        else:r=bounded_command(command,120);write(path,r)
        engineering.append(dict(name=name,status=r['status'],seconds=r['wall_seconds']))
    assert all(r['status']=='PASS' for r in engineering)
    new_cost=summary['worker_seconds']+verify_s+sum(r['seconds'] for r in engineering)+3.8343419
    oldcost=read(PREVIOUS/'COST_LEDGER.json');oldfinal=read(PREVIOUS/'FINAL_REVIEW_VALIDATION.json')
    write(OUT/'CLOSEOUT.json',dict(engineering='PASSED',tests=45,independent_state_audits=details,candidate_audits=checks,
        audit_seconds=verify_s,engineering_checks=engineering,new_accounted_seconds=new_cost,
        prefreeze_test_command_seconds=3.8343419,prefreeze_timing_source='tool-measured command wall time',
        historical_phase1_seconds=oldcost['stage1_cost_unchanged']['current_recorded_compute_seconds'],
        historical_reconstruction_seconds=oldcost['stage1_cost_unchanged']['historical_reconstruction_seconds'],
        historical_phase1b_success_seconds=oldcost['historical_successful_activity_measured_seconds'],
        previous_corrective_seconds=oldfinal['new_accounted_seconds'],
        cumulative_accounted_excluding_historical_reconstruction_and_estimated_failures=new_cost+oldcost['stage1_cost_unchanged']['current_recorded_compute_seconds']+oldcost['historical_successful_activity_measured_seconds']+oldfinal['new_accounted_seconds'],
        historical_failed_estimates=oldcost['historical_failed_compute_estimates'],
        matrix_estimator_seconds=sum(r['estimate_seconds'] for r in valid),matrix_spectrum_seconds=sum(r['spectrum_seconds'] for r in valid),
        matrix_oracle_seconds=sum(r['oracle_seconds'] for r in valid),matrix_extra_A_matvecs=sum(r['A_matvec_count'] for r in valid),
        original_results_preserved=len(snap['history'])))
    capcounts={c:sum(r['old_termination_evidence']==c for r in details) for c in set(r['old_termination_evidence'] for r in details)}
    worsened=sum(r['upper_effectivity']>r['old_upper_effectivity'] for r in valid)
    eigfail=[r for r in details if r['failure_reason']=='state_not_SPD']
    lines=['# Phase 1C 审计结论','',
        '工程检查 PASSED：45 项测试、统一仓库 validator 和独立状态重载核验通过。科学结果有明确局限。','',
        f"1. 驻点诊断：旧 LBFGS 终止证据为 {capcounts}。函数评估上限早于迭代上限可以终止优化，不能据此宣称达到驻点；未保存原因的其他终止不作臆测。",
        f"Burgers 六个状态全部经两步 Newton 达标；Allen–Cahn 六个仍失败，其中 {len(eigfail)} 个在更新后的 Hessian 检查失去数值 SPD，另一个用完固定八步预算。",
        'Newton 降低目标并不保证留在原局部正定区域。这个试验显示 Allen–Cahn 的障碍超出单纯放宽 LBFGS 预算；不继续救援或替换中心。',
        '失败状态的最小特征值与位移范数：','```json',json.dumps([r for r in details if r['status']!='PASS'],ensure_ascii=False,indent=2),'```','',
        f"2. 新一步试验：{summary['accepted_steps']}/16 接受；Allen–Cahn 的八条由于公共起点失败而未执行候选求解，仍计入计划分母。",
        'Burgers 两个偏移中 SO 实际下降均优于 GN，差值见 SUMMARY.json；三种曲率的候选不再因共同截断而相同。',
        '这只是一个有效根中心上的两个关联观测，不支持跨 PDE 或独立统计结论。目标下降与合成真值误差改善分别报告。','',
        f"3. 固定八步残差能量估计未成功：新界在 {worsened}/21 中更松，通过 {summary['new_estimated_pass']}/21，原估计通过 {summary['old_estimated_pass']}/21。",
        'PCG 减少能量误差不保证欧氏残差范数下降，残差平方除以小 mu 的剩余项仍会膨胀。恒等式与参考包络核验通过，瓶颈是界的实用性，不是代数错误。',
        '新旧界可在未来前瞻性协议中考虑组合，但本次没有事后更换估计器以提高通过数。停止这条固定八步方案；不宣称认证或效率提升。','',
        f"本轮新增可核算 {new_cost:.3f} 秒，其中实验 worker {summary['worker_seconds']:.3f} 秒；历史成本和估计失败账详见 COST_LEDGER/CLOSEOUT.json 引用。无新训练、无新种子。",'',
        '结论：SO 局部一步用途为 PARTIALLY_SUPPORTED（仅 Burgers 开发中心）；SO-ADAPT 新估计方案 NOT_SUPPORTED。独立协议冻结继续暂缓，尤其不能绕过 Allen–Cahn 的局部有效性失败。',
        '历史修正报告与全部失败保留，不把此次开发结果混入原 confirmation。']
    (OUT/'FINAL_REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
    manifest=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']
    write(OUT/'MANIFEST.json',manifest)
    print(json.dumps(dict(engineering='PASSED',new_seconds=new_cost,files=len(manifest)),ensure_ascii=False))

if __name__=='__main__':main()
