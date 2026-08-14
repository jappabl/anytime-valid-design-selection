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

REVISION 2 (post-severe-test, per the peer re-analysis and
ISEF_PLAN.md 1.1 blocking prerequisite). The V1 design had two defects
this tool now detects and refuses:
  (a) JOINT SATISFIABILITY: criteria on multiple arms can become
      mutually exclusive once the first arm's outcome is realized
      (V1: median(tau1) = 982 forced C2 <= 240 while C3 required
      >= 253.4 — a dead zone the disclosed severity ignored). The
      check now runs conditional on every plausible realized first
      arm and reports the dead-zone probability.
  (b) DISCRIMINATING POWER: a window narrower than its statistic's
      sampling noise tests a coin (V1's C3: P(pass | theory true)
      = 0.59 vs P(pass | d = 0 world) computed here — if those are
      close, the criterion discriminates nothing). Each criterion now
      reports P(inside | d = 0), P(inside | d = 1), P(inside | d = 2)
      using the closed-form predicted centers under each dimension
      hypothesis with the d = 1 dispersion, and the tool REFUSES the
      design when the d = 1 pass probability does not exceed the best
      alternative by at least 0.30.

REVISION 3 RULES (post margin-sweep, per peer review): (c) PROCEDURE
IDENTITY — a power calculation is void unless the powered model and
the executed replay share the SAME stopping rule (v1 of the margin
sweep printed DESIGN ACCEPTED for a one-sided power model gating a
two-sided replay; the gate worked as built and still validated a
procedure that was not the one executed). Any test using this tool
must state the stopping rule once and assert both stages read it from
the same constant. (d) GATE EVERY CLAUSE — every scored criterion
must appear in the power calculation or be explicitly marked
ungated-and-why; the margin sweep's P4 was ungated and was exactly
the clause that turned out ill-posed.
"""

import sys

import numpy as np
from scipy.special import betaln

N_MAX = 4000
N_SIMS = 8000
LOG1A = float(np.log(20.0))
OFFSETS = [-0.006, 0.0, +0.006]   # pilot-estimate MC band (se 0.0053)


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

    # (a) JOINT SATISFIABILITY conditional on the realized first arm:
    # for each simulated m1, the C2 window and the C3-implied window
    # [r_lo*m1, r_hi*m1] must intersect.
    m1c = all_meds[0.0][0]
    m1c = m1c[~np.isnan(m1c)]
    # Stress the FULL plausible realization range, not just the
    # theory-true design distribution: V1's dead zone only bit because
    # m1 realized at 982, far outside its design spread — exactly the
    # regime (a rate error inflating both arms) where C2/C3 still get
    # scored. Any m1 up to 2.5x the design median must leave C2 and C3
    # jointly satisfiable.
    stress_lo = 0.4 * float(np.min(m1c))
    stress_hi = 2.5 * float(np.max(m1c))
    # Closed form: C2 [a2,b2] and C3 [r_lo,r_hi] are jointly
    # satisfiable iff r_lo*m1 <= b2 and r_hi*m1 >= a2, i.e.
    # m1 in [a2/r_hi, b2/r_lo]. The grid is display-only.
    win_lo = c2[0] / c3[1]
    win_hi = c2[1] / c3[0]
    print(f"\n  (a) joint satisfiability over realized m1 in "
          f"[{stress_lo:.0f}, {stress_hi:.0f}]:")
    print(f"      satisfiable window: m1 in [{win_lo:.0f}, "
          f"{win_hi:.0f}]; dead-zone tails: "
          f"[{stress_lo:.0f}, {win_lo:.0f}) and ({win_hi:.0f}, "
          f"{stress_hi:.0f}]")
    med_m1 = float(np.median(m1c))
    edge = min(abs(med_m1 - win_lo), abs(win_hi - med_m1))
    print(f"      design-expected m1 = {med_m1:.0f} "
          f"({edge:.0f} from the nearest window edge)")
    dead = float(not (stress_lo >= win_lo and stress_hi <= win_hi))
    if dead:
        print("      REFUSE: dead-zone tails are reachable within the "
              "stress range — a rate error inflating the first arm "
              "beyond the window forces C2/C3 mutually exclusive")

    # (b) DISCRIMINATING POWER: predicted medians under d in {0, 1, 2}
    # from n*V = log(1/alpha) + (d/2)*log n (c absorbed into the d=1
    # centering), scaled off the d = 1 simulated centers; pass
    # probabilities computed by shifting the d = 1 median distribution
    # to each alternative's predicted center.
    from scipy.optimize import brentq
    print("  (b) discriminating power per criterion "
          "(needs P(d=1) - max alt >= 0.30):")
    refuse = False
    for label, meds, win, tau in [("C1", all_meds[0.0][0], c1, tau1),
                                  ("C2", all_meds[0.0][1], c2, tau2)]:
        meds = meds[~np.isnan(meds)]
        v = (p_pool * np.log(p_pool / tau)
             + (1 - p_pool) * np.log((1 - p_pool) / (1 - tau)))
        center1 = float(np.median(meds))
        cc = center1 * v - np.log(20) - 0.5 * np.log(center1)
        ps = {}
        for d in (0, 1, 2):
            f = lambda n: n * v - np.log(20) - (d / 2) * np.log(n) - cc
            nd = brentq(f, 8, 1e7)
            shifted = meds * (nd / center1)
            ps[d] = float(np.mean((shifted >= win[0])
                                  & (shifted <= win[1])))
        gap = ps[1] - max(ps[0], ps[2])
        flag = "ok" if gap >= 0.30 else "REFUSE (window tests a coin)"
        refuse |= gap < 0.30
        print(f"      {label}: P(inside) d=0 {ps[0]:.2f} | d=1 "
              f"{ps[1]:.2f} | d=2 {ps[2]:.2f}  gap {gap:+.2f}  {flag}")
    # C3 (the ratio): its rate-cancellation also cancels most of its
    # d-sensitivity — compute the predicted ratio under each d and
    # score against the bootstrap dispersion of the realized ratio.
    r_meds = all_meds[0.0][2]
    r_meds = r_meds[~np.isnan(r_meds)]
    centers = {}
    for d in (0, 1, 2):
        nds = []
        for meds_c, tau in [(all_meds[0.0][0], tau1),
                            (all_meds[0.0][1], tau2)]:
            mc = meds_c[~np.isnan(meds_c)]
            v = (p_pool * np.log(p_pool / tau)
                 + (1 - p_pool) * np.log((1 - p_pool) / (1 - tau)))
            c1_ = float(np.median(mc))
            cc = c1_ * v - np.log(20) - 0.5 * np.log(c1_)
            f = lambda n: n * v - np.log(20) - (d / 2) * np.log(n) - cc
            nds.append(brentq(f, 8, 1e7))
        centers[d] = nds[1] / nds[0]
    r_center = float(np.median(r_meds))
    ps3 = {d: float(np.mean(((r_meds - r_center + centers[d]) >= c3[0])
                            & ((r_meds - r_center + centers[d]) <= c3[1])))
           for d in (0, 1, 2)}
    gap3 = ps3[1] - max(ps3[0], ps3[2])
    flag3 = "ok" if gap3 >= 0.30 else "REFUSE (window tests a coin)"
    refuse |= gap3 < 0.30
    print(f"      C3: P(inside) d=0 {ps3[0]:.2f} | d=1 {ps3[1]:.2f} | "
          f"d=2 {ps3[2]:.2f}  gap {gap3:+.2f}  {flag3}  (predicted "
          f"ratio centers {centers[0]:.3f}/{centers[1]:.3f}/"
          f"{centers[2]:.3f})")
    if refuse or dead > 0.05:
        print("\n  DESIGN NOT ACCEPTABLE under revision-2 rules.")


if __name__ == "__main__":
    main()
