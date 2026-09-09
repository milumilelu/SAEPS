"""Shared Phase 2 provenance, serialization, hard budgets and saved-state IO."""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[key]='1'
import csv,ctypes,hashlib,json,platform,shutil,subprocess,sys,time
os.environ['PYTHONIOENCODING']='utf-8'
os.environ['PYTHONUTF8']='1'
for stream_handle in (sys.stdout,sys.stderr):
    if hasattr(stream_handle,'reconfigure'):stream_handle.reconfigure(encoding='utf-8',errors='replace')
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'revision_week'));sys.path.insert(0,str(ROOT/'src'))
from core import quadratic,numerical_mu,refine,sym
torch.set_default_dtype(torch.float64);torch.set_num_threads(1)
SPEC=ROOT/'revision_week/protocols/phase2/phase2_spec.json'
OUT=ROOT/'revision_week/outputs/phase2_v1'
LOCK=ROOT/'revision_week/protocols/phase2_locked_v1'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def native(x):
    if isinstance(x,dict):return {str(k):native(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [native(v) for v in x]
    if isinstance(x,torch.Tensor):return native(x.detach().cpu().numpy())
    if isinstance(x,np.ndarray):return native(x.tolist())
    if isinstance(x,np.generic):return native(x.item())
    if isinstance(x,Path):return str(x)
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(native(data),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8',newline='\n');tmp.replace(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon_sha(p):return hashlib.sha256(Path(p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args]).decode('utf-8').rstrip()
def csvout(p,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row));p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:json.dumps(native(v),ensure_ascii=False) if isinstance(v,(dict,list)) else native(v) for k,v in row.items()} for row in rows])
def norm(x):return float(np.linalg.norm(x))
def stream(name):return int.from_bytes(hashlib.sha256(('SAEPS-PHASE2/'+name).encode()).digest()[:8],'little')%2**31
def runtime(name):
    from saeps.config import load_config
    from saeps.p5_confirmation import _runtime_config
    if name=='burgers':return _runtime_config(load_config(ROOT/'configs/locked/scalar.yaml'))
    if name=='allen_cahn':
        cfg=load_config(ROOT/'configs/p4_screening.yaml');cfg['network']['hidden_width']=8;cfg['network']['architecture']='tanh_mlp_2x8x1';return cfg
    cfg=load_config(ROOT/'configs/locked/multi.yaml');cfg['network']['hidden_width']=6;cfg['network']['architecture']='two_channel_tanh_mlp_2x6x1';return cfg
def residual_from_payload(payload):
    from saeps.scalar import ScalarPoints,scalar_residual
    from saeps.multi import MultiPoints,multi_residual
    from saeps.forward import ForwardSolution
    cfg=payload['runtime'];bench=payload['benchmark']
    if bench=='multi':
        points=MultiPoints(**payload['points']);return lambda t,l:multi_residual(t,l,points,cfg)
    points=ScalarPoints(**payload['points']);truth=ForwardSolution(**payload['truth'])
    return lambda t,l:scalar_residual(t,l,bench,points,truth,cfg)
def save_payload(p,payload):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');torch.save(payload,tmp);tmp.replace(p)
def load_payload(p):return torch.load(p,map_location='cpu',weights_only=True)
def memory():
    if os.name=='nt':
        class M(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ['total','available','total_page','avail_page','total_virtual','avail_virtual','extended']]
        m=M();m.length=ctypes.sizeof(m)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError('GlobalMemoryStatusEx failed')
        return dict(total_bytes=m.total,available_bytes=m.available)
    import os as _os
    return dict(total_bytes=_os.sysconf('SC_PAGE_SIZE')*_os.sysconf('SC_PHYS_PAGES'),available_bytes=_os.sysconf('SC_PAGE_SIZE')*_os.sysconf('SC_AVPHYS_PAGES'))
def process_memory(pid):
    if os.name!='nt':return dict(rss=None,peak_working_set=None)
    from ctypes import wintypes
    class P(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ['peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile']]
    kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(P),wintypes.DWORD]
    h=kernel.OpenProcess(0x0410,False,pid)
    if not h:return dict(rss=None,peak_working_set=None)
    p=P();p.cb=ctypes.sizeof(p)
    try:
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(h,ctypes.byref(p),p.cb)
        return dict(rss=int(p.working) if ok else None,peak_working_set=int(p.peak) if ok else None)
    finally:kernel.CloseHandle(h)
