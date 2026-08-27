"""Post-hoc whitening stabilizer sensitivity from immutable V5.3C matrices."""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from pathlib import Path
import numpy as np
import torch, yaml

ROOT=Path(__file__).resolve().parents[1]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def summarize(xs):
    a=np.asarray(xs,dtype=np.float64)
    return {"n":int(a.size),"median":float(np.median(a)),"Q25":float(np.quantile(a,.25)),"Q75":float(np.quantile(a,.75)),"min":float(a.min()),"max":float(a.max())}

def whiten(matrix, chol):
    left=torch.linalg.solve_triangular(chol,matrix,upper=False)
    return torch.linalg.solve_triangular(chol,left.T,upper=False).T

def metrics(raw,fse,exact,c,epsilon):
    raw=torch.as_tensor(raw,dtype=torch.float64); fse=torch.as_tensor(fse,dtype=torch.float64); exact=torch.as_tensor(exact,dtype=torch.float64)
    scale=max(float(torch.trace(raw).item())/2.0,1.0); tau=float(c)*scale
    b=.5*(raw+raw.T)+tau*torch.eye(2,dtype=torch.float64)
    eig=torch.linalg.eigvalsh(b); chol=torch.linalg.cholesky(b)
    reconstruction=float(torch.linalg.matrix_norm(b-chol@chol.T).item())/(float(torch.linalg.matrix_norm(b).item())+epsilon)
    wh=whiten(exact,chol); den=float(torch.linalg.matrix_norm(wh).item())+epsilon
    er=float(torch.linalg.matrix_norm(whiten(raw-exact,chol)).item())/den
    es=float(torch.linalg.matrix_norm(whiten(fse-exact,chol)).item())/den
    return {"tau":tau,"E_raw":er,"E_SAEPS":es,"D":er-es,"lambda_min_B2":float(eig[0]),"condition_number_B2":float(eig[-1]/eig[0]),"cholesky_relative_reconstruction_error":reconstruction,"whitening_scale":scale}

def direction(er,es,tol):
    margin=float(tol['atol'])+float(tol['rtol'])*max(abs(er),abs(es),1.0)
    d=er-es
    return ("SAEPS_BETTER" if d>margin else "RAW_BETTER" if d < -margin else "NUMERICAL_TIE"),margin

def load_inputs(cfg):
    ep=ROOT/cfg['source']['evidence_path']
    if sha(ep)!=cfg['source']['evidence_sha256']: raise RuntimeError('source evidence hash mismatch')
    for key,pathkey,hashkey in [('metric','metric_implementation','metric_implementation_sha256'),('config','metric_config','metric_config_sha256')]:
        p=ROOT/cfg['source'][pathkey]
        if sha(p)!=cfg['source'][hashkey]: raise RuntimeError(f'{key} source hash mismatch')
    ev=json.loads(ep.read_text(encoding='utf-8'))
    if ev['planned_denominator']!=cfg['planned_records'] or ev['binding_valid_count']!=cfg['expected_valid_records']: raise RuntimeError('provenance mismatch: planned/valid')
    rows={x['seed']:x for x in ev['seed_rows']}; valid=[]; invalid=[]
    for src in ev['source_records']:
        p=ROOT/src['path']
        if sha(p)!=src['sha256']: raise RuntimeError(f'source record hash mismatch: {p}')
        r=json.loads(p.read_text(encoding='utf-8'))
        (valid if rows[r['seed']]['binding_valid'] else invalid).append((p,r,src['sha256']))
    if len(valid)!=8 or len(invalid)!=2: raise RuntimeError('provenance mismatch: valid/invalid source split')
    return ev,valid,invalid

def nominal_check(r,cfg):
    z=metrics(r['F_raw'],r['F_se_GN_explicit'],r['H_red_exact_gamma'],cfg['nominal_tau_relative_factor'],cfg['epsilon'])
    h=r['primary']; t=cfg['nominal_reproduction_tolerance']
    ok=np.isclose(z['E_raw'],h['E_raw2'],rtol=t['rtol'],atol=t['atol']) and np.isclose(z['E_SAEPS'],h['E_SAEPS2'],rtol=t['rtol'],atol=t['atol'])
    return z,bool(ok)

def preflight(cfg):
    _,valid,_=load_inputs(cfg); z,ok=nominal_check(valid[0][1],cfg)
    if not ok: raise RuntimeError('real-record nominal reproduction failed')
    return {"status":"PASSED","seed":valid[0][1]['seed'],"recomputed":z}

