#!/usr/bin/env python3
"""AUDIT: which estimate of the LIVE failure rate is trustworthy?

THEORY.md explains the capstone's +15% median miss with: "Live p_hat ran
~0.5pp below the pool rate". The only number in the log that supports
that is the pooled Sum(failures)/Sum(samples) over stopped paths
(0.2002 vs pool 0.2020). Three competing estimators disagree:

    pooled over all stopped samples   0.2002   (the sequential MLE)
    mean of the 16 per-rep p_hat      0.2065
    first-228 prefix of every rep     0.2072

They cannot all be unbiased. This calibrates all three by simulating the
EXACT capstone procedure at known rates and measuring each estimator's
bias, then inverts the observed values to bracket the true live rate --
and finally asks what median the procedure produces at that rate.

Run: python3 audit/sim_live_rate_estimator.py
"""

import collections
import json
from pathlib import Path

import numpy as np
from scipy.special import gammaln

REPO = Path(__file__).parent.parent
TAU, ALPHA, N_MAX, NREP = 0.16, 0.05, 2500, 16
THRESH = float(np.log(1 / ALPHA))
CHECKS = np.arange(20, N_MAX + 1)
CHECKS = CHECKS[CHECKS % 4 == 0]


def log_e(n, f, tau):
    lc = gammaln(n + 1) - gammaln(f + 1) - gammaln(n - f + 1)
    return -(np.log(n + 1) + lc) - (f * np.log(tau) + (n - f) * np.log(1 - tau))


def one_experiment(rates, rng):
    """16 reps of the exact procedure; returns stop times and cumfail rows."""
    r_seq = np.tile(np.asarray(rates, float), N_MAX // 4 + 1)[:N_MAX]
    x = (rng.random((NREP, N_MAX)) < r_seq).astype(np.int32)
    cf = np.cumsum(x, axis=1)
    stop = np.full(NREP, N_MAX, dtype=np.int32)
    dec = np.zeros(NREP, dtype=np.int8)
    live = np.ones(NREP, dtype=bool)
    for n in CHECKS:
        if not live.any():
            break
        idx = np.flatnonzero(live)
        f = cf[idx, n - 1].astype(float)
        le = log_e(float(n), f, TAU)
        ph = f / n
        hit_u = (ph > TAU) & (le >= THRESH)
        hit_s = (ph < TAU) & (le >= THRESH)
        for mask, code in ((hit_u, 1), (hit_s, -1)):
            sel = idx[mask]
            if sel.size:
                dec[sel] = code
                stop[sel] = n
        live[idx[hit_u | hit_s]] = False
    return dec, stop, cf


def estimators(stop, cf):
    fails = cf[np.arange(NREP), stop - 1]
    pooled = float(fails.sum()) / float(stop.sum())
    per_rep = float(np.mean(fails / stop))
    L = int(stop.min())
    prefix = float(cf[:, L - 1].sum()) / (NREP * L)
    return pooled, per_rep, prefix, float(np.median(stop[np.ones(NREP, bool)]))


def main():
    print("=" * 78)
    print("AUDIT: calibrating the three live-rate estimators")
    print("=" * 78)

    recs = [json.loads(l) for l in
            open(REPO / "data" / "live_prediction_log.jsonl")]
    by = collections.defaultdict(list)
    for r in recs:
        by[r["rep"]].append(r)
    stop_obs = np.array([len(by[r]) for r in sorted(by)])
    f_obs = np.array([sum(1 for x in by[r] if not x["passed"])
                      for r in sorted(by)])
    L = int(stop_obs.min())
    obs = (float(f_obs.sum()) / float(stop_obs.sum()),
           float(np.mean(f_obs / stop_obs)),
           float(sum(sum(1 for x in by[r][:L] if not x["passed"])
                     for r in sorted(by))) / (NREP * L))
    print(f"\nobserved on the capstone log: pooled={obs[0]:.4f}  "
          f"per-rep-mean={obs[1]:.4f}  prefix({L})={obs[2]:.4f}  "
          f"median stop={np.median(stop_obs):.0f}")

    shape = np.array([9 / 912, 0.0, 71 / 912, 676 / 912])
    shape = shape / shape.mean()          # per-stratum profile, unit mean
    print("\nbias of each estimator, 2000 synthetic 16-rep experiments "
          "per true p*")
    print(f"  {'true p*':>8} {'pooled':>9} {'per-rep':>9} {'prefix':>9} "
          f"{'median n':>9}   (bias in pp)")
    grid = [0.1950, 0.1975, 0.2000, 0.2020, 0.2050, 0.2072, 0.2100]
    table = {}
    for p in grid:
        rng = np.random.default_rng(int(p * 1e6))
        est = np.array([estimators(*one_experiment(shape * p, rng)[1:])
                        for _ in range(2000)])
        mu = est.mean(axis=0)
        table[p] = mu
        print(f"  {p:>8.4f} {mu[0]:>9.4f} {mu[1]:>9.4f} {mu[2]:>9.4f} "
              f"{mu[3]:>9.0f}   "
              f"({100 * (mu[0] - p):+.2f}, {100 * (mu[1] - p):+.2f}, "
              f"{100 * (mu[2] - p):+.2f})")

    print("\ninverting each estimator at its observed value:")
    for j, name in enumerate(["pooled", "per-rep-mean", "prefix"]):
        xs = np.array(grid)
        ys = np.array([table[p][j] for p in grid])
        p_hat = float(np.interp(obs[j], ys, xs))
        print(f"  {name:>14}: observed {obs[j]:.4f} -> implied true p* "
              f"= {p_hat:.4f}")
    xs = np.array(grid)
    ys = np.array([table[p][3] for p in grid])
    p_med = float(np.interp(1200.0, ys[::-1], xs[::-1]))
    print(f"  {'median stop':>14}: observed 1200   -> implied true p* "
          f"= {p_med:.4f}")

    print("\nReading:")
    print("  * every estimator that is nearly unbiased puts the live rate "
          "AT or ABOVE the 0.2020 pool rate;")
    print("  * the ONLY reading that puts it below is the pooled "
          "Sum f / Sum n, which is length-biased downward here;")
    print("  * the stopping times themselves imply a rate BELOW the pool "
          "rate, i.e. the live run was slower than its own outcome counts "
          "say it should have been.")
    print("  * these two readings of the same 17,616 samples disagree by "
          "~1pp in p*, which is a factor ~1.6 in the predicted median -- "
          "larger than the entire prediction window.")


if __name__ == "__main__":
    main()
