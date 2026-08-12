#!/usr/bin/env python3
"""Generate demo/index.html: an animated, self-contained comparison of
a fixed-n Wilson interval vs the anytime-valid betting CS under
continuous peeking, on Bernoulli streams at the real gpt-4o-mini pool
rate (p* = 0.2020). All statistics are precomputed here with the
repo's own implementations; the HTML only animates them.
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.fast_bounds import betting_bounds, wilson_interval

P_TRUE = 0.2020
N_MAX = 400
SEEDS = [3, 11, 27, 42, 58, 77]


def trajectory(seed):
    rng = np.random.default_rng(seed)
    xs = (rng.random(N_MAX) < P_TRUE).astype(int)
    rows = []
    f = 0
    for n in range(1, N_MAX + 1):
        f += xs[n - 1]
        wl, wh = wilson_interval(f, n, alpha=0.05)
        bl, bh = betting_bounds(f, n, alpha=0.05)
        rows.append([n, round(wl, 4), round(wh, 4),
                     round(bl, 4), round(bh, 4)])
    return rows


def main():
    data = {"p": P_TRUE, "runs": [trajectory(s) for s in SEEDS]}
    html = HTML.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    out = REPO / "demo" / "index.html"
    out.write_text(html)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


HTML = """<!doctype html>
<meta charset="utf-8">
<title>Peeking breaks fixed-n intervals; the betting CS survives</title>
<style>
 body{font:14px/1.45 -apple-system,system-ui,sans-serif;background:#fcfcfb;
      color:#0b0b0b;max-width:860px;margin:2rem auto;padding:0 1rem}
 h1{font-size:1.15rem} canvas{width:100%;background:#fff;border:1px solid #e5e4e0;
      border-radius:8px} .row{display:flex;gap:1.5rem;align-items:center;margin:.6rem 0}
 .stat{font-variant-numeric:tabular-nums} .bad{color:#d03b3b;font-weight:600}
 .good{color:#0ca30c;font-weight:600} button{font:inherit;padding:.35rem .9rem;
      border:1px solid #ccc;border-radius:6px;background:#fff;cursor:pointer}
 small{color:#52514e}
</style>
<h1>Watch an evaluation stream with continuous peeking</h1>
<p>True failure rate <b>p = 0.202</b> (the real gpt-4o-mini JSON-task
pool rate). Both intervals are nominal 95%. The moment an interval
excludes the truth at <em>any</em> n, a peeking analyst would draw a
wrong conclusion.</p>
<div class="row">
 <button id="go">Restart</button>
 <span class="stat">n = <b id="n">0</b></span>
 <span class="stat">Wilson violations: <b id="wv" class="bad">0</b></span>
 <span class="stat">Betting-CS violations: <b id="bv" class="good">0</b></span>
 <span><small id="seed"></small></span>
</div>
<canvas id="c" width="1680" height="760"></canvas>
<p><small>Wilson band in orange, betting confidence sequence in blue,
truth dashed. Data precomputed by demo/make_demo.py with the repo's
implementations (src/eval_harness/stats/fast_bounds.py). Across 2,000
replications the measured any-time miscoverage is 47.7% for Wilson vs
3.6% for the betting CS (results_advanced.txt).</small></p>
<script>
const D=__DATA__;let run=0,t=0,timer=null;
const cv=document.getElementById('c'),cx=cv.getContext('2d');
const W=cv.width,H=cv.height,ML=70,MB=50,MT=20,MR=20;
const xmap=n=>ML+(Math.log(n)/Math.log(400))*(W-ML-MR);
const ymap=p=>MT+(1-p)*(H-MT-MB);
function axes(){cx.clearRect(0,0,W,H);cx.strokeStyle='#e5e4e0';cx.fillStyle='#52514e';
 cx.font='24px system-ui';cx.textAlign='center';
 for(const p of [0,0.2,0.4,0.6,0.8,1]){cx.beginPath();cx.moveTo(ML,ymap(p));
  cx.lineTo(W-MR,ymap(p));cx.stroke();cx.fillText(p.toFixed(1),ML-35,ymap(p)+8)}
 for(const n of [1,3,10,30,100,400]){cx.fillText(n,xmap(n),H-15)}}
function truthline(){cx.setLineDash([8,6]);cx.strokeStyle='#0b0b0b';
 cx.lineWidth=3;cx.beginPath();cx.moveTo(ML,ymap(D.p));
 cx.lineTo(W-MR,ymap(D.p));cx.stroke();cx.setLineDash([]);cx.lineWidth=1;}
function band(rows,i,lo,hi,color,alpha){cx.beginPath();
 for(let j=0;j<=i;j++)cx[j?'lineTo':'moveTo'](xmap(rows[j][0]),ymap(rows[j][hi]));
 for(let j=i;j>=0;j--)cx.lineTo(xmap(rows[j][0]),ymap(rows[j][lo]));
 cx.closePath();cx.globalAlpha=alpha;cx.fillStyle=color;cx.fill();cx.globalAlpha=1;}
function draw(){const rows=D.runs[run];axes();
 band(rows,t,3,4,'#2a78d6',0.28);band(rows,t,1,2,'#eb6834',0.38);truthline();
 let wv=0,bv=0;for(let j=0;j<=t;j++){const r=rows[j];
  if(D.p<r[1]||D.p>r[2])wv++;if(D.p<r[3]||D.p>r[4])bv++;}
 document.getElementById('n').textContent=rows[t][0];
 const w=document.getElementById('wv');w.textContent=wv;
 document.getElementById('bv').textContent=bv;
 document.getElementById('seed').textContent='replication '+(run+1)+'/'+D.runs.length;
 if(t<rows.length-1){t++;timer=setTimeout(draw,t<40?70:12)}}
document.getElementById('go').onclick=()=>{clearTimeout(timer);
 run=(run+1)%D.runs.length;t=0;draw()};
draw();
</script>
"""


if __name__ == "__main__":
    main()
