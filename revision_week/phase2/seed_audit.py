"""Read all accessible historical text blobs and worktree materials before seed lock."""
from __future__ import annotations
import ast,gzip,re,subprocess,time
from pathlib import Path
from common import ROOT,OUT,read,write,git,sha,memory,environment

EXT={'.json','.yaml','.yml','.toml','.csv','.md','.txt','.py','.ps1','.ipynb'}
NUM=re.compile(r'(?<![\w.])[-+]?\d[\d_]*(?![\w.])')
KEY=re.compile(r'\b(?:[\w]*seed[\w]*)\b',re.I)
PATHSEED=re.compile(r'(?:seed[_-]?|checkpoint[_-]?)(\d+)',re.I)

def literals(line):
    values=set()
    for m in NUM.finditer(line):
        try:values.add(int(m.group().replace('_','')))
        except ValueError:pass
    for m in re.finditer(r'range\(\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)',line):
        a,b,step=int(m[1]),int(m[2]),int(m[3] or 1)
        if 0<=b-a<=100000 and step>0:values.update(range(a,b,step))
    return values

def scan_text(data,path,source,records,used):
    if b'\x00' in data[:2048]:return
    text=data.decode('utf-8',errors='replace');lines=text.splitlines();selected=set()
    for i,line in enumerate(lines):
        if KEY.search(line):
            selected.add(i)
            # YAML lists and wrapped literal seed lists can span following lines.
            if re.search(r'seeds?[^\n]*[:=]\s*(?:\[\s*)?$',line,re.I):
                for j in range(i+1,min(i+105,len(lines))):
                    if re.match(r'^\s*(?:-\s*)?[\d,\s\[\]_-]+$',lines[j]):selected.add(j)
                    else:break
    for i in sorted(selected):
        values=literals(lines[i])
        for value in values:
            used.add(value);records.append(dict(seed=value,path=path,source=source,line=i+1,purpose='used_or_reserved_or_ambiguous_seed_context',context=lines[i][:250]))
    for m in PATHSEED.finditer(path):
        value=int(m[1]);used.add(value);records.append(dict(seed=value,path=path,source=source,purpose='seed_path'))

def main():
    start=time.perf_counter();dest=OUT/'preflight';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'SEED_AUDIT.json').exists():raise RuntimeError('audit exists; preserve and inspect before rerun')
    objects=git('rev-list','--objects','--all','--reflog').splitlines();candidates={};binaries=[]
    for line in objects:
        parts=line.split(' ',1)
        if len(parts)!=2:continue
        oid,path=parts
        if Path(path).suffix.lower() in EXT:candidates.setdefault(oid,path)
        if Path(path).suffix.lower() in {'.pt','.npz','.npy','.zip','.gz'}:binaries.append(dict(blob=oid,path=path))
    records=[];used=set();scanned=[]
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    for oid,path in candidates.items():
        proc.stdin.write((oid+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().strip().split()
        if len(header)!=3 or header[1]!='blob':raise RuntimeError('unexpected git batch object')
        size=int(header[2]);data=proc.stdout.read(size);proc.stdout.read(1)
        scan_text(data,path,oid,records,used);scanned.append(dict(blob=oid,path=path,size=size))
    proc.stdin.close();proc.wait()
    roots=[Path(line[9:]) for line in git('worktree','list','--porcelain').splitlines() if line.startswith('worktree ')]
    local=[];caches=[]
    for root in roots:
        # rg honours neither gitignore nor hidden filtering here; exclusions only tooling caches.
        command=['rg','--files','--hidden','--no-ignore','-g','!.git/**','-g','!.venv/**','-g','!**/node_modules/**','-g','!**/__pycache__/**','-g','!**/.pytest_cache/**',str(root)]
        res=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
        for name in res.stdout.splitlines():
            p=Path(name)
            if 'phase2_v1' in p.parts:continue
            if p.suffix.lower() in {'.pt','.npz','.npy','.zip'}:caches.append(str(p))
            if p.suffix.lower() not in EXT:continue
            try:data=p.read_bytes()
            except OSError as e:raise RuntimeError(f'unreadable audit input: {p}') from e
            scan_text(data,str(p),sha(p),records,used);local.append(dict(path=str(p),sha256=sha(p)))
    # Conservative token exclusion does not evaluate code or train anything.
    # Dynamic actual run seed arguments must be traced via archived configs/manifests.
    fresh=[];candidate=1000
    while len(fresh)<30:
        if candidate not in used:fresh.append(candidate)
        candidate+=1
    import json
    evidence=dest/'SEED_EVIDENCE.json.gz'
    with gzip.open(evidence,'wt',encoding='utf-8') as f:json.dump(records,f,ensure_ascii=False)
    write(dest/'BLOB_INVENTORY.json',dict(text=scanned,binary=binaries,local=local,checkpoint_cache_candidates=caches))
    write(dest/'SEED_AUDIT.json',dict(status='PENDING_DYNAMIC_SOURCE_REVIEW',scope='all refs + reflogs + two accessible worktrees, full text seed-context and literal range expansion',
        parent_commit=git('rev-parse','HEAD'),ref_snapshot=git('show-ref'),used_or_reserved_or_ambiguous=sorted(used),
        proposed_groups=dict(burgers=fresh[:10],allen_cahn=fresh[10:20],multi=fresh[20:]),frozen=False,
        text_blobs=len(scanned),worktree_text_files=len(local),evidence_records=len(records),evidence_sha256=sha(evidence),
        binary_candidates=len(binaries),wall_seconds=time.perf_counter()-start,environment=environment(),
        limitations='Unreachable/deleted external records cannot be audited. Dynamic Python seed producers require a separate source review before confirmation lock.'))
    print('seed audit completed; pending dynamic source review',fresh,flush=True)

if __name__=='__main__':main()
