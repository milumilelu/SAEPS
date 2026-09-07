"""Frozen sequential Phase 1.5 historical-matrix runner and audit writer."""
import os
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[_name]='1'
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
import numpy as np
from saeps.v6.operators import load_blocks, DenseOperators
from saeps.v6.curvature import oracle, curvature
from saeps.v6.preconditioners import Exact, LowRank
from saeps.v6.pcg import trajectory
from saeps.v6.experiment import candidate_run

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/'configs/v6/development/phase15.json'
AUTH=ROOT/'configs/v6/development/phase15_execution_001.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2,allow_nan=False); f.write('\n')
def pack(path,obj):
    with path.open('xb') as f:
        f.write(gzip.compress(json.dumps(obj,allow_nan=False,separators=(',',':')).encode(),mtime=0))
def unpack(path): return json.loads(gzip.decompress(path.read_bytes()))


def environment():
    output=io.StringIO(); old=sys.stdout
    try:
        sys.stdout=output; np.show_config()
    finally: sys.stdout=old
    return {'hardware':platform.platform(), 'processor':platform.processor(), 'dtype':'float64',
            'python':platform.python_version(),'numpy':np.__version__, 'numpy_blas_config':output.getvalue(),
            'thread_environment':{n:os.environ[n] for n in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS')},
            'JVP_actual':0,'VJP_actual':0,'HVP_actual':0,'peak_native_memory':None,
            'peak_native_memory_reason':'not reliably measured; dense allocated bytes recorded separately'}


def authorization():
    config=read(CFG); inventory=read(ROOT/'configs/v6/development/phase15_inputs.json')
    for row in inventory['records']:
        assert sha(ROOT/row['path'])==row['sha256'],row['path']
    files=[CFG,ROOT/'configs/v6/development/phase15_inputs.json',ROOT/'docs/v6/PHASE15_EXECUTION_PROTOCOL.md']
    files+=sorted((ROOT/'src/saeps/v6').glob('*.py'))+sorted((ROOT/'scripts/v6').glob('*.py'))+sorted((ROOT/'tests/v6').glob('*.py'))
    data={'execution_id':'20260907_001','authorization':'User: 开始运行 (2026-09-07)',
          'scientific_execution_authorized':True,'confirmation_authorized':False,
          'scope':config['scope'],'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'files':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
          'timestamp':datetime.now(timezone.utc).isoformat(),'environment':environment(),
          'initial_dirty_files':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
          'implementation_notes':'B trajectories reused as fixed/adaptive prefixes in C; prefix selection reads indicator only. Oracle runs after timed repeats. No candidate setup sharing across starts; same RNG. Native triangular systems solved with NumPy solve.',
          'timing_repeats':config['timing']}
    write(AUTH,data); print('AUTHORIZATION WRITTEN',AUTH)


def context():
    config=read(CFG); auth=read(AUTH)
    assert auth['scientific_execution_authorized'] and not auth['confirmation_authorized']
    for name,digest in auth['files'].items(): assert sha(ROOT/name)==digest,name
    inventory=read(ROOT/'configs/v6/development/phase15_inputs.json')['records']
    for r in inventory: assert sha(ROOT/r['path'])==r['sha256'],r['path']
    base=ROOT/config['output_root']/auth['execution_id']
    return config,auth,inventory,base


def common(source,auth):
    return {'schema_version':1,'execution_id':auth['execution_id'],'authorization_sha256':sha(AUTH),
            'git_commit':auth['git_commit'],'config_sha256':sha(CFG),
            'source':source,'split':'HISTORICAL_DEVELOPMENT','dtype':'float64',
            'training':None,'profile':None,'not_run_reason':'archived matrix-only study',
            'environment_reference':'configs/v6/development/phase15_execution_001.json'}


def spectrum(blocks):
    g,h,b,c,gll,hll,gamma=blocks; ref=oracle(*blocks)
    m,a=ref['M'],ref['A']; l=np.linalg.cholesky(m)
    left=np.linalg.solve(l,a); w=np.linalg.solve(l,left.T).T
    ev,q=np.linalg.eigh((w+w.T)/2)
    d=c-a@ref['z0']; coeff=q.T@np.linalg.solve(l,d)
    energy=coeff**2/ev; total=float(sum(energy)); weights=energy/total if total>1e-25 else None
    delta_fix=float(gll-hll); delta_relax=float(b@ref['z0']-c@ref['zstar'])
    ops=DenseOperators(g,h,gamma)
    run=trajectory(ops,c,hll,ref['z0'],Exact(m),5)
    ratios=[]; kappa=float(ev[-1]/ev[0]); rate=(np.sqrt(kappa)-1)/(np.sqrt(kappa)+1)
    for row in run['rows']:
        z=np.array(row['z']); gap=float((z-ref['zstar'])@a@(z-ref['zstar']))
        if row['step'] in (0,1,3,5):
            ratios.append({'step':row['step'],'energy_ratio':gap/total if total>1e-25 else None,
                           'classical_upper_bound':min(1.,float(4*rate**(2*row['step']))),
                           'absolute_energy_gap':gap})
    k0=curvature(hll,c,ref['z0'],a@ref['z0'])
    identity=abs(k0-ref['reference']-total)/max(abs(k0),abs(ref['reference']),1e-8)
    defect_identity=np.linalg.norm(d-((c-b)-(h-g)@ref['z0']))/max(np.linalg.norm(c),1e-8)
    decomposition=abs(ref['gn']-ref['reference']-delta_fix+delta_relax)/max(abs(ref['reference']),1e-8)
    assert max(identity,defect_identity,decomposition)<1e-8
    return {'status':'PASS','failure_reason':None,'gamma':gamma,'n_theta':len(g),'p':1,
            'eigenvalues':ev.tolist(),'condition_number':kappa,'relative_residual_Hessian_norm':float(max(abs(ev-1))),
            'outliers':{str(t):{'count':int(sum(abs(ev-1)>t)),
                               'energy_fraction':float(sum(weights[abs(ev-1)>t])) if weights is not None else None} for t in (.1,.5)},
            'defect_energy_by_direction':energy.tolist(),'energy_weights':weights.tolist() if weights is not None else None,
            'directions_for_energy':{str(t):int(np.searchsorted(np.cumsum(np.sort(weights)[::-1]),t)+1) if weights is not None else None for t in (.5,.9,.99)},
            'delta_fix':delta_fix,'delta_relax':delta_relax,
            'chi':abs(delta_fix-delta_relax)/(abs(delta_fix)+abs(delta_relax)+1e-8),
            'gn_error':ref['gn_error'],'K0_error':abs(k0-ref['reference'])/(abs(ref['reference'])+1e-8),
            'reference':ref['reference'],'pcg_bound_comparison':ratios,
            'algebra_checks':{'gap_identity':identity,'defect_identity':float(defect_identity),'signed_decomposition':decomposition},
            'pcg_five_step_status':run['status']}


def phase_a():
    config,auth,inventory,base=context(); folder=base/'A'; folder.mkdir(parents=True,exist_ok=False)
    results=[]
    for source in inventory:
        record=read(ROOT/source['path']); result=common(source,auth)
        tick=perf_counter()
        if not source['analysis_valid']:
            result.update(status='CHECKPOINT_INVALID',failure_reason=source['failure_reason'])
        else:
            try: result.update(spectrum(load_blocks(record)))
            except (ValueError,AssertionError,np.linalg.LinAlgError) as exc:
                result.update(status='NUMERICAL_FAILURE',failure_reason=str(exc))
        result['oracle_audit_seconds']=perf_counter()-tick
        name=f"{source['benchmark']}_{source['seed']}.json"; write(folder/name,result)
        results.append({'file':name,'sha256':sha(folder/name),'status':result['status']})
    passed=all(r['status'] in ('PASS','CHECKPOINT_INVALID') for r in results)
    write(folder/'manifest.json',{'status':'PASSED' if passed else 'FAILED','records':results,
                                 'counts':dict(Counter(r['status'] for r in results))})
    print('A',passed,Counter(r['status'] for r in results))
    if not passed: raise SystemExit(1)


def plan(config):
    for candidate in config['candidates']:
        for rank in candidate['ranks']:
            for seed in (config['sketch_seeds'] if candidate['randomized'] else [None]):
                for start in ('zero','gn'):
                    yield candidate,rank,seed,start


def measured_case(blocks,candidate,rank,seed,start,config):
    runs=[]; valid_runs=[]
    for repeat in range(1+config['timing']['measured_repeats']):
        run=candidate_run(blocks,candidate['name'],rank,seed,start,config)
        if repeat: runs.append(run)
    first=runs[0]
    if not first['rows']: return first
    # Counters and numerical trajectories must reproduce; timings are separate.
    for run in runs[1:]:
        assert run['status']==first['status'] and len(run['rows'])==len(first['rows'])
        for x,y in zip(first['rows'],run['rows']):
            assert x['counts']==y['counts'] and np.allclose(x['z'],y['z'],rtol=1e-10,atol=1e-12)
    tick=perf_counter(); ref=oracle(*blocks); a=ref['A']; p=first.pop('preconditioner')
    pm=p.matrix(); l=np.linalg.cholesky(pm); left=np.linalg.solve(l,a)
    w=np.linalg.solve(l,left.T).T; pe=np.linalg.eigvalsh((w+w.T)/2)
    checks=[]; gamma=blocks[-1]
    for vector in (blocks[3],np.ones(len(a))):
        applied=p(vector); den=max(np.linalg.norm(applied),1e-30)
        checks.append({'relative_inverse_residual':float(np.linalg.norm(pm@applied-vector)/max(np.linalg.norm(vector),1e-8)),
                       'woodbury_relative_difference':float(np.linalg.norm(applied-p.woodbury(vector))/den) if isinstance(p,LowRank) else None})
    cache=first.pop('GN_cache')
    if cache:
        z0=cache['z']; g,h,b,c,_,_,_=blocks
        first['initial_GN_dense_difference']=float(np.linalg.norm(z0-ref['z0'])/max(np.linalg.norm(ref['z0']),1e-8))
        first['GN_cache']={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in cache.items()}
    for index,row in enumerate(first['rows']):
        z=np.array(row.pop('z')); e=z-ref['zstar']; energy=float(e@a@e)
        defect=blocks[3]-a@z
        row['oracle']={'relative_error':abs(row['K']-ref['reference'])/(abs(ref['reference'])+1e-8),
                       'energy_gap':energy,'defect_energy':float(defect@np.linalg.solve(a,defect)),
                       'identity_relative_error':abs(row['K']-ref['reference']-energy)/max(abs(row['K']),abs(ref['reference']),1e-8),
                       'indicator_to_gap':row['eta']/energy if energy>1e-25 else None}
        row['timing_repeats']={key:[r['rows'][index][key] for r in runs] for key in ('cold_seconds','incremental_seconds','verification_seconds')}
        row['cold_seconds']=float(np.median(row['timing_repeats']['cold_seconds']))
        row['incremental_seconds']=float(np.median(row['timing_repeats']['incremental_seconds']))
    first['component_timing_repeats']={key:[r[key] for r in runs] for key in ('initial_GN_seconds','preconditioner_setup_seconds','setup_defect_seconds','cross_block_access_seconds')}
    first['oracle_reference']=ref['reference']; first['gn_error']=ref['gn_error']
    first['oracle_preconditioned_spectrum']=pe.tolist(); first['preconditioner_checks']=checks
    first['oracle_validation_seconds']=perf_counter()-tick
    first['target_hits']={str(t):next(({'step':r['step'],'counts':r['counts'],'cold_seconds':r['cold_seconds'],
                                      'incremental_seconds':r['incremental_seconds']} for r in first['rows'] if r['oracle']['relative_error']<=t),None)
                          for t in config['start_comparison']['oracle_error_targets']}
    return first


def phase_b():
    config,auth,inventory,base=context()
    assert read(base/'A/manifest.json')['status']=='PASSED'
    folder=base/'B'; folder.mkdir(exist_ok=False); entries=[]
    for source in inventory:
        original=read(ROOT/source['path'])
        blocks=load_blocks(original) if source['analysis_valid'] else None
        for candidate,rank,seed,start in plan(config):
            result=common(source,auth)
            result.update(candidate=candidate['name'],rank_requested=rank,sketch_seed=seed,start=start,budgets=candidate['budgets'])
            if blocks is None:
                result.update(status='CHECKPOINT_INVALID',failure_reason=source['failure_reason'],rows=[])
            else:
                try: result.update(measured_case(blocks,candidate,rank,seed,start,config))
                except (ValueError,AssertionError,np.linalg.LinAlgError,FloatingPointError) as exc:
                    result.update(status='NUMERICAL_FAILURE',failure_reason=f'{type(exc).__name__}: {exc}',rows=[])
            name=f"{source['benchmark']}_{source['seed']}_{candidate['name']}_{rank}_{seed}_{start}.json.gz"
            pack(folder/name,result); entries.append({'file':name,'sha256':sha(folder/name),'status':result['status']})
        print('B completed source',source['benchmark'],source['seed'],len(entries),flush=True)
    expected=len(inventory)*len(list(plan(config))); assert len(entries)==expected
    write(folder/'manifest.json',{'status':'PASSED','records':entries,'expected':expected,
                                 'counts':dict(Counter(r['status'] for r in entries)),
                                 'engineering_meaning':'all planned trajectories terminal; solver failures retained'})


def prefix(row,budget=None,adaptive=False):
    rows=row.get('rows',[])
    if not rows: return {'status':row['status'],'failure_reason':row.get('failure_reason'),'selected':None}
    if adaptive:
        selected=next((r for r in rows if r['step']<=5 and r['indicator_relative']<1e-3),None)
        reason='INDICATOR' if selected else 'MAX_BUDGET'
        if selected is None: selected=next((r for r in rows if r['step']==5),None)
    else:
        selected=next((r for r in rows if r['step']==budget),None); reason='FIXED_BUDGET'
    if selected is None and row['status']=='PASS':
        selected=rows[-1]; reason='VERIFIED_RESIDUAL'
    if selected is None: return {'status':row['status'],'failure_reason':row.get('failure_reason'),'selected':None}
    if row['status']=='NUMERICAL_FAILURE' and selected['step']>=rows[-1]['step']:
        return {'status':row['status'],'failure_reason':row.get('failure_reason'),'selected':selected}
    return {'status':'PASS','failure_reason':None,'selected':selected,'stop_reason':reason,
            'indicator_triggered':selected['indicator_relative']<1e-3}


def phase_c():
    config,auth,inventory,base=context(); manifest=read(base/'B/manifest.json')
    assert manifest['status']=='PASSED'
    folder=base/'C'; folder.mkdir(exist_ok=False); entries=[]
    for item in manifest['records']:
        path=base/'B'/item['file']; assert sha(path)==item['sha256']
        run=unpack(path)
        if run['start']!='gn': continue
        outputs=[(f'fixed_{budget}',prefix(run,budget=budget)) for budget in run['budgets']]
        outputs.append(('adaptive',prefix(run,adaptive=True)))
        for mode,value in outputs:
            data={k:run[k] for k in ('source','candidate','rank_requested','sketch_seed','gn_error') if k in run}
            data.update(value,mode=mode,B_source=item['file'],B_sha256=item['sha256'])
            name=item['file'].replace('.json.gz',f'_{mode}.json.gz');pack(folder/name,data)
            entries.append({'file':name,'sha256':sha(folder/name),'status':data['status']})
    write(folder/'manifest.json',{'status':'PASSED','records':entries,'counts':dict(Counter(x['status'] for x in entries)),
                                 'selection_policy':'prefix selected with fixed budget or indicator only, no oracle; times are corresponding B prefixes'})
    print('C',len(entries),Counter(x['status'] for x in entries))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['authorize','A','B','C'])
    args=parser.parse_args()
    {'authorize':authorization,'A':phase_a,'B':phase_b,'C':phase_c}[args.phase]()
