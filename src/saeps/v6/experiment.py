"""Timed candidate execution; no exact response or reference curvature access."""
from time import perf_counter
import numpy as np
from .operators import DenseOperators
from .defect_response import initialize
from .preconditioners import build, LowRank
from .pcg import trajectory


def candidate_run(blocks,name,rank,seed,start,config):
    started=perf_counter()
    g,h,b,c,gll,hll,gamma=blocks
    ops=DenseOperators(g,h,gamma)
    cross_tick=perf_counter(); c=c.copy(); b=b.copy()
    cross_seconds=perf_counter()-cross_tick
    needs_gn=start=='gn' or name in ('recycled_ritz','hybrid_defect')
    tick=perf_counter()
    cache=initialize(ops,b,config['gn_initialization']['residual_rtol']) if needs_gn else None
    gn_seconds=perf_counter()-tick
    if cache and cache['status']!='PASS':
        return {'status':'SOLVER_FAILURE','failure_reason':cache['failure_reason'],
                'rows':[], 'initial_GN_history':cache['history'], 'counts':ops.snapshot()}
    z0=cache['z'] if needs_gn else np.zeros(len(g))
    tick=perf_counter()
    defect=c-ops.A(z0,'setup_defect') if name=='hybrid_defect' else None
    setup_defect_seconds=perf_counter()-tick
    tick=perf_counter(); p=build(name,rank,seed,ops,cache,defect)
    setup_seconds=perf_counter()-tick
    pre_counts=ops.snapshot()
    prefix_seconds=perf_counter()-started
    run=trajectory(ops,c,hll,z0 if start=='gn' else np.zeros(len(g)),p,len(g),config['start_comparison']['residual_rtol'])
    for row in run['rows']:
        row['cold_seconds']=prefix_seconds+row['elapsed_seconds']
        row['incremental_seconds']=row['cold_seconds']-gn_seconds
    run.update({'rank_actual':p.rank,'initial_GN_history':cache['history'] if cache else [],
                'initial_GN_seconds':gn_seconds,'cross_block_access_seconds':cross_seconds,
                'preconditioner_setup_seconds':setup_seconds,'setup_defect_seconds':setup_defect_seconds,
                'pre_counts':pre_counts,'storage_dense_bytes':int(g.nbytes+h.nbytes+b.nbytes+c.nbytes),
                'storage_preconditioner_bytes':int(sum(x.nbytes for x in vars(p).values() if isinstance(x,np.ndarray))),
                'preconditioner':p,'GN_cache':cache})
    return run
