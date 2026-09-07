"""Independent raw lineage, denominator, cost and aggregation validation."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from run_phase15 import context,read,sha,unpack,plan,write
from build_phase15_report import aggregate


def main():
    config,auth,inventory,base=context()
    report=read(base/'report/summary.json')
    _,rebuilt,_=aggregate()
    assert json.loads(json.dumps(rebuilt,allow_nan=False))==report,'raw-to-summary differs'
    checked=0;worst_identity=0.;statuses=Counter(); maximum_bound_violation=0.
    bmanifest=read(base/'B/manifest.json')
    expected={(r['benchmark'],r['seed'],candidate['name'],rank,seed,start)
              for r in inventory for candidate,rank,seed,start in plan(config)}
    observed=set()
    for item in bmanifest['records']:
        path=base/'B'/item['file'];assert sha(path)==item['sha256']
        row=unpack(path);s=row['source']
        key=(s['benchmark'],s['seed'],row['candidate'],row['rank_requested'],row['sketch_seed'],row['start'])
        assert key not in observed;observed.add(key);statuses[row['status']]+=1
        assert row['status'] in config['terminal_statuses']
        if row['status']!='PASS':assert row.get('failure_reason')
        if not s['analysis_valid']:
            assert row['status']=='CHECKPOINT_INVALID' and row['rows']==[]
        if not row.get('rows'):continue
        for index,r in enumerate(row['rows']):
            assert r['step']==index
            assert len(r['timing_repeats']['cold_seconds'])==5
            assert r['cold_seconds']==float(np.median(r['timing_repeats']['cold_seconds']))
            assert r['incremental_seconds']==float(np.median(r['timing_repeats']['incremental_seconds']))
            counts=r['counts']
            assert counts['HVP_actual']==counts['JVP']==counts['VJP']==0
            assert counts.get('outer_Hv',0)==index
            assert counts['verification_Hv']==index+1
            assert counts['Hv']==sum(v for k,v in counts.items() if k.endswith('_Hv'))
            assert counts['Gv']==sum(v for k,v in counts.items() if k.endswith('_Gv'))
            ref=row['oracle_reference'];error=abs(r['K']-ref)/(abs(ref)+1e-8)
            assert abs(error-r['oracle']['relative_error'])<1e-12
            worst_identity=max(worst_identity,r['oracle']['identity_relative_error'])
            assert r['oracle']['identity_relative_error']<1e-8
            assert r['oracle']['energy_gap']>=0
            eig=row['oracle_preconditioned_spectrum']; energy=r['oracle']['energy_gap']
            scale=max(abs(r['K']),abs(ref),energy,1e-8)
            bound_violation=max(0.,r['eta']/eig[-1]-energy,energy-r['eta']/eig[0])/scale
            maximum_bound_violation=max(maximum_bound_violation,bound_violation)
            assert bound_violation<1e-8, 'spectral-equivalence oracle bound violation'
            assert r['residual_discrepancy']<=1e-8 or row['status']=='NUMERICAL_FAILURE'
            assert r['cold_seconds']>=r['incremental_seconds']>=0
            checked+=1
    assert observed==expected
    for item in read(base/'report/manifest.json')['files'].items():
        assert sha(base/'report'/item[0])==item[1]
    result={'status':'PASSED','raw_B_records':len(observed),'raw_iteration_rows':checked,
            'maximum_identity_relative_error':worst_identity,'B_terminal_statuses':dict(statuses),
            'maximum_spectral_bound_violation_relative':maximum_bound_violation,
            'aggregation_recomputed_exactly':True,'cost_column_counts_verified':True,
            'all_source_hashes_unchanged':True,'all_frozen_implementation_hashes_unchanged':True,
            'scientific_development_gate':report['development_conclusion'],
            'validator_sha256':sha(Path(__file__))}
    write(base/'RESULT_VALIDATION_V2.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
