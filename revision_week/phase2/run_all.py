"""One-shot Phase 2 DAG execution. Resume only finished tasks; never replace seeds."""
from common import *
from execution import task,skip
from reporting import dev_summary,e1_summary,development_report,costs,validate_manifests,records
from gates import e3_allowed

def checked(command):
    started=time.perf_counter();r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if command[0]==sys.executable:
        p=OUT/'preflight/ENGINEERING_COMMAND_COSTS.json';ledger=read(p) if p.exists() else []
        ledger.append(dict(command=command,exit_code=r.returncode,wall_seconds=time.perf_counter()-started,stdout=r.stdout,stderr=r.stderr))
        write(p,ledger)
    print(r.stdout[-3000:],flush=True)
    if r.returncode:raise RuntimeError(r.stderr[-3000:] or r.stdout[-3000:])
    return r

def sync(message,full_tests=False):
    validate_manifests()
    if full_tests:checked([sys.executable,'-m','pytest','revision_week','-q'])
    checked([sys.executable,'scripts/validate_repository.py'])
    if git('remote','get-url','origin')!='https://github.com/milumilelu/SAEPS.git':raise RuntimeError('unexpected remote')
    allowed=('revision_week/phase2/','revision_week/outputs/phase2_v1/','revision_week/protocols/phase2_locked_v1/','revision_week/outputs/phase2_v1/run_manifests/','TASKS.md','docs/ISSUES.md')
    for line in git('-c','core.quotepath=false','status','--porcelain').splitlines():
        path=line[3:]
        if not path.startswith(allowed):raise RuntimeError('unattributed changes; no automatic commit: '+line)
    if git('status','--porcelain'):
        checked(['git','add','--',*[p for p in allowed if (ROOT/p).exists()]])
        checked(['git','commit','-m',message])
    checked(['git','fetch','origin'])
    for branch in ['main','codex/saeps-so-week1']:
        checked(['git','merge-base','--is-ancestor','origin/'+branch,'HEAD'])
    push=checked(['git','push','--atomic','origin','HEAD:main','HEAD:codex/saeps-so-week1'])
    if push.stderr:print(push.stderr,flush=True)
    if git('status','--porcelain'):raise RuntimeError('worktree not clean after sync')

