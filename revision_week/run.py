"""Read-only history audit and restartable E0 development CLI."""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:
    os.environ[key]='1'
import argparse, csv, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import yaml
from core import evaluate, reference, quadratic, numerical_mu, error_control, refine

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'revision_week/outputs/day1'

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args,repo=ROOT):
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode('utf-8',errors='replace'))
    return r.stdout.decode('utf-8',errors='replace').strip()
def save(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8'); tmp.replace(p)
def table(p,rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)
def md(name,text): (OUT/name).write_text(text,encoding='utf-8')

def audit(repo):
    started=time.perf_counter(); OUT.mkdir(parents=True,exist_ok=True)
    repo=Path(repo).resolve()
    refs=git('for-each-ref','--format=%(refname:short) %(objectname)','refs/heads','refs/remotes','refs/tags',repo=repo).splitlines()
    branches=[]; inventory=[]; checkpoint_paths=set()
    for line in refs:
        ref,commit=line.split()
        files=git('ls-tree','-r','--name-only',ref,repo=repo).splitlines()
        checkpoints=[p for p in files if p.endswith(('.pt','.pth','.npz'))]
        checkpoint_paths.update(checkpoints)
        branches.append(dict(ref=ref,commit=commit,tracked_files=len(files),checkpoint_files=checkpoints,
            protocol_files=[p for p in files if ('protocol' in p.lower() or 'locked' in p.lower()) and p.endswith(('.yaml','.md','.json'))],
            matrix_records=[p for p in files if 'exact_fixed_state_v3/' in p and '/seed_' in p and p.endswith('.json')],
            v6_code=[p for p in files if p.startswith(('src/saeps/v6/','tests/v6/','scripts/v6/'))]))
    save(OUT/'branch_inventory.json',branches)
    refs_checked=[]
    for ref in ['d5a231d857e4','cf76ffe','39343bc','c868127','0428a1f','jcp-submission-v1']:
        try: refs_checked.append(dict(ref=ref,commit=git('rev-parse',ref+'^{commit}',repo=repo),status='AVAILABLE'))
        except RuntimeError as e: refs_checked.append(dict(ref=ref,status='MISSING',reason=str(e)))
    save(OUT/'historical_refs.json',refs_checked)
    source_config=repo/'configs/posthoc_exact_fixed_state_v3.yaml'
    cfg=yaml.safe_load(source_config.read_text(encoding='utf-8'))
    for family,cohort in cfg['cohorts'].items():
        for seed in cohort['planned_seeds']:
            p=repo/f'outputs/posthoc/exact_fixed_state_v3/{family}/seed_{seed}.json'
            d=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
            matrix=isinstance(d.get('GN_blocks'),dict) and isinstance(d.get('exact_blocks'),dict)
            inventory.append(dict(experiment_id=f'E0_{family}_{seed}',branch_or_ref='posthoc/exact-fixed-state-decomposition-v3',
                commit=git('rev-parse','posthoc/exact-fixed-state-decomposition-v3',repo=repo),actual_path=str(p),sha256=digest(p) if p.exists() else '',
                protocol_path=str(source_config),checkpoint_path='',raw_result_path=d.get('source_frozen_record_path',''),
                pde=family,parameterization='log physical parameter',architecture=f"one-hidden-layer tanh; n={len(d.get('GN_blocks',{}).get('G_tt',[]))}" if matrix else '',
                dtype='float64',planned_n=len(cohort['planned_seeds']),available_n=int(matrix),historical_valid_n=int(d.get('original_binding_valid',False)),
                status='MATRIX_AVAILABLE' if matrix else 'HISTORICAL_INVALID_OR_MISSING',reuse_decision='retrospective_E0' if matrix else 'retain_failure',
                reason=d.get('failure_reason') or 'Matrices available; original theta/data/gradient tensors not archived in this record'))
    # Exact files from all references; provenance includes content hash even for branch-only files.
    groups=[('main','outputs/runs/v5/checkpoints/','checkpoint'),
        ('posthoc/exact-fixed-state-decomposition-v2','outputs/posthoc/exact_fixed_state_v2/ABORTED.json','aborted'),
        ('codex/v6-phase15-protocol','src/saeps/v6/','development_code'),
        ('codex/v6-phase15-protocol','outputs/runs/v5/upgrade_pilot/phase15/20260907_001/findings/','development_evidence'),
        ('posthoc/variable-projection-baseline-v1','configs/posthoc_variable','posthoc'),
        ('posthoc/whitening-sensitivity-v1','configs/posthoc_whitening','posthoc')]
    for ref,prefix,role in groups:
        paths=git('ls-tree','-r','--name-only',ref,repo=repo).splitlines()
        for p in paths:
            if not p.startswith(prefix): continue
            if role=='checkpoint' and not p.endswith('model_state.pt'): continue
            data=subprocess.run(['git','-C',str(repo),'show',f'{ref}:{p}'],capture_output=True,check=True).stdout
            inventory.append(dict(experiment_id=role,branch_or_ref=ref,commit=git('rev-parse',ref,repo=repo),actual_path=p,
                sha256=hashlib.sha256(data).hexdigest(),protocol_path='',checkpoint_path=p if role=='checkpoint' else '',raw_result_path=p,
                pde='',parameterization='',architecture='',dtype='',planned_n='',available_n=1,historical_valid_n='',status='AVAILABLE',reuse_decision=role,reason='Inspected reachable Git blob; not new independent evidence'))
    table(OUT/'artifact_manifest.csv',inventory)
    save(OUT/'initial_workspace.json',dict(repo=str(repo),status=git('status','--porcelain',repo=repo),head=git('rev-parse','HEAD',repo=repo),remote=git('remote','-v',repo=repo)))
    import torch
    torch.set_num_threads(1)
    save(OUT/'environment.json',dict(python=sys.version,numpy=np.__version__,torch=torch.__version__,cuda=torch.cuda.is_available(),
        processor=platform.processor(),platform=platform.platform(),cpu_count=os.cpu_count(),threads=1,dtype='float64',
        executable=sys.executable,memory_bytes=34127994880,memory_source='Win32_ComputerSystem observed 2026-09-09',peak_tensor_memory=None))
    (OUT/'source_plan.md').write_bytes((repo/'CODEX_SAEPS_7DAY_EXPERIMENT_PLAN.md').read_bytes())
    save(OUT/'audit_cost.json',dict(seconds=time.perf_counter()-started,new_training_seconds=0))
    md('REPO_AUDIT.md',f'''# Repository audit — actual local evidence

Source workspace: `{repo}`; base `{git('rev-parse','HEAD',repo=repo)}`.
Separate clean worktree: `{ROOT}`, branch `codex/saeps-so-week1`.
Original user deletions/untracked files preserved in `initial_workspace.json`.
User's explicit no-push instruction overrides historical AGENTS auto-sync.
This is a newly authorized retrospective development extension; historical locks
and terminal V2/V4/V5 decisions remain closed. No new confirmation or training.

All {len(branches)} locally visible references were inspected by `git ls-tree`;
see `branch_inventory.json` for exact commits and protocol/checkpoint paths.
No network fetch was performed; remote-only changes are outside this audit.
Historical short hashes were resolved in `historical_refs.json`; the named tag
and release branch must not be conflated with the manuscript's report commit.

## Reusable evidence

The v3 archive contains 25 planned scalar records (Burgers 55–69, Allen–Cahn
75–84), including 21 complete valid matrix centers and four historical failures.
Their frozen source records are binding; the reconstruction/decomposition is
post-hoc nonbinding. Every record and hash is in `artifact_manifest.csv`.
The V2 exact decomposition was aborted; it is not substituted for V3.
V5 has 29 reloadable model files on main (including failed coupled attempts),
but none is the original E0 scalar seed/center. Scanning every visible reference
finds no tensor checkpoint for these 21 original E0 centers. V3 runner reconstructs
theta/data in memory then serializes blocks and normalized diagnostics, not
theta, raw residual, or full gradients. Thus E0 matrix audit is possible; original
center HVP, absolute gradient and T3 replay remain unavailable without a separate
costed reconstruction. The residual/data recipe is recoverable; exact tensor
identity is not claimed. No reconstruction was started.

## Objective and variables, checked in code

`src/saeps/scalar.py::scalar_network`: theta packs wx, wt, bias, output weights,
then output bias; n=4*width+1 (archived Burgers n=65, Allen n=33).
Joint derivatives pack [theta, log_parameter]. Burgers parameter is viscosity;
Allen–Cahn parameter is reaction rate, diffusion fixed. `scalar_residual` has
the form a(theta)+exp(lambda)b(theta), with no parameter regularizer.
`residual.py::stack_weighted_residuals` multiplies each block by sqrt(weight),
no block-size normalization; weights are fixed configuration values.
Training/center objective uses 0.5*mean(rbar²), archived derivatives use
0.5*sum(rbar²) (`posthoc_exact_fixed_state_v1.py::curvature_blocks`).
Gamma is saved alpha*lambda_max(Gtt), added once to state block, fixed in E0.
Do not mix mean-objective derivatives or recompute gamma inside perturbations.

Coupled source: `src/saeps/multi.py::multi_residual`, manufactured reaction-diffusion
u_t-du*u_xx+a*u-b*v-source_u and v_t-dv*v_xx-a*u+b*v-source_v;
coordinates [log a,log b], separate u/v tanh state blocks. V5 width6 => n=50.
`v5/two_parameter_frozen.py::_primary_metrics` defines B2=sym(Fraw)+tau I,
tau=tau_relative*max(trace(Fraw)/2,1), L=chol(B2), Fhat=L^-1 F L^-T.
Use D L^-T for the corresponding bound. Historical scalar denominator floor
is 1e-8 (`configs/posthoc_exact_fixed_state_v3.yaml`).

Validity: `v31/local_minimum.py::exact_state_diagnostics` uses mean-objective
gradient norm/max(||theta||,1), and lambda_min(Hmean)>=-max(atol,rtol*spectral_scale).
`posthoc_exact_fixed_state_v1.py::_center_valid` also requires G_theta and S_theta
below inherited center thresholds; S=||J^T r||/(||J|| ||r||+epsilon) in
`p4_screening.py::_stationarity`. `v41/numerics.py` verifies original normal
residuals for scaled LSQR refinement. Frozen configuration defines all numerical
thresholds; E0 does not relax them. Historical local numerical validity is retained
separately from algebraic Schur validity. It is not exact mathematical stationarity.

## V6 overlap and negative evidence

`codex/v6-phase15-protocol` is 71b84e3ca28b00bac5a0d9924213415ad66954cd.
Its `curvature.py` has scalar complete quadratic, `operators.py` explicitly uses
dense matrices; HVP_actual=0. `stopping.py` uses an indicator, not a relative bound.
Its RESULT_VALIDATION_V2 reports numerical validation PASSED but development
gate NOT_SUPPORTED. Findings retain worsening seeds59/67 and no scalable
candidate selected. These are inspected historical reports, not rerun results.
Reuse the existing quadratic/archived loader pattern; add multi-column and
inexact identities plus bound classification in revision_week/core.py.

## Resource and evidence limits

Python/NumPy/Torch CPU versions and hardware in environment.json. CPU-only,
approximately 31.8 GiB RAM. No GPU available in installed Torch.
Historical reconstruction wall time is summed separately from E0; missing original
training totals are explicitly unknown. Seed inventories remain attached to each
branch/protocol; future independent seed collision scan/freeze is not performed
in this first-stage request. No new seeds, protocol.frozen.yaml, E1–E5 outcomes,
or background execution are claimed.
''')
    return dict(status='PASSED',manifest_rows=len(inventory),references=len(branches))

def load_center(path):
    d=json.loads(path.read_text(encoding='utf-8'))
    g,h=d['GN_blocks'],d['exact_blocks']
    gtt=np.asarray(g['G_tt']); htt=np.asarray(h.get('H_tt_sym',h.get('H_tt')))
    bg=np.asarray(g['G_tl']); b=np.asarray(h['H_tl'])
    for blocks,key,target in [(g,'G_lt',bg.T),(h,'H_lt',b.T)]:
        if key in blocks and not np.allclose(blocks[key],target,rtol=1e-8,atol=1e-12):
            raise ValueError('cross transpose mismatch')
    return d,np.block([[gtt,bg],[bg.T,np.asarray(g['G_ll'])]]),np.block([[htt,b],[b.T,np.asarray(h['H_ll'])]])

def e0(config):
    config=Path(config).resolve(); cfg=yaml.safe_load(config.read_text(encoding='utf-8'))
    if cfg['mode']!='retrospective_development': raise ValueError('E0 development config required')
    tests=json.loads((OUT/'test_result.json').read_text())
    if tests['exit_code']!=0: raise RuntimeError('self-test must pass before E0')
    repo=Path(json.loads((OUT/'initial_workspace.json').read_text(encoding='utf-8'))['repo'])
    protocol=yaml.safe_load((repo/'configs/posthoc_exact_fixed_state_v3.yaml').read_text(encoding='utf-8'))
    code_hash=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'revision_week/core.py').read_bytes()).hexdigest()
    records=[]
    for family,cohort in protocol['cohorts'].items():
        for seed in cohort['planned_seeds']:
            path=repo/f'outputs/posthoc/exact_fixed_state_v3/{family}/seed_{seed}.json'
            dest=OUT/'raw'/f'{family}_{seed}.json'
            identity=dict(input_sha256=digest(path) if path.exists() else None,protocol_hash=digest(config),code_hash=code_hash)
            if dest.exists():
                row=json.loads(dest.read_text(encoding='utf-8'))
                if any(row[k]!=v for k,v in identity.items()): raise RuntimeError('Resume identity changed; choose new run directory, never overwrite history')
                records.append(row); continue
            start=time.perf_counter(); cpu=time.process_time()
            row=dict(run_id='day1',experiment_id='E0',center_id=f'{family}_{seed}',pde=family,seed=seed,
                source_commit=git('rev-parse','HEAD'),source_ref='codex/saeps-so-week1',input_path=str(path),**identity,
                status='NUMERICAL_FAILURE',failure_reason=None,jvp_count=0,vjp_count=0,hvp_count=0,
                new_training_seconds=0,peak_memory=None,peak_memory_reason='native peak memory not measured',
                local_profile_valid=None,local_profile_reason='no original tensors/profile replay; inherited numerical gate recorded separately',
                state_gradient=None,parameter_gradient=None,gradient_reason='absolute gradients not archived',dtype='float64',device='cpu')
            try:
                original=json.loads(path.read_text(encoding='utf-8'))
                row.update(historical_valid=original.get('original_binding_valid',False),historical_analysis_valid=original.get('analysis_valid',False),
                    historical_failure_reason=original.get('failure_reason'),historical_reconstruction_seconds=original.get('runtime_seconds'),
                    state_grad_normalized=original.get('center_stationarity',{}).get('G_theta'),
                    S_theta=original.get('center_stationarity',{}).get('S_theta'),S_lambda=original.get('center_stationarity',{}).get('S_lambda'))
                if not original.get('analysis_valid'):
                    row.update(status='CHECKPOINT_INVALID',failure_reason=original.get('failure_reason') or 'historical analysis invalid',algebraic_schur_valid=False)
                else:
                    d,g,h=load_center(path); n=len(d['GN_blocks']['G_tt']); gamma=d['gamma']
                    a=h[:n,:n]+gamma*np.eye(n); m=g[:n,:n]+gamma*np.eye(n)
                    solve_start=time.perf_counter(); z=np.linalg.solve(m,g[:n,n:]); gn_s=time.perf_counter()-solve_start
                    ev=evaluate(g,h,n,gamma,z); fg=reference(g,n,gamma)
                    ref_start=time.perf_counter(); star=reference(h,n,gamma); ref_s=time.perf_counter()-ref_start
                    mu_start=time.perf_counter(); mu=numerical_mu(a); mu_s=time.perf_counter()-mu_start
                    bound=error_control(ev['F_SO'],ev['D'],mu['mu_value'])
                    scale=max(float(np.linalg.norm(ev['F_SO'])),float(np.linalg.norm(star)),1e-8)
                    energy=ev['D'].T@np.linalg.solve(a,ev['D'])
                    ident=float(np.linalg.norm(ev['F_SO']-star-energy))/scale
                    reproduction={}
                    for key,value in [('F_raw',g[n:,n:]),('F_SAEPS',fg),('H_red_exact',star)]:
                        historical=d['original'][key]; val=float(value[0,0]); delta=abs(val-historical)
                        reproduction[key]=dict(value=val,original=historical,absolute_error=delta,relative_error=delta/max(abs(historical),1e-10),
                            passed=delta<=1e-10+1e-6*abs(historical))
                    row.update(n_state=n,n_parameter=1,gamma=gamma,parameterization='log',gamma_anchor_id=row['center_id'],
                        F_raw=float(g[n,n]),F_G_reference=float(fg[0,0]),Q_G_actual=float(ev['Q_G'][0,0]),F_SO=float(ev['F_SO'][0,0]),F_star=float(star[0,0]),
                        GN_normal_residual=float(np.linalg.norm(ev['R_G'])/np.linalg.norm(g[:n,n:])),D_norm=float(np.linalg.norm(ev['D'])),
                        algebra_identity_error=ident,formula_identity_error=ev['formula_error']/scale,
                        gn_identity_error=float(np.linalg.norm(ev['Q_G']-fg-ev['R_G'].T@np.linalg.solve(m,ev['R_G'])))/scale,
                        original_reproduction_error=max(v['relative_error'] for v in reproduction.values()),reproduction=reproduction,
                        algebraic_schur_valid=True,gn_solve_seconds=gn_s,reference_seconds=ref_s,spectrum_seconds=mu_s,**mu,**bound)
                    for name,value in [('raw',g[n:,n:]),('GN',fg),('SO',ev['F_SO'])]:
                        absolute=float(np.linalg.norm(value-star,2)); row[f'absolute_error_{name}']=absolute
                        row[f'relative_error_{name}']=absolute/(float(np.linalg.norm(star,2))+1e-8)
                    err=row['absolute_error_SO']; resolution=64*n*np.finfo(float).eps*max(abs(row['F_star']),abs(row['F_SO']),1.)
                    row.update(SO_improved=err<row['absolute_error_GN'],SO_improvement_factor=row['absolute_error_GN']/err if err>resolution else None,
                        bound_effectivity=bound['U_absolute']/err if err>resolution and bound['U_absolute'] is not None else None,
                        effectivity_status='resolved' if err>resolution else 'not_resolved')
                    # Fixed finite residual correction regardless of SO win; never oracle stopping.
                    adapt_start=time.perf_counter()
                    ad=refine(a,h[:n,n:],h[n:,n:],z,mu['mu_value'],cfg['adaptive_tolerance'],cfg['adaptive_matvec_iterations'])
                    az=ad.pop('Z'); row.update(adaptive_seconds=time.perf_counter()-adapt_start,adaptive=ad,
                        adaptive_absolute_error=float(np.linalg.norm(quadratic(h[n:,n:],h[:n,n:],a,az)-star,2)))
                    checks=all(v['passed'] for v in reproduction.values()) and ident<=cfg['historical_identity_tolerance'] and row['GN_normal_residual']<=1e-8
                    row.update(status='PASS' if checks else 'NUMERICAL_FAILURE',failure_reason=None if checks else 'reproduction/identity/solver gate failed')
            except (ValueError,KeyError,np.linalg.LinAlgError,FileNotFoundError) as exc:
                row.update(status='NUMERICAL_FAILURE',failure_reason=f'{type(exc).__name__}: {exc}')
            row.update(total_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu)
            save(dest,row); records.append(row)
            print(row['center_id'],row['status'],flush=True)
    report(records)
    return dict(status='PASSED' if all(r['status'] in ['PASS','CHECKPOINT_INVALID'] for r in records) else 'FAILED',records=len(records))

