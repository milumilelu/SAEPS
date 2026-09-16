"""Write a deterministic job manifest. This script never launches experiments."""
from __future__ import annotations
import argparse, hashlib, json
from itertools import product
from pathlib import Path
import yaml


def make_plan(config: dict, extended: bool = False) -> list[dict]:
    e = config['E3']
    rows = []
    for split, key in [('development','development_data_seeds'),('heldout','heldout_data_seeds')]:
        for noise, data_seed, init_seed in product(e['noise_levels'], e[key], e['initialization_seeds']):
            rows.append(dict(task='E3', split=split, data_seed=data_seed,
                             initialization_seed=init_seed, noise=float(noise),
                             architecture=e['architecture'], status='NOT_RUN'))
    if extended:
        x=config['E6']
        for arch, data_seed, init_seed in product(x['additional_architectures'],x['data_seeds'],x['initialization_seeds']):
            rows.append(dict(task='E6',split='paired_architecture_extension',data_seed=data_seed,
                             initialization_seed=init_seed,noise=float(x['noise_level']),
                             architecture=arch,status='NOT_RUN'))
    for i,row in enumerate(rows,1):
        row['job_id']=f"paper-revision-{i:04d}"
        row['protocol_id']=config['protocol_id']
    return rows


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--extended',action='store_true')
    a=p.parse_args()
    raw=a.config.read_bytes()
    config=yaml.safe_load(raw)
    rows=make_plan(config,a.extended)
    digest=hashlib.sha256(raw).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:
        for row in rows:
            row['config_sha256']=digest
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    print(f'{len(rows)} planned fits; zero tasks executed. Manifest: {a.out}')

if __name__=='__main__': main()
