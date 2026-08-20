#!/usr/bin/env python3
"""Measure the JOINT (heterogeneity R, block size K) surface of the WSR
overhead envelope.

WHY. results_wsr_k.txt (checksum f6aea65aa754d0d8) measured the envelope's
K-dependence on a HOMOGENEOUS grid (R = 1) and found its constants linear in
K, d_K = 4.1407 - 0.4267 K and c_K = 0.9638 K - 8.9801. Its own diagnostic
then showed that a K-only correction accounts for most of the MAGNITUDE of
the safety-domain miss (results_safety.txt, checksum a369e454bc5450fd) and
NONE of its RESOLUTION, and recorded the honest next clause verbatim: the
envelope needs a JOINT c(R, K), not a K-only patch. That clause has been
outstanding since THEORY.md (2026-08-15) recorded near-homogeneity running
~0.7-1.0 nats cheaper than an envelope calibrated on extreme-heterogeneity
pools -- the long-hypothesized c_short(R) dependence, never measured on a
designed grid. This script measures it.

PRE-REGISTERED PROTOCOL (committed with the artifact; the protocol is a
measurement GRID, not a prediction test, so the freeze is the protocol plus
the three predicates -- all of which print PASS/FAIL).

SETUP. Two-level K-stratum pools: half the strata at p_lo, half at p_hi with
p_hi / p_lo = R and (p_lo + p_hi)/2 = p* exactly (K in {2, 4, 6} are even, so
the half-half split hits the mean exactly; no ceil/floor adjustment is
needed). A BLOCK is one draw per stratum in round-robin order; the block mean
over K is fed to the SHIPPED WSRBlockCS(alpha=0.05) (not a reimplementation);
the run certifies UNSAFE the first block at which the CS lower bound clears
tau = p* - delta (polled every block, as in run_wsr_expansion.py and
measure_wsr_k.py). Median crossing over reps; non-crossing reps censored at
n_max. R = 1 reduces to the homogeneous pool of the K artifact.

CRN. One uniform stream per (p*, rung, rep), seeded from (p*, rung) alone and
therefore SHARED by all twelve (K, R) arms of that rung; the stream is mapped
to strata by position mod K and thresholded at that arm's stratum rates. K and
R change the mapping and the thresholds, never the randomness.

V (information rate). The block mean is (1/K) * sum of K INDEPENDENT
NON-IDENTICAL Bernoullis, i.e. a Poisson-binomial scaled by 1/K. Its exact PMF
is computed by dynamic-programming convolution in O(K^2) (no 2**K enumeration,
no simulation), then
    V = max_lam E[log(1 + lam*(M_K - tau))] / K
over the project's lambda convention (3000-point grid on (0.001, 1/tau)). The
first line of the artifact verifies this against derive_phase_boundary's
v_kelly_block (the shipped 2**K enumeration) at K=4: both at (K=4, R=1) as
required, and over the ENTIRE K=4 sub-grid (all R, all p*, all tau) since the
enumeration is exact for unequal rates too.

GRID (frozen). K in {2, 4, 6} x R in {1, 3, 10, 30} x p* in {0.20, 0.35}; four
margins per cell. Every tau is a 3-decimal multiple of 0.001, the identical
convention to run_safety_cert's round(mu - m, 3). The ladder is solved PER
(p*, R) so that the K=4 median lands near the SAME four targets
{250, 800, 2500, 8000} in every cell, and is then shared by K = 2 and 6 (V is
recomputed exactly per K). Designing to a common n-window is deliberate: an
EFFECTIVE LOCAL fit depends on the range it is taken over, so if cells were
fit over different n-ranges a range difference would masquerade as
R-dependence. DISCLOSED DEVIATION from the task sketch: four margins spanning
~32x in n, not ~8x. Two free parameters fit from eight points need leverage in
log n, and ~8x cannot reach the requested 200-15000 window at all; the
operative constraint (every median inside ~200-15000) is met -- measured
medians run ~210 to ~14000. Reps taper 250/250/180/120 from shallow to deep
rungs (DISCLOSED: the deep rungs are the expensive ones and carry fewer reps).
n_max = 10x the target median (rounded up to a whole number of blocks); a
16-cell pilot at the grid corners crossed 100% at that cap (grid DESIGN, not a
result). n_max only controls censoring, and the validity guard checks it.

FIT. Per (K, R) cell the two p* ladders are POOLED (8 rungs per cell, stated
here and again at the table), and with O(n) := n*V - log(1/alpha) the
single-regime form
    O = (d/2) log n + c
is fit by OLS on log n. Single-regime only: the K artifact's pre-registered
uniform selection rule already reported the single-regime pair (the plateau
was absent at K=2), so this is like-for-like with the anchor. OLS standard
errors are printed so P1 can be read at the right resolution.

PRE-REGISTERED PREDICATES:
  P1 (REGRESSION ANCHOR) the R = 1 column reproduces results_wsr_k.txt's
     measured (d_K, c_K) at K = 2, 4, 6 within +/-0.25 in d and +/-0.6 in c.
     The anchor artifact's checksum is re-verified and its constants are
     PARSED out of it and asserted against the values hard-coded here, so the
     comparison cannot silently drift. NOTE the two grids are not identical:
     the anchor used p in {0.20, 0.35, 0.50} x 5 margins over n ~ 200-24000,
     this one uses p* in {0.20, 0.35} x 4 margins over n ~ 210-14000. P1 asks
     whether the same envelope comes back through a differently-designed
     window, which is the useful anchor question.
  P2 (THE JOINT CLAUSE) at fixed K, c varies MONOTONICALLY in R across
     R = 1, 3, 10, 30. Direction is NOT pre-committed; whatever is measured is
     stated. This is the long-hypothesized c_short(R) dependence on a designed
     grid for the first time. d's behaviour in R is reported but NOT scored.
  P3 (VALIDITY GUARD) every rung achieves >= 90% crossings. Rungs below 90%
     are EXCLUDED from every fit and reported; P3 FAILS if any rung had to be
     excluded. HARD GUARD: if fewer than 6 of the 8 rungs certify in any cell
     the artifact declares itself INVALID and scores no verdicts at all.

SURFACE FIT (OBSERVED REGULARITY, explicitly NOT a derivation). Least squares
over the 12 cells of
    d(K, R) = a + b*K + e*log R,      c(K, R) = f + g*K + h*log R.
Coefficients, max residual and the full 12-cell residual table are printed.
log R is ACCEPTED as the carrier for a constant iff (i) max|residual| <= 15%
of that constant's range over the 12 cells AND (ii) the residual sign pattern
across R is not identical in all three K rows (which would be structure the
form is missing). If it is rejected, the artifact says so and prints the
residual table rather than fitting something else to force it.

POST-HOC DIAGNOSTIC (clearly labeled; does NOT re-score the safety miss, which
stands as a scored ledger miss). run_safety_cert.py's prediction step is
reused verbatim -- its load_pool, its mu, its tau = round(mu - 0.045, 3), its
single_fourterm, its 64-atom v_kelly_block_K at K=6, its +/-5% tie band --
with only the WSR overhead swapped, for ALL SIX scored pools at their own
(p*, R) and K = 6. Three overheads:
  COMMITTED  the K=4 central envelope (must reproduce the frozen table),
  JOINT-S    THE HEADLINE: the fitted surface evaluated at (K=6, R_pool),
  JOINT-I    robustness: linear-in-log-R interpolation between the MEASURED
             K=6 cells bracketing R_pool (no surface form assumed).
Reported per pool: predicted n_wsr, its signed percentage error against the
measured WSR median parsed out of results_safety.txt (whose checksum is
re-verified), and the resulting design call. Positive error = over-predicts
n_wsr = WSR looks slower than it is, the direction of the +19 to +37% safety
miss. A fitted overhead extrapolated below its measured range can go negative,
in which case the solve reports '<4' -- an EXTRAPOLATION ARTIFACT read as "WSR
immediately", never as no-crossing. The pre-registered diagnostic question is
the one asked of this artifact: does the joint envelope give >= 2 RESOLVING
predictions AND match the measured winners better than the frozen 1/2? Both
clauses are answered explicitly.

SCOPE / KNOWN SYSTEMATICS (stated before the numbers):
  * The grid's R is a two-level half-half ratio. A real pool's R is
    max/min over six category rates, a coarser summary of a richer profile;
    evaluating the surface at that summary is an ASSUMPTION, disclosed, not a
    proof of equivalence.
  * The surface has no p* term by construction (the two p* ladders are pooled
    per cell). The grid spans p* in {0.20, 0.35}; the safety pools span 0.107
    to 0.857, so the diagnostic EXTRAPOLATES in p* on mistral-7b (0.857) most
    of all. Disclosed; it is the same extrapolation the K artifact carried.
  * Stock WSR has NO fixed (d, c) asymptotically (results_wsr_expansion.txt:
    nV ~ A log n (loglog n)^2). Every envelope here is an EFFECTIVE LOCAL fit
    over the measured range, which is the range the boundary machinery is
    actually used in. It is not an expansion claim.
  * tau on the 0.001 lattice sits mid-cell on the shipped CS grid
    (linspace(0.0005, 0.9995, 1000)), a fixed +0.0005 effective-margin offset,
    0.6-3.6% of the margin (printed per rung). It is the same convention
    run_safety_cert uses and it is held FIXED across every cell, so it cannot
    masquerade as R- or K-dependence.
  * V is evaluated at the NOMINAL tau, as the shipped machinery does.

Offline, deterministic (fixed seeds; rungs are independent, so the worker-pool
schedule cannot affect any number). Writes results_wsr_rk.txt.
"""

