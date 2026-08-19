"""Build Figure 3 from immutable P5 raw record JSON without recomputation."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--run-dir",type=Path);args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    run_dir=args.run_dir or sorted((root/"outputs/runs/p5_scalar").iterdir(),key=lambda p:p.stat().st_mtime)[-1]
    records=[json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir/"records").glob("*.json"))]
    valid=[record for record in records if record["status"]=="PASS"]
    if not valid: raise RuntimeError("Figure 3 requires at least one valid P5 record")
    record=valid[0];offsets=[float(v) for v in record["profile_points"]]
    frozen=[float(v) for v in record["frozen_profile"]["losses"]];reopt=[float(v) for v in record["reoptimized_profile"]["losses"]];classical=[float(v) for v in record["classical_profile"]["losses"]]
    def normalize(values):
        base=values[offsets.index(0.0)]; shifted=[v-base for v in values]; scale=max(max(abs(v) for v in shifted),1e-30);return [v/scale for v in shifted]
    series=[("frozen",normalize(frozen),"#D55E00"),("reoptimized",normalize(reopt),"#0072B2"),("classical",normalize(classical),"#009E73")]
    width,height=760,480;left,top,pw,ph=85,45,630,350;y_values=[v for _,values,_ in series for v in values];ymin=min(y_values);ymax=max(y_values)
    px=lambda s:left+(s-min(offsets))/(max(offsets)-min(offsets))*pw;py=lambda v:top+(ymax-v)/max(ymax-ymin,1e-30)*ph
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">','<rect width="100%" height="100%" fill="white"/>',f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" stroke="black"/>',f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="black"/>',f'<text x="380" y="25" text-anchor="middle" font-size="18" font-weight="bold">Scalar profiles, first valid locked seed {record["seed"]}</text>']
    for name,values,color in series:
        points=" ".join(f"{px(s):.2f},{py(v):.2f}" for s,v in zip(offsets,values,strict=True));lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
    lines.extend(['<text x="390" y="455" text-anchor="middle" font-size="15">log-parameter offset</text>','<text x="20" y="220" text-anchor="middle" font-size="15" transform="rotate(-90 20 220)">centered normalized profile loss</text>','</svg>'])
    (run_dir/"figure3_scalar_profiles.svg").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n");print(run_dir/"figure3_scalar_profiles.svg");return 0
if __name__=="__main__":raise SystemExit(main())