def prepare():
    summary=development_report()
    if not summary['E5AB_engineering_pass'] or not summary['solver_development_pass']:raise RuntimeError('development engineering gate failed')
    audit=read(OUT/'preflight/SEED_AUDIT.json');used=set(audit['used_or_reserved_or_ambiguous'])|{3,827}
    # All observed source arithmetic: conservative expansion, even for ambiguous tokens.
    offsets=[1,20000,40000,43000,45000,46000,48000,49000,53000,60000]
    original=set(used)
    for offset in offsets:used.update(s+offset for s in original if 0<=s<2**31-offset)
    used.update(54000+n+m for n in [1001,10001,100001] for m in [213,853,3413])
    fresh=[];candidate=1000
    while len(fresh)<30:
        if candidate not in used:fresh.append(candidate)
        candidate+=1
    groups=dict(burgers=fresh[:10],allen_cahn=fresh[10:20],multi=fresh[20:])
    review=dict(status='PASSED',freshness_scope='all accessible refs/reflogs/worktrees/configs/manifests; inaccessible external or deleted history cannot be proven absent',
        expression_inventory_sha256=sha(OUT/'preflight/DYNAMIC_SEED_EXPRESSIONS.json'),reviewed_arithmetic_offsets=offsets,
        conclusions=['Training entrypoints pass root seed from archived configs/manifests; no hidden root seed transform found.',
                     'Named manual_seed offsets and fixed scalability n/m expressions expanded conservatively.',
                     'An ambiguous token is excluded; these are candidate reservations, not observations or replacement seeds.'],
        proposed_groups=groups,exclusions=sorted(used),prior_proposal_not_frozen=True)
    write(OUT/'preflight/SEED_SOURCE_REVIEW.json',review)
    history={}
    for relative in git('ls-files','outputs','revision_week/outputs').splitlines():
        if '/phase2_v1/' in relative:continue
        p=ROOT/relative
        if p.is_file():history[relative]=canon_sha(p) if p.suffix.lower() in ['.json','.csv','.md','.txt','.yaml','.yml','.log'] else sha(p)
    write(OUT/'preflight/HISTORICAL_HASHES.json',history)
    checked([sys.executable,'-m','pytest','revision_week','-q'])
    checked([sys.executable,'scripts/validate_repository.py'])
    write(OUT/'preflight/ENGINEERING_GATE.json',dict(status='PASSED',tests='Full revision_week regression suite passed; real four-center MF/HVP and two-PDE saved-state strict solver passed',
        new_training_started=False,seed_review=review['status'],implemented_modules=['workers','numerics','matrix_free','historical','locality','one_step','execution','reporting','run_all','finalize_phase2'],
        mathematical_interpretations=['Already stationary iterates use two explicit zero-displacement accepted revalidations to satisfy the plateau check.',
        'Root refinement is unanchored; final validity uses A after nominal gamma is fixed. Unanchored Htt is separately retained.',
        'CG restores finite-precision A-conjugacy twice, verifies the actual residual each iteration, with the same zero start/no preconditioner/tolerance/500-iteration cap.'],
        historical_files=len(history)))
    with (ROOT/'TASKS.md').open('a',encoding='utf-8') as f:f.write('\n\n## Phase 2 actual execution\n\n**状态:** `IN_PROGRESS` — development engineering passed; fresh execution awaits immutable lock.\n\n- Real development data, failures and costs: revision_week/outputs/phase2_v1/DEVELOPMENT_REPORT.md.\n- New source modules implement the whole conditional DAG; historical results and unrelated original worktree edits preserved.\n')
    with (ROOT/'docs/ISSUES.md').open('a',encoding='utf-8') as f:f.write('\n\n### Phase2 pre-lock engineering diagnostics\n\nClassification: implementation failure / numerical failure, resolved before fresh execution. NumPy block input lists were normalized to arrays; prior failed E0/E6 attempts remain archived. Plain CG lost conjugacy on compact Burgers centers; deterministic two-pass A-conjugacy restoration and true residual verification passed the unchanged tolerances and iteration budget. Exact stationary solver points require two saved zero-displacement plateau revalidations; no positive-step manufacture. E6 oracle k=8 effectivity fails its predeclared scientific gate; E6-P is a protocol stop, not an engineering error.\n')
    with (ROOT/'docs/ISSUES.md').open('a',encoding='utf-8') as f:f.write('\nPhase2 manifests use the explicitly authorized revision_week/outputs/phase2_v1/run_manifests namespace. The legacy outputs/runs tree is itself immutable under V5; the initial newly added manifests were moved, without changing historical files or weakening the old validator. Initial debug attempts had uncommitted-code hashes; final development acceptance is repeated under a committed executable and separately identified. User explicitly authorized continued pushes to the currently PUBLIC milumilelu/SAEPS repository in this session.\n')
    sync('Implement and verify Phase 2 numerical runners and historical development')

