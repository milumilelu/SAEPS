"""Supplementary all-ref source review inventory. Does not freeze new seeds."""
import ast,subprocess,time
from common import ROOT,OUT,read,write,git,sha

def main():
    start=time.perf_counter();inv=read(OUT/'preflight/BLOB_INVENTORY.json');expressions={};robust=[]
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    for entry in inv['text']:
        path=entry['path']
        if not path.endswith('.py') and not ('noise_sparsity' in path and path.endswith('.json')):continue
        proc.stdin.write((entry['blob']+'\n').encode());proc.stdin.flush();head=proc.stdout.readline().split();data=proc.stdout.read(int(head[-1]));proc.stdout.read(1)
        if path.endswith('.py'):
            try:tree=ast.parse(data.decode('utf-8-sig'))
            except (SyntaxError,UnicodeError):continue
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    name=ast.unparse(node.func)
                    if any(s in name for s in ('manual_seed','default_rng','set_deterministic_seed','train_scalar_checkpoint','train_multi_checkpoint')):
                        expr=ast.unparse(node);expressions.setdefault(expr,[]).append(dict(path=path,blob=entry['blob'],line=node.lineno))
        elif any(k in data for k in [b'"theta"',b'"G_tt"',b'"H_tt"',b'"H_tt_sym"']):robust.append(entry)
    proc.stdin.close();proc.wait()
    binary=[r for r in inv['binary'] if 'noise_sparsity' in r['path']]
    caches=[p for p in inv['checkpoint_cache_candidates'] if 'noise_sparsity' in p]
    write(OUT/'preflight/DYNAMIC_SEED_EXPRESSIONS.json',expressions)
    write(OUT/'preflight/ROBUSTNESS_INPUT_AUDIT.json',dict(scope='all historical text blobs for noise_sparsity plus all reachable binary paths and both worktree checkpoint/cache paths',
        matching_full_state_or_blocks_found=bool(robust or binary or caches),full_block_candidates=robust,binary_candidates=binary,cache_candidates=caches,
        unrelated_checkpoint_inventory_sha256=sha(OUT/'preflight/BLOB_INVENTORY.json'),seconds=time.perf_counter()-start))
    print('\n'.join(expressions));print('robustness_candidates',len(robust),len(binary),len(caches))

if __name__=='__main__':main()