import hashlib
import io
import math
import multiprocessing as mp
import os
import re
import sys
import types as _types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

ALPHA = 0.05
L = float(np.log(1 / ALPHA))
BASE_SEED = 42
KS = (2, 4, 6)
RS = (1, 3, 10, 30)
PS = (0.20, 0.35)
TARGETS = (250, 800, 2500, 8000)
REPS = (250, 250, 180, 120)
NMAX_MULT = 10
MIN_CERTIFIED_PER_CELL = 6      # of 8; below this the artifact is INVALID

# Frozen tau ladder: solved per (p*, R) at K=4 to the TARGETS above, on the
# 0.001 lattice, then shared by every K. See docstring (grid DESIGN).
LADDER = {
    (0.20, 1): [0.133, 0.156, 0.171, 0.182],
    (0.20, 3): [0.135, 0.157, 0.172, 0.183],
    (0.20, 10): [0.138, 0.159, 0.174, 0.184],
    (0.20, 30): [0.139, 0.160, 0.174, 0.184],
    (0.35, 1): [0.266, 0.295, 0.315, 0.329],
    (0.35, 3): [0.271, 0.299, 0.318, 0.330],
    (0.35, 10): [0.279, 0.305, 0.322, 0.333],
    (0.35, 30): [0.284, 0.308, 0.324, 0.334],
}

