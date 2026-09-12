import json
from pathlib import Path
import torch
from saeps.identifiability import benchmark_observation_jacobian, benchmark_rank, heat_temperature, add_observation_noise
D=torch.float64
x_base=torch.tensor([0.2,0.4,0.7],dtype=D)
t_multi=torch.tensor([0.02,0.08,0.2,0.4],dtype=D)
x,t=torch.meshgrid(x_base,t_multi,indexing='xy'); x=x.reshape(-1); t=t.reshape(-1)
rows=[]
for b,xx,tt in [
 ('B1',x,t),('B2',x,torch.full_like(x,1e-4)),('B3',x,t),
 ('B4',torch.tensor([0.2,0.4,0.7,0.8],dtype=D),torch.full((4,),0.2,dtype=D)),
 ('B5',torch.tensor([0.2,0.4,0.7,0.8]*2,dtype=D),torch.tensor([0.2]*4+[0.4]*4,dtype=D)),('B6',x,t)]:
 jac=benchmark_observation_jacobian(b,xx,tt); rows.append({'benchmark':b,'rank':benchmark_rank(b,xx,tt),'shape':list(jac.shape),'singular_values':[float(v) for v in torch.linalg.svdvals(jac)]})
obs=heat_temperature(x,t,0.6,1.2)
a=add_observation_noise(obs,0.01,123); bb=add_observation_noise(obs,0.01,123)
result={'protocol_id':'reliability_audit_v1','reference_kind':'analytic_heat_observation_map','truth':{'k':0.6,'C':1.2,'a':1.0},'rows':rows,'expected_rank':{'B1':1,'B2':1,'B3':1,'B4':1,'B5':2,'B6':2},'noise_reproducible':bool(torch.equal(a,bb)),'scope':'Independent analytic/torch reference; no PINN training or confirmation claim.'}
Path('outputs/reliability_audit_v1/pilot/ri1').mkdir(parents=True,exist_ok=True)
Path('outputs/reliability_audit_v1/pilot/ri1/REFERENCE_RANK_REPORT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

