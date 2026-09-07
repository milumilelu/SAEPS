"""Static Phase 1.5 protocol preflight. Does not execute scientific experiments."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'configs/v6/development/phase15.json'
INVENTORY = ROOT / 'configs/v6/development/phase15_inputs.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(config):
    rows = []
    for path in sorted(ROOT.glob(config['input_glob'])):
        record = json.loads(path.read_text(encoding='utf-8'))
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path),
                     'benchmark': record['benchmark'], 'seed': record['seed'],
                     'analysis_valid': record['analysis_valid'], 'failure_reason': record['failure_reason']})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-inventory', action='store_true')
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    assert config['scope'] == 'historical_matrix_development_only'
    assert config['scientific_execution_authorized'] is False
    assert config['confirmation_authorized'] is False
    assert config['gamma_policy'] == 'archived_per_checkpoint_unchanged'
    assert config['sketch_seeds'] == list(range(5))
    rows = inventory(config)
    expected = {(b, s) for b, seeds in config['cohorts'].items() for s in seeds}
    observed = {(r['benchmark'], r['seed']) for r in rows}
    assert observed == expected and len(rows) == len(expected)
    assert len(expected) == 25
    assert config['entry_gate']['random_seed_reduction'] == 'worst_per_checkpoint'
    assert not config['entry_gate']['exact_gn_eligible']
    names = [c['name'] for c in config['candidates']]
    assert len(names) == len(set(names)) == 5
    assert config['adaptive']['oracle_access'] is False
    assert config['adaptive']['maximum_steps'] == config['entry_gate']['maximum_correction_steps']
    planned = 0
    for candidate in config['candidates']:
        assert 0 in candidate['budgets']
        assert sorted(set(candidate['budgets'])) == candidate['budgets']
        repeats = len(config['sketch_seeds']) if candidate['randomized'] else 1
        planned += len(rows) * len(candidate['ranks']) * repeats
    if args.create_inventory:
        with INVENTORY.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump({'scope': config['scope'], 'records': rows}, stream, indent=2)
            stream.write('\n')
    saved = json.loads(INVENTORY.read_text(encoding='utf-8'))
    assert saved['records'] == rows, 'Input inventory changed'
    assert not (ROOT / config['output_root']).exists(), 'Scientific outputs exist while execution unauthorized'
    result = {'status': 'PASSED', 'type': 'STATIC_PROTOCOL_PREFLIGHT_ONLY',
              'config_sha256': digest(CONFIG), 'inventory_sha256': digest(INVENTORY),
              'protocol_sha256': digest(ROOT / 'docs/v6/PHASE15_EXECUTION_PROTOCOL.md'),
              'validator_sha256': digest(Path(__file__)),
              'git_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'planned_source_records': len(rows),
              'source_valid': sum(r['analysis_valid'] is True for r in rows),
              'source_invalid': sum(r['analysis_valid'] is not True for r in rows),
              'candidate_trajectories_per_start': planned,
              'scientific_execution_performed': False,
              'legacy_validation': 'NOT_RERUN: prior missing historical files retained; see layer-1 repository_validation.json'}
    output = ROOT / 'docs/v6/PHASE15_PREFLIGHT.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
