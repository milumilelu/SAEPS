"""First-stage result audit, cost ledger and report generation (no experiments)."""
from __future__ import annotations
import os
os.environ['OMP_NUM_THREADS']='1'; os.environ['MKL_NUM_THREADS']='1'; os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
import numpy as np
from run import ROOT,OUT,save,digest,table,md,git


def restore_checkout_bytes():
    """Copy verified historical bytes only into the separate new worktree."""
    from saeps.v5.governance import validate_historical_inventory
    src=Path(json.loads((OUT/'initial_workspace.json').read_text(encoding='utf-8'))['repo'])
    if ROOT.resolve()==src.resolve(): raise RuntimeError('must not repair original workspace')
    inv=json.loads((src/'configs/v5/HISTORICAL_HASH_INVENTORY.json').read_text(encoding='utf-8'))
    validate_historical_inventory(src,inv)
    rows=[]
    for p in (src/'outputs/runs').rglob('*'):
        if not p.is_file() or '/v5/' in p.as_posix(): continue
        q=ROOT/p.relative_to(src); old=q.read_bytes(); data=p.read_bytes()
        if old==data: continue
        if old.replace(b'\r\n',b'\n')!=data.replace(b'\r\n',b'\n'): raise RuntimeError('non-newline mismatch')
        rows.append(dict(path=p.relative_to(src).as_posix(),checkout_sha256=hashlib.sha256(old).hexdigest(),historical_sha256=hashlib.sha256(data).hexdigest()))
        q.write_bytes(data)
    validate_historical_inventory(ROOT,inv)
    save(OUT/'new_worktree_byte_restoration.json',dict(reason='Verified source inventory; repaired new checkout newline representation only',files=rows))
    print('Byte-exact historical inventory restored:',len(rows))


