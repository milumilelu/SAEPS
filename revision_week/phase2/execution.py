"""Immutable task claims, measured process budgets, raw-file manifests and resume."""
from common import *
import contextlib

@contextlib.contextmanager
def single_runner():
    """Native Windows mutex is released by the OS after death; no stale lock deletion."""
    from ctypes import wintypes
    k=ctypes.windll.kernel32;k.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];k.CreateMutexW.restype=wintypes.HANDLE
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.ReleaseMutex.argtypes=[wintypes.HANDLE];k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.CreateMutexW(None,False,'Local\\SAEPS_PHASE2_'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:16])
    if not handle:raise OSError('cannot create execution mutex')
    acquired=k.WaitForSingleObject(handle,0)
    if acquired not in (0,0x80):k.CloseHandle(handle);raise RuntimeError('another Phase2 runner is active')
    try:yield
    finally:k.ReleaseMutex(handle);k.CloseHandle(handle)

def manifest(dest,node,name,job,config,r):
    files=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=canon_sha(p) if p.suffix in ['.json','.log','.csv'] else sha(p),
                raw_sha256=sha(p)) for p in dest.rglob('*') if p.is_file()]
    write(ROOT/'revision_week/outputs/phase2_v1/run_manifests'/node/name/'manifest.json',dict(schema=1,phase=node,run_id='phase2_v1',node=node,name=name,job=job,process=r,raw_directory=str(dest.relative_to(ROOT)),
        split='development' if config==SPEC else 'confirmation' if node in ['E1','E4C'] else 'preregistered_secondary',attempt=1,
        config_hash=canon_sha(config),git_commit=read(dest/'claim.json')['source_commit'],files=files))

def task(node,name,job,config=SPEC,timeout=120):
    dest=OUT/'tasks'/node/name;claim=dest/'claim.json';process=dest/'process.json';cfg=read(config)
    if claim.exists():
        old=read(claim)
        if old['job']!=native(job) or old['config_sha256']!=canon_sha(config):raise RuntimeError('existing task identity differs; preserve '+str(dest))
        if process.exists():
            mp=OUT/'run_manifests'/node/name/'manifest.json'
            if mp.exists():
                for item in read(mp).get('files',[]):
                    p=ROOT/item['path'];actual=canon_sha(p) if p.suffix in ['.json','.log','.csv'] else sha(p)
                    if actual!=item['sha256']:raise RuntimeError('completed task raw hash changed: '+str(p))
            else:manifest(dest,node,name,job,config,read(process))
            return dest,read(process)
        started=read(dest/'process_started.json') if (dest/'process_started.json').exists() else None
        if started and process_memory(started['pid'])['rss']:
            raise RuntimeError('claimed task PID is still alive; observe rather than launch again: '+str(dest))
        r=dict(status='SOLVER_FAILURE',failure_reason='interrupted_attempt_no_retry',exit_code=None,wall_seconds=old['timeout_seconds'],
               timing_kind='conservative_upper_bound_not_measured',timing_evidence='dead claimed PID or claim before launch; charge full reserved timeout',execution_disposition='INTERRUPTED')
        write(process,r);manifest(dest,node,name,job,config,r);return dest,r
    budget=next(n['budget_seconds'] for n in cfg['nodes'] if n['id']==node)
    spent=sum(read(p)['wall_seconds'] for p in (OUT/'tasks'/node).glob('*/process.json'))
    timeout=max(0.,min(timeout,budget-spent));dest.mkdir(parents=True,exist_ok=False)
    write(claim,dict(node=node,name=name,job=job,config=str(config),config_sha256=canon_sha(config),source_commit=git('rev-parse','HEAD'),
        source_sha256={p.name:canon_sha(p) for p in Path(__file__).parent.glob('*.py')},timeout_seconds=timeout,start_unix=time.time(),environment=environment()))
    if memory()['available_bytes']<4*2**30 or shutil.disk_usage(ROOT).free<10*2**30:
        r=dict(status='SOLVER_FAILURE',failure_reason='resource_minimum_unavailable',wall_seconds=0.,exit_code=None)
    elif timeout<=0:r=dict(status='SOLVER_FAILURE',failure_reason='budget_exhausted',wall_seconds=0.,exit_code=None)
    else:r=bounded_process([sys.executable,str(ROOT/'revision_week/phase2/workers.py'),str(dest)],dest,timeout)
    r['timing_kind']='measured';write(process,r);manifest(dest,node,name,job,config,r)
    print(node,name,r['status'],round(r['wall_seconds'],3),flush=True)
    return dest,r

def skip(node,name,reason,job):
    p=ROOT/'revision_week/outputs/phase2_v1/run_manifests'/node/name/'manifest.json'
    if p.exists():return read(p)
    record=dict(node=node,name=name,job=job,execution_disposition='PROTOCOL_STOP',status=None,failure_reason=reason,wall_seconds=0.,numerical_result=None)
    write(p,record);return record