def run(cfg):
    started=time.perf_counter(); ev,valid,invalid=load_inputs(cfg); records=[]
    labels={1e-8:'1e-8',1e-10:'1e-10',1e-12:'1e-12'}
    for p,r,source_hash in valid:
        results={}; nominal,ok=nominal_check(r,cfg)
        if not ok: raise RuntimeError(f"REPRODUCTION_MISMATCH seed {r['seed']}")
        for c in cfg['tau_relative_factors']:
            key=labels[float(c)]
            try:
                z=metrics(r['F_raw'],r['F_se_GN_explicit'],r['H_red_exact_gamma'],c,cfg['epsilon'])
                dr,margin=direction(z['E_raw'],z['E_SAEPS'],cfg['comparison_tolerance']); z.update(paired_direction=dr,comparison_margin=margin,status='PASS')
            except torch.linalg.LinAlgError as exc:
                z={"status":"NUMERICAL_FAILURE","failure_reason":str(exc),"paired_direction":None}
            results[key]=z
        h=r['primary']; rec={"seed":r['seed'],"original_valid_status":True,"source_record":p.relative_to(ROOT).as_posix(),"source_sha256":source_hash,
          "F_raw":r['F_raw'],"F_SAEPS":r['F_se_GN_explicit'],"H_red":r['H_red_exact_gamma'],"epsilon":cfg['epsilon'],"whitening_scale":nominal['whitening_scale'],"results":results,
          "nominal_reproduction":{"historical_E_raw":h['E_raw2'],"recomputed_E_raw":nominal['E_raw'],"relative_error_raw":abs(nominal['E_raw']-h['E_raw2'])/(abs(h['E_raw2'])+cfg['epsilon']),
            "historical_E_SAEPS":h['E_SAEPS2'],"recomputed_E_SAEPS":nominal['E_SAEPS'],"relative_error_SAEPS":abs(nominal['E_SAEPS']-h['E_SAEPS2'])/(abs(h['E_SAEPS2'])+cfg['epsilon']),"status":"PASS"}}
        records.append(rec)
        out=ROOT/cfg['outputs']['raw_root']/f"seed_{r['seed']}.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    nominal_key='1e-10'; aggregate={}
    for key in labels.values():
        good=[r['results'][key] for r in records if r['results'][key]['status']=='PASS']; directions=[z['paired_direction'] for z in good]
        entry={"valid_denominator":8,"SAEPS_BETTER":directions.count('SAEPS_BETTER'),"RAW_BETTER":directions.count('RAW_BETTER'),"NUMERICAL_TIE":directions.count('NUMERICAL_TIE'),"NUMERICAL_FAILURE":8-len(good),
          "metrics":{m:summarize([z[m] for z in good]) for m in ['E_raw','E_SAEPS','D']},"same_direction_as_nominal":sum(r['results'][key].get('paired_direction')==r['results'][nominal_key].get('paired_direction') for r in records)}
        for m in ['E_raw','E_SAEPS']:
            x=[abs(r['results'][key][m]-r['results'][nominal_key][m])/(abs(r['results'][nominal_key][m])+cfg['epsilon']) for r in records if r['results'][key]['status']=='PASS']
            entry[f'relative_metric_change_{m}']={"median":float(np.median(x)),"max":float(np.max(x))}
        aggregate[key]=entry
    artifact={"schema_version":1,"analysis_classification":cfg['analysis_classification'],"source_commit":cfg['source']['evidence_commit'],"planned":10,"original_valid":8,"invalid_seeds":[r['seed'] for _,r,_ in invalid],"nominal_reproduction_pass_count":8,"aggregate":aggregate,"records":records,"runtime_seconds":time.perf_counter()-started,"historical_evidence_modified":False,"training_performed":False,"new_pde_experiment":False,"primary_claims_changed":False}
    jp=ROOT/cfg['outputs']['json']; jp.parent.mkdir(parents=True,exist_ok=True); jp.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    flat=[]
    for r in records:
        for key,z in r['results'].items(): flat.append({"seed":r['seed'],"tau_relative_factor":key,**{k:v for k,v in z.items() if not isinstance(v,(dict,list))}})
    with (ROOT/cfg['outputs']['csv']).open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(flat[0])); w.writeheader(); w.writerows(flat)
    return artifact

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/posthoc_whitening_sensitivity_v1.yaml'); ap.add_argument('--preflight',action='store_true'); a=ap.parse_args(); cfg=yaml.safe_load((ROOT/a.config).read_text(encoding='utf-8')); print(json.dumps(preflight(cfg) if a.preflight else run(cfg),indent=2))