# results_wsr_k.txt anchor (its REPORTED CONSTANTS PER K, single-regime pair);
# parsed out of the artifact and asserted against these at run time.
ANCHOR = {2: (3.386, -6.922), 4: (2.343, -5.351), 6: (1.465, -3.138)}
ANCHOR_LAW = ((4.1407, -0.4267), (-8.9801, 0.9638))   # d = a+bK, c = a+bK
ANCHOR_SHA = "f6aea65aa754d0d8"
SAFETY_SHA = "a369e454bc5450fd"
P1_DTOL, P1_CTOL = 0.25, 0.6
SURFACE_TOL = 0.15


def profile(p_star, r, k):
    """Two-level K-stratum profile: k/2 at p_lo, k/2 at p_hi, p_hi/p_lo = R,
    mean exactly p*."""
    p_hi = 2 * p_star * r / (1 + r)
    return np.array([p_hi / r] * (k // 2) + [p_hi] * (k // 2))


def poisson_binomial_pmf(rates):
    """Exact PMF of the sum of independent non-identical Bernoullis, by DP
    convolution in O(K^2)."""
    pmf = np.array([1.0])
    for p in rates:
        nxt = np.zeros(len(pmf) + 1)
        nxt[:-1] += pmf * (1 - p)
        nxt[1:] += pmf * p
        pmf = nxt
    return pmf


def v_kelly_pb(rates, tau):
    """Per-sample Kelly growth of the EXACT block-mean law (Poisson-binomial
    over the K stratum rates, divided by K); same 3000-point lambda grid as
    derive_phase_boundary.v_kelly_block."""
    k = len(rates)
    pmf = poisson_binomial_pmf(rates)
    atoms = np.arange(k + 1) / k
    lams = np.linspace(0.001, 1 / max(tau, 1e-9) - 1e-6, 3000)
    return float(np.max(np.log1p(np.outer(lams, atoms - tau)) @ pmf)) / k


def median_crossing(rates, tau, reps, n_max, seed0):
    """Median UNSAFE-crossing sample count and the crossing fraction. Same
    instrument as measure_wsr_k.median_crossing, with the block built as one
    draw per stratum (round-robin) instead of one iid draw per slot."""
    k = len(rates)
    n_blocks = n_max // k
    times = []
    done = 0
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        u = rng.random(n_blocks * k).reshape(n_blocks, k)
        means = (u < rates).mean(axis=1)
        cs = WSRBlockCS(alpha=ALPHA)
        crossed = None
        for j in range(n_blocks):
            cs.update(float(means[j]))
            lo, _ = cs.get_bounds()
            if lo > tau:
                crossed = k * (j + 1)
                break
        if crossed:
            done += 1
            times.append(crossed)
        else:
            times.append(n_max)
    return int(np.median(times)), done / reps


def build_jobs():
    """Frozen job list: one (K, R, p*, rung) entry each; CRN seed per
    (p*, rung), shared by all twelve (K, R) arms."""
    jobs = []
    for pi, p in enumerate(PS):
        for ri, target in enumerate(TARGETS):
            seed0 = BASE_SEED + 1000 * (10 * pi + ri)
            for k in KS:
                n_blocks = math.ceil(NMAX_MULT * target / k)
                for r in RS:
                    jobs.append(dict(k=k, r=r, p=p, ri=ri,
                                     tau=LADDER[(p, r)][ri], reps=REPS[ri],
                                     n_max=k * n_blocks, seed0=seed0))
    return jobs


def _run_job(job):
    rates = profile(job["p"], job["r"], job["k"])
    n, frac = median_crossing(rates, job["tau"], job["reps"], job["n_max"],
                              job["seed0"])
    return job["k"], job["r"], job["p"], job["ri"], n, frac


def fit_line(logn, o):
    """OLS of O on (log n / 2, 1); returns d, c, SSE, max|resid|, SE_d, SE_c."""
    a = np.stack([logn / 2, np.ones_like(logn)], axis=1)
    (d, c), *_ = np.linalg.lstsq(a, o, rcond=None)
    resid = o - (d * logn / 2 + c)
    sse = float(np.sum(resid ** 2))
    dof = max(len(o) - 2, 1)
    cov = (sse / dof) * np.linalg.inv(a.T @ a)
    return (float(d), float(c), sse, float(np.max(np.abs(resid))),
            float(np.sqrt(cov[0, 0])), float(np.sqrt(cov[1, 1])))


def crossing_with_overhead(v, o_fn):
    """Solve n*V = log(1/alpha) + O(n); mirrors wsr_crossing's bracket.
    Returns (n, flag). A fitted overhead extrapolated below its fitted range
    can go negative, so the model claims a crossing before the bracket floor:
    an EXTRAPOLATION ARTIFACT, flagged 'below-range', never silently inf."""
    from scipy.optimize import brentq
    if v <= 0:
        return float("inf"), "no-signal"
    f = lambda n: n * v - L - o_fn(n)
    if f(4.0) > 0:
        return 4.0, "below-range"
    try:
        return float(brentq(f, 4.0, 1e8)), "ok"
    except ValueError:
        return float("inf"), "above-range"


def call_of(n_s, n_w, band):
    if not np.isfinite(n_w):
        return "single"
    if abs(n_s - n_w) / min(n_s, n_w) < band:
        return "tie"
    return "single" if n_s < n_w else "wsr"


def read_artifact(name, expect_sha):
    """Read a committed artifact and re-verify its own SHA256 footer."""
    text = (REPO / name).read_text()
    marker = "\n" + "=" * 76 + "\nChecksum (SHA256): "
    body, rest = text.split(marker, 1)
    stated = rest.split("\n", 1)[0].strip()
    recomputed = hashlib.sha256(body.encode()).hexdigest()[:16]
    ok = stated == recomputed == expect_sha
    return body, stated, recomputed, ok


def parse_anchor(body):
    """Parse results_wsr_k.txt's REPORTED CONSTANTS PER K table."""
    out = {}
    tail = body.split("REPORTED CONSTANTS PER K", 1)[1]
    for line in tail.splitlines():
        m = re.match(r"\s+(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$", line)
        if m:
            out[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
        elif out:
            break
    return out


def parse_safety(body):
    rows = {}
    for line in body.splitlines():
        m = re.match(r"\s+(\S+)\s+dir=\S+ \(p\*>tau\): meds "
                     r"S(\d+) U(\d+) W(\d+)", line)
        if m:
            w = re.search(r"measured (SINGLE|WSR|TIE)", line)
            rows[m.group(1)] = dict(single=int(m.group(2)),
                                    wsr=int(m.group(4)),
                                    measured=w.group(1).lower() if w else "?")
    return rows


def load_safety_machinery():
    src = open(REPO / "scripts" / "run_safety_cert.py").read()
    mod = _types.ModuleType("sc")
    mod.__dict__["__file__"] = str(REPO / "scripts" / "run_safety_cert.py")
    exec(src.rsplit("if __name__", 1)[0], mod.__dict__)
    return mod


# Shipped 2**K enumeration, loaded lazily (parent process only).
def _pbv(rates, tau):
    global _PB
    try:
        _PB
    except NameError:
        src = open(REPO / "scripts" / "derive_phase_boundary.py").read()
        _PB = _types.ModuleType("pb")
        _PB.__dict__["__file__"] = str(REPO / "scripts"
                                       / "derive_phase_boundary.py")
        exec(src.rsplit("if __name__", 1)[0], _PB.__dict__)
    return _PB.v_kelly_block(rates, tau)


def main():
    print("=" * 76)
    print("WSR OVERHEAD ENVELOPE: JOINT (R, K) SURFACE")
    print("=" * 76)
    print(f"alpha={ALPHA}, K in {KS} x R in {RS} x p* in {PS}, two-level "
          f"K-stratum pools (half\nat p_lo, half at p_hi, p_hi/p_lo = R, mean "
          f"p*), one draw per stratum per block, shipped\nWSRBlockCS polled "
          f"every block, certify UNSAFE at tau = p* - delta.")

    body_k, st_k, rc_k, ok_k = read_artifact("results_wsr_k.txt", ANCHOR_SHA)
    parsed = parse_anchor(body_k)
    same = all(parsed.get(k) == ANCHOR[k] for k in ANCHOR)
    print(f"\nAnchor artifact results_wsr_k.txt: stated {st_k}, recomputed "
          f"{rc_k} -> {'OK' if ok_k else 'STALE'} (expected {ANCHOR_SHA});\n"
          f"  its parsed (d_K, c_K) at K=2,4,6 == the values scored here: "
          f"{'OK' if same else 'MISMATCH'}  {ANCHOR}")

    chk1 = max(abs(v_kelly_pb(profile(p, 1, 4), tau) - _pbv(profile(p, 1, 4),
                                                            tau))
               for p in PS for tau in LADDER[(p, 1)])
    chkall = max(abs(v_kelly_pb(profile(p, r, 4), tau)
                     - _pbv(profile(p, r, 4), tau))
                 for p in PS for r in RS for tau in LADDER[(p, r)])
    print(f"\nV form check vs the shipped 2**K enumeration "
          f"(derive_phase_boundary.v_kelly_block) at K=4:\n  (K=4, R=1) as "
          f"required, max abs diff = {chk1:.2e};  over the WHOLE K=4 sub-grid "
          f"(all R,\n  p*, tau), max abs diff = {chkall:.2e}")

    print(f"\nStratum profiles (p_lo, p_hi) and the frozen tau ladder "
          f"(0.001 lattice, solved at K=4\nto median targets {TARGETS} and "
          f"shared by every K; reps {REPS}, n_max = {NMAX_MULT}x target):")
    for p in PS:
        for r in RS:
            pr = profile(p, r, 2)
            print(f"  p*={p:.2f} R={r:>2}: p_lo={pr[0]:.4f} p_hi={pr[1]:.4f} "
                  f"tau={LADDER[(p, r)]} "
                  f"delta={[round(p - t, 3) for t in LADDER[(p, r)]]}")
    print()

    jobs = build_jobs()
    jobs_sorted = sorted(jobs, key=lambda j: -j["reps"] * j["n_max"] / j["k"])
    nproc = max(1, min(8, (os.cpu_count() or 2) - 2))
    with mp.get_context("spawn").Pool(processes=nproc) as pool:
        raw = list(pool.imap_unordered(_run_job, jobs_sorted, chunksize=1))
    meas = {(k, r, p, ri): (n, frac) for k, r, p, ri, n, frac in raw}

    print("-" * 76)
    print("MEASURED GRID  (median crossing; O(n) := n*V - log(1/alpha))")
    print("-" * 76)
    data = {(k, r): [] for k in KS for r in RS}
    excluded = []
    for k in KS:
        print(f"  K = {k}")
        print(f"    {'R':>3} {'p*':>5} {'tau':>6} {'delta':>6} {'q_grid':>7} "
              f"{'V':>10} {'n_med':>7} {'cert':>5} {'nV':>7} {'O':>7}")
        for r in RS:
            for p in PS:
                for ri in range(len(TARGETS)):
                    tau = LADDER[(p, r)][ri]
                    n, frac = meas[(k, r, p, ri)]
                    v = v_kelly_pb(profile(p, r, k), tau)
                    o = n * v - L
                    delta = round(p - tau, 4)
                    print(f"    {r:>3} {p:>5.2f} {tau:>6.3f} {delta:>6.3f} "
                          f"{0.0005 / delta:>6.1%} {v:>10.6f} {n:>7} "
                          f"{frac:>5.2f} {n * v:>7.3f} {o:>7.3f}")
                    if frac >= 0.9:
                        data[(k, r)].append((n, o, v))
                    else:
                        excluded.append((k, r, p, tau, frac))
            print()

    p3 = not excluded
    if excluded:
        print("  EXCLUDED (cert < 0.90, a censored median would bias the fit): "
              + ", ".join(f"K={k} R={r} p*={p} tau={t} cert={f:.2f}"
                          for k, r, p, t, f in excluded))
    for cell, rows in data.items():
        if len(rows) < MIN_CERTIFIED_PER_CELL:
            print(f"\n  INVALID: only {len(rows)} of {2 * len(TARGETS)} rungs "
                  f"certified in cell K={cell[0]} R={cell[1]} "
                  f"(< {MIN_CERTIFIED_PER_CELL}) — instrument failure, no "
                  f"verdicts scored.")
            return

    print("-" * 76)
    print("ENVELOPE FIT PER (K, R) CELL")
    print("-" * 76)
    print(f"  Each cell POOLS the two p* ladders: {2 * len(TARGETS)} rungs per "
          f"cell, fit O = (d/2) log n + c\n  by OLS (SE = OLS standard error). "
          f"Effective LOCAL fits over the measured n-range,\n  which is by "
          f"design the same window in every cell; not an expansion claim.")
    fits = {}
    print(f"\n  {'K':>3} {'R':>3} | {'n range':>13} | {'d':>7} {'SE':>6} "
          f"{'c':>8} {'SE':>6} {'SSE':>7} {'max|r|':>7}")
    for k in KS:
        for r in RS:
            rows = data[(k, r)]
            n = np.array([x[0] for x in rows], float)
            o = np.array([x[1] for x in rows], float)
            d, c, sse, mx, sd, scc = fit_line(np.log(n), o)
            fits[(k, r)] = (d, c, sd, scc, sse, mx)
            print(f"  {k:>3} {r:>3} | {int(n.min()):>6}-{int(n.max()):>6} | "
                  f"{d:>7.3f} {sd:>6.3f} {c:>8.3f} {scc:>6.3f} {sse:>7.3f} "
                  f"{mx:>7.3f}")
    print("\n  THE 12-CELL TABLE (d above, c below; rows K, columns R)")
    print("    " + "K\\R".rjust(5)
          + "".join(f"{('R=' + str(r)):>16}" for r in RS))
    for k in KS:
        print("    " + str(k).rjust(5)
              + "".join(f"{fits[(k, r)][0]:>8.3f}/{fits[(k, r)][1]:<7.3f}"
                        for r in RS))
    print()

    print("-" * 76)
    print("PRE-REGISTERED PREDICATES")
    print("-" * 76)
    p1 = True
    for k in KS:
        d, c = fits[(k, 1)][0], fits[(k, 1)][1]
        ad, ac = ANCHOR[k]
        ld = ANCHOR_LAW[0][0] + ANCHOR_LAW[0][1] * k
        lc = ANCHOR_LAW[1][0] + ANCHOR_LAW[1][1] * k
        ok = abs(d - ad) <= P1_DTOL and abs(c - ac) <= P1_CTOL
        p1 &= ok
        print(f"  P1 K={k}: d {d:>7.3f} vs anchor {ad:>6.3f} "
              f"(diff {d - ad:+.3f}, tol +/-{P1_DTOL}); "
              f"c {c:>7.3f} vs {ac:>7.3f} (diff {c - ac:+.3f}, tol "
              f"+/-{P1_CTOL}) -> {'PASS' if ok else 'FAIL'}")
        print(f"        [reference only, not scored: the anchor's linear LAW "
              f"gives d_K={ld:.3f}, c_K={lc:.3f}]")
    print(f"  P1 (regression anchor) the R=1 column reproduces "
          f"results_wsr_k.txt: {'PASS' if p1 else 'FAIL'}")

    print()
    p2 = True
    for k in KS:
        cs_ = [fits[(k, r)][1] for r in RS]
        up = all(cs_[i + 1] > cs_[i] for i in range(len(cs_) - 1))
        dn = all(cs_[i + 1] < cs_[i] for i in range(len(cs_) - 1))
        p2 &= up or dn
        print(f"  P2 K={k}: c "
              f"{'increasing' if up else 'decreasing' if dn else 'NOT monotone'}"
              f" in R: " + " -> ".join(f"{v:.3f}" for v in cs_)
              + f"   (span {max(cs_) - min(cs_):+.3f} nats over R=1..30)")
    print(f"  P2 (joint clause) c monotone in R at every K: "
          f"{'PASS' if p2 else 'FAIL'}")
    for k in KS:
        ds = [fits[(k, r)][0] for r in RS]
        up = all(ds[i + 1] > ds[i] for i in range(len(ds) - 1))
        dn = all(ds[i + 1] < ds[i] for i in range(len(ds) - 1))
        print(f"     (reported, NOT scored) d at K={k}: "
              f"{'increasing' if up else 'decreasing' if dn else 'NOT monotone'}"
              f" in R: " + " -> ".join(f"{v:.3f}" for v in ds))
    print(f"\n  P3 validity guard, every rung >= 90% crossings: "
          f"{'PASS' if p3 else 'FAIL'} "
          f"({len(excluded)} rung(s) excluded of {len(jobs)})")
    print()

    print("-" * 76)
    print("SURFACE FIT (OBSERVED REGULARITY; no derivation claimed)")
    print("-" * 76)
    cells = [(k, r) for k in KS for r in RS]
    x = np.stack([np.ones(len(cells)),
                  np.array([k for k, _ in cells], float),
                  np.log(np.array([r for _, r in cells], float))], axis=1)
    surf, resid_tab = {}, {}
    for idx, nm in ((0, "d"), (1, "c")):
        y = np.array([fits[cl][idx] for cl in cells], float)
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        resid = y - x @ beta
        rng_ = float(y.max() - y.min())
        mx = float(np.max(np.abs(resid)))
        surf[nm] = (beta, mx, rng_)
        resid_tab[nm] = {cl: float(rr) for cl, rr in zip(cells, resid)}
        print(f"  {nm}(K,R) = {beta[0]:+.4f} {beta[1]:+.4f}*K "
              f"{beta[2]:+.4f}*log R      max|resid| {mx:.4f} vs range "
              f"{rng_:.4f} ({mx / rng_:.0%} of range)")
    print(f"\n  RESIDUAL TABLE (measured cell minus surface; rows K, columns "
          f"R) — printed in full, always")
    for nm in ("d", "c"):
        print(f"    {nm}:  " + "".join(f"{('R=' + str(r)):>10}" for r in RS))
        for k in KS:
            print(f"      K={k} " + "".join(f"{resid_tab[nm][(k, r)]:>+10.4f}"
                                            for r in RS))
    verdict = {}
    for nm in ("d", "c"):
        beta, mx, rng_ = surf[nm]
        small = mx <= SURFACE_TOL * rng_
        sgn = [tuple(np.sign(round(resid_tab[nm][(k, r)], 6)) for r in RS)
               for k in KS]
        structured = len(set(sgn)) == 1
        ok = small and not structured
        verdict[nm] = ok
        print(f"\n  {nm}: max|resid| {'<=' if small else '>'} "
              f"{SURFACE_TOL:.0%} of range; residual sign pattern across R "
              f"{'IDENTICAL in all three K rows (structure the form misses)' if structured else 'differs across K rows'}\n"
              f"     -> log R {'ACCEPTED' if ok else 'REJECTED'} as the "
              f"carrier for {nm}"
              + ("" if ok else "; the residual table above is reported as "
                               "measured and nothing else is fitted to force "
                               "it."))
    print()

    print("-" * 76)
    print("POST-HOC DIAGNOSTIC — labeled; does NOT re-score the safety miss")
    print("-" * 76)
    body_s, st_s, rc_s, ok_s = read_artifact("results_safety.txt", SAFETY_SHA)
    meds = parse_safety(body_s)
    print(f"  results_safety.txt identity: stated {st_s}, recomputed {rc_s} -> "
          f"{'OK' if ok_s else 'STALE'} (expected {SAFETY_SHA})")
    sc = load_safety_machinery()
    print("  Machinery reused verbatim from run_safety_cert (load_pool, mu, "
          "tau=round(mu-0.045,3),\n  single_fourterm, 64-atom "
          "v_kelly_block_K at K=6, +/-5% tie band); only the WSR overhead is "
          "swapped.\n  err% = (predicted n_wsr - measured WSR median)/"
          "measured; POSITIVE = over-predicts, i.e. WSR\n  looks slower than "
          "it is (the direction of the safety miss, which was +19 to +37%).\n"
          "  JOINT-S = the fitted surface at (K=6, R_pool). JOINT-I = "
          "linear-in-log-R interpolation\n  between the MEASURED K=6 cells "
          "bracketing R_pool (no surface form assumed).")

    def o_surface(r):
        bd, bc = surf["d"][0], surf["c"][0]
        d = bd[0] + bd[1] * 6 + bd[2] * math.log(r)
        c = bc[0] + bc[1] * 6 + bc[2] * math.log(r)
        return (lambda n: 0.5 * d * math.log(n) + c), d, c

    def o_interp(r):
        lo = max([g for g in RS if g <= r], default=RS[0])
        hi = min([g for g in RS if g >= r], default=RS[-1])
        if lo == hi:
            d, c = fits[(6, lo)][0], fits[(6, lo)][1]
        else:
            w = (math.log(r) - math.log(lo)) / (math.log(hi) - math.log(lo))
            d = (1 - w) * fits[(6, lo)][0] + w * fits[(6, hi)][0]
            c = (1 - w) * fits[(6, lo)][1] + w * fits[(6, hi)][1]
        return (lambda n: 0.5 * d * math.log(n) + c), d, c

    print(f"\n  {'pool':14s} {'p*':>5} {'R':>6} {'n_s':>5} {'W_meas':>7} | "
          f"{'COMMIT':>7} {'err%':>7} | {'JOINT-S':>8} {'err%':>7} | "
          f"{'JNT-I':>6} {'err%':>7} | {'frozen':>7} {'JNT-S':>6} "
          f"{'JNT-I':>6} {'meas':>6}")
    flags = set()
    errs_c, errs_s, calls = [], [], {}
    for model in sc.SCORED:
        _arrs, rates, mu, _pooled, r_pool = sc.load_pool(model)
        tau = round(mu - sc.M, 3)
        n_s = sc.single_fourterm(mu, tau)
        v6 = sc.v_kelly_block_K(rates, tau, 6)
        n_c = sc.wsr_crossing(v6, *sc.CORNERS[-1])
        fn_s, _ds, _cs = o_surface(r_pool)
        fn_i, _di, _ci = o_interp(r_pool)
        n_1, f1 = crossing_with_overhead(v6, fn_s)
        n_2, f2 = crossing_with_overhead(v6, fn_i)
        flags |= {f1, f2}
        c_frozen = call_of(n_s, n_c, sc.TIE_BAND)
        c_1 = call_of(n_s, n_1, sc.TIE_BAND)
        c_2 = call_of(n_s, n_2, sc.TIE_BAND)
        w = meds[model]["wsr"]
        e_c, e_1, e_2 = ((v - w) / w for v in (n_c, n_1, n_2))
        errs_c.append(e_c)
        errs_s.append(e_1)
        calls[model] = (c_frozen, c_1, c_2, meds[model]["measured"])
        s1 = "<4" if f1 == "below-range" else f"{n_1:.0f}"
        s2 = "<4" if f2 == "below-range" else f"{n_2:.0f}"
        print(f"  {model:14s} {mu:>5.3f} {r_pool:>6.2f} {n_s:>5.0f} {w:>7} | "
              f"{n_c:>7.0f} {e_c:>+7.1%} | {s1:>8} {e_1:>+7.1%} | "
              f"{s2:>6} {e_2:>+7.1%} | {c_frozen:>7} {c_1:>6} {c_2:>6} "
              f"{meds[model]['measured']:>6}")
    if "below-range" in flags:
        print("  '<4' = the fitted overhead, extrapolated below its measured "
              "range, goes negative and the\n        model claims a crossing "
              "before the bracket floor: an EXTRAPOLATION ARTIFACT, read as "
              "'WSR immediately'.")
    ok_frozen = all(calls[m][0] == sc.FROZEN[m] for m in sc.SCORED)
    print(f"\n  COMMITTED column reproduces the frozen table exactly: "
          f"{'YES' if ok_frozen else 'NO'}")
    print(f"  PREDICTION ERROR, all six scored pools: COMMITTED "
          f"[{min(errs_c):+.1%}, {max(errs_c):+.1%}] -> JOINT-S "
          f"[{min(errs_s):+.1%}, {max(errs_s):+.1%}]")

    res = [m for m in sc.SCORED if calls[m][1] != "tie"]
    hit = [m for m in res if calls[m][1] == calls[m][3]]
    mis = [m for m in res if calls[m][3] not in ("tie", "?")
           and calls[m][1] != calls[m][3]]
    unc = [m for m in res if calls[m][3] == "tie"]
    rate = len(hit) / (len(hit) + len(mis)) if (hit or mis) else float("nan")
    q1 = len(res) >= 2
    q2 = (len(hit) + len(mis)) > 0 and rate > 0.5
    print(f"\n  frozen baseline (COMMITTED, as scored in #50): 2 resolving, "
          f"1 HIT 1 MISS = 1/2 matched.")
    print(f"  JOINT-S: {len(res)} resolving prediction(s) {res}; "
          f"{len(hit)} HIT {len(mis)} MISS {len(unc)} unconfirmed "
          f"(measured TIE) -> matched "
          + (f"{len(hit)}/{len(hit) + len(mis)}" if (hit or mis) else "n/a"))
    print(f"  Q1 >= 2 resolving predictions: {'YES' if q1 else 'NO'}    "
          f"Q2 matches the measured winners better than 1/2: "
          f"{'YES' if q2 else 'NO'}")
    if q1 and q2:
        answer = ("YES on both — the joint (R, K) envelope is non-vacuous "
                  "AND beats the frozen call rate.")
    elif q1:
        answer = ("PARTIAL — the joint envelope stays non-vacuous (>= 2 "
                  "resolving) but does not beat 1/2 on the\n  measured "
                  "winners.")
    elif q2:
        answer = ("PARTIAL — what the joint envelope does resolve it gets "
                  "right, but it resolves fewer than 2\n  pools, so it would "
                  "not have cleared the discrimination gate.")
    else:
        answer = ("NO on both — the joint envelope neither resolves >= 2 "
                  "pools nor beats 1/2.")
    print(f"\n  DIAGNOSTIC ANSWER (not a verdict; the #50 MISS stands as "
          f"scored): {answer}")
    print("  Assumptions carried, both disclosed and neither proved: a real "
          "pool's R (max/min over six\n  category rates) is the same object "
          "as the grid's two-level ratio, and the surface (fit at\n  p* in "
          "{0.20, 0.35}) extrapolates to pool p* up to 0.857.")
    print()

    print("-" * 76)
    print("SUMMARY")
    print("-" * 76)
    print(f"  P1 {'PASS' if p1 else 'FAIL'}  |  P2 {'PASS' if p2 else 'FAIL'}"
          f"  |  P3 {'PASS' if p3 else 'FAIL'}")
    bd, bc = surf["d"][0], surf["c"][0]
    print(f"  Joint surface over 12 cells: d = {bd[0]:+.3f} {bd[1]:+.3f}K "
          f"{bd[2]:+.3f}logR,  c = {bc[0]:+.3f} {bc[1]:+.3f}K "
          f"{bc[2]:+.3f}logR")
    print(f"  log R accepted as the carrier: d {'YES' if verdict['d'] else 'NO'}"
          f", c {'YES' if verdict['c'] else 'NO'}.")
    print("-" * 76)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_wsr_rk.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_wsr_rk.txt'}")
