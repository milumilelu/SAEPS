"""Read-only aggregation and integrity validation for the corrective run."""
from __future__ import annotations
import csv,json,time,hashlib,re
from pathlib import Path
import numpy as np
from p1b_correct import OUT,OLD,ROOT,read,write,sha,csvout


def main():
    t=time.perf_counter(); frozen=read(OUT/'protocol_snapshot.json')
    assert sha(ROOT/'revision_week/p1b_correct.py')==frozen['code_sha256']
    assert sha(ROOT/'revision_week/p1b_onestep.py')==frozen['solver_sha256']
    for row in frozen['historical_artifacts']: assert sha(row['path'])==row['sha256'],row['path']
    checks=read(OUT/'engineering_checks.json');assert all(r['exit_code']==0 for r in checks)
    passed=int(re.search(r'(\d+) passed', (OUT/'regressions.log').read_text(encoding='utf-8')).group(1))
    resume=read(OUT/'RESUME_VERIFICATION.json')
    assert resume['all_task_files_unchanged'] and resume['numerical_tasks_reexecuted']==0
    rows=read(OUT/'profile_audit.json');valid=read(OUT/'VALIDATION.json');cost=read(OUT/'COST_LEDGER.json')
    expected={(cid,off,method) for cid in frozen['config']['roots'] for off in frozen['config']['offsets']
              for method in ['RAW','SAEPS-GN','SO','EXACT-REDUCED-ORACLE']}
    assert {(r['root'],r['offset'],r['method']) for r in rows}==expected and len(rows)==len(expected)
    for r in rows:
        b=read(OUT/'tasks'/r['strict_start_task']/'result.json');c=read(OUT/'tasks'/r['strict_candidate_task']/'result.json')
        assert abs(r['strict_actual']-(b['final_loss']-c['final_loss']))<1e-14
        assert r['stationarity_pass']==(b['converged'] and c['converged'])
    oldrows=list(csv.DictReader((OLD/'ONE_STEP_PILOT.csv').open(encoding='utf-8')))
    parameter_rows=[]
    for r in oldrows:
        cid=r['root_id'];p=OLD/'recovery'/cid
        prov=read(p/'provenance.json');ck=np.load(p/'state_checkpoint.npz')
        bench='Burgers' if cid.startswith('burgers') else 'Allen-Cahn'
        truth=prov['data_recipe']['runtime_config']['benchmarks'][bench]['truth_parameter']
        before=abs(np.exp(float(ck['log_parameter'][0])+float(r['offset_id']))-truth)/truth
        after=abs(np.exp(float(r['trial_lambda']))-truth)/truth
        assert abs(before-float(r['parameter_error_before']))<1e-12
        assert abs(after-float(r['parameter_error_after']))<1e-12
        parameter_rows.append(dict(root=cid,offset=r['offset_id'],method=r['method'],before=float(before),after=float(after),improved=bool(after<before)))
    csvout(OUT/'PARAMETER_ERROR_AUDIT.csv',parameter_rows)
    observed=sum(r['strict_actual']>r['error_estimate'] and r['strict_actual']-1e-4*r['predicted']>r['error_estimate'] for r in rows)
    report=dict(engineering_status='PASSED',regression_tests=passed,unified_validator_exit_code=checks[-1]['exit_code'],
        historical_output_hashes_preserved=len(frozen['historical_artifacts']),
        method_rows=len(rows),independent_roots=len(frozen['config']['roots']),
        objective_margin_above_precision_estimate=observed,
        state_SPD_pass=sum(r['SPD_pass'] for r in rows),strict_stationarity_pass=sum(r['stationarity_pass'] for r in rows),
        strict_profile_full_gate_pass=valid['profile_numerically_resolved'],
        strict_profile_gate=frozen['config']['profile_gate_mean_normalized'],
        gradient_min=min(min(r['start_grad'],r['candidate_grad']) for r in rows),
        gradient_max=max(max(r['start_grad'],r['candidate_grad']) for r in rows),
        strict_decrease_min=min(r['strict_actual'] for r in rows),strict_decrease_max=max(r['strict_actual'] for r in rows),
        replay_max_absolute_difference=max(r['replay_absolute_difference'] for r in rows),
        parameter_error_improved=sum(r['improved'] for r in parameter_rows),
        new_profile_solves=cost['new_profile_solves'],new_HVP_centers=valid['hvp_attempted'],
        new_worker_seconds=cost['new_validation_process_seconds'],
        new_matrix_seconds=cost['new_matrix_analysis_seconds'],
        new_engineering_check_seconds=sum(r['seconds'] for r in checks),
        resume_verification_seconds=resume['seconds'],
        pre_freeze_regression_command_seconds=3.472926,
        pre_freeze_regression_timing_source='exec command result: 40 passed; wall_time_seconds=3.472926, before source commit 1d528af',
        failed_closeout_seconds=1.6450914,
        failed_closeout_reason='NumPy boolean sum became int64; JSON serialization failed. No numerical task retried; explicit bool conversion fixes aggregation.',
        original_phase1b_compliance='DEVIATIONS_RETAINED; not retrospectively repaired',
        scientific_claim='Local decrease remains positive and exceeds numerical precision estimate; stricter profile stationarity not achieved',
        SO_incremental_update_benefit='NOT_SUPPORTED: same clipped candidate as GN',
        next_independent_protocol='DEFER_FREEZE; discuss a new prospective protocol with all limitations disclosed')
    report['new_accounted_seconds']=sum(report[k] for k in ['new_worker_seconds','new_matrix_seconds','new_engineering_check_seconds','pre_freeze_regression_command_seconds','failed_closeout_seconds','resume_verification_seconds'])
    report['closeout_seconds']=time.perf_counter()-t
    write(OUT/'FINAL_REVIEW_VALIDATION.json',report)
    ledger=read(OUT/'CLAIM_LEDGER.json')
    ledger.append(dict(claim='Observed decrease exceeds precision-change estimate',status='SUPPORTED' if observed==len(rows) else 'PARTIALLY_SUPPORTED',
                       limitation='does not imply strict stationary-profile gate or rigorous error certificate; separate from strict gate'))
    write(OUT/'CORRECTED_CLAIM_LEDGER.json',ledger)
    txt=f'''# Phase 1B 修复完成报告

工程修复已完成：{passed}项数学/回归测试通过，统一仓库validator退出码{report['unified_validator_exit_code']}。
day1/day2的{report['historical_output_hashes_preserved']}个历史产物逐文件校验未变；本轮新增训练0次。
完整块恢复核对及真实HVP补验通过，使用保存数据而非重新生成训练数据。

## 结果必须分开解读

原试验来自{report['independent_roots']}个根中心，不是16个独立样本。
{observed}/{len(rows)}方法行的精化后目标下降与接受余量高于数值精度变化估计；
下降范围{report['strict_decrease_min']:.8g}–{report['strict_decrease_max']:.8g}。
{report['state_SPD_pass']}/{len(rows)}通过状态块SPD检查。
但严格归一化梯度范围{report['gradient_min']:.5g}–{report['gradient_max']:.5g}，
未通过本轮事先固定的{report['strict_profile_gate']:g}门槛；严格profile全链通过
{report['strict_profile_full_gate_pass']}/{len(rows)}。不得把“严格门未过”写成没有观察到下降，
也不得把正下降自动写成精确profile验证通过。不会据此调低门槛或增加精化次数。
重放与旧实际下降的最大绝对差{report['replay_max_absolute_difference']:.6g}，没有声称逐位重现一步求解。

真实参数误差独立重算：{report['parameter_error_improved']}/{len(parameter_rows)}改善；
仅限合成数据事后评价。GN/SO/ORACLE对应相同截断后坐标，SO增量实际收益仍未获支持。

ADAPT四格表仍为{valid['quadrants']}；终止缺陷的界有效度中位数
{valid['terminal_median_effectivity']:.6g}，初始为{valid['initial_median_effectivity']:.6g}，已分开报告。
“12个中心估计未过”并非“12个中心真实精度失败”；不存在严格误差认证或总成本优势主张。

## 修复范围与保留的历史偏差

旧脚本入口拒绝执行以防覆盖原输出和再次重放；新任务采用独立运行ID、进程硬超时、
一次尝试声明和完整失败计时，已完成任务不再执行。超时与不合格状态不能被接受。
恢复完整块比较、状态SPD、HVP分项计时、终止缺陷分析和数据驱动报告均已补齐。
历史重复重放、失败计算只有估计时间以及缺少可独立确认的运行前冻结证据，均不可事后消除。
原“全部合规、冻结条件满足”结论撤回，旧报告保留供审计；以本目录更正报告为准。

新增可计量计算合计{report['new_accounted_seconds']:.3f}秒，含首次修复测试、
{report['new_HVP_centers']}个HVP工作进程、{report['new_profile_solves']}次去重后的状态求解、
矩阵分析与最终工程验收；收尾聚合另计{report['closeout_seconds']:.3f}秒。
工作进程计时包含启动与任何失败/超时，旧失败成本仍按原台账标注估计，无法报告精确历史总成本。
未启动独立确认、未推送。可以讨论新协议，当前不自动冻结。

数据：ONE_STEP_PRECISION_AUDIT.csv、PARAMETER_ERROR_AUDIT.csv、ADAPT_TERMINAL_ANALYSIS.csv、
HVP_COST_AND_PARITY.csv、tasks/*/result.json、COST_LEDGER.json、FINAL_REVIEW_VALIDATION.json。
旧输出的校验清单在protocol_snapshot.json；新输出在OUTPUT_MANIFEST.json。
'''
    (OUT/'FINAL_CORRECTION_REPORT.md').write_text(txt,encoding='utf-8',newline='\n')
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='OUTPUT_MANIFEST.json']
    write(OUT/'OUTPUT_MANIFEST.json',dict(files=[dict(path=p.relative_to(OUT).as_posix(),sha256=sha(p),
        canonical_lf_sha256=hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() if p.suffix in ['.json','.csv','.md','.log'] else None) for p in files]))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
