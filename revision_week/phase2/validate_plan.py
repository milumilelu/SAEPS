"""Validate the planning package. This is not a scientific experiment runner."""
import argparse,hashlib,json
from pathlib import Path
from gates import topological_order
ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'revision_week/protocols/phase2'

def validate():
    s=json.loads((PACKAGE/'phase2_spec.json').read_text(encoding='utf-8'))
    order=topological_order(s['nodes'])
    assert sum(n['budget_seconds'] for n in s['nodes'])==s['total_activity_budget_seconds']
    assert set(s['required_handlers'])=={n['handler'] for n in s['nodes']}
    assert s['e1']['planned']==sum(v for k,v in s['seed_policy']['groups_in_order'].items() if k!='multi')
    assert s['e3']['planned_candidates']==s['e3']['planned_roots']*len(s['e3']['offsets'])*len(s['e3']['methods'])
    assert s['e3']['required_bidirectional_reach']>=max(abs(x) for x in s['e3']['offsets'])
    assert s['e2']['offset_max']>=s['e3']['required_bidirectional_reach']
    assert s['e2']['step']/(2**s['e2']['step_halving_levels'])==s['e2']['min_step']
    assert s['e6']['gate_k'] in s['e6']['k'] and s['e6']['primary_defect']=='terminal'
    assert not s['execution_ready'] and not s['all_handlers_implemented']
    assert not s['e0']['development_outcome_may_cancel_E1']
    assert not s['e5']['requires_positive_SO_science']
    assert not s['seed_policy']['replacement'] and s['seed_policy']['actual_seeds'] is None
    assert len(s['e5']['n_state'])*len(s['e5']['m_residual'])*(s['e5']['cold_passes']+s['e5']['warmup_passes']+s['e5']['steady_passes'])==45
    required=['PHASE2_EXECUTION_RULES.md','phase2_spec.json','SOURCE_AUDIT.json','SOURCE_PROPOSAL.txt']
    assert all((PACKAGE/p).is_file() for p in required)
    audit=json.loads((PACKAGE/'SOURCE_AUDIT.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((PACKAGE/'SOURCE_PROPOSAL.txt').read_bytes()).hexdigest()==audit['proposal_sha256']
    return dict(status='PASSED',scope='plan consistency only; numerical execution unavailable',
        topological_order=order,total_activity_seconds=s['total_activity_budget_seconds'],execution_ready=False,
        missing_implementation=s['required_handlers'],
        numerical_experiments_started=0,known_input_gap='E0-C original state/full blocks not found in inspected anchor directory')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--execution-ready',action='store_true');args=p.parse_args()
    result=validate()
    if args.write:
        (PACKAGE/'PLAN_VALIDATION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8',newline='\n')
        s=json.loads((PACKAGE/'phase2_spec.json').read_text(encoding='utf-8'))
        lines=['flowchart TD']
        for n in s['nodes']:
            lines.append(f'  {n["id"]}["{n["id"]}: {n["condition"]}"]')
            lines.extend(f'  {d} --> {n["id"]}' for d in n['depends_on'])
        (PACKAGE/'DECISION_TREE.mmd').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if args.execution_ready:raise SystemExit(1)