def freeze():
    if (LOCK/'LOCK.json').exists():verify_lock();sync('Synchronize previously committed Phase 2 lock');return
    if git('status','--porcelain'):raise RuntimeError('commit executable before lock')
    if read(OUT/'preflight/ENGINEERING_GATE.json')['status']!='PASSED':raise RuntimeError('engineering not ready')
    cfg=read(SPEC);cfg.update(status='EXECUTABLE_LOCKED',execution_ready=True,all_handlers_implemented=True,current_delivery='full numerical execution')
    cfg['seed_policy']['actual_seeds']=read(OUT/'preflight/SEED_SOURCE_REVIEW.json')['proposed_groups'];cfg['resolved_runtime']={k:runtime(k) for k in ['burgers','allen_cahn','multi']}
    cfg['engineering_gate']=read(OUT/'preflight/ENGINEERING_GATE.json');cfg['development_gates']=dev_summary()
    write(LOCK/'execution.json',cfg)
    import yaml
    for group,rt in cfg['resolved_runtime'].items():(LOCK/f'RESOLVED_RUNTIME_{group}.yaml').write_text(yaml.safe_dump(rt,allow_unicode=True,sort_keys=True),encoding='utf-8')
    write(LOCK/'SEED_REGISTRY.json',dict(groups=cfg['seed_policy']['actual_seeds'],replacement=False,review_sha256=canon_sha(OUT/'preflight/SEED_SOURCE_REVIEW.json')))
    runplan=[]
    for i in range(10):
        for group in ['burgers','allen_cahn']:
            seed=cfg['seed_policy']['actual_seeds'][group][i]
            for node in ['E1','E2']:runplan.append(dict(node=node,name=f'{group}_{seed}',group=group,seed=seed))
            for off in cfg['e3']['offsets']:
                for method in cfg['e3']['methods']:runplan.append(dict(node='E3',group=group,seed=seed,offset=off,method=method))
    runplan.extend(dict(node='E4C',group='multi',seed=s) for s in cfg['seed_policy']['actual_seeds']['multi'])
    runplan.extend(dict(node='E5C',n=n,m=m,pass_label=label) for n in cfg['e5']['n_state'] for m in cfg['e5']['m_residual'] for label in ['cold','warmup','steady_1','steady_2','steady_3'])
    write(LOCK/'RUN_PLAN.json',runplan)
    files=[p for folder in ['revision_week/phase2','src/saeps'] for p in (ROOT/folder).rglob('*.py')]
    files += [ROOT/'revision_week'/name for name in ['core.py','p1b_correct.py','p1b_onestep.py','p1c_development.py']]
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):canon_sha(p) for p in files}
    write(LOCK/'LOCK.json',dict(status='EXECUTABLE_LOCKED',source_commit=git('rev-parse','HEAD'),time_unix=time.time(),configuration_sha256=canon_sha(LOCK/'execution.json'),
        run_plan_sha256=canon_sha(LOCK/'RUN_PLAN.json'),source_hashes=hashes,all_groups_frozen_before_any_fresh_run=True,source_hash_mode='CRLF-normalized SHA256',
        named_streams={k:stream(k) for k in [cfg['e1']['bootstrap_stream'],*[f'scale/{n}/{m}' for n in cfg['e5']['n_state'] for m in cfg['e5']['m_residual']]]}))
    write(LOCK/'LOCK_RECORD.json',read(LOCK/'LOCK.json'))
    sync('Freeze Phase 2 executable, all 30 fresh seeds and conditional run plan')

def verify_lock():
    lock=read(LOCK/'LOCK.json')
    if canon_sha(LOCK/'execution.json')!=lock['configuration_sha256'] or canon_sha(LOCK/'RUN_PLAN.json')!=lock['run_plan_sha256']:raise RuntimeError('locked design changed')
    for name,digest in lock['source_hashes'].items():
        if canon_sha(ROOT/name)!=digest:raise RuntimeError('locked executable changed: '+name)
    if (git('status','--porcelain') and not all(line[3:].startswith(('revision_week/outputs/phase2_v1/','revision_week/outputs/phase2_v1/run_manifests/')) for line in git('status','--porcelain').splitlines())):raise RuntimeError('unexpected uncommitted change during confirmation')

def finish_node(node):
    costs();write(OUT/'node_status'/f'{node}.json',dict(status='PASSED',engineering_meaning='all planned positions terminal; scientific failures retained',time_unix=time.time()))
    sync('Record Phase 2 '+node+' terminal runs and measured costs')

