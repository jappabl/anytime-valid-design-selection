#!/usr/bin/env python3
"""Long high-rep floored-arm ladder: discriminate d=1 vs d=1.53.

The shipped KellyFloorWSR's measured d = 1.36 +/- 0.20 (results_floor_d)
cannot separate the post-warmup idealization (d=1) from the warmup-
corrected prediction (+1.53). This run multiplies reps ~8x so the
bootstrap SE targets ~0.07, separating the candidates at ~3.8 sigma.
JOURNALED: appends one line per (rung, rep) to data/floor_ladder_long.jsonl
so the run resumes after interruption (days-scale, machine may sleep).
Analysis (fit + verdict) runs separately when all rungs reach target.
Same ladder/seed structure as run_wsr_expansion.py v2 (offset seeds).
"""
import json, sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))
from eval_harness.stats.wsr_kelly_floor import KellyFloorWSR

ALPHA, P, BASE = 0.05, 0.5, 7100
LADDER = [(0.035, 2400, 30000), (0.025, 2400, 60000),
          (0.018, 2400, 120000), (0.013, 1600, 250000),
          (0.009, 1200, 600000)]
OUT = REPO / "data" / "floor_ladder_long.jsonl"

done = {}
if OUT.exists():
    for line in open(OUT):
        r = json.loads(line)
        done.setdefault(r["i"], set()).add(r["rep"])

with open(OUT, "a") as fh:
    for i, (delta, reps, n_max) in enumerate(LADDER):
        tau = P - delta
        for rep in range(reps):
            if rep in done.get(i, ()):
                continue
            rng = np.random.default_rng(BASE + 100000 * i + rep)
            cs = KellyFloorWSR(alpha=ALPHA)
            nb = n_max // 4
            x = (rng.random(nb * 4) < P).astype(np.int8)
            means = x.reshape(-1, 4).mean(axis=1)
            n = n_max
            for j in range(nb):
                cs.update(float(means[j]))
                lo, _ = cs.get_bounds()
                if lo > tau:
                    n = 4 * (j + 1)
                    break
            fh.write(json.dumps({"i": i, "rep": rep, "n": n}) + "\n")
            fh.flush()
print("ladder complete")