def environment():return dict(python=platform.python_version(),torch=str(torch.__version__),numpy=np.__version__,platform=platform.platform(),processor=platform.processor(),device='cpu',dtype='float64',threads=1,memory=memory(),free_disk_bytes=shutil.disk_usage(ROOT).free)
class Deadline:
    def __init__(self,seconds):self.end=time.perf_counter()+max(0,seconds)
    def check(self):
        if time.perf_counter()>=self.end:raise TimeoutError('budget_exhausted')
    def remaining(self):return max(0,self.end-time.perf_counter())

class NativeJob:
    """All descendants of a suspended child enter one kill-on-close Windows job."""
    def __init__(self):
        from ctypes import wintypes as W
        self.W=W;self.k=ctypes.windll.kernel32
        self.k.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];self.k.CreateJobObjectW.restype=W.HANDLE
        self.k.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
        self.k.QueryInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.c_void_p]
        self.k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]
        self.k.TerminateJobObject.argtypes=[W.HANDLE,W.UINT];self.k.CloseHandle.argtypes=[W.HANDLE]
        class Basic(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',W.DWORD),('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),('active',W.DWORD),('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',ctypes.c_ulonglong*6),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.handle=self.k.CreateJobObjectW(None,None)
        if not self.handle:raise OSError('CreateJobObjectW failed')
        limits=Extended();limits.basic.flags=0x2000
        if not self.k.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):self.close();raise OSError('job kill-on-close configuration failed')
    def attach_and_resume(self,p):
        if not self.k.AssignProcessToJobObject(self.handle,int(p._handle)):p.kill();raise OSError('AssignProcessToJobObject failed')
        resume=ctypes.windll.ntdll.NtResumeProcess;resume.argtypes=[self.W.HANDLE];resume.restype=ctypes.c_long
        if resume(int(p._handle))!=0:self.kill();raise OSError('NtResumeProcess failed')
    def pids(self):
        class IDs(ctypes.Structure):
            _fields_=[('assigned',self.W.DWORD),('count',self.W.DWORD),('pids',ctypes.c_size_t*64)]
        ids=IDs()
        if not self.k.QueryInformationJobObject(self.handle,3,ctypes.byref(ids),ctypes.sizeof(ids),None):raise OSError('cannot audit job process tree')
        return list(ids.pids[:ids.count])
    def kill(self):self.k.TerminateJobObject(self.handle,1)
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
def bounded_process(command,dest,seconds,memory_fraction=.8):
    """One child, native Windows peak + 20ms samples, no automatic retry."""
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True);start=time.perf_counter();limit=int(memory()['available_bytes']*memory_fraction)
    with (dest/'stdout.log').open('w',encoding='utf-8') as out,(dest/'stderr.log').open('w',encoding='utf-8') as err:
        job=NativeJob() if os.name=='nt' else None
        try:
            p=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,creationflags=0x4 if job else 0)
            if job:job.attach_and_resume(p)
            write(dest/'process_started.json',dict(pid=p.pid,start_unix=time.time(),timeout_seconds=seconds,process_tree_job=bool(job)))
            peak=0;ospeak=0;reason=None;seen=set()
            while p.poll() is None:
                pids=job.pids() if job else [p.pid];seen.update(pids);measurements=[process_memory(pid) for pid in pids]
                peak=max(peak,sum(pm['rss'] or 0 for pm in measurements));ospeak=max(ospeak,sum(pm['peak_working_set'] or 0 for pm in measurements))
                if time.perf_counter()-start>=seconds:reason='budget_exhausted';job.kill() if job else p.kill();break
                if peak>limit:reason='resource_limit';job.kill() if job else p.kill();break
                time.sleep(.02)
            code=p.wait()
        finally:
            if job:job.close()
    return dict(exit_code=code,status='PASS' if code==0 and reason is None else 'SOLVER_FAILURE',failure_reason=reason or ('worker_exit_nonzero' if code else None),wall_seconds=time.perf_counter()-start,sampled_peak_rss_bytes=peak,os_peak_working_set_bytes=ospeak,memory_limit_bytes=limit,
        memory_source='Windows Job process tree, 20ms sum RSS samples; sum of process OS peaks is an upper estimate of simultaneous working-set peak',timeout_seconds=seconds,observed_process_ids=sorted(seen),process_tree_kill_enforced=bool(job))
