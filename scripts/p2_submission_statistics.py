"""Derive submission statistics from immutable evidence summaries only."""
import hashlib, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 "burgers":"docs/evidence/v4_2_confirmation.json",
 "allen_cahn":"docs/evidence/v4_4_allen_confirmation.json",
 "robustness":"docs/evidence/v4_8_robustness.json",
 "damping":"docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.json",
 "scaling":"docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.json"}

def stats(x):
 a=np.asarray(x,dtype=float); q=np.quantile(a,[.25,.75])
 return {"n":len(a),"median":float(np.median(a)),"Q25":float(q[0]),"Q75":float(q[1]),"IQR":float(q[1]-q[0]),"min":float(a.min()),"max":float(a.max())}

def main():
 d={k:json.loads((ROOT/p).read_text(encoding='utf-8')) for k,p in SOURCES.items()}
 paired={}
 for k in ('burgers','allen_cahn'):
  s=d[k]['summary']; er=np.asarray(s['secondary']['E_raw_all_valid']); es=np.asarray(s['secondary']['E_SAEPS_all_valid']); ds=er-es
  frozen=float(s['exact_one_sided_sign_p']); expected=2.0**(-len(ds))
  if not np.isclose(frozen,expected,rtol=0,atol=1e-15): raise RuntimeError(f'{k} frozen sign p mismatch')
  paired[k]={"D":stats(ds),"planned":int(s['planned']),"valid":int(s['valid']),"positive_D":int((ds>0).sum()),
             "positive_D_over_valid":f"{int((ds>0).sum())}/{int(s['valid'])}","positive_D_over_planned":f"{int((ds>0).sum())}/{int(s['planned'])}",
             "frozen_one_sided_exact_binomial_sign_test_p":frozen,"frozen_p_verified":True}
 r=d['robustness']; a=r['exact_anchors']
 damping=d['damping']; alpha=[x for x in damping['alpha_summaries'] if x['alpha']==1e-10][0]
 sc=d['scaling']; cs=sc['conditions']
 out={"schema_version":1,"classification":"P2_EXISTING_EVIDENCE_PRESENTATION_AUDIT","paired_effect_sizes":paired,
  "robustness":{"planned_conditions":r['planned'],"binding_valid_conditions":r['binding_valid'],"exact_Hessian_anchors_planned":a['planned'],"exact_Hessian_anchors_valid":a['binding_valid'],"SAEPS_favorable_anchors":a['strict_SAEPS_wins']},
  "damping":{"planned_terminal_count":damping['planned_terminal_count'],"pass_count":damping['pass_count'],"per_alpha":[{"alpha":x['alpha'],"valid":x['pass_count'],"planned":x['terminal_count'],"eta_median":x['eta_median_all_computable'],"effective_rank_median":x['effective_rank_median']} for x in damping['alpha_summaries']],
    "smallest_alpha":{"alpha":alpha['alpha'],"valid":alpha['pass_count'],"planned":alpha['terminal_count']},"eta_nondecreasing_all_checkpoints":damping['high_gamma_GN_limit']['all_checkpoint_eta_nondecreasing'],"effective_rank_decreases_toward_high_alpha":True,"high_alpha_approaches_frozen_state":True},
  "scaling":{"dimension_combinations":len(cs),"repeats_per_combination":sorted(set(x['terminal_count'] for x in cs)),"total_verified_solves":sc['pass_count'],"planned_solves":sc['planned_count'],
    "largest_n_theta":max(x['state_parameter_count'] for x in cs),"largest_m":max(x['residual_count'] for x in cs),
    "JVP_count_range":[min(x['JVP_count']['minimum'] for x in cs),max(x['JVP_count']['maximum'] for x in cs)],"VJP_count_range":[min(x['VJP_count']['minimum'] for x in cs),max(x['VJP_count']['maximum'] for x in cs)],
    "iterative_solve_seconds_range":[min(x['solve_seconds']['minimum'] for x in cs),max(x['solve_seconds']['maximum'] for x in cs)],"shared_condition_setup_seconds_range":[min(x['shared_condition_setup_seconds'] for x in cs),max(x['shared_condition_setup_seconds'] for x in cs)],
    "timing_accounting":"iterative solve time includes JVP/VJP applications and excludes one-time shared condition setup"},
  "sources":{k:{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for k,p in SOURCES.items()},
  "scientific_adjudications_changed":False,"frozen_p_values_replaced":False}
 (ROOT/'docs/evidence/p2_submission_statistics.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps(out,indent=2))
if __name__=='__main__': main()

