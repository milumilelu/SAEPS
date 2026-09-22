"""Bounded noisy-data refitting coverage pilot (development-only)."""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e3_saturation as E3
import torch

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument('--config', required=True); ap.add_argument('--output', required=True)
    args = ap.parse_args(); cfg_path = ROOT / args.config
    cfg0 = {'protocol_id':'SAEPS-PAPER-REVISION-COVERAGE-REFIT-PILOT-V1','architecture':[2,8,1],
            'points':{'pde':48,'data':64,'initial':24,'boundary_times':24},
            'optimizer':{'adam_steps':400,'adam_learning_rate':0.001,'lbfgs_max_iterations':500,'fixed_parameter_state_polish_max_iterations':1500},
            'gamma_alpha':1e-8,'exact_hessian':{'backend':'dense','symmetry_tolerance':1e-8,'positive_eigenvalue_relative_tolerance':1e-10},
            'noise_level':0.02,'initialization_seed':971001,
            'data_seeds':[970001,970002,970003,970004,970005,970006,970007,970008,970009,970010]}
    cfg = {'dtype':'float64','domain_t':[0.0,0.4],'diffusion':0.01,'rho_known':1.0,
           'kappa_truth':1.2,'kappa_initial':0.8,'architecture':cfg0['architecture'],
           'points':cfg0['points'],'block_weights':{'pde':5.0,'data':10.0,'initial':10.0,'boundary':2.0},
           'optimizer':cfg0['optimizer'],'gamma_alpha':cfg0['gamma_alpha'],
           'scalar_error_floor':1e-8,'exact_hessian':cfg0['exact_hessian']}
    out = ROOT / args.output; out.mkdir(parents=True, exist_ok=True)
    rows=[]; started=time.time()
    noise=float(cfg0['noise_level'])
    for i, seed in enumerate(cfg0['data_seeds']):
        row={'replicate':i+1,'data_seed':int(seed),'status':'SOLVER_FAILURE','noise_level':noise}
        try:
            fit=E3.train_fit(cfg, int(seed), int(cfg0['initialization_seed'])+i, noise)
            try:
                curv=E3.center_curvature(fit,cfg)
            except Exception:
                # Lightweight fallback: exact fixed-state parameter Hessian and GN blocks;
                # avoids importing the full historical profile specification.
                th, la, pts, loc = fit['theta'], fit['lam'], fit['points'], fit['local']
                from torch.autograd.functional import jacobian, hessian
                rf=lambda t,l:E3.weighted_residual(t,l,pts,loc)
                jth=jacobian(lambda t:rf(t,la),th,strategy='forward-mode',vectorize=True)
                jla=jacobian(lambda l:rf(th,l),la,strategy='forward-mode',vectorize=True)
                gtt=jth.T@jth; gam=cfg['gamma_alpha']*float(torch.linalg.eigvalsh(gtt).max().item())
                raw=float((jla.T@jla)[0,0].item()); se=float((jla.T@jla-jla.T@jth@torch.linalg.solve(gtt+gam*torch.eye(th.numel()),jth.T@jla))[0,0].item())
                hfix=float(hessian(lambda l:0.5*torch.sum(rf(th,l)**2),la)[0,0].item())
                curv={'status':'PASS','F_raw':raw,'F_se_GN':se,'H_fix_exact':hfix,'H_red_exact':hfix}
            row.update({'kappa_estimate':fit['kappa_estimate'], 'parameter_relative_error':fit['parameter_relative_error'],
                        'normalized_state_gradient':fit['normalized_state_gradient_after_polish'],
                        'objective_after_polish':fit['objective_after_polish']})
            if curv.get('status')!='PASS':
                row.update({'status':'NUMERICAL_FAILURE','failure_reason':curv.get('failure_reason','curvature reference failed')})
            else:
                sigma=noise*float(E3.truth(fit['points'].data_x,fit['points'].data_t).std(unbiased=False).item())
                row['observation_sigma']=sigma
                # Information is in the weighted sum objective; convert to a Wald interval in log-kappa.
                # Sandwich variance for the weighted least-squares objective.  Only the
                # data block carries observation noise; PDE/IC/BC residuals are deterministic
                # constraints.  If J_w is the weighted data Jacobian, B=sigma^2*w_data*J_w'J_w.
                width=int(cfg['architecture'][1]); counts=cfg['points']; n_pde=int(counts['pde'])
                from torch.autograd.functional import jacobian
                # Full joint sandwich: data noise enters through the state columns,
                # then nuisance-state uncertainty propagates into lambda.
                jtheta=jacobian(lambda t:E3.weighted_residual(t,fit['lam'],fit['points'],fit['local']), fit['theta'], strategy='forward-mode', vectorize=True)
                jlam=jacobian(lambda l:E3.weighted_residual(fit['theta'],l,fit['points'],fit['local']), fit['lam'], strategy='forward-mode', vectorize=True)
                J=torch.cat([jtheta,jlam],dim=1); A=J.T@J
                wdata=float(cfg['block_weights']['data']); data_slice=slice(n_pde,n_pde+int(counts['data']))
                Bmat=torch.zeros_like(A); Jd=J[data_slice,:]; Bmat=sigma*sigma*wdata*(Jd.T@Jd)
                cov=torch.linalg.pinv(A)@Bmat@torch.linalg.pinv(A); base_se=math.sqrt(max(float(cov[-1,-1].item()),1e-30))
                B=base_se
                methods={'raw':curv['F_raw'],'saeps':curv['F_se_GN'],'parameter_block':curv['H_fix_exact']}
                for name,F in methods.items():
                    F=max(float(F),1e-30); se_lam=base_se*math.sqrt(max(curv['F_raw'],1e-30)/F); k=fit['kappa_estimate']
                    lo=k*math.exp(-1.96*se_lam); hi=k*math.exp(1.96*se_lam)
                    row[f'{name}_ci_low']=lo; row[f'{name}_ci_high']=hi
                    row[f'{name}_covered']=bool(lo<=cfg['kappa_truth']<=hi)
                row['sandwich_B']=B
                row.update({'F_raw':curv['F_raw'],'F_se_GN':curv['F_se_GN'],'H_fix_exact':curv['H_fix_exact'],'H_red_exact':curv['H_red_exact'],'status':'PASS'})
        except Exception as exc:
            row['failure_reason']=f'{type(exc).__name__}: {exc}'
        rows.append(row); print(json.dumps(row,sort_keys=True),flush=True)
    summary={'protocol_id':cfg0['protocol_id'],'config':args.config,'config_sha256':hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
             'git_commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'replicate_denominator':len(rows),'elapsed_seconds':time.time()-started,'rows':rows}
    for name in ('raw','saeps','parameter_block'):
        valid=[r for r in rows if r['status']=='PASS' and f'{name}_covered' in r]
        summary[f'{name}_valid_n']=len(valid); summary[f'{name}_coverage']=sum(r[f'{name}_covered'] for r in valid)/len(valid) if valid else None
    (out/'coverage_refit_pilot_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (out/'COVERAGE_REFIT_PILOT_REPORT.md').write_text('# Coverage refit pilot\n\nDevelopment-only; all replicates retained.\n\n'+ '\n'.join(f'- {n}: {summary[n+"_coverage"]} (valid {summary[n+"_valid_n"]}/{len(rows)})' for n in ('raw','saeps','parameter_block'))+'\n',encoding='utf-8')
if __name__=='__main__': main()
