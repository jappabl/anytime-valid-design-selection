#!/usr/bin/env python3
"""AUDIT: scoped reproduction of results_frontier.txt.

A full re-run of scripts/run_frontier.py exceeded the audit's compute
budget on a contended machine (the one-shot arm abstains on 76-100% of
paths and therefore runs every one of them to n_max = 6000, three times).
This reproduces the tau = 0.15 block for the four arms that matter to the
conservation claim, using the script's own code objects (imported by
exec, not re-implemented), and compares to the committed medians.

Because run_frontier.py re-seeds np.random.default_rng(BASE_SEED + 7919)
independently for every arm and every tau, restricting to one tau does
not perturb any number.

Run: python3 audit/repro_frontier_tau015.py
"""

import json
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

src = open(REPO / "scripts" / "run_frontier.py").read().split(
    '\nif __name__ == "__main__":')[0]
fr = types.ModuleType("fr")
fr.__dict__["__file__"] = str(REPO / "scripts" / "run_frontier.py")
exec(src, fr.__dict__)

COMMITTED = {"UI mixture": (200, 0, 960, 15.47),
             "epoch-split": (200, 0, 1502, 25.90),
             "single-stream": (200, 0, 576, 2.62),
             "WSR (ref)": (200, 0, 248, None)}


def main():
    pools = {s: [] for s in fr.STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    pools = {s: np.array(v, dtype=np.int8) for s, v in pools.items()}
    rates = np.array([float(pools[s].mean()) for s in fr.STRATA])
    p_star = float(rates.mean())
    tau = 0.15
    lam = w = np.full(4, 0.25)
    m = fr.bench._inner_min(lam, rates, w, tau)
    v_rr = float(np.sum(lam * [fr.bench.kl_bern(rates[i], m[i])
                               for i in range(4)]))
    v_pool = fr.bench.kl_bern(p_star, tau)
    log1a = float(np.log(1 / fr.ALPHA))

    print("=" * 78)
    print("AUDIT: scoped reproduction of results_frontier.txt, tau = 0.15")
    print("=" * 78)
    print(f"V_rr = {v_rr:.4f} (committed 0.0192), "
          f"V_pool = {v_pool:.4f} (committed 0.0097)\n")
    print(f"  {'arm':16s} {'cert':>9} {'median':>7} {'overhead':>9}   "
          f"committed")

    arms = [("UI mixture", lambda: fr.StratifiedUICS(k=4, alpha=fr.ALPHA)),
            ("epoch-split", lambda: fr.EpochSplitUICS(k=4, alpha=fr.ALPHA)),
            ("single-stream", lambda: fr.StratifiedUICS(k=1, weights=[1.0],
                                                        alpha=fr.ALPHA))]
    ok = True
    for name, mk in arms:
        rng = np.random.default_rng(fr.BASE_SEED + 7919)
        outs = [fr.run_arm(pools, tau, rng, mk) for _ in range(fr.N_REPS)]
        good = [n for d, n in outs if d == "UNSAFE"]
        ab = sum(1 for d, _ in outs if d == "ABSTAIN")
        med = int(np.median(good)) if good else None
        v = v_pool if name == "single-stream" else v_rr
        oh = med * v - log1a if med else None
        c = COMMITTED[name]
        match = (len(good) == c[0] and ab == c[1] and med == c[2]
                 and abs(oh - c[3]) < 0.005)
        ok &= match
        print(f"  {name:16s} {len(good):>4d}/200 {med:>7d} {oh:>+9.2f}   "
              f"{c[2]:>5d} {c[3]:+.2f}  {'MATCH' if match else 'MISMATCH'}")

    rng = np.random.default_rng(fr.BASE_SEED + 7919)
    outs = [fr.run_wsr(pools, tau, rng) for _ in range(fr.N_REPS)]
    good = [n for d, n in outs if d == "UNSAFE"]
    med = int(np.median(good)) if good else None
    c = COMMITTED["WSR (ref)"]
    match = (len(good) == c[0] and med == c[2])
    ok &= match
    print(f"  {'WSR (ref)':16s} {len(good):>4d}/200 {med:>7d} "
          f"{'--':>9}   {c[2]:>5d}         "
          f"{'MATCH' if match else 'MISMATCH'}")

    print(f"\n  tau=0.15 block reproduces exactly: {ok}")
    print(f"  conservation ratio at tau=0.15: "
          f"{25.90 / 15.47:.3f}  (pre-registered window [0.7, 1.5])")


if __name__ == "__main__":
    main()