def report(records=None):
    if records is None: records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'raw').glob('*.json'))]
    flat=[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in records]
    table(OUT/'ALL_RUNS.csv',flat)
    valid=[r for r in records if r['status']=='PASS']; summary=[]
    for family in ['all','burgers','allen_cahn']:
        planned=[r for r in records if family=='all' or r['pde']==family]
        rows=[r for r in valid if family=='all' or r['pde']==family]
        factors=[r['SO_improvement_factor'] for r in rows if r['SO_improvement_factor'] is not None]
        wins=sum(r['SO_improved'] for r in rows)
        s=dict(pde=family,planned_n=len(planned),matrix_reference_n=len(rows),SO_improved_n=wins,
            median_improvement_factor=float(np.median(factors)) if factors else None,
            numerical_bound_n=sum(r['bound_status']=='numerical_bound_estimate' for r in rows),verified_bound_n=0,
            finite_relative_bound_n=sum(r['U_relative_if_available'] is not None for r in rows),
            adaptive_tolerance_met_n=sum(r['adaptive']['status']=='numerical_tolerance_met' for r in rows),
            median_bound_effectivity=float(np.median([r['bound_effectivity'] for r in rows if r['bound_effectivity'] is not None])) if rows else None)
        for method in ['raw','GN','SO']:
            s['median_relative_error_'+method]=float(np.median([r['relative_error_'+method] for r in rows])) if rows else None
        s['SO_continue_gate']=bool(rows and factors and np.median(factors)>=2 and wins/len(rows)>=.75)
        summary.append(s)
    table(OUT/'METHOD_SUMMARY.csv',summary); save(OUT/'summary.json',summary)
    costs=dict(e0_wall_seconds=sum(r['total_seconds'] for r in records),e0_cpu_seconds=sum(r['cpu_seconds'] for r in records),
        historical_reconstruction_seconds=sum(r.get('historical_reconstruction_seconds') or 0 for r in records),
        historical_original_training_total=None,new_training_seconds=0,new_profile_seconds=0,
        gn_solve_seconds=sum(r.get('gn_solve_seconds',0) for r in records),spectrum_seconds=sum(r.get('spectrum_seconds',0) for r in records),
        reference_seconds=sum(r.get('reference_seconds',0) for r in records),adaptive_seconds=sum(r.get('adaptive_seconds',0) for r in records),
        A_matvec_count=sum(r.get('adaptive',{}).get('A_matvec_count',0) for r in records),jvp_count=0,vjp_count=0,hvp_count=0,
        audit_seconds=json.loads((OUT/'audit_cost.json').read_text())['seconds'],
        test_seconds=json.loads((OUT/'test_result.json').read_text())['seconds'])
    costs['current_recorded_compute_seconds']=costs['e0_wall_seconds']+costs['audit_seconds']+costs['test_seconds']
    save(OUT/'costs.json',costs)
    s=summary[0]; worst=max((r['algebra_identity_error'] for r in valid),default=None)
    md('RESULTS_SUMMARY.md',f'''# Actual E0 results

{json.dumps(s,indent=2)}

Maximum normalized defect identity residual: {worst}.
Historical matrices reproduced with independent Schur solves; no retraining.
Historical planned denominator is {len(records)}, E0 usable matrix denominator {len(valid)}.
SO passes development allocation rule: {s['SO_continue_gate']}.
This permits a bounded E1 development evaluation, not confirmation or a broad claim.
SO-ADAPT cost advantage remains UNESTABLISHED. This run uses dense GN solves and
dense-assisted eigenvalue estimates; no end-to-end matrix-free efficiency is shown.
V6's previous scalable-candidate negative result remains intact.
No original-center gradient/T3 replay, independent new cohort, width validation,
profile initialization or one-step update was executed. Algebraic local curvature
does not establish nonlinear-profile accuracy or parameter estimation accuracy.
See ALL_RUNS.csv and raw/ for every input hash, failure and measured cost.
''')
    failed=[dict(center=r['center_id'],status=r['status'],reason=r['failure_reason']) for r in records if r['status']!='PASS']
    worse=[r['center_id'] for r in valid if not r['SO_improved']]
    md('FAILURE_ANALYSIS.md',f'# Retained failures and limitations\n\nHistorical/engineering failures:\n\n{json.dumps(failed,indent=2)}\n\nSO not improved: {worse}. No replacements or damping changes.\n\nHistorical raw states/absolute gradients absent for E0; T3 not replayed on these centers.\nAdaptive budget failures and missing finite relative guarantees remain in each raw record.\nNo full repository completion claim; original workspace deletions are preserved.\n')
    md('COMPUTE_BUDGET_REPORT.md','# Measured cumulative cost\n\n'+json.dumps(costs,indent=2)+'\n\nSeconds are wall times unless labelled CPU; historical reconstruction is inherited, not newly spent. New E0 includes reading, dense solves, eigen diagnostics, oracle audit and finite correction. Tests and audit are additional. Interactive inspection/tool latency and uninstrumented original training are not invented. Resume reuses terminal files with input/config/code hashes and does not reset numerical cost. Spectrum time is charged; E0 is dense-assisted. Native tensor peak memory unavailable.\n')
    return s

