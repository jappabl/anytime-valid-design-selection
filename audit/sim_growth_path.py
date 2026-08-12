#!/usr/bin/env python3
"""AUDIT: does the UI product e-process actually grow at V_rr, and is the
path-measured dimension really d = K + #boundary-strata?

THEORY.md asserts (referee-verdict section):
  * "UI rate V_rr ... SOUND (envelope argument; measured E[LLR]/(nV) -> 1.002)"
  * "d = K + #boundary-strata ... 4o-mini JSON pools predict 5,
     path-measured 4.99"

Neither claim has a committed script or artifact in the repo. This
reproduces both from scratch:

  L(n) := E[ min over the null boundary of log E_n ]  under round-robin
  overhead(n) := n * V_rr - L(n)
  regress overhead(n) on log n  ->  slope = d/2, intercept = c

Run: python3 audit/sim_growth_path.py
"""

import json
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

STRATA = ["simple", "medium", "complex", "extreme"]
NGRID = [500, 1000, 2000, 4000, 8000, 16000]
REPS = 120


def load(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def v_rr(rates, tau, safe):
    r = 1 - rates if safe else rates
    t = 1 - tau if safe else tau
    lam = w = np.full(4, 0.25)
    m = bench._inner_min(lam, r, w, t)
    return float(np.sum(lam * [bench.kl_bern(r[i], m[i]) for i in range(4)]))


def run(name, fname, taus, safe):
    pools = load(fname)
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    nb = int(np.sum((rates <= 1e-12) | (rates >= 1 - 1e-12)))
    print(f"\n{name}: rates {np.round(rates, 5).tolist()}  "
          f"p*={rates.mean():.4f}  boundary strata={nb}  "
          f"predicted d = 4 + {nb} = {4 + nb}")
    side = "ge" if safe else "le"

    # accumulate min_log_e at each n in NGRID, for each tau, one path set
    acc = {tau: {n: [] for n in NGRID} for tau in taus}
    for r in range(REPS):
        rng = np.random.default_rng(20260811 + 7919 * r)
        cs = StratifiedUICS(k=4, alpha=0.05)
        idx = 0
        for step in range(1, NGRID[-1] + 1):
            k = (step - 1) % 4
            pool = pools[STRATA[k]]
            cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
            if step == NGRID[idx]:
                for tau in taus:
                    acc[tau][step].append(cs.min_log_e(tau, side))
                idx += 1

    print(f"  {'tau':>6} {'V_rr':>9} | " + " ".join(
        f"{'n=' + str(n):>10}" for n in NGRID) + "   -> d_path    c")
    for tau in taus:
        v = v_rr(rates, tau, safe)
        oh = np.array([float(np.mean(acc[tau][n])) for n in NGRID])
        overhead = np.array(NGRID, dtype=float) * v - oh
        x = np.log(NGRID)
        A = np.vstack([x, np.ones_like(x)]).T
        (slope, c), *_ = np.linalg.lstsq(A, overhead, rcond=None)
        row = " ".join(f"{o:>10.2f}" for o in overhead)
        print(f"  {tau:>6.3f} {v:>9.5f} | {row}   -> "
              f"{2 * slope:>6.2f}  {c:>+6.2f}")
        # asymptotic rate check: slope of L(n) between the last two n
        n1, n2 = NGRID[-2], NGRID[-1]
        emp = (oh[-1] - oh[-2]) / (n2 - n1)
        print(f"         empirical local growth rate on [{n1},{n2}] = "
              f"{emp:.6f}  ratio to V_rr = {emp / v:.4f}")


def main():
    print("=" * 78)
    print("AUDIT: growth-rate and path-dimension measurement for UI+RR")
    print(f"{REPS} reps, n up to {NGRID[-1]}")
    print("=" * 78)
    run("gpt-4o-mini JSON (UNSAFE)", "llm_outcomes_diverse_json.jsonl",
        [0.15, 0.16, 0.17], safe=False)
    run("gpt-4.1-nano JSON (SAFE)",
        "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
        [0.12, 0.11, 0.10], safe=True)
    run("gpt-4o-mini CODE (SAFE)",
        "llm_outcomes_diverse_code_gpt-4o-mini.jsonl",
        [0.09, 0.08, 0.075], safe=True)
    run("gpt-4.1-nano CODE (SAFE)",
        "llm_outcomes_diverse_code_gpt-4.1-nano.jsonl",
        [0.04, 0.035, 0.03], safe=True)
    run("gpt-4.1-mini CODE (SAFE)",
        "llm_outcomes_diverse_code_gpt-4.1-mini.jsonl",
        [0.03, 0.025, 0.02], safe=True)


if __name__ == "__main__":
    main()
