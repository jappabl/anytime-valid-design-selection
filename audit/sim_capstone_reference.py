#!/usr/bin/env python3
"""AUDIT: what median SHOULD the capstone procedure produce?

The capstone claims a zero-fit closed-form prediction of the live median.
Rather than argue about the closed form, run the EXACT live procedure
(StratifiedUICS k=1, weights=[1.0], alpha=0.05, round-robin over the 4
strata, checks at n>=20 and n%4==0, n_max=2500) on synthetic streams with
known per-stratum rates and read the median off directly.

For k=1 the null set {w.m = tau} is the single point m = tau, so the
e-value has the closed form

    log E_n = -log(n+1) - log C(n, f) - f log(tau) - (n-f) log(1-tau)

(verified against StratifiedUICS.min_log_e to 1e-8), which makes a large
vectorised simulation cheap.

Reference points:
  (i)   offline pool rates 0.004/0.000/0.068/0.736 (p* = 0.2020)
        -- must reproduce results_overhead_law.txt's single-stream
        median 1024 at tau = 0.16
  (ii)  the de-biased live rates measured from the capstone log
        (0.00987/0.0/0.0779/0.7412, p* = 0.2072)
  (iii) an iid Bernoulli stream at the same p*, to size the effect of
        stratification (the log has variance ratio rho ~ 0.41)

It also reports the sampling distribution of the median of 16 reps, so
the prediction window's discriminating power is a number, not a claim.

Run: python3 audit/sim_capstone_reference.py
"""

import numpy as np
from scipy.special import gammaln

TAU, ALPHA, N_MAX = 0.16, 0.05, 2500
THRESH = float(np.log(1 / ALPHA))
CHECKS = np.arange(20, N_MAX + 1)
CHECKS = CHECKS[CHECKS % 4 == 0]
REPS = 20000


def log_e(n, f, tau):
    lc = gammaln(n + 1) - gammaln(f + 1) - gammaln(n - f + 1)
    return -(np.log(n + 1) + lc) - (f * np.log(tau) + (n - f) * np.log(1 - tau))


def simulate(rates, reps, seed):
    """Vectorised: returns (decision_code, stop_n) per rep.
    decision 1 = UNSAFE, -1 = SAFE, 0 = ABSTAIN."""
    rng = np.random.default_rng(seed)
    rates = np.asarray(rates, float)
    r_seq = np.tile(rates, N_MAX // 4 + 1)[:N_MAX]        # round-robin
    x = (rng.random((reps, N_MAX)) < r_seq).astype(np.int32)
    cf = np.cumsum(x, axis=1)
    dec = np.zeros(reps, dtype=np.int8)
    stop = np.full(reps, N_MAX, dtype=np.int32)
    live = np.ones(reps, dtype=bool)
    for n in CHECKS:
        if not live.any():
            break
        f = cf[live, n - 1].astype(float)
        le = log_e(float(n), f, TAU)
        ph = f / n
        hit_u = (ph > TAU) & (le >= THRESH)
        hit_s = (ph < TAU) & (le >= THRESH)
        idx = np.flatnonzero(live)
        for mask, code in ((hit_u, 1), (hit_s, -1)):
            sel = idx[mask]
            if sel.size:
                dec[sel] = code
                stop[sel] = n
        live[idx[hit_u | hit_s]] = False
    return dec, stop


def report(label, rates, reps=REPS, seed=99):
    dec, stop = simulate(rates, reps, seed)
    ns = stop[dec == 1]
    med = float(np.median(ns)) if ns.size else float("nan")
    print(f"  {label:42s} p*={float(np.mean(rates)):.4f}  "
          f"median {med:7.1f}  UNSAFE {int((dec == 1).sum())}/{reps} "
          f"SAFE {int((dec == -1).sum())} ABSTAIN {int((dec == 0).sum())}")
    if ns.size >= 16:
        rng = np.random.default_rng(5)
        m16 = np.median(rng.choice(ns, size=(40000, 16)), axis=1)
        q = np.percentile(m16, [2.5, 50, 97.5])
        inwin = float(np.mean((m16 >= 800) & (m16 <= 1450)))
        p16 = float(np.mean(np.sum(rng.choice(dec, size=(40000, 16)) == 1,
                                   axis=1) >= 14))
        print(f"  {'':42s} median-of-16: [{q[0]:.0f}, {q[1]:.0f}, "
              f"{q[2]:.0f}]  P(in [800,1450])={inwin:.3f}  "
              f"P(>=14/16 UNSAFE)={p16:.3f}")
    return med


def main():
    print("=" * 78)
    print("AUDIT: reference medians for the exact capstone procedure")
    print(f"{REPS} synthetic replications per rate vector, "
          f"tau={TAU}, checks at n>=20, n%4==0, n_max={N_MAX}")
    print("=" * 78)
    pool = [0.004, 0.000, 0.068, 0.736]
    live = [9 / 912, 0.0, 71 / 912, 676 / 912]

    print("\n(i) offline pool rates -- sanity check vs "
          "results_overhead_law.txt single-stream median 1024")
    report("pool 0.0040/0.0000/0.0680/0.7360", pool)

    print("\n(ii) de-biased live rates measured from the capstone log")
    report("live 0.0099/0.0000/0.0779/0.7412", live)

    print("\n(iii) sensitivity: uniform shift of the live rates")
    for delta in [-0.010, -0.005, -0.002, 0.002, 0.005]:
        report(f"live {delta:+.3f}", np.clip(np.array(live) + delta, 0, 1),
               reps=6000, seed=5)

    print("\n(iv) iid Bernoulli (no stratification) at the same p*")
    for p in [0.2020, 0.2072]:
        report(f"iid Bernoulli p={p}", [p] * 4, reps=6000, seed=7)

    print("\n(v) what live rate would make the procedure's median 1200?")
    lo, hi = 0.190, 0.212
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        scale = mid / float(np.mean(live))
        d, s = simulate(np.clip(np.array(live) * scale, 0, 1), 6000, 11)
        m = float(np.median(s[d == 1]))
        if m > 1200:
            lo = mid
        else:
            hi = mid
    print(f"  the exact procedure gives median ~1200 at p* ~ "
          f"{0.5 * (lo + hi):.4f}; the log's de-biased live p* is 0.2072 "
          f"(95% CI 0.194-0.220)")


if __name__ == "__main__":
    main()