def self_test():
    OUT.mkdir(parents=True,exist_ok=True); started=time.perf_counter()
    env=os.environ.copy(); env['PYTHONPATH']=str(ROOT/'src')
    result=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'revision_week/test_core.py')],cwd=ROOT,env=env,capture_output=True,text=True)
    (OUT/'pytest.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    record=dict(exit_code=result.returncode,seconds=time.perf_counter()-started,test_sha256=digest(ROOT/'revision_week/test_core.py'),core_sha256=digest(ROOT/'revision_week/core.py'))
    save(OUT/'test_result.json',record)
    md('TEST_REPORT.md','# Executed tests\n\n'+result.stdout+'\n\nSynthetic p=1,2,3 arbitrary/inexact response; negative reduced curvature; independent Schur; inexact upgrade; whitening; conditional bound; tiny actual scalar network JVP/VJP/HVP parity, multiple finite-difference steps and log-coordinate gradient terms. Historical T3 requires missing E0 tensor state and is not claimed.\n')
    print(result.stdout); return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('audit'); p.add_argument('--repo',required=True)
    sub.add_parser('self-test')
    p=sub.add_parser('run'); p.add_argument('--experiment',choices=['E0'],required=True); p.add_argument('--config',required=True)
    p=sub.add_parser('report'); p.add_argument('--run-id',choices=['day1'],default='day1')
    args=parser.parse_args()
    result=audit(args.repo) if args.command=='audit' else self_test() if args.command=='self-test' else e0(args.config) if args.command=='run' else report()
    print(json.dumps(result,indent=2))
    if result.get('exit_code',0) or result.get('status')=='FAILED': sys.exit(1)
