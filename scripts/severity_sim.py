#!/usr/bin/env python3
"""Severity calibrator for the severe live test.

Audit round 2 showed the first capstone was near-unfalsifiable
(P(pass) ~ 0.94). This tool computes, BEFORE launch, the probability
that the severe test passes under "theory + pool rates + an assumed
live-rate offset band" — so the frozen window can be CHOSEN to make
the test hard (target overall severity ~0.6-0.75) and the number is
disclosed in the pre-registration rather than discovered by auditors.

Simulates the exact procedure: k=1 single-stream mixture CS on a
Bernoulli stream at rate p_live, decision checks every 4th sample from
n >= 20, UNSAFE when rejects_le(tau) fires, cap n_max. The e-value is
the closed form log E = betaln(1+f, 1+s) - [f log tau + s log(1-tau)]
(the boundary of the [0, tau] null maximizes the null likelihood when
p_hat > tau), which matches StratifiedUICS(k=1) — verified by the
audit's sim_capstone_reference.py to 1e-8.

Usage:
    python3 scripts/severity_sim.py <p_pool> <tau1> <tau2> <reps_per_tau>
Then iterate window choices in-place (edit CANDS) and freeze the final
numbers into run_severe_live.py.
"""

import sys

import numpy as np
from scipy.special import betaln

N_MAX = 4000
N_SIMS = 8000
LOG1A = float(np.log(20.0))
OFFSETS = [-0.008, 0.0, +0.008]   # assumed live-vs-pool rate band


def crossing_times(p_live, tau, sims, rng):
    """Vectorized stopping times for `sims` streams at rate p_live."""
    x = (rng.random((sims, N_MAX)) < p_live).astype(np.int32)
    f = np.cumsum(x, axis=1)
    n = np.arange(1, N_MAX + 1)
    s = n[None, :] - f
    log_e = (betaln(1 + f, 1 + s)
             - (f * np.log(tau) + s * np.log(1 - tau)))
    check = (n >= 20) & (n % 4 == 0)
    fired = (log_e >= LOG1A) & check[None, :]
    first = np.where(fired.any(axis=1), fired.argmax(axis=1) + 1, 0)
    return first  # 0 = never fired (abstain)


def median_dist(p_live, tau, reps, rng, batches=400):
    """Distribution of the median over `reps` replications."""
    times = crossing_times(p_live, tau, batches * reps, rng)
    times = times.reshape(batches, reps)
    ok = times > 0
    meds = np.array([np.median(t[o]) if o.sum() >= reps * 0.75 else np.nan
                     for t, o in zip(times, ok)])
    return meds, ok.mean()


def main():
    p_pool, tau1, tau2, reps = (float(sys.argv[1]), float(sys.argv[2]),
                                float(sys.argv[3]), int(sys.argv[4]))
    rng = np.random.default_rng(20260812)

    print(f"p_pool={p_pool}, taus=({tau1}, {tau2}), reps/tau={reps}, "
          f"offsets={OFFSETS}, n_max={N_MAX}")
    all_meds = {}
    for off in OFFSETS:
        p = p_pool + off
        m1, cert1 = median_dist(p, tau1, reps, rng)
        m2, cert2 = median_dist(p, tau2, reps, rng)
        ratio = m2 / m1
        all_meds[off] = (m1, m2, ratio)
        print(f"  offset {off:+.3f}: median(tau1) "
              f"[{np.nanpercentile(m1, 5):.0f}, "
              f"{np.nanpercentile(m1, 50):.0f}, "
              f"{np.nanpercentile(m1, 95):.0f}] cert {cert1:.3f} | "
              f"median(tau2) [{np.nanpercentile(m2, 5):.0f}, "
              f"{np.nanpercentile(m2, 50):.0f}, "
              f"{np.nanpercentile(m2, 95):.0f}] cert {cert2:.3f} | "
              f"ratio [{np.nanpercentile(ratio, 5):.3f}, "
              f"{np.nanpercentile(ratio, 50):.3f}, "
              f"{np.nanpercentile(ratio, 95):.3f}]")

    # Candidate windows: evaluate P(pass all criteria) under the
    # CENTRAL offset and under the band edges.
    c1 = (np.nanpercentile(all_meds[0.0][0], 12),
          np.nanpercentile(all_meds[0.0][0], 88))
    c2 = (np.nanpercentile(all_meds[0.0][1], 12),
          np.nanpercentile(all_meds[0.0][1], 88))
    c3 = (np.nanpercentile(all_meds[0.0][2], 8),
          np.nanpercentile(all_meds[0.0][2], 92))
    print(f"\n  proposed windows (from central offset):")
    print(f"    C1 median(tau1) in [{c1[0]:.0f}, {c1[1]:.0f}]")
    print(f"    C2 median(tau2) in [{c2[0]:.0f}, {c2[1]:.0f}]")
    print(f"    C3 ratio in [{c3[0]:.3f}, {c3[1]:.3f}]")
    for off in OFFSETS:
        m1, m2, ratio = all_meds[off]
        p1 = np.nanmean((m1 >= c1[0]) & (m1 <= c1[1]))
        p2 = np.nanmean((m2 >= c2[0]) & (m2 <= c2[1]))
        p3 = np.nanmean((ratio >= c3[0]) & (ratio <= c3[1]))
        pall = np.nanmean((m1 >= c1[0]) & (m1 <= c1[1])
                          & (m2 >= c2[0]) & (m2 <= c2[1])
                          & (ratio >= c3[0]) & (ratio <= c3[1]))
        print(f"    offset {off:+.3f}: P(C1)={p1:.2f} P(C2)={p2:.2f} "
              f"P(C3)={p3:.2f}  P(all)={pall:.2f}")


if __name__ == "__main__":
    main()
