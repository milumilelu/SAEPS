"""Frozen post-hoc variable-projection analysis using only saved V3 blocks."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _summary(values):
    a = np.asarray(values, dtype=np.float64)
    return {"n": int(a.size), "median": float(np.median(a)), "Q25": float(np.quantile(a, .25)),
            "Q75": float(np.quantile(a, .75)), "min": float(np.min(a)), "max": float(np.max(a))}


def _scalar(x):
    a = np.asarray(x, dtype=np.float64)
    if a.size != 1:
        raise ValueError("v1 supports scalar physical parameters only")
    return float(a.reshape(-1)[0])


def analyze_blocks(gtt, gtl, glt, gll, htt, htl, hlt, hll, gamma, f_raw, f_gamma,
                   *, norm_eps=1e-8, exact_rel_tol=1e-10, solve_tol=1e-10,
                   tsvd_cutoffs=(1e-8, 1e-10, 1e-12)):
    g = .5 * (np.asarray(gtt, dtype=np.float64) + np.asarray(gtt, dtype=np.float64).T)
    vals, vecs = np.linalg.eigh(g)
    n = g.shape[0]; lmax = float(vals[-1]); tau = n * np.finfo(np.float64).eps * lmax
    mask = vals > tau
    pinv = (vecs[:, mask] / vals[mask]) @ vecs[:, mask].T if np.any(mask) else np.zeros_like(g)
    b = np.asarray(gtl, dtype=np.float64)
    c = np.asarray(glt, dtype=np.float64)
    vp = _scalar(np.asarray(gll, dtype=np.float64) - c @ pinv @ b)
    rank = int(mask.sum())
    cond = float(lmax / vals[mask][0]) if rank else None
    reff = float(np.sum(np.maximum(vals, 0) / (np.maximum(vals, 0) + gamma)))
    tsvd = {}
    for cutoff in tsvd_cutoffs:
        m = vals > cutoff * lmax
        p = (vecs[:, m] / vals[m]) @ vecs[:, m].T if np.any(m) else np.zeros_like(g)
        ft = _scalar(np.asarray(gll) - c @ p @ b)
        tsvd[f"{cutoff:.0e}"] = {"rank": int(m.sum()), "F_TSVD": ft,
            "relative_difference_to_default_VP0": abs(ft-vp)/(abs(vp)+norm_eps)}
    h = .5 * (np.asarray(htt, dtype=np.float64) + np.asarray(htt, dtype=np.float64).T)
    he = np.linalg.eigvalsh(h); ptol = exact_rel_tol * max(float(np.max(np.abs(he))), 1.0)
    exact = {"minimum_eigenvalue": float(he[0]), "maximum_eigenvalue": float(he[-1]),
             "positive_tolerance": ptol, "status": "NOT_CLASSICALLY_ADMISSIBLE"}
    if he[0] > ptol:
        x = np.linalg.solve(h, np.asarray(htl, dtype=np.float64))
        rr = float(np.linalg.norm(h @ x - np.asarray(htl)) / (np.linalg.norm(np.asarray(htl)) + norm_eps))
        exact["solve_relative_residual"] = rr
        if np.isfinite(rr) and rr <= solve_tol:
            hr0 = _scalar(np.asarray(hll) - np.asarray(hlt) @ x)
            exact.update(status="ADMISSIBLE_CLASSICAL", H_red_exact_0=hr0,
                         E_VP0_exact0=abs(vp-hr0)/(abs(hr0)+norm_eps),
                         E_raw_exact0=abs(f_raw-hr0)/(abs(hr0)+norm_eps))
        else: exact["reason"] = "unstable_solve"
    else: exact["reason"] = "not_numerically_positive_definite"
    return {"n_theta": n, "tau_pinv": tau, "lambda_min": float(vals[0]), "lambda_max": lmax,
            "lambda_min_resolved": float(vals[mask][0]) if rank else None, "numerical_rank": rank,
            "nullity": n-rank, "rank_fraction": rank/n, "resolved_condition_number": cond,
            "effective_rank_gamma": reff, "gamma_over_lambda_max": gamma/lmax if lmax else None,
            "F_raw": f_raw, "F_SAEPS_gamma": f_gamma, "F_VP0": vp,
            "Delta_VP_gamma": f_gamma-vp,
            "relative_finite_vs_undamped": abs(f_gamma-vp)/(abs(f_gamma)+norm_eps),
            "retained_fraction_gamma": f_gamma/f_raw if abs(f_raw)>norm_eps else None,
            "retained_fraction_VP0": vp/f_raw if abs(f_raw)>norm_eps else None,
            "exact_gamma0": exact, "tsvd": tsvd}


def run(config_path):
    started=time.perf_counter(); cfg=yaml.safe_load((ROOT/config_path).read_text(encoding="utf-8"))
    ev=ROOT/cfg["input"]["evidence"]
    if hashlib.sha256(ev.read_bytes()).hexdigest()!=cfg["input"]["evidence_sha256"]: raise RuntimeError("V3 evidence hash mismatch")
    records=[]
    for p in sorted((ROOT/cfg["input"]["raw_root"]).glob("*/*.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        if not d.get("analysis_valid"): continue
        r=d["rerun"]; nb=cfg["numerics"]
        z=analyze_blocks(**{"gtt":d["GN_blocks"]["G_tt"],"gtl":d["GN_blocks"]["G_tl"],"glt":d["GN_blocks"]["G_lt"],"gll":d["GN_blocks"]["G_ll"],
          "htt":d["exact_blocks"]["H_tt_sym"],"htl":d["exact_blocks"]["H_tl"],"hlt":d["exact_blocks"]["H_lt"],"hll":d["exact_blocks"]["H_ll"],
          "gamma":float(d["gamma"]),"f_raw":float(r["F_raw"]),"f_gamma":float(r["F_SAEPS_mechanistic_explicit"]),
          "norm_eps":nb["normalization_epsilon"],"exact_rel_tol":nb["exact_positive_relative_tolerance"],
          "solve_tol":nb["exact_solve_relative_residual_tolerance"],"tsvd_cutoffs":nb["tsvd_relative_cutoffs"]})
        z.update(benchmark="allen_cahn" if "allen" in d["benchmark"].lower() else "burgers", seed=d["seed"],
                 analysis_valid_v3=True, gamma=d["gamma"], alpha=d["alpha"], source=str(p.relative_to(ROOT)).replace('\\','/'),
                 source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if abs(z["gamma_over_lambda_max"]-d["alpha"]) > 1e-12: raise RuntimeError(f"alpha mismatch {p}")
        if z["F_VP0"] > z["F_raw"] + 1e-8*max(abs(z["F_raw"]),1): raise RuntimeError(f"PSD bound failed {p}")
        records.append(z)
    counts={b:sum(r["benchmark"]==b for r in records) for b in ("burgers","allen_cahn")}
    if counts != cfg["input"]["expected_analysis_valid"]: raise RuntimeError(f"unexpected cohort counts {counts}")
    outroot=ROOT/cfg["outputs"]["raw_root"]
    for r in records:
        p=outroot/r["benchmark"]/f"seed_{r['seed']}.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    metrics=["numerical_rank","rank_fraction","nullity","resolved_condition_number","effective_rank_gamma","relative_finite_vs_undamped"]
    cohorts={}
    for b in counts:
        rs=[r for r in records if r["benchmark"]==b]; adm=[r for r in rs if r["exact_gamma0"]["status"]=="ADMISSIBLE_CLASSICAL"]
        cohorts[b]={"n":len(rs),"metrics":{m:_summary([r[m] for r in rs]) for m in metrics},
          "exact_gamma0_admissible":len(adm),"exact_gamma0_not_admissible":len(rs)-len(adm),
          "exact_metrics":({m:_summary([r["exact_gamma0"][m] for r in adm]) for m in ("E_VP0_exact0","E_raw_exact0")} if adm else {})}
    artifact={"schema_version":1,"analysis_classification":cfg["analysis_classification"],"input_v3_commit":cfg["input"]["v3_commit"],
              "cohorts":cohorts,"records":records,"runtime_seconds":time.perf_counter()-started,
              "primary_confirmation_claims_changed":False,"scientific_adjudication_changed":False}
    jp=ROOT/cfg["outputs"]["json"]; jp.parent.mkdir(parents=True,exist_ok=True); jp.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    cp=ROOT/cfg["outputs"]["csv"]
    flat=[]
    for r in records:
        q={k:v for k,v in r.items() if not isinstance(v,(dict,list))}; q.update({"exact_gamma0_status":r["exact_gamma0"]["status"],"H_red_exact_0":r["exact_gamma0"].get("H_red_exact_0"),"E_VP0_exact0":r["exact_gamma0"].get("E_VP0_exact0"),"E_raw_exact0":r["exact_gamma0"].get("E_raw_exact0")}); flat.append(q)
    with cp.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(flat[0])); w.writeheader(); w.writerows(flat)
    return artifact


if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/posthoc_variable_projection_v1.yaml")
    a=run(ap.parse_args().config); print(json.dumps({"status":"PASSED","runtime_seconds":a["runtime_seconds"],"cohorts":a["cohorts"]},indent=2))

