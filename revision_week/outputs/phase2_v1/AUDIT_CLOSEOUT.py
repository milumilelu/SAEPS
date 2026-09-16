"""Reporting-only correction; immutable numerical inputs are never modified."""
import sys, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'phase2'))
from common import *
from reporting import costs,validate_manifests
from finalize_phase2 import artifact_stage
start=time.perf_counter()
lock=read(LOCK/'LOCK.json')
for name,digest in lock['source_hashes'].items(): assert canon_sha(ROOT/name)==digest,name
assert canon_sha(LOCK/'execution.json')==lock['configuration_sha256']
assert canon_sha(LOCK/'RUN_PLAN.json')==lock['run_plan_sha256']
archive=OUT/'reporting_correction_original'
if not archive.exists():
    archive.mkdir()
    for name in ['final','e5c']:
        shutil.copytree(OUT/name,archive/name)
    shutil.copy2(OUT/'FINAL_MANIFEST.json',archive/'FINAL_MANIFEST.json')
allrows=read(archive/'final/ALL_RAW_AGGREGATED.json')
rows=allrows['E5C']
p=OUT/'tasks/E5C/n100001_m3413'
proc=read(p/'process.json')
assert proc['failure_reason']=='resource_limit' and (p/'setup.json').exists()
assert not any((p/(label+'.json')).exists() for label in ['cold','warmup','steady_1','steady_2','steady_3'])
for row in rows:
    if row['status']=='PASS':
        row.update(numerical_status='PASS',execution_disposition='COMPLETED')
    else:
        assert (row['n'],row['m'])==(100001,3413)
        started=row['pass_label']=='cold'
        row.update(status='SOLVER_FAILURE' if started else None,numerical_status='SOLVER_FAILURE' if started else None,execution_disposition='INTERRUPTED' if started else 'PROTOCOL_STOP',attempted=started,failure_reason='resource_limit',upstream_gate='n100001_m3413 process memory limit')
counts=dict(planned=len(rows),valid=sum(r['status']=='PASS' for r in rows),failed_started=sum(r['status']=='SOLVER_FAILURE' for r in rows),not_started=sum(r['status'] is None for r in rows),planned_cells=len(set((r['n'],r['m']) for r in rows)),completed_cells=len(set((r['n'],r['m']) for r in rows if r['status']=='PASS')))
assert (counts['planned'],counts['valid'],counts['failed_started'],counts['not_started'])==(45,40,1,4)
assert len(allrows['E2'])==20 and len(allrows['E3'])==160 and len(allrows['E4C'])==10
summary=read(archive/'final/SUMMARY.json');summary['E5C']=counts
cost=costs();summary['cost']=cost
summary['independent_evidence_interpretation']='PARTIALLY_SUPPORTED is the locked availability-limited gate label, not independent evidence that SO improves curvature. All 30 roots fail binding eligibility.'
write(OUT/'final/ALL_RAW_AGGREGATED.json',allrows);write(OUT/'final/SUMMARY.json',summary)
artifact_stage('E5C',rows,counts,cost)
validation=read(OUT/'e5c/VALIDATION.json');validation.update(failed_started=1,not_started=4);write(OUT/'e5c/VALIDATION.json',validation)
report=(archive/'final/PHASE2_REPORT.md').read_text(encoding='utf-8')
report=report.replace('"E5C": 0','"E5C": 4')
report=report.replace('1600.673',f"{cost['measured_activity_seconds']:.3f}")
report+='\n## Reporting audit\n\n独立比较有效根为 0/30；PARTIALLY_SUPPORTED 是冻结规则的可用性不足分类，不表示 SO 已获得独立支持。失败根的诊断曲率不能进入科学主比较。\n\nE5-C: '+json.dumps(counts)+'。冷启动因 resource_limit 中断；warmup 和三次 steady 未启动，numerical_status=null。无实验重跑。\n\n成本是已记录活动之和，不是整个会话耗时。原最终聚合/绘图 '+str(read(archive/'final/VALIDATION.json')['aggregation_and_plot_seconds'])+' 秒另列；早期未计时命令、下载等待、模型推理未计入。历史重构单列。\n'
(OUT/'final/PHASE2_REPORT.md').write_text(report,encoding='utf-8')
v=read(archive/'final/VALIDATION.json');v.update(run_manifests=validate_manifests(),source_summary_sha256=canon_sha(OUT/'final/SUMMARY.json'),reporting_correction_passed=True);write(OUT/'final/VALIDATION.json',v)
for old,new in [('e4d','e4_d'),('e4c','e4_c'),('e5ab','e5_ab'),('e5c','e5_c'),('e6d','e6_d'),('e6p','e6_p')]:shutil.copytree(OUT/old,OUT/new,dirs_exist_ok=True)
write(OUT/'final/REPORTING_CORRECTION.json',dict(reason='Distinguish aborted cold pass from four unstarted positions per protocol section 16',source_process_sha256=canon_sha(p/'process.json'),original_report_archive=str(archive.relative_to(ROOT)),original_summary_sha256=canon_sha(archive/'final/SUMMARY.json'),immutable_sources_verified=True,seconds=time.perf_counter()-start))
write(OUT/'FINAL_MANIFEST.json',[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=canon_sha(p) if p.suffix in ['.json','.md','.csv','.svg'] else sha(p)) for p in (OUT/'final').rglob('*') if p.is_file()])
print(json.dumps(dict(counts=counts,measured=cost['measured_activity_seconds'],cumulative=cost['cumulative_accounted_excluding_historical_reconstruction_and_estimated_failures'],validation=v)))
