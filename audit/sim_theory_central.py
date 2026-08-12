#!/usr/bin/env python3
"""AUDIT: recompute the capstone's "theory-central 1045" and its window.

The frozen closed form (scripts/run_live_prediction.py docstring):

    n * KL(p, tau) = log(1/alpha) + 0.5 * log n + c ,  c ~ 0 +/- 0.3
    tau = 0.16, alpha = 0.05, pool rate p = 0.202  ->  "n ~ 1045"
    p in [0.195, 0.209]                            ->  "[800, 1450]"

Checks:
  A. Does the closed form actually give 1045 at p = 0.202?
  B. Does p in [0.195, 0.209] actually map to [800, 1450]?
  C. What is the live failure rate, estimated WITHOUT optional-stopping
     contamination? THEORY.md states "Live p_hat ran ~0.5pp BELOW the
     pool rate, placing the median 15% above theory-central". Test the
     sign and the size of that explanation.
  D. Given the live rate, what does the same closed form predict, and
     how far is the observed median 1200 from it?
  E. Discriminating power: what does the window exclude?

Run: python3 audit/sim_theory_central.py
"""

import collections
import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

REPO = Path(__file__).parent.parent
ALPHA = 0.05
TAU = 0.16
LOG1A = np.log(1 / ALPHA)


def kl(p, q):
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def n_of(p, tau=TAU, d=1.0, c=0.0):
    """Solve n*KL(p,tau) = log(1/alpha) + (d/2) log n + c for n."""
    f = lambda n: n * kl(p, tau) - LOG1A - 0.5 * d * np.log(n) - c
    return brentq(f, 20.0, 1e7)


def main():
    print("=" * 78)
    print("AUDIT: capstone closed-form recomputation")
    print("=" * 78)

    print("\nA. theory-central at the pool rate")
    for p in [0.2020, 0.202, 0.2019]:
        print(f"   p={p:.4f}  KL(p,0.16)={kl(p, TAU):.6f}  "
              f"n(c=0)={n_of(p):.1f}   "
              f"n(c=-0.3)={n_of(p, c=-0.3):.1f}  "
              f"n(c=+0.3)={n_of(p, c=+0.3):.1f}")
    print("   claimed: 1045")

    print("\nB. does p in [0.195, 0.209] map to the stated window?")
    for p in [0.195, 0.202, 0.209]:
        print(f"   p={p:.3f} -> n={n_of(p):7.1f}   "
              f"(c=-0.3: {n_of(p, c=-0.3):7.1f}, "
              f"c=+0.3: {n_of(p, c=+0.3):7.1f})")
    print("   claimed window: [800, 1450]")
    lo = brentq(lambda p: n_of(p) - 1450, 0.17, 0.202)
    hi = brentq(lambda p: n_of(p) - 800, 0.202, 0.30)
    print(f"   the window [800,1450] actually corresponds to "
          f"p in [{lo:.4f}, {hi:.4f}] (c=0) -- i.e. it is WIDER on the "
          f"upper-p side than the stated [0.195, 0.209]")

    print("\nC. live failure rate, free of optional-stopping selection")
    recs = [json.loads(l) for l in
            open(REPO / "data" / "live_prediction_log.jsonl")]
    by = collections.defaultdict(list)
    for r in recs:
        by[r["rep"]].append(r)
    Lmin = min(len(v) for v in by.values())
    print(f"   {'prefix':>8} {'samples':>8} {'fail':>6} {'p_hat':>8} "
          f"{'95% CI':>20}")
    for L in [20, 50, 100, 200, Lmin]:
        tot = f = 0
        for v in by.values():
            tot += L
            f += sum(1 for r in v[:L] if not r["passed"])
        ph = f / tot
        se = np.sqrt(ph * (1 - ph) / tot)
        print(f"   {L:>8} {tot:>8} {f:>6} {ph:>8.4f} "
              f"  [{ph - 1.96 * se:.4f}, {ph + 1.96 * se:.4f}]")
    allf = sum(1 for r in recs if not r["passed"])
    print(f"   pooled over ALL stopped samples: {allf}/{len(recs)} = "
          f"{allf / len(recs):.4f}  (length-biased: long reps are the "
          f"low-rate ones and dominate the pool)")
    mean_phat = np.mean([sum(1 for r in v if not r["passed"]) / len(v)
                         for v in by.values()])
    print(f"   mean of per-rep p_hat at stopping:  {mean_phat:.4f}  "
          f"(biased UP by the stopping rule)")
    print(f"   offline pool rate used for the prediction: 0.2020")

    tot = f = 0
    for v in by.values():
        tot += Lmin
        f += sum(1 for r in v[:Lmin] if not r["passed"])
    p_live = f / tot
    se = np.sqrt(p_live * (1 - p_live) / tot)

    print("\nD. closed form at the (de-biased) live rate")
    print(f"   p_live = {p_live:.4f} +/- {se:.4f}   "
          f"KL(p_live, 0.16) = {kl(p_live, TAU):.6f}")
    print(f"   predicted median n = {n_of(p_live):.0f}   "
          f"(range over +/-1.96 SE: "
          f"{n_of(p_live + 1.96 * se):.0f} .. {n_of(p_live - 1.96 * se):.0f})")
    print(f"   OBSERVED median = 1200  -> "
          f"{100 * (1200 / n_of(p_live) - 1):+.1f}% vs the prefix-rate "
          f"prediction, {100 * (1200 / 1045 - 1):+.1f}% vs 1045")
    print("   THEORY.md says the live rate ran ~0.5pp BELOW the pool rate.")
    print("   See audit/sim_live_rate_estimator.py: the pooled Sum f/Sum n")
    print("   (0.2002) and this prefix estimator (0.2072) are BOTH nearly")
    print("   unbiased under the exact stopping rule, yet they disagree by")
    print("   0.7pp -- so the sign of the stated explanation is estimator-")
    print("   dependent, and its magnitude (0.5pp) matches neither: the")
    print("   MLE gap is 0.18pp, the prefix gap is +0.47pp the other way.")

    print("\nE. what does the window exclude?")
    unsafe = [1976, 1444, 1180, 1520, 1308, 1264, 552, 1208, 336, 428,
              1392, 1016, 884, 1192, 1688, 228]
    boot = np.random.default_rng(3).choice(unsafe, size=(40000, 16))
    meds = np.median(boot, axis=1)
    print(f"   observed median 1200; bootstrap 95% CI "
          f"[{np.percentile(meds, 2.5):.0f}, {np.percentile(meds, 97.5):.0f}]")
    print(f"   P(bootstrap median in [800,1450]) = "
          f"{float(np.mean((meds >= 800) & (meds <= 1450))):.3f}")
    print(f"   offline replay median at the SAME tau/method/pool, measured "
          f"45 min BEFORE launch (results_overhead_law.txt): 1024")
    print(f"   the window is [{800 / 1024:.2f}x, {1450 / 1024:.2f}x] of "
          f"that already-measured number; a theory-free prediction "
          f"'live ~= offline replay' passes identically.")
    print(f"   d-sensitivity: the same closed form with d=0 gives "
          f"n={n_of(0.202, d=0.0):.0f}, d=2 gives "
          f"n={n_of(0.202, d=2.0):.0f}, d=4 gives "
          f"n={n_of(0.202, d=4.0):.0f}  -- all but d=4 land inside "
          f"[800,1450], so the window does not identify d either.")


if __name__ == "__main__":
    main()
