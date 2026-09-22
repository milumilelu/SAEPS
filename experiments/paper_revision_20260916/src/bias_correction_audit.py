"""Development-only bias-correction audit on the 100-refit cohort."""
import json, math, random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
INPUT=ROOT/'outputs/posthoc/paper_strengthening/coverage_refit_mc100_v1/coverage_refit_pilot_results.json'
OUT=ROOT/'outputs/posthoc/paper_strengthening/coverage_refit_mc100_v1/bias_correction_audit.json'
def wilson(x,n):
 z=1.95996398454; p=x/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return [c-h,c+h]
def main():
 d=json.loads(INPUT.read_text()); rows=d['rows']; train=rows[:50]; test=rows[50:]
 bias=sum(r['kappa_estimate']-1.2 for r in train)/len(train)
 result={'method':'development_truth_based_bias_shift_audit','train_n':50,'test_n':50,'estimated_bias':bias,'methods':{}}
 for m in ['raw','saeps','parameter_block']:
  raw=sum(r[m+'_covered'] for r in test)
  corrected=0
  for r in test:
   lo=r[m+'_ci_low']-bias; hi=r[m+'_ci_high']-bias
   corrected += int(lo<=1.2<=hi)
  result['methods'][m]={'uncorrected_count':raw,'uncorrected_coverage':raw/50,'corrected_count':corrected,'corrected_coverage':corrected/50,'uncorrected_wilson':wilson(raw,50),'corrected_wilson':wilson(corrected,50)}
 OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
 (OUT.with_suffix('.md')).write_text('# Bias-correction audit\n\nDevelopment-only split-sample audit; the bias estimate uses the synthetic truth and is not a deployable estimator.\n\n'+json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__': main()