def repository_validation():
    p=OUT/'repository_validator_attempts'; p.mkdir(exist_ok=True)
    number=len(list(p.glob('*.json')))+1
    started=time.perf_counter()
    r=subprocess.run([sys.executable,'scripts/validate_repository.py'],cwd=ROOT,capture_output=True,text=True)
    (p/f'{number}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    save(p/f'{number}.json',dict(seconds=time.perf_counter()-started,exit_code=r.returncode))
    print('Repository validator exit:',r.returncode)
    return r.returncode


def validate_and_report():
    started=time.perf_counter()
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'raw').glob('*.json'))]
    expected={('burgers',s) for s in range(55,70)}|{('allen_cahn',s) for s in range(75,85)}
    assert {(r['pde'],r['seed']) for r in rows}==expected and len(rows)==25
    valid=[r for r in rows if r['status']=='PASS']
    assert len(valid)==21
    cfg=ROOT/'revision_week/config/protocol.template.yaml'
    expected_code=hashlib.sha256((ROOT/'revision_week/run.py').read_bytes()+(ROOT/'revision_week/core.py').read_bytes()).hexdigest()
    for r in rows:
        assert digest(r['input_path'])==r['input_sha256']
        assert digest(cfg)==r['protocol_hash'] and expected_code==r['code_hash']
        if r['status']!='PASS': assert r['failure_reason']; continue
        # Independent block reference recomputation; never uses D to define it.
        d=json.loads(Path(r['input_path']).read_text(encoding='utf-8'))
        h=d['exact_blocks']; g=d['GN_blocks']; n=r['n_state']; gamma=r['gamma']
        a=np.array(h.get('H_tt_sym',h.get('H_tt')))+gamma*np.eye(n)
        b=np.array(h['H_tl']); c=np.array(h['H_ll'])
        oracle=float((c-b.T@np.linalg.solve(a,b))[0,0])
        assert abs(oracle-r['F_star'])<=1e-9*max(abs(oracle),1)
        for name in ['raw','GN','SO']:
            f=r[{'raw':'F_raw','GN':'F_G_reference','SO':'F_SO'}[name]]
            np.testing.assert_allclose(abs(f-oracle),r['absolute_error_'+name],rtol=1e-9,atol=1e-10)
        assert r['bound_status']=='numerical_bound_estimate' and r['U_absolute']>=r['absolute_error_SO']
        assert r['algebra_identity_error']<1e-10 and r['gn_identity_error']<1e-10
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    for s in summary:
        subset=[r for r in valid if s['pde']=='all' or r['pde']==s['pde']]
        assert s['matrix_reference_n']==len(subset)
        assert s['SO_improved_n']==sum(r['absolute_error_SO']<r['absolute_error_GN'] for r in subset)
        for name in ['raw','GN','SO']:
            np.testing.assert_allclose(s['median_relative_error_'+name],np.median([r['relative_error_'+name] for r in subset]),rtol=1e-14)
    # Actual resume: terminal raw files must remain byte-identical.
    before={p.name:digest(p) for p in (OUT/'raw').glob('*.json')}
    resumed=subprocess.run([sys.executable,str(ROOT/'revision_week/run.py'),'run','--experiment','E0','--config',str(cfg)],capture_output=True,text=True,cwd=ROOT)
    assert resumed.returncode==0,resumed.stdout+resumed.stderr
    assert before=={p.name:digest(p) for p in (OUT/'raw').glob('*.json')}
    (OUT/'resume_check.log').write_text(resumed.stdout+resumed.stderr,encoding='utf-8')
    initial=json.loads((OUT/'initial_workspace.json').read_text(encoding='utf-8'))
    assert git('status','--porcelain',repo=initial['repo'])==initial['status']
    costs=json.loads((OUT/'costs.json').read_text(encoding='utf-8'))
    validation_attempts=[json.loads((OUT/'repository_validator_cost.json').read_text(encoding='utf-8'))]
    validation_attempts += [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'repository_validator_attempts').glob('*.json'))]
    costs.update(failed_audit_seconds=1.7435761,failed_byte_repair_syntax_command_seconds=.5267703,
        validator_attempts=validation_attempts,stage_audit_and_resume_seconds=time.perf_counter()-started)
    costs['current_recorded_compute_seconds'] += costs['failed_audit_seconds']+costs['failed_byte_repair_syntax_command_seconds']+sum(a['seconds'] for a in validation_attempts)+costs['stage_audit_and_resume_seconds']
    save(OUT/'cumulative_costs.json',costs)
    max_id=max(r['algebra_identity_error'] for r in valid)
    max_rep=max(r['original_reproduction_error'] for r in valid)
    result=dict(status='PASSED',planned=25,valid_matrix_centers=21,historical_failures=4,
        max_identity_error=max_id,max_historical_reproduction_relative_error=max_rep,
        source_hashes_unchanged=True,resume_deduplication_pass=True,summary_recomputed_from_raw=True,
        original_workspace_status_unchanged=True,source_commit=valid[0]['source_commit'],
        unified_validator_exit_code=validation_attempts[-1]['exit_code'])
    save(OUT/'STAGE_VALIDATION.json',result)
    md('COMPUTE_BUDGET_REPORT.md','# Cumulative measured cost\n\n'+json.dumps(costs,indent=2)+'\n\nHistorical reconstruction costs are inherited (not newly incurred). Original training total is unknown. Includes failed audit, failed repair command, both repository validator attempts, unit tests, E0, result audit and resume. Interactive inspection latency not exhaustively instrumented. No new training/profile; actual E0 JVP/VJP/HVP=0. Dense eigenspectrum and correction are charged. E0 refinement budget is 100 PCG iterations, up to 201 A products/RHS including explicit defect checks, not the proposed E1 100-product cap. This E0 diagnostic budget must not be represented as the future E1 budget. No efficiency conclusion is based on those differing budgets.\n')
    s=summary[0]
    md('FIRST_STAGE_REPORT.md',f'''# 第一阶段实际交付

工作树：{ROOT}；实现提交：{valid[0]['source_commit']}。
本地分支 codex/saeps-so-week1；没有 push。原工作区状态与输入矩阵 hash 检查通过。

27 个数学/算子测试通过；E0 保存 25/25 历史计划记录，21/21 可用矩阵通过复现。
最大历史曲率相对复现误差 {max_rep:.6g}，最大归一化缺陷恒等式误差 {max_id:.6g}。
19/21 中心改善，逐中心 GN/SO 误差倍数中位数 {s['median_improvement_factor']:.6g}。
GN 相对误差中位数 {s['median_relative_error_GN']:.6g}；SO {s['median_relative_error_SO']:.6g}。
四个旧无效种子 Burgers57/61/63、Allen81 保留；Burgers59/67 的 SO 变差保留。

21 条为数值误差界估计，严格验证型 0；初始有限相对界 0/21。
界/实际误差倍数中位数 {s['median_bound_effectivity']:.6g}，界很松。
有限对角 PCG 修正 {s['adaptive_tolerance_met_n']}/21 达到数值估计 10% 容差，
其余保留超预算状态。SO-ADAPT 的总成本优势尚未建立。

按任务书规则，**值得继续有预算限制的 SO 开发 E1**；不能直接冻结独立验证。
SO-ADAPT 仅值得作为有限开发诊断，不宜据此推广；V6 的可扩展候选阴性结论不变。
局部代数曲率结果不是 profile 精度或反演参数精度的证明。

本轮可计量累计计算 {costs['current_recorded_compute_seconds']:.3f} 秒；
E0 本身 {costs['e0_wall_seconds']:.3f} 秒；历史归档重构耗时
{costs['historical_reconstruction_seconds']:.3f} 秒单列，未重复训练。
详细口径见 COMPUTE_BUDGET_REPORT.md；真实 HVP=0，原始训练总成本不可完整恢复。

统一 validator 最终退出码 {validation_attempts[-1]['exit_code']}。初次检查发现新 worktree
LF 检出与历史 CRLF 字节库存不一致；只对新 worktree 恢复85个已核验历史文件的
字节表示，未改变数值、锁定库存或原工作区。首次失败日志和修复 hash 均保存。

缺口：21个原始中心的 theta/data/绝对梯度张量未归档。其他29个检查点不能替代它们。
因此未完成这些历史中心的真实 HVP/T3 重放；没有新队列、宽度实验、profile 或一步更新。
本次仅完成用户要求的第一阶段，不声称整个七天任务完成，也没有后台继续运行。

入口与路径：REPO_AUDIT.md、artifact_manifest.csv、ALL_RUNS.csv、METHOD_SUMMARY.csv、
raw/、TEST_REPORT.md、STAGE_VALIDATION.json；代码在 revision_week/core.py 和 run.py。
恢复命令见 RESUME_COMMANDS.md；数学说明见 ../../METHOD_MATH_NOTE.md。
''')
    md('RESUME_COMMANDS.md',f'''# Resume / reproduce saved stage

```powershell
Set-Location '{ROOT}'
$py = '{sys.executable}'
& $py revision_week/run.py run --experiment E0 --config revision_week/config/protocol.template.yaml
& $py revision_week/run.py report --run-id day1
```

The first command was actually rerun and left all terminal raw hashes unchanged.
No seed replacements or automatic background continuation. The raw results,
source commit and input hashes remain the authoritative numerical evidence.
Do not rerun audit against this changed branch inventory and call it the old audit.
New E1 needs explicit historical tensor recovery/provenance work before use.
''')
    md('PAPER_REVISION_NOTES.md',f'''# Evidence-limited paper notes

| 可进入主文的结论 | 直接支持的运行/图表 | 必须保留的限定条件 |
|---|---|---|
| 完整方向二次型及不精确响应缺陷恒等式通过数值检查 | TEST_REPORT.md; raw/; STAGE_VALIDATION.json | 恒等式不是首次提出证明；局部固定目标 |
| 历史开发集 SO 改善 {s['SO_improved_n']}/{s['matrix_reference_n']} | ALL_RUNS.csv; METHOD_SUMMARY.csv | 回顾性开发；两个变差中心和四个旧无效样本保留 |
| 普通谱数值估计的界很松 | ALL_RUNS.csv U与error字段 | 严格证书0；不能保证真实参数或全局可辨识 |
| SO-ADAPT效率未建立 | raw/ adaptive; V6历史findings | 稠密辅助；无生产HVP精度/成本验证 |

No new claims about independent two-parameter validation, width32 accuracy,
profile acceleration or inverse-parameter accuracy. Figures A–G were not created
in this first-stage delivery; full numerical tables are supplied instead.
''')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['restore-checkout-bytes','validate-repository','report'])
    a=p.parse_args()
    if a.action=='restore-checkout-bytes': restore_checkout_bytes()
    elif a.action=='validate-repository': sys.exit(repository_validation())
    else: validate_and_report()
