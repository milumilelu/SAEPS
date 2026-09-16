"""Read frozen SAEPS records via git show. No checkout, training, or repository writes.

This is a focused scalar-statistics audit, not a whole-repository validator.
Run from outside the source repository and send --out outside it.
"""
from __future__ import annotations
import argparse, hashlib, json, math, statistics, subprocess
from pathlib import Path

COHORTS={
 'Burgers': ('outputs/runs/v4_2_corrected_confirmation/',range(55,70)),
 'Allen-Cahn': ('outputs/runs/v4_4_allen_cahn_confirmation/',range(75,85)),
}


def summarize(records: dict[int,dict], planned: list[int]) -> dict:
    rows=[]; raw=[]; sae=[]; ratios=[]; wins=0; non_tied=0
    for seed in planned:
        r=records.get(seed)
        if r is None:
            rows.append(dict(seed=seed,status='MISSING',binding_valid=False))
            continue
        valid=r.get('binding_valid') is True
        row=dict(seed=seed,status=r.get('status','UNKNOWN'),binding_valid=valid,
                 failure_reason=r.get('failure_reason'))
        if valid:
            er,es=float(r['E_raw']),float(r['E_SAEPS'])
            if not all(math.isfinite(v) and v>=0 for v in (er,es)):
                raise ValueError(f'Invalid numeric error for binding-valid seed {seed}')
            raw.append(er);sae.append(es)
            if es>0: ratios.append(er/es)
            if er!=es:non_tied+=1
            wins+=er>es
            row.update(E_raw=er,E_SAEPS=es,D=er-es)
        rows.append(row)
    medr=statistics.median(raw) if raw else None
    meds=statistics.median(sae) if sae else None
    p=sum(math.comb(non_tied,i) for i in range(wins,non_tied+1))/2**non_tied if non_tied else None
    return dict(planned=len(planned),available=len(records),valid=len(raw),
                wins_among_valid=wins,planned_wins=wins,missing=sum(r['status']=='MISSING' for r in rows),
                median_E_raw=medr,median_E_SAEPS=meds,
                ratio_of_median_errors=(medr/meds if meds is not None and meds>0 else None),
                median_paired_ratio=(statistics.median(ratios) if ratios else None),
                paired_ratio_count=len(ratios),zero_SAEPS_error_count=sum(v==0 for v in sae),
                one_sided_sign_p_valid_non_ties=p,rows=rows)


def git(repo: Path, *args: str) -> bytes:
    proc=subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode('utf-8',errors='replace').strip())
    return proc.stdout


def audit(repo: Path, ref: str) -> dict:
    # Resolve once to an immutable commit, then use that commit for every read.
    commit=git(repo,'rev-parse','--verify',ref+'^{commit}').decode().strip()
    output=dict(classification='NEW_POSTHOC_READ_ONLY',source_ref=ref,source_commit=commit,
                training_executed=False,cohorts={},input_sha256={})
    for name,(prefix,seeds) in COHORTS.items():
        paths=git(repo,'ls-tree','-r','--name-only',commit,'--',prefix).decode().splitlines()
        found={}
        for path in paths:
            if not path.endswith('.json'): continue
            blob=git(repo,'show',f'{commit}:{path}')
            value=json.loads(blob)
            if not isinstance(value,dict):continue
            seed=value.get('seed')
            if seed not in seeds or 'binding_valid' not in value:continue
            # Summaries without single-run curvature fields are not run records.
            if not any(k in value for k in ('E_raw','F_raw','center_stationarity')):continue
            if seed in found:
                raise ValueError(f'Duplicate single-run records for {name}, seed {seed}; resolve explicitly')
            found[seed]=value
            output['input_sha256'][path]=hashlib.sha256(blob).hexdigest()
        output['cohorts'][name]=summarize(found,list(seeds))
    return output


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--ref',default='jcp-submission-v1')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    repo=a.repo.resolve();dest=a.out.resolve()
    if dest==repo or repo in dest.parents:
        raise ValueError('Audit output must be outside the source repository')
    if dest.exists():raise FileExistsError(dest)
    result=audit(repo,a.ref)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(dest)

if __name__=='__main__':main()