def run():
    verify_lock();cfg=read(LOCK/'execution.json');config=LOCK/'execution.json';groups=cfg['seed_policy']['actual_seeds']
    for node in ['E1','E2','E4C','E5C','E3','E6P']:
        if (OUT/'node_status'/f'{node}.json').exists():continue
        verify_lock()
        if node=='E1':
            for i in range(10):
                for group in ['burgers','allen_cahn']:
                    seed=groups[group][i];task(node,f'{group}_{seed}',dict(kind='fresh',group=group,seed=seed),config,1800)
            e1_summary()
        elif node=='E2':
            for m,r in records('E1'):
                name=m['name'];job=dict(kind='locality',group=m['job']['group'],seed=m['job']['seed'],input=str(ROOT/m['raw_directory']))
                if r and r.get('binding_valid'):task(node,name,job,config,1440)
                else:skip(node,name,'E1_root_invalid',job)
        elif node=='E4C':
            for seed in groups['multi']:
                job=dict(kind='fresh',group='multi',seed=seed)
                if cfg['development_gates']['E4C_allowed']:task(node,f'multi_{seed}',job,config,1800)
                else:skip(node,f'multi_{seed}','gate_E_failed',job)
        elif node=='E5C':
            for n in cfg['e5']['n_state']:
                for m in cfg['e5']['m_residual']:
                    job=dict(kind='scale',n=n,m=m)
                    if cfg['development_gates']['E5AB_engineering_pass']:task(node,f'n{n}_m{m}',job,config,1200)
                    else:skip(node,f'n{n}_m{m}','E5AB_engineering_failed',job)
        elif node=='E3':
            summary=e1_summary();pdes={r['group']:r for r in summary['pdes']};local={m['name']:(m,r) for m,r in records('E2')}
            gates={}
            for group in ['burgers','allen_cahn']:
                ready=[r for m,r in local.values() if m['job']['group']==group and r and r.get('E3_ready')]
                e2=dict(roots_with_both_sides_micro_and_reverse_valid=len(ready),verified_bidirectional_offset=min((r['bidirectional_reach'] for r in ready),default=0))
                gates[group]=e3_allowed(pdes[group],e2,cfg['e3'])
            write(OUT/'E3_GATE.json',gates)
            for m,r in records('E1'):
                group=m['job']['group'];name=m['name'];lm,lr=local[name];job=dict(kind='one_step',group=group,seed=m['job']['seed'],input=str(ROOT/m['raw_directory']),locality=str(OUT/'tasks/E2'/name))
                if gates[group] and lr and lr.get('E3_ready'):task(node,name,job,config,720)
                else:skip(node,name,'gate_D_or_root_eligibility_failed',job)
        elif node=='E6P':
            if cfg['development_gates']['E6P_allowed']:task(node,'terminal',dict(kind='lanczos_practical'),config,900)
            else:
                for p in sorted((ROOT/'revision_week/outputs/day1/raw').glob('*.json')):skip(node,p.stem,'gate_F_oracle_effectivity_failed',dict(kind='lanczos_practical',center=p.stem))
        finish_node(node)
    from finalize_phase2 import finalize
    finalize();sync('Finalize Phase 2 all planned denominators, scientific gates and cost audit',full_tests=True)

def all_stages():
    if not (OUT/'preflight/SEED_AUDIT.json').exists():
        from seed_audit import main
        main()
    if not (OUT/'preflight/ROBUSTNESS_INPUT_AUDIT.json').exists():
        from review_inputs import main
        main()
    if not (OUT/'preflight/ENGINEERING_GATE.json').exists():
        sync('Checkpoint complete Phase 2 executable before final development verification',full_tests=True)
        # Final developer verification uses committed code. Earlier uncommitted debug
        # attempts retain hash-only provenance and are not the release acceptance run.
        for node,kind in [('E0','scalar_history'),('E4D','multi_history'),('E6D','lanczos_history')]:task(node,'verified01',dict(kind=kind),timeout=600)
        for cid in read(SPEC)['e5']['compact_centers']:
            src,_=task('E5AB',cid+'_export_verified01',dict(kind='compact_export',center=cid),timeout=60)
            for kind in ['compact_explicit','compact_mf']:task('E5AB',cid+'_'+kind+'_verified01',dict(kind=kind,center=cid,input=str(src/'state.pt')),timeout=120)
        for cid in ['burgers_55','allen_cahn_84']:
            task('PREFLIGHT',cid+'_solver_verified01',dict(kind='solver_audit',input=str(OUT/'tasks/E5AB'/f'{cid}_export_verified01/state.pt'),
                old_state=str(ROOT/'revision_week/outputs/phase1b_correction_v1/tasks'/f'{cid}_plus_start_strict')),timeout=600)
        write(OUT/'preflight/DEVELOPMENT_SELECTION.json',dict(historical={n:'verified01' for n in ['E0','E4D','E6D']},MF='verified01',explicit='verified01',solver='verified01',
            rationale='Final fixed-code acceptance; initial debug attempts are retained and not substituted for confirmation.'))
        prepare()
    freeze();run()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='all',choices=['all','prepare','freeze','run']);p.add_argument('--spec',default=str(SPEC));p.add_argument('--run-id',default='phase2_v1');a=p.parse_args()
    if Path(a.spec).resolve()!=SPEC.resolve() or a.run_id!='phase2_v1':raise ValueError('this executable implements only the audited Phase2 v1 specification')
    from execution import single_runner
    with single_runner():{'all':all_stages,'prepare':prepare,'freeze':freeze,'run':run}[a.action]()
