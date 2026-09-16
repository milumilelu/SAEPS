"""Read an exported E1/E2 block archive; never train or change its source."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from numerics import load_blocks, reduced_matrices, log_affine_identity


def serializable(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    raise TypeError(type(x).__name__)


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--log-affine',action='store_true',help='Only for the original affine physical-coefficient benchmarks')
    args=p.parse_args()
    if args.out.exists(): raise FileExistsError(args.out)
    b,gamma=load_blocks(args.archive)
    result=reduced_matrices(b,gamma)
    if args.log_affine: result['log_affine_identity']=log_affine_identity(b)
    result.update(classification='NEW_POSTHOC_READ_ONLY',source=str(args.archive),training_executed=False)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as f:
        json.dump(result,f,default=serializable,indent=2,allow_nan=False)
        f.write('\n')
    print(args.out)

if __name__=='__main__': main()
