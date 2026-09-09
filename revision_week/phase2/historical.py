"""Read-only E0/E4-D/E6-D/P matrices and checkpoints; all positions retained."""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import torch
from common import ROOT,OUT,read,write,sha,runtime,load_payload,residual_from_payload,norm,numerical_mu,refine,csvout,native
from numerics import matrices,dense_curvature,lanczos_inverse

def load_archive(old):
    rawpath=old['input_path'];portable=ROOT/('outputs/'+rawpath.replace('\\','/').split('/outputs/',1)[1])
    candidates=[portable,Path(rawpath)]
    for path in candidates:
        if path.exists() and sha(path)==old['input_sha256']:
            data=read(path);gg=data['GN_blocks'];hh=data['exact_blocks']
            gg={k:np.asarray(v) for k,v in gg.items()};hh={k:np.asarray(v) for k,v in hh.items()}
            g=np.block([[gg['G_tt'],gg['G_tl']],[gg['G_tl'].T,gg['G_ll']]])
            h=np.block([[hh['H_tt_sym'],hh['H_tl']],[hh['H_tl'].T,hh['H_ll']]])
            return g,h,path
    raise ValueError('historical source hash unavailable: '+old['center_id'])

def scalar(dest,cfg):
    mechanism=[];sweep=[];robustness=[]
    for path in sorted((ROOT/'revision_week/outputs/day1/raw').glob('*.json')):
        old=read(path);base=dict(center=old['center_id'],pde=old['pde'],seed=old['seed'],historical_status=old['status'])
        if old['status']!='PASS':
            mechanism.append(dict(**base,status=old['status'],failure_reason=old['failure_reason']))
            sweep.extend(dict(**base,alpha=alpha,status=old['status'],failure_reason=old['failure_reason']) for alpha in cfg['e0']['gamma_alphas']);continue
        g,h,source=load_archive(old);n=old['n_state'];r=matrices(g,h,n,old['gamma']);write(dest/'raw'/f'{old["center_id"]}_nominal.json',r)
        if not r['binding_valid']:raise AssertionError('previous valid matrix fails numerical definition')
        eg=float((r['F_GN']-r['F_star'])[0,0]);c=float((r['F_SO']-r['F_GN'])[0,0]);es=eg+c;eta=r['eta_F']
        cls='unresolved' if min(abs(eg),abs(c))<=eta or abs(abs(c)-2*abs(eg))<=2*eta else 'wrong_direction' if eg*c>0 else 'appropriate' if abs(c)<2*abs(eg) else 'overshoot'
        vals,vecs=np.linalg.eigh(r['A']);d=r['D'];q=float(r['defect_energy'][0,0]);energy=(vecs.T@d).ravel()**2/vals
        mechanism.append(dict(**base,status='PASS',failure_reason=None,e_GN=eg,correction=c,e_SO=es,classification=cls,
            scalar_improvement_product=c*(2*eg+c),identity_error=r['identity_error'],r_D=norm(d)/max(norm(r['B']),1e-30),
            Z_norm=norm(r['Z_G']),condition_A=float(vals[-1]/vals[0]),lambda_min=float(vals[0]),q=q,
            min_direction_energy_fraction=float(energy[0]/q),weak10percent_energy_fraction=float(energy[:max(1,int(np.ceil(.1*n)))].sum()/q),
            mu_effective=norm(d)**2/q,SO_win=r['metrics']['fro']['strict_SO_win'],source_sha256=sha(source)))
        for alpha in cfg['e0']['gamma_alphas']:
            gamma=alpha*float(np.linalg.eigvalsh(g[:n,:n])[-1]);r=matrices(g,h,n,gamma)
            write(dest/'raw'/f'{old["center_id"]}_alpha_{alpha}.json',r)
            sweep.append(dict(**base,alpha=alpha,gamma=gamma,status=r['status'],failure_reason=r['failure_reason'],
                **(r['metrics']['fro'] if r.get('binding_valid') else {})))
    audit=read(ROOT/'revision_week/protocols/phase2/SOURCE_AUDIT.json')
    availability=read(OUT/'preflight/ROBUSTNESS_INPUT_AUDIT.json')
    if availability['matching_full_state_or_blocks_found']:raise RuntimeError('new recoverable anchor requires audited input adapter, not silent omission')
    for a in audit['robustness_exact_anchor_records']:
        robustness.append(dict(source=a['path'],source_sha256=a['sha256'],status='CHECKPOINT_INVALID',execution_disposition='UNAVAILABLE',failure_reason='missing_original_state_or_full_blocks',historical_binding_valid=a['binding_valid']))
    result=dict(mechanism=mechanism,gamma_sweep=sweep,robustness=robustness)
    write(dest/'result.json',result);csvout(dest/'MECHANISM.csv',mechanism);csvout(dest/'GAMMA_SWEEP.csv',sweep);csvout(dest/'ROBUSTNESS.csv',robustness)

