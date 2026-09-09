from pathlib import Path
import subprocess,json,csv,datetime
ROOT=Path.cwd(); out=ROOT/'docs/provenance'; out.mkdir(exist_ok=True); raw=out/'branch_audit_raw'; raw.mkdir(exist_ok=True)
def git(*args,ok=(0,)):
 p=subprocess.run(['git','-c','core.quotepath=false',*args],capture_output=True,encoding='utf-8'); assert p.returncode in ok,(args,p.stderr); return p.stdout.strip()
def save(name,s): (raw/name).write_text(s+'\n',encoding='utf-8')
def anc(a,b): return subprocess.run(['git','merge-base','--is-ancestor',a,b],capture_output=True).returncode==0
refs=git('for-each-ref','--format=%(refname)|%(objectname)|%(committerdate:iso-strict)|%(symref)','refs/heads','refs/remotes').splitlines()
main=git('rev-parse','main'); tags=git('tag','--list').splitlines(); stable=['main','refs/heads/codex/saeps-so-week1']+['refs/tags/'+t for t in tags]
wt=git('worktree','list','--porcelain'); save('worktrees.txt',wt)
for i,block in enumerate(wt.split('\n\n')):
 path=block.splitlines()[0][9:]; save(f'worktree_{i}_status.txt',git('-C',path,'status','--porcelain=v1','--untracked-files=all')); save(f'worktree_{i}_log.txt',git('-C',path,'log','-5','--oneline','--decorate'))
for name,args in [('dag.txt',['log','--graph','--decorate','--oneline','--all','--date-order']),('refs.txt',['show-ref']),('remote.txt',['remote','-v']),('remote_live.txt',['ls-remote','--heads','--tags','origin']),('branches.txt',['branch','-avv']),('tags.txt',['show','--no-patch','--decorate','jcp-submission-v1'])]: save(name,git(*args))
required=['da5e67b','acf848f','cf76ffe','39343bc','c868127','0428a1f','d5a231d857e4']; prov=[]
for s in required:
 full=git('rev-parse',s+'^{commit}'); prov.append(dict(short=s,sha=full,stable=[r for r in stable if anc(full,r)],branches=git('branch','-a','--contains',full).splitlines(),tags=git('tag','--contains',full).splitlines()))
save('provenance.json',json.dumps(prov,indent=2))
# Compare every path/mode/object at each tip with retained tip snapshots, not just filenames.
def tree(ref):
 d={}
 for x in git('ls-tree','-r',ref).splitlines():
  meta,path=x.split('\t',1); d[path]=meta
 return d
stable_trees=[tree(r) for r in stable]; rows=[]
for i,line in enumerate(refs):
 ref,sha,date,sym=line.split('|');
 if sym: continue
 local=ref.startswith('refs/heads/'); name=ref[len('refs/heads/'):] if local else ref[len('refs/remotes/'):]; stem=f'{i:02d}'
 unique=git('log','--format=%H %s','main..'+ref); save(stem+'_unique.txt',unique)
 for suffix,args in [('mergebase_stat',['diff','--stat','main...'+ref]),('mergebase_names',['diff','--name-status','main...'+ref]),('tip_names',['diff','--name-status','main',ref]),('cherry',['cherry','main',ref])]: save(stem+'_'+suffix+'.txt',git(*args))
 tr=tree(ref); absent=[p for p,v in tr.items() if not any(t.get(p)==v for t in stable_trees)]; save(stem+'_unpreserved_tip_blobs.txt','\n'.join(absent))
 merged=anc(sha,main); bname=name.removeprefix('origin/'); attached=[b.splitlines()[0][9:] for b in wt.split('\n\n') if 'branch refs/heads/'+bname in b.splitlines()]
 if bname in ['main','codex/saeps-so-week1']: action='KEEP'; reason='Protected stable main / active SO worktree; no rename or rewrite.'
 elif merged: action='DELETE_AFTER_VERIFY'; reason='Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs.'
 else: action='ARCHIVE_TAG_THEN_DELETE'; reason='Unmerged unique DAG and tip content; preserve exact tip with a NEW annotated archive tag before any deletion.'
 rows.append(dict(branch_name=name,scope='local' if local else 'origin',tip_sha=sha,last_commit_date=date,worktree_attached=';'.join(attached),merged_into_main=merged,unique_commit_count=len(unique.splitlines()) if unique else 0,unique_commit_list=unique,tree_diff_summary=git('diff','--shortstat','main...'+ref),tip_tree_diff_summary=git('diff','--shortstat','main',ref),contained_by_tags=';'.join(git('tag','--contains',sha).splitlines()),contains_paper_provenance_commit=';'.join(p['short'] for p in prov[2:] if anc(p['sha'],sha)),contains_unique_evidence=bool(absent) and not merged,unpreserved_tip_path_count=len(absent),active_or_historical='active' if action=='KEEP' else 'historical',recommended_action=action,reason=reason,raw_prefix=stem))
with (out/'branch_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
save('audit.json',json.dumps(dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),main=main,rows=rows,provenance=prov),indent=2))
print(json.dumps([{k:r[k] for k in ['branch_name','unique_commit_count','unpreserved_tip_path_count','recommended_action']} for r in rows],indent=2))
