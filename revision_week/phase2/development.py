"""Explicitly numbered developer attempts; no fresh training or silent rerun."""
from common import *
from execution import task

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);a=p.parse_args()
    for node,kind in [('E0','scalar_history'),('E4D','multi_history'),('E6D','lanczos_history')]:
        task(node,a.attempt,dict(kind=kind),timeout=600)
    for cid in read(SPEC)['e5']['compact_centers']:
        src,_=task('E5AB',cid+'_export',dict(kind='compact_export',center=cid),timeout=60)
        for kind in ['compact_explicit','compact_mf']:
            task('E5AB',cid+'_'+kind+'_'+a.attempt,dict(kind=kind,center=cid,input=str(src/'state.pt')),timeout=120)

if __name__=='__main__':main()