def multi(dest,cfg):
    rows=[]
    for path in sorted((ROOT/cfg['e4']['source_results']).glob('seed_*/result.json')):
        old=read(path);seed=old['seed'];base=dict(seed=seed,historical_binding_valid=old['binding_valid'])
        if not old['binding_valid']:rows.append(dict(**base,status='CHECKPOINT_INVALID',failure_reason='historical_invalid_retained'));continue
        cp=ROOT/cfg['e4']['source_checkpoints']/f'seed_{seed}'/'model_state.pt';payload=load_payload(cp)
        payload.update(benchmark='multi',runtime=runtime('multi'));residual=residual_from_payload(payload)
        r=dense_curvature(residual,payload['theta'],payload['coordinate'],float(old['gamma']));write(dest/'raw'/f'seed_{seed}.json',r)
        checks={key:norm(r[key]-np.array(old[other]))/max(norm(old[other]),1e-30) for key,other in [('F_RAW','F_raw'),('F_GN','F_se_GN_explicit'),('F_star','H_red_exact_gamma')]}
        parity=all(x<=1e-6 for x in checks.values());assert parity,'historical multi reload mismatch'
        vf,vecf=np.linalg.eigh(r['F_star']);gap=float(vf[1]-vf[0]);resolved=gap>cfg['e4']['reference_eigengap_relative']*max(norm(r['F_star']),r['eta_F'])
        geometry={}
        for method in ['RAW','GN','SO']:
            value=r['F_'+method];vals,vecs=np.linalg.eigh(value)
            geometry[method]=dict(eigenvalues=vals,weak_eigenvalue_error=float(vals[0]-vf[0]),weak_angle_degrees=float(np.degrees(np.arccos(np.clip(abs(vecs[:,0]@vecf[:,0]),0,1)))) if resolved else None,
                signature=list(np.sign(vals)),SPD=bool(vals[0]>r['eta_F']),SPD_condition=float(vals[-1]/vals[0]) if vals[0]>r['eta_F'] else None)
        m=len(r['residual']);grad=norm(r['gradient_sum'][:len(payload['theta'])])/m/max(norm(payload['theta'].numpy()),1.)
        rows.append(dict(**base,status=r['status'],failure_reason=r['failure_reason'],reload_pass=parity,reload_errors=checks,
            strict_state_gradient=grad,strict_state_pass=grad<=1e-8,metrics=r['metrics'],geometry=geometry,reference_eigengap=gap,eigenvector_resolved=resolved,checkpoint_sha256=sha(cp)))
    write(dest/'result.json',rows);csvout(dest/'MULTI_DEVELOPMENT.csv',rows)

def lanczos(dest,cfg,practical=False):
    rows=[]
    for path in sorted((ROOT/'revision_week/outputs/day1/raw').glob('*.json')):
        old=read(path)
        if old['status']!='PASS':rows.append(dict(center=old['center_id'],status=old['status'],failure_reason=old['failure_reason']));continue
        g,h,_=load_archive(old);n=old['n_state'];gamma=old['gamma'];a=h[:n,:n]+gamma*np.eye(n);b=h[:n,n:];c=h[n:,n:]
        z=np.linalg.solve(g[:n,:n]+gamma*np.eye(n),g[:n,n:]);t=time.perf_counter();terminal=refine(a,b,c,z,old['mu_value'],.1,100)
        replay_seconds=time.perf_counter()-t
        assert len(terminal['trace'])==len(old['adaptive']['trace']) and terminal['status']==old['adaptive']['status']
        t=time.perf_counter();mu=numerical_mu(a);endpoint=mu['mu_value'];spectral_seconds=time.perf_counter()-t
        if practical:
            t=time.perf_counter();margin=32*len(a)*np.finfo(float).eps*max(float(np.linalg.norm(a,np.inf)),1.)
            endpoint=float(np.min(np.diag(a)-(np.abs(a).sum(axis=1)-np.abs(np.diag(a))))-margin);endpoint_seconds=time.perf_counter()-t
        else:endpoint_seconds=spectral_seconds
        for label,zz in [('initial',z),('terminal',terminal['Z'])]:
            if practical and label!='terminal':continue
            d=(b-a@zz).ravel();r=lanczos_inverse(a,d,endpoint,ks=(8,) if practical else tuple(cfg['e6']['k']))
            # Independent reference is evaluated AFTER the complete quadrature trace.
            t=time.perf_counter();chol=np.linalg.cholesky(a);w=np.linalg.solve(chol.T,np.linalg.solve(chol,d));q=float(d@w)
            vals,vecs=np.linalg.eigh(a);energies=(vecs.T@d)**2/vals;q2=float(np.sum(energies));eta=max(100*np.finfo(float).eps*norm(d)**2/mu['mu_value'],10*abs(q-q2));qseconds=time.perf_counter()-t
            if not r['rows']:rows.append(dict(center=old['center_id'],defect=label,status='NUMERICAL_FAILURE',failure_reason=r['status'],endpoint=endpoint));continue
            for rec in r['rows']:
                l,u=rec['lower'],rec['upper'];qresolved=bool(q>0 and eta<=.01*q)
                coverage=bool(qresolved and u is not None and l-eta<=q<=u+eta and rec.get('failure_reason') is None)
                rows.append(dict(center=old['center_id'],defect=label,status='PASS' if coverage else 'NUMERICAL_FAILURE',failure_reason=None if coverage else 'interval_or_reference_unresolved',
                    **{k:v for k,v in rec.items() if k!='failure_reason'},q=q,eta_q=eta,coverage=coverage,effectivity=u/q if u is not None and q>0 else None,
                    interval_gap=u-l if u is not None else None,estimator_seconds=r['seconds'],spectral_seconds=spectral_seconds,endpoint_seconds=endpoint_seconds,
                    original_replay_seconds=replay_seconds,reference_seconds=qseconds,trace_shared_across_k=True,oracle_endpoint=not practical,
                    r_D=norm(d)/max(norm(b),1e-30),Z_norm=norm(zz),mu_effective=norm(d)**2/q,
                    min_direction_energy_fraction=float(energies[0]/q),weak10percent_energy_fraction=float(energies[:max(1,int(np.ceil(.1*n)))].sum()/q)))
    write(dest/'result.json',rows);csvout(dest/'LANCZOS.csv',rows)
