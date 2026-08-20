#!/usr/bin/env python3
"""WSR STOCK-SCHEDULE ENVELOPE: derived from the wealth-sum integral.

WHY THIS EXISTS. results_wsr_k.txt measured the stock WSRBlockCS overhead
envelope O(n) := n*V - log(1/alpha) = (d_K/2) log n + c_K on a frozen
15-rung ladder at K in {2,4,6,8} (R=1, UNSAFE, p* in {0.20,0.35,0.50},
median crossings n ~ 200-25000) and reported two OBSERVED REGULARITIES,
explicitly labelled "no derivation claimed":

    d_K = -0.4267 K + 4.1407      c_K = +0.9638 K - 8.9801

and results_wsr_pdir.txt measured a 6-cell (direction x p*) table whose
"direction effect" was reported as real but unexplained. This script
derives both, from the shipped schedule, with no constant fitted to any
measured number.

--------------------------------------------------------------------------
THE REDUCTION (each step is checked numerically against shipped code)
--------------------------------------------------------------------------
Write M_t for the K-block mean, m for the BINDING grid point, and note
that WSRBlockCS's `lo > tau` needs every grid point <= tau dead; capital
is strictly decreasing in the candidate, so the last to die is
m = max{grid <= tau} = tau - 0.0005 (every tau on the 0.001 lattice is
mid-cell). The reported crossing is the death of that single point, and
the minus arm is ~e^-10 there, so the barrier on the plus arm is
log K+_T = log(2/alpha) =: L2.

(1) SCHEDULE. lam_t = min( sqrt(2 L2 / (sq_t log(t+1))), c/m ), where
    sq_t = 1/4 + sum_{i<t}(x_i - mean_{i-1})^2 is the shipped running
    statistic (prior sq_0 = 1/4, mean_0 = 1/2, divisor t+1). Its mean is
    available in closed form,
        E[sq_t] = 1/4 + sum_{i=1}^{t-1}[ mu2 (1 + (i-1)/i^2)
                                         + (1/2 - p)^2 / i^2 ],
    mu2 = p(1-p)/K being the block-mean variance. So to leading order
        sq_t ~ mu2 (t + t0 - 1),   t0 := (1/4)/mu2 = K/(4 p(1-p)).
    t0 IS the schedule's warm-up length MEASURED IN BLOCKS, and it is
    proportional to K. This is the first of the two K channels.

(2) PER-BLOCK GROWTH. With g = p - m, lam* = g/(mu2+g^2),
    V* = g^2/(2(mu2+g^2)) and r_t := lam_t/lam*,
        E log(1 + lam_t (M-m)) = V* (2 r_t - r_t^2) + O(lam^3),
        r_t = sqrt( L2 / (V* (t + t0 - 1) log(t+1)) ).
    The stock bet is therefore a pure Kelly FRACTION whose square is
    L2/(V* (t+t0-1) log(t+1)): it over-bets (r>1) during the warm-up and
    under-bets (r<1) forever after.

(3) WEALTH SUM. Summing (2),
        W(T) = 2 sqrt(L2 V*) G1(T) - L2 G2(T),
        G1(T) = sum_{t<=T} [(t+t0-1) log(t+1)]^{-1/2},
        G2(T) = sum_{t<=T} [(t+t0-1) log(t+1)]^{-1},
    i.e. a sqrt(T/log T) gross gain minus a loglog T Kelly deficit. The
    crossing W(T) = L2 and the ordinate nV = T V*(tau) (n = KT, V per
    sample) then give, by implicit differentiation along the ladder,

        d_eff = 2 rho T V* [ 1 - 2 T w_T / A ],
        A := 2 L2 u G1(T) = Lambda + L2 G2(T),  u = sqrt(V*/L2),
        w_T := V* r_T (2 - r_T),  rho := V*(tau)/V*(m),

    where Lambda is the crossing level (= L2 in the bare form above;
    section 4's closed form refines it with the renewal terms, and the
    primary of section 5 dispenses with a level convention entirely),

    and, using G1 = 2 sqrt(T/log T)(1 + 1/log T + ...),

        nV    ~ (A^2 / 16 L2) log T / (1 + 1/log T)^2
        d_eff ~ rho A (A + 2 L2) / ( 8 L2 (1 + 1/log T)^2 ).      (*)

(4) WHERE K ENTERS. (*) depends on K only through A = L2 + L2 G2(T; t0),
    and G2 is a loglog integral whose BOTH limits are K-driven:
        upper  T  = n/K            (fewer blocks per sample budget),
        lower  t0 = K/(4 p(1-p))   (longer warm-up, in blocks),
        G2(T;t0) ~ loglog(T+t0) - loglog(1+t0).
    Both ends shrink G2 as K grows, so
        dA/dK = -(L2/K)[ 1/log T + 1/log t0 ] + O(...),
        dd_eff/dK = -rho (A + L2)[1/log T + 1/log t0]
                    / (4 K (1 + 1/log T)^2).
    THE K-LINEARITY IS THEREFORE NOT EXACT. The derivation predicts a
    CONVEX d(K) (the 1/K prefactor), which a straight line through
    K = 2,4,6,8 renders as a slope with residuals in the pattern
    (+,-,-,+). That pattern is a scored predicate below (P4), and it is
    what results_wsr_k.txt's own printed residuals show.

(5) DIRECTION AND p*. Two separate statements.
    T1 (EXACT, a theorem about the shipped code). WSRBlockCS is
       equivariant under x -> 1-x: its grid is symmetric (0.0005+0.001k
       maps to 0.9995-0.001k), its priors (1/2, 1/4) are symmetric,
       sq_t is invariant, the two arms and their truncations c/m and
       c/(1-m) swap, and the hedge (K+ + K-)/2 is symmetric. Hence
       lo(x) = 1 - hi(1-x) at EVERY poll, and SAFE certification of pool
       P at threshold tau is PATHWISE IDENTICAL to UNSAFE certification
       of pool 1-P at threshold 1-tau. Direction is NOT an independent
       envelope argument: the (direction, p*) surface is one function of
       p* evaluated on the reflected pool. Predicted: the 6-cell table
       collapses across its anti-diagonal.
    T2 (the carrier of the p* dependence itself). The first term the
       quadratic reduction drops is the block skewness:
           eps_skew = (2/3) r^3 g mu3/mu2^2 = (2/3) r^3 g (1-2p)/(p(1-p)),
       since mu3/mu2^2 = (1-2p)/(p(1-p)) EXACTLY for a K-block mean --
       K CANCELS. It vanishes at p = 1/2 (where results_wsr_pdir.txt
       measured exact V-symmetry), is odd in (p - 1/2), and flips sign
       with direction (Z -> -Z). It is largest at the SHALLOW rungs
       (eps ~ g r^3, both falling down the ladder), so eps > 0 pulls the
       small-n ordinates down and RAISES the fitted d. Predicted signs:
       d_SAFE - d_UNSAFE < 0 at p* < 1/2, > 0 at p* > 1/2, = 0 at 1/2,
       equal in magnitude at p* and 1-p*, with c moving oppositely.

--------------------------------------------------------------------------
PRIMARY EVALUATION AND ITS THREE APPROXIMATIONS
--------------------------------------------------------------------------
The ladder is solved WITHOUT the quadratic reduction: the exact (K+1)-atom
increment law log(1 + lam_bar_t (a_j - m)) is pushed through an exact
grid-convolution first-passage operator with absorption at L2, which
returns the MEDIAN crossing block directly -- overshoot, the
median-vs-mean shift and the strongly non-homogeneous early variance are
all carried exactly, so no renewal level convention is assumed. The
schedule's own randomness enters as a mean correction
delta_t = E[V(lam_t;m)] - V(lam_bar_t;m) estimated by a Rao-Blackwellised
simulation of sq_t alone. Three approximations remain, and each is scored
as a variant:
  A1  drop delta_t entirely (deterministic sigma-hat),
  A2  replace the first-passage operator by the crudest convention,
      the crossing of the MEAN wealth path at the bare barrier L2,
  A3  displace the barrier by sigma_J, the path-level standard deviation
      of the accumulated Kelly deficit (the dispersion channel that
      delta_t's mean correction does not carry).

WINDOW RULE (fixed before the derived constants were computed):
    W(X) = |X_primary - X_A1| + |X_primary - X_A2| + |X_primary - X_A3|
           + 2 SE_meas(X),
SE_meas being the OLS standard error of the MEASURED K-law, recomputed
here from results_wsr_k.txt's own per-K constants. HIT iff the measured
constant lies in [X - W, X + W]. Windows are NOT widened; a MISS is
reported as a MISS.

DISCLOSED ORDERING. The four measured constants were on the record before
this derivation began, so a blind freeze was impossible; what is frozen is
the PIPELINE and the WINDOW RULE, both fixed before any derived constant
was evaluated, plus the FROZEN dict below, which the script recomputes and
checks for identity. Sections 1-5 never read results_wsr_k.txt: section 3
validates the instrument against a direct simulation of the shipped
WSRBlockCS run here, with this script's own seeds. Section 6 is the first
line that touches the artifact.

PRE-REGISTERED PREDICATES:
  P1  d_K slope in K            HIT iff measured -0.4267 in the window
  P2  d_K intercept in K        HIT iff measured +4.1407 in the window
  P3  c_K slope / intercept     HIT iff +0.9638 / -8.9801 in the window
  P4  (mechanism, sign only) the derived d(K) is CONVEX in K and the
      measured linear-in-K residuals carry the convex signature (+,-,-,+)
  P5  (T1) the measured 6-cell table collapses under the anti-diagonal
      reflection: |X_SAFE(p*) - X_UNSAFE(1-p*)| <= the pooled OLS SE of
      the two cells, for all three pairs and both constants
  P6  (T2) the four sign predicates of the skewness carrier

FROZEN PREDICTIONS (derived; recomputed and identity-checked in section 5,
which is printed before section 6 reads any artifact):

    d_K = -0.4542 K + 4.3004        c_K = +1.0455 K - 9.4935

    per K: d(2,4,6,8) = 3.6237, 2.2135, 1.4212, 0.8601
           c(2,4,6,8) = -7.7018, -4.9646, -3.0159, -1.3812
    variant sums (the window's derivation half, before 2 SE_meas):
           d_slope 0.1089   d_int 0.8721   c_slope 0.2656   c_int 2.3118

The G1/G2 quadratic closed form is printed with its own accuracy and is
deliberately NOT a window term: the primary never invokes it, and section 3
validates the primary, not it. Including a strictly coarser approximation
would only widen the window, i.e. weaken the test.

Offline, deterministic (fixed seeds). Writes results_wsr_envelope.txt.
"""

import hashlib
import io
import math
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS      # noqa: E402

ALPHA = 0.05
L = math.log(1 / ALPHA)
L2 = math.log(2 / ALPHA)
GRID = np.linspace(0.0005, 0.9995, 1000)
C_TRUNC = 0.75
LO, NPTS = -25.0, 4000              # first-passage wealth grid
RB_REPS, RB_MARKS, RB_SEED = 3000, 260, 909
PROBE_REPS, PROBE_SEED = 500, 4242
KS = (2, 4, 6, 8)
LADDER = [
    (0.50, [0.402, 0.443, 0.464, 0.476, 0.484]),
    (0.35, [0.260, 0.297, 0.317, 0.328, 0.334]),
    (0.20, [0.129, 0.157, 0.173, 0.182, 0.187]),
]
# results_wsr_pdir.txt's frozen ladder (K=6, R=1.2 two-level pools).
PDIR_K = 6                          # its pools are R = 1.2, two-level
PDIR = {
    (0.20, "UNSAFE"): [0.126, 0.155, 0.170, 0.181, 0.188],
    (0.20, "SAFE"): [0.299, 0.248, 0.224, 0.216, 0.212],
    (0.50, "UNSAFE"): [0.414, 0.447, 0.467, 0.477, 0.484],
    (0.50, "SAFE"): [0.590, 0.552, 0.534, 0.522, 0.517],
    (0.80, "UNSAFE"): [0.706, 0.757, 0.773, 0.782, 0.789],
    (0.80, "SAFE"): [0.877, 0.847, 0.827, 0.817, 0.813],
}
WSR_K_SHA = "f6aea65aa754d0d8"
WSR_PDIR_SHA = "eb8f5f8d7eb4efad"
PROBES = [(4, 0.50, 0.402, 2000), (4, 0.50, 0.464, 20000),
          (8, 0.35, 0.297, 6000), (2, 0.20, 0.157, 9000),
          (2, 0.50, 0.443, 6000)]

# FROZEN: this derivation's own output, committed with the artifact and
# recomputed on every run (section 5 prints a FROZEN-IDENTITY line).
FROZEN = dict(
    d_slope=-0.4542, d_int=+4.3004, c_slope=+1.0455, c_int=-9.4935,
    Wv_d_slope=0.1089, Wv_d_int=0.8721, Wv_c_slope=0.2656, Wv_c_int=2.3118,
)


# ------------------------------------------------------------------ core
class Pool:
    """One K-block: one draw per stratum, hence a block-mean law on j/K."""

    def __init__(self, rates):
        self.rates = np.asarray(rates, float)
        self.K = self.rates.size
        probs = np.zeros(self.K + 1)
        probs[0] = 1.0
        for pi in self.rates:
            probs = np.concatenate([[0.0], probs[:-1]]) * pi + probs * (1 - pi)
        self.atoms = np.arange(self.K + 1) / self.K
        self.w = probs
        self.pbar = float(self.atoms @ probs)
        d = self.atoms - self.pbar
        self.mu2 = float(probs @ d ** 2)
        self.mu3 = float(probs @ d ** 3)
        self.iid = bool(np.all(self.rates == self.rates[0]))

    def reflect(self):
        return Pool(1.0 - self.rates)


def binding_m(tau):
    """The last grid point to die under `lo > tau` (all ladder taus mid-cell)."""
    return float(GRID[GRID <= tau][-1])


def esq(pool, T):
    """E[sq_t] for t = 1..T; exact for the shipped recursion."""
    i = np.arange(1, T)
    incr = (pool.mu2 * (1.0 + (i - 1) / i ** 2)
            + (0.5 - pool.pbar) ** 2 / i ** 2)
    return np.concatenate([[0.25], 0.25 + np.cumsum(incr)])


def lam_bar(pool, T, m):
    t = np.arange(1, T + 1)
    return np.minimum(np.sqrt(2 * L2 / (esq(pool, T) * np.log(t + 1))),
                      C_TRUNC / m)


def vpath(pool, T, m, lam=None):
    lb = lam_bar(pool, T, m) if lam is None else lam
    out = np.zeros_like(lb)
    for a, wj in zip(pool.atoms, pool.w):
        out += wj * np.log1p(lb * (a - m))
    return out


def draw_blocks(pool, rng, reps):
    if pool.iid:
        return rng.binomial(pool.K, pool.rates[0], size=reps) / pool.K
    return (rng.random((reps, pool.K)) < pool.rates).sum(axis=1) / pool.K


def rb_delta(pool, ms, T, seed=RB_SEED):
    """delta_t = E[V(lam_t;m)] - V(lam_bar_t;m) (the schedule's own
    randomness, mean channel) and sigma_J(t), the path-level sd of the
    accumulated deviation (dispersion channel). From sq_t alone."""
    marks = np.unique(np.round(np.geomspace(1, T, RB_MARKS)).astype(int))
    rng = np.random.default_rng(seed)
    sq = np.full(RB_REPS, 0.25)
    mean = np.full(RB_REPS, 0.5)
    raw = {m: np.empty(marks.size) for m in ms}
    sdj = {m: np.empty(marks.size) for m in ms}
    cum = {m: np.zeros(RB_REPS) for m in ms}
    j, prev = 0, 0
    for t in range(1, T + 1):
        if j < marks.size and t == marks[j]:
            lam = np.sqrt(2 * L2 / (sq * math.log(t + 1)))
            for m in ms:
                lp = np.minimum(lam, C_TRUNC / m)
                acc = np.zeros(RB_REPS)
                for a, wj in zip(pool.atoms, pool.w):
                    acc += wj * np.log1p(lp * (a - m))
                raw[m][j] = acc.mean()
                cum[m] += (acc - acc.mean()) * (t - prev)
                sdj[m][j] = cum[m].std()
            prev = t
            j += 1
        e = draw_blocks(pool, rng, RB_REPS) - mean
        sq += e * e
        mean += e / (t + 1)
    lt = np.log(np.arange(1, T + 1))
    out = {}
    for m in ms:
        vd = vpath(pool, T, m)
        out[m] = (np.interp(lt, np.log(marks), raw[m] - vd[marks - 1]),
                  np.interp(lt, np.log(marks), sdj[m]))
    return out


def fp_cdf(pool, m, T_max, delta=None, barrier=L2):
    """Exact grid-convolution first-passage CDF (per block) of the derived
    wealth walk, absorbing at `barrier`. Carries overshoot, the
    median-vs-mean shift and the non-homogeneous early variance exactly."""
    z = pool.atoms - m
    lam = lam_bar(pool, T_max, m)
    h = (barrier - LO) / (NPTS - 1)
    dens = np.zeros(NPTS)
    dens[int(round(-LO / h))] = 1.0
    buf = np.empty(NPTS)
    absorbed, lost = 0.0, 0.0
    cdf = np.empty(T_max)
    for ti in range(T_max):
        y = np.log1p(lam[ti] * z)
        if delta is not None:
            y = y + delta[ti]
        buf.fill(0.0)
        for yj, wj in zip(y, pool.w):
            s = yj / h
            a = math.floor(s)
            f = s - a
            for aa, ww in ((a, wj * (1 - f)), (a + 1, wj * f)):
                if ww == 0.0:
                    continue
                if aa >= 0:
                    if aa < NPTS:
                        buf[aa:] += ww * dens[:NPTS - aa]
                        absorbed += ww * dens[NPTS - aa:].sum()
                    else:
                        absorbed += ww * dens.sum()
                else:
                    b = -aa
                    if b < NPTS:
                        buf[:NPTS - b] += ww * dens[b:]
                        lost += ww * dens[:b].sum()
                    else:
                        lost += ww * dens.sum()
        absorbed += buf[NPTS - 1]
        buf[NPTS - 1] = 0.0
        dens, buf = buf, dens
        cdf[ti] = absorbed
    return cdf, lost


def median_of(cdf):
    if cdf[-1] < 0.5:
        return float("nan")
    k = int(np.searchsorted(cdf, 0.5))
    if k == 0:
        return 1.0
    return float(k + (0.5 - cdf[k - 1]) / (cdf[k] - cdf[k - 1]))


def mean_cross(pool, m, delta=None, cap=600000):
    """T where the MEAN wealth path first reaches L2 (variant A2; sizing)."""
    T = 64
    while T < cap:
        v = vpath(pool, T, m)
        if delta is not None:
            v = v + delta[:T]
        if delta is not None and T > delta.size:
            v = vpath(pool, T, m) + np.concatenate(
                [delta, np.full(T - delta.size, delta[-1])])
        cw = np.cumsum(v)
        if cw[-1] >= L2:
            k = int(np.searchsorted(cw, L2))
            return 1.0 if k == 0 else float(
                k + (L2 - cw[k - 1]) / (cw[k] - cw[k - 1]))
        T *= 2
    return float(cap)


def v_kelly(pool, tau):
    """Per-SAMPLE Kelly rate of the block game; measure_wsr_k's convention
    (3000-point lambda grid on (0.001, 1/tau))."""
    lams = np.linspace(0.001, 1 / max(tau, 1e-9) - 1e-6, 3000)
    g = np.log1p(np.outer(lams, pool.atoms - tau)) @ pool.w
    return float(np.max(g)) / pool.K


def closed_form_rung(pool, tau, T_max):
    """The G1/G2 quadratic reduction solved against the homogeneous level
    Lambda = L2 + rho_ov - kappa (kappa = r_T/(2-r_T), rho_ov = Spitzer*s_T).
    Reported as the ANALYTIC form; NOT used by the primary and NOT in the
    window."""
    m = binding_m(tau)
    mu2, g = pool.mu2, pool.pbar - m
    t0 = 0.25 / mu2
    vstar = g * g / (2 * (mu2 + g * g))
    lam_star = g / (mu2 + g * g)
    r_cap = (C_TRUNC / m) / lam_star
    t = np.arange(1, T_max + 1, dtype=float)
    r = np.minimum(np.sqrt(L2 / (vstar * (t + t0 - 1) * np.log(t + 1))), r_cap)
    W = vstar * np.cumsum(2 * r - r * r)
    S1, S2 = np.cumsum(r), np.cumsum(r * r)
    Lam, T = L2, float(T_max)
    for _ in range(200):
        if W[-1] < Lam:
            return dict(T=float("nan"))
        k = int(np.searchsorted(W, Lam))
        Tn = 1.0 if k == 0 else k + (Lam - W[k - 1]) / (W[k] - W[k - 1])
        ri = min(math.sqrt(L2 / (vstar * (Tn + t0 - 1) * math.log(Tn + 1))),
                 r_cap)
        Lam_n = (L2 + 0.5826 * ri * lam_star * math.sqrt(mu2)
                 - ri / (2 - ri))
        if abs(Lam_n - Lam) < 1e-10 and abs(Tn - T) < 1e-8 * Tn:
            T = Tn
            break
        Lam, T = Lam_n, Tn
    i = min(int(T), T_max) - 1
    # G1 = u sum r, G2 = u^2 sum r^2 with u = sqrt(V*/L2), so that
    # A := 2 L2 u G1 = 2 V* sum r = Lambda + L2 G2.
    u = math.sqrt(vstar / L2)
    G1, G2 = u * float(S1[i]), (vstar / L2) * float(S2[i])
    return dict(T=T, A=2 * L2 * u * G1, G1=G1, G2=G2, r_T=float(r[i]),
                w_T=vstar * r[i] * (2 - r[i]), vstar=vstar, t0=t0, Lam=Lam)


def ols(x, y):
    a = np.stack([np.asarray(x, float), np.ones(len(x))], axis=1)
    (s, i), *_ = np.linalg.lstsq(a, np.asarray(y, float), rcond=None)
    return float(s), float(i), np.asarray(y, float) - (s * np.asarray(x, float) + i)


def ols_se(x, y):
    x = np.asarray(x, float)
    s, i, r = ols(x, y)
    sxx = float(np.sum((x - x.mean()) ** 2))
    if x.size <= 2:
        return s, i, float("inf"), float("inf")
    sig2 = float(np.sum(r ** 2)) / (x.size - 2)
    return (s, i, math.sqrt(sig2 / sxx),
            math.sqrt(sig2 * (1 / x.size + x.mean() ** 2 / sxx)))


def sim_median(pool, tau, reps, n_max, seed0):
    """Direct simulation of the SHIPPED CS -- the measurement's instrument."""
    K = pool.K
    nb = n_max // K
    times = []
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        cs = WSRBlockCS(alpha=ALPHA)
        xx = draw_blocks(pool, rng, nb)
        crossed = None
        for j in range(nb):
            cs.update(float(xx[j]))
            lo, _ = cs.get_bounds()
            if lo > tau:
                crossed = j + 1
                break
        times.append(crossed if crossed else nb)
    return float(np.median(times))


def read_artifact(name, expect):
    body, rest = (REPO / name).read_text().split(
        "\n" + "=" * 76 + "\nChecksum (SHA256): ", 1)
    stated = rest.split("\n", 1)[0].strip()
    got = hashlib.sha256(body.encode()).hexdigest()[:16]
    print(f"   {name}: stated {stated}, recomputed {got} -> "
          f"{'OK' if stated == got else 'STALE'} (expected {expect})")
    return body


def solve_rung(pool, tau, want_variants=True):
    """Every arm of one rung. Returns dict of block counts."""
    m = binding_m(tau)
    Tmax = int(2.0 * mean_cross(pool, m)) + 80
    dl, sj = rb_delta(pool, [m], Tmax)[m]
    cdf, lost = fp_cdf(pool, m, Tmax, delta=dl)
    TP = median_of(cdf)
    out = dict(P=TP, lost=lost, Tmax=Tmax, m=m)
    if want_variants:
        out["A1"] = median_of(fp_cdf(pool, m, Tmax)[0])
        out["A2"] = mean_cross(pool, m, delta=dl)
        s = float(sj[min(int(TP), Tmax) - 1])
        out["sigJ"] = s
        out["A3"] = median_of(fp_cdf(pool, m, Tmax, delta=dl,
                                     barrier=L2 + s)[0])
    return out


def fit_ladder(rows):
    """rows: list of (n, O). Returns (d, c)."""
    n = np.array([r[0] for r in rows], float)
    o = np.array([r[1] for r in rows], float)
    d, c, _ = ols(np.log(n) / 2, o)
    return d, c


# ------------------------------------------------------------------ main
def main():
    print("=" * 76)
    print("WSR STOCK-SCHEDULE ENVELOPE: DERIVED FROM THE WEALTH-SUM INTEGRAL")
    print("=" * 76)
    print("alpha=0.05, shipped WSRBlockCS, K in (2,4,6,8), the frozen 15-rung")
    print("R=1 UNSAFE ladder of results_wsr_k.txt. Sections 1-5 read NO measured")
    print("artifact; section 6 is the first line that does.")

    # ------------------------------------------------- 1. shipped-code audit
    print("\n" + "-" * 76)
    print("1. SHIPPED-CODE AUDIT")
    print("-" * 76)
    print(f"   grid = linspace(.0005,.9995,1000), step {GRID[1]-GRID[0]:.6f}; "
          f"reflection m -> 1-m closes on the grid:")
    print(f"     max |grid + grid[::-1] - 1| = "
          f"{np.max(np.abs(GRID + GRID[::-1] - 1.0)):.2e}")
    offs = [tau - binding_m(tau) for _, ts in LADDER for tau in ts]
    print(f"   every ladder tau is mid-cell: offset in "
          f"[{min(offs):.6f}, {max(offs):.6f}]; binding point m = tau - 0.0005")
    pos = 1e9
    for K in KS:
        for p, ts in LADDER:
            po = Pool([p] * K)
            for tau in ts:
                m = binding_m(tau)
                pos = min(pos, float(np.min(1 + (C_TRUNC / m)
                                            * (po.atoms - m))))
    print(f"   capital stays positive at the truncation cap over every ladder")
    print(f"     atom: min (1 + (c/m)(a-m)) = {pos:.4f} > 0, so")
    print(f"     d/dm log(1+lam(a-m)) = -lam/(1+lam(a-m)) < 0; and where the")
    print(f"     cap binds (lam = c/m) the capital is log(1 + c a/m - c), also")
    print(f"     decreasing in m for a > 0 and constant at a = 0. Monotone in")
    print(f"     BOTH regimes, so the LAST candidate to die is m and the")
    print(f"     reported crossing is m's death.")
    rng = np.random.default_rng(1)
    cs = WSRBlockCS(alpha=ALPHA)
    xs = rng.binomial(4, 0.5, size=60) / 4
    sq, mean, wsq, wlam = 0.25, 0.5, 0.0, 0.0
    for t in range(1, 61):
        wsq = max(wsq, abs(sq - cs.sq))
        t_ship = cs.t + 1
        lam_ship = math.sqrt(2 * math.log(2 / ALPHA)
                             / (cs.sq / t_ship * t_ship
                                * math.log(t_ship + 1) + 1e-12))
        wlam = max(wlam, abs(math.sqrt(2 * L2 / (sq * math.log(t + 1)))
                             - lam_ship))
        cs.update(float(xs[t - 1]))
        sq += (xs[t - 1] - mean) ** 2
        mean += (xs[t - 1] - mean) / (t + 1)
    print(f"   sq_t recursion vs WSRBlockCS.sq over 60 steps: "
          f"max abs diff {wsq:.1e}")
    print(f"   lam_t = sqrt(2 log(2/alpha)/(sq_t log(t+1))) vs the shipped "
          f"expression: max abs diff {wlam:.1e}")
    pool4 = Pool([0.5] * 4)
    print(f"   V convention vs the 2**K enumeration of "
          f"derive_phase_boundary.v_kelly_block (K=4):")
    try:
        import types as _t
        _pb = _t.ModuleType("pb")
        _pb.__dict__["__file__"] = str(REPO / "scripts" / "derive_phase_boundary.py")
        exec(open(REPO / "scripts" / "derive_phase_boundary.py").read()
             .rsplit("if __name__", 1)[0], _pb.__dict__)
        dv = max(abs(v_kelly(Pool([p] * 4), tau) - _pb.v_kelly_block(np.array([p] * 4), tau))
                 for p, ts in LADDER for tau in ts)
        print(f"     max abs diff over the ladder = {dv:.2e}")
    except Exception as exc:                                  # pragma: no cover
        print(f"     UNAVAILABLE ({exc.__class__.__name__}) -- V convention "
              f"unchecked against shipped code")
    # minus-arm leak: the barrier on the plus arm is log(2/alpha) only if
    # the minus arm is negligible at the crossing.
    worst = -99.0
    for (K, p, tau, nmx) in PROBES[:3]:
        m = binding_m(tau)
        jm = int(np.where(GRID == m)[0][0])
        rg = np.random.default_rng(31)
        c2 = WSRBlockCS(alpha=ALPHA)
        xx = draw_blocks(Pool([p] * K), rg, nmx // K)
        for j in range(nmx // K):
            c2.update(float(xx[j]))
            lo, _ = c2.get_bounds()
            if lo > tau:
                break
        worst = max(worst, float(c2.log_km[jm] - c2.log_kp[jm]))
    print(f"   minus-arm leak at the crossing: max (log K- - log K+) = "
          f"{worst:+.2f} -> barrier displaced by log(1+e^leak) = "
          f"{math.log1p(math.exp(worst)):.2e} nats (neglected)")

    # ---------------------------------------------------- 2. the reduction
    print("\n" + "-" * 76)
    print("2. THE REDUCTION, CHECKED STEP BY STEP")
    print("-" * 76)
    rg = np.random.default_rng(77)
    sqs = np.full(4000, 0.25)
    mns = np.full(4000, 0.5)
    pool = Pool([0.5] * 4)
    worst_sq = 0.0
    ex = esq(pool, 400)
    for t in range(1, 401):
        worst_sq = max(worst_sq, abs(sqs.mean() - ex[t - 1]) / ex[t - 1])
        e = draw_blocks(pool, rg, 4000) - mns
        sqs += e * e
        mns += e / (t + 1)
    print(f"   E[sq_t] closed form vs 4000-rep simulation, t<=400 (K=4,p=.5): "
          f"max rel diff {worst_sq:.3%}")
    print(f"   quadratic growth law  V(lam;m) = V*(2r - r^2),  "
          f"r = sqrt(L2/(V*(t+t0-1)log(t+1))):")
    print(f"     {'K':>2} {'p':>5} {'tau':>6} {'t0=1/4/mu2':>11} "
          f"{'r@T':>6} {'V_quad':>9} {'V_exact':>9} {'rel':>8}")
    for (K, p, tau) in ((4, 0.50, 0.464), (2, 0.20, 0.157), (8, 0.35, 0.328)):
        po = Pool([p] * K)
        m = binding_m(tau)
        g = po.pbar - m
        mu2 = po.mu2
        t0 = 0.25 / mu2
        vst = g * g / (2 * (mu2 + g * g))
        T = mean_cross(po, m)
        r = min(math.sqrt(L2 / (vst * (T + t0 - 1) * math.log(T + 1))),
                (C_TRUNC / m) * (mu2 + g * g) / g)
        lam = r * g / (mu2 + g * g)
        vq = vst * (2 * r - r * r)
        ve = float(np.sum(po.w * np.log1p(lam * (po.atoms - m))))
        print(f"     {K:>2} {p:>5.2f} {tau:>6.3f} {t0:>11.2f} {r:>6.3f} "
              f"{vq:>9.6f} {ve:>9.6f} {abs(vq/ve-1):>8.2%}")
    print("   (the quadratic law is the ANALYTIC route only; the primary uses")
    print("    the exact (K+1)-atom increment law and never invokes it)")

    # ------------------------------------------- 3. instrument validation
    print("\n" + "-" * 76)
    print("3. INSTRUMENT VALIDATION -- derived median crossing vs a DIRECT")
    print("   simulation of the shipped WSRBlockCS (this script's own seeds;")
    print("   no measured artifact is read)")
    print("-" * 76)
    print(f"   {PROBE_REPS} reps/probe, seed {PROBE_SEED}")
    print(f"     {'K':>2} {'p':>5} {'tau':>6} {'T_derived':>10} "
          f"{'T_shipped':>10} {'ratio':>7}")
    ratios = []
    for (K, p, tau, nmx) in PROBES:
        po = Pool([p] * K)
        m = binding_m(tau)
        Tm = nmx // K
        dl, _sj = rb_delta(po, [m], Tm)[m]
        Td = median_of(fp_cdf(po, m, Tm, delta=dl)[0])
        Ts = sim_median(po, tau, PROBE_REPS, nmx, PROBE_SEED)
        ratios.append(Td / Ts)
        print(f"     {K:>2} {p:>5.2f} {tau:>6.3f} {Td:>10.2f} {Ts:>10.1f} "
              f"{Td/Ts:>7.3f}")
    print(f"   derived/shipped in [{min(ratios):.3f}, {max(ratios):.3f}] "
          f"(median-of-{PROBE_REPS} sampling error alone is ~3%)")

    # ------------------------------------------ 4. closed form and K-trace
    print("\n" + "-" * 76)
    print("4. THE CLOSED FORM AND THE K-TRACE")
    print("-" * 76)
    print("   d_eff = 2 rho T V* [1 - 2 T w_T / A]           (exact implicit)")
    print("   d_eff ~ rho A (A + 2 L2) / (8 L2 (1+1/log T)^2)  (asymptotic)")
    print("   A = Lambda + L2 G2(T; t0) = 2 V* sum_t r_t,"
          "  T = n/K,  t0 = K/(4 p(1-p))")
    print(f"     {'K':>2} {'p':>5} {'tau':>6} {'t0':>7} {'T':>9} {'G2':>7} "
          f"{'A':>7} {'d_implicit':>11} {'d_asympt':>9} {'dA/dK':>8}")
    ktrace = {}
    for K in KS:
        for (p, tau) in ((0.50, 0.464),):
            po = Pool([p] * K)
            Tm = int(2.2 * mean_cross(po, binding_m(tau))) + 80
            cf = closed_form_rung(po, tau, Tm)
            m = binding_m(tau)
            rho = (K * v_kelly(po, tau)) / cf["vstar"]
            di = 2 * rho * cf["T"] * cf["vstar"] * (
                1 - 2 * cf["T"] * cf["w_T"] / cf["A"])
            da = (rho * cf["A"] * (cf["A"] + 2 * L2)
                  / (8 * L2 * (1 + 1 / math.log(cf["T"])) ** 2))
            dadk = -(L2 / K) * (1 / math.log(cf["T"])
                                + 1 / math.log(cf["t0"]))
            ktrace[K] = (cf, di, da, dadk)
            print(f"     {K:>2} {p:>5.2f} {tau:>6.3f} {cf['t0']:>7.2f} "
                  f"{cf['T']:>9.1f} {cf['G2']:>7.3f} {cf['A']:>7.3f} "
                  f"{di:>11.3f} {da:>9.3f} {dadk:>8.4f}")
    print("   the dA/dK column is the closed form's own leading term")
    print("   -(L2/K)[1/log T + 1/log t0]; against it, the finite differences")
    print("   of the A column (which include every subleading piece):")
    for a, b in zip(KS[:-1], KS[1:]):
        fd = (ktrace[b][0]["A"] - ktrace[a][0]["A"]) / (b - a)
        av = 0.5 * (ktrace[a][3] + ktrace[b][3])
        print(f"     K={a}->{b}: measured-on-the-form {fd:+.4f} vs endpoint "
              f"mean of the leading term {av:+.4f}")
    worst_as = max(abs(ktrace[K][2] / ktrace[K][1] - 1) for K in KS)
    print(f"   LIMITATION, stated: the ASYMPTOTIC form overstates the exact")
    print(f"   implicit one by up to {worst_as:.0%} over this K range (the")
    print(f"   G1 ~ 2 sqrt(T/log T)(1 + 1/log T) step is not converged at")
    print(f"   T ~ 200-1600). It is kept because it EXHIBITS the mechanism in")
    print(f"   closed form, not because it is accurate; the scored prediction")
    print(f"   comes from the exact operator of section 5 and never from (*).")
    print("   BOTH K channels push the same way: T = n/K shrinks the upper")
    print("   loglog limit and t0 = K/(4pq) raises the lower one, so G2 -- the")
    print("   accumulated Kelly deficit that IS the log-n slope -- falls with K.")
    print("   The 1/K prefactor makes d(K) CONVEX, not linear (predicate P4).")

    # ------------------------------------------------ 5. frozen predictions
    print("\n" + "-" * 76)
    print("5. FROZEN PREDICTIONS  (computed here; no artifact read yet)")
    print("-" * 76)
    arms = ("P", "A1", "A2", "A3")
    store = {k: {a: [] for a in arms} for k in KS}
    grid_rows = {k: [] for k in KS}
    worst_lost = 0.0
    for K in KS:
        for p, taus in LADDER:
            po = Pool([p] * K)
            ms = [binding_m(t) for t in taus]
            Tmax = max(int(2.0 * mean_cross(po, m)) + 80 for m in ms)
            rb = rb_delta(po, ms, Tmax)
            for tau, m in zip(taus, ms):
                v = v_kelly(po, tau)
                dl, sj = rb[m]
                cdf, lost = fp_cdf(po, m, Tmax, delta=dl)
                worst_lost = max(worst_lost, lost)
                TP = median_of(cdf)
                TA1 = median_of(fp_cdf(po, m, Tmax)[0])
                TA2 = mean_cross(po, m, delta=dl)
                s = float(sj[min(int(TP), Tmax) - 1])
                TA3 = median_of(fp_cdf(po, m, Tmax, delta=dl,
                                       barrier=L2 + s)[0])
                for a, T in zip(arms, (TP, TA1, TA2, TA3)):
                    store[K][a].append((K * T, K * T * v - L))
                grid_rows[K].append((p, tau, v, K * TP, K * TP * v, s))
    print(f"   first-passage mass lost below the wealth grid floor "
          f"({LO:.0f} nats): max {worst_lost:.1e}")
    print(f"\n   DERIVED GRID (primary):  n = K T,  O := n V(tau) - log(1/alpha)")
    for K in KS:
        print(f"     K = {K}")
        print(f"       {'p':>5} {'tau':>6} {'V':>10} {'n_der':>9} "
              f"{'nV':>7} {'O':>7} {'sigma_J':>8}")
        for (p, tau, v, n, nv, s) in grid_rows[K]:
            print(f"       {p:>5.2f} {tau:>6.3f} {v:>10.6f} {n:>9.1f} "
                  f"{nv:>7.3f} {nv-L:>7.3f} {s:>8.3f}")
    fits = {}
    for a in arms:
        ds, cs_ = [], []
        for K in KS:
            d, c = fit_ladder(store[K][a])
            ds.append(d)
            cs_.append(c)
        sd, idd, rd = ols(KS, ds)
        sc, ic, rc = ols(KS, cs_)
        fits[a] = dict(d=ds, c=cs_, ks=(sd, idd, sc, ic), rd=rd, rc=rc)
    print("\n   PER-K ENVELOPE, ALL FOUR ARMS")
    print(f"     {'arm':>4} | " + " ".join(f"d(K={k}){'':>1}" for k in KS)
          + " | " + " ".join(f"c(K={k}){'':>1}" for k in KS))
    for a in arms:
        print(f"     {a:>4} | " + " ".join(f"{x:8.4f}" for x in fits[a]["d"])
              + " | " + " ".join(f"{x:8.4f}" for x in fits[a]["c"]))
    print("\n   K-LAWS")
    for a in arms:
        sd, idd, sc, ic = fits[a]["ks"]
        print(f"     {a:>4}: d = {sd:+.4f} K {idd:+.4f} | "
              f"c = {sc:+.4f} K {ic:+.4f}")
    print(f"     residuals of the PRIMARY d-vs-K line (K=2,4,6,8): "
          + " ".join(f"{x:+.4f}" for x in fits["P"]["rd"]))
    names = ("d_slope", "d_int", "c_slope", "c_int")
    Wv = {}
    print("\n   VARIANT SPREAD (window terms, |primary - variant|)")
    print(f"     {'constant':>9} {'primary':>10} {'A1':>8} {'A2':>8} "
          f"{'A3':>8} {'sum':>8}")
    for i, nm in enumerate(names):
        t = [abs(fits["P"]["ks"][i] - fits[a]["ks"][i]) for a in arms[1:]]
        Wv[nm] = sum(t)
        print(f"     {nm:>9} {fits['P']['ks'][i]:>10.4f} "
              + " ".join(f"{x:>8.4f}" for x in t) + f" {Wv[nm]:>8.4f}")
    fz = [("d_slope", "d_slope"), ("d_int", "d_int"),
          ("c_slope", "c_slope"), ("c_int", "c_int")]
    ok = all(abs(fits["P"]["ks"][i] - FROZEN[k]) < 5e-4
             for i, (_, k) in enumerate(fz))
    okw = all(abs(Wv[nm] - FROZEN["Wv_" + nm]) < 5e-4 for nm in names)
    print(f"\n   FROZEN-IDENTITY (docstring constants vs this run): "
          f"constants {'OK' if ok else 'DRIFTED'}, variant sums "
          f"{'OK' if okw else 'DRIFTED'}")
    print(f"   FROZEN: d = {FROZEN['d_slope']:+.4f} K {FROZEN['d_int']:+.4f}"
          f"   c = {FROZEN['c_slope']:+.4f} K {FROZEN['c_int']:+.4f}")

    # ---------------------------------------------------------- 6. scoring
    print("\n" + "-" * 76)
    print("6. SCORING vs results_wsr_k.txt  (first artifact read)")
    print("-" * 76)
    body = read_artifact("results_wsr_k.txt", WSR_K_SHA)
    blk = body.split("REPORTED CONSTANTS PER K", 1)[1]
    meas = {}
    for ln in blk.splitlines()[2:]:
        f = ln.split()
        if len(f) == 3 and f[0].isdigit():
            meas[int(f[0])] = (float(f[1]), float(f[2]))
        elif meas:
            break
    pub = {a: (b, c) for a, b, c in re.findall(
        r"\n  ([dc])\s+best basis K\s+:\s+[dc] = "
        r"([-+][\d.]+)\*K ([-+][\d.]+);", body)}
    print(f"   parsed per-K constants: " + ", ".join(
        f"K={k}: d {meas[k][0]:.3f} c {meas[k][1]:.3f}" for k in KS))
    md = [meas[k][0] for k in KS]
    mc = [meas[k][1] for k in KS]
    msd, mid_, sesd, sesi = ols_se(KS, md)
    msc, mic, sesc, seci = ols_se(KS, mc)
    print(f"   measured K-laws recomputed here: d = {msd:+.4f} K {mid_:+.4f}"
          f" (SE {sesd:.4f} / {sesi:.4f});  c = {msc:+.4f} K {mic:+.4f}"
          f" (SE {sesc:.4f} / {seci:.4f})")
    print(f"   artifact's own printed law: d = {pub['d'][0]}*K {pub['d'][1]}"
          f";  c = {pub['c'][0]}*K {pub['c'][1]}  -> parse "
          f"{'OK' if abs(float(pub['d'][0])-msd) < 5e-4 else 'MISMATCH'}")
    se = dict(d_slope=sesd, d_int=sesi, c_slope=sesc, c_int=seci)
    measured = dict(d_slope=msd, d_int=mid_, c_slope=msc, c_int=mic)
    print(f"\n   {'constant':>9} {'derived':>10} {'measured':>10} "
          f"{'diff':>9} {'W':>9} {'2SE':>7} {'verdict':>8} {'tight W':>9}")
    verdict = {}
    for i, nm in enumerate(names):
        P = fits["P"]["ks"][i]
        W = Wv[nm] + 2 * se[nm]
        tight = W - abs(fits["P"]["ks"][i] - fits["A3"]["ks"][i])
        diff = measured[nm] - P
        hit = abs(diff) <= W
        verdict[nm] = hit
        print(f"   {nm:>9} {P:>10.4f} {measured[nm]:>10.4f} {diff:>+9.4f} "
              f"{W:>9.4f} {2*se[nm]:>7.4f} {'HIT' if hit else 'MISS':>8} "
              f"{'hit' if abs(diff) <= tight else 'miss':>9}")
    print("   'tight W' drops the A3 (barrier-dispersion) term, which is a")
    print("   one-sided probe of a mean-zero channel and therefore the most")
    print("   conservative of the three; it is reported, not scored.")
    conv = all(fits["P"]["d"][j] - fits["P"]["d"][j + 1]
               > fits["P"]["d"][j + 1] - fits["P"]["d"][j + 2]
               for j in range(len(KS) - 2))
    sig = [1 if r > 0 else -1 for r in ols(KS, md)[2]]
    p4 = conv and sig == [1, -1, -1, 1]
    print(f"\n   P4 (mechanism) derived d(K) convex in K: "
          f"{'YES' if conv else 'NO'}; measured linear-in-K residual signs "
          f"{sig} vs the convex signature [1, -1, -1, 1]: "
          f"{'MATCH' if sig == [1,-1,-1,1] else 'NO MATCH'} -> "
          f"{'PASS' if p4 else 'FAIL'}")
    print(f"   P1 d_slope {'HIT' if verdict['d_slope'] else 'MISS'} | "
          f"P2 d_int {'HIT' if verdict['d_int'] else 'MISS'} | "
          f"P3 c_slope {'HIT' if verdict['c_slope'] else 'MISS'} and c_int "
          f"{'HIT' if verdict['c_int'] else 'MISS'}")

    # ------------------------------------------------- 7. direction and p*
    print("\n" + "-" * 76)
    print("7. DIRECTION x p*  (results_wsr_pdir.txt)")
    print("-" * 76)
    wl, wt = 0.0, 0
    for (K, p, tau) in ((6, 0.20, 0.170), (4, 0.50, 0.464), (2, 0.35, 0.317)):
        for rep in range(4):
            rg = np.random.default_rng(500 + 17 * K + rep)
            xx = draw_blocks(Pool([p] * K), rg, 900)
            a, b = WSRBlockCS(alpha=ALPHA), WSRBlockCS(alpha=ALPHA)
            cu = csf = None
            for j in range(900):
                a.update(float(xx[j]))
                b.update(float(1.0 - xx[j]))
                lo, _ = a.get_bounds()
                _, hi = b.get_bounds()
                wl = max(wl, abs(lo - (1.0 - hi)))
                if cu is None and lo > tau:
                    cu = j + 1
                if csf is None and hi <= 1.0 - tau:
                    csf = j + 1
                if cu and csf:
                    break
            wt = max(wt, abs((cu or 0) - (csf or 0)))
    print(f"   T1 (EXACT) x -> 1-x equivariance of the shipped CS:")
    print(f"     max |lo(x) - (1 - hi(1-x))| over all polls = {wl:.2e}")
    print(f"     max |T_UNSAFE(x,tau) - T_SAFE(1-x,1-tau)| over all reps = {wt}")
    print(f"   => SAFE certification of pool P at tau IS UNSAFE certification")
    print(f"      of pool 1-P at 1-tau. Direction is not an independent axis.")
    print(f"   T2 skewness carrier eps = (2/3) r^3 g mu3/mu2^2, and")
    print(f"      mu3/mu2^2 = (1-2p)/(p(1-p)) exactly -- K CANCELS:")
    print(f"     {'K':>2} {'p':>5} {'mu3/mu2^2':>10} {'(1-2p)/pq':>10}")
    for K in (2, 6):
        for p in (0.20, 0.50, 0.80):
            po = Pool([p] * K)
            print(f"     {K:>2} {p:>5.2f} {po.mu3/po.mu2**2:>10.4f} "
                  f"{(1-2*p)/(p*(1-p)):>10.4f}")
    pbody = read_artifact("results_wsr_pdir.txt", WSR_PDIR_SHA)
    cells = {}
    for ln in pbody.splitlines():
        m6 = re.match(r"\s+([\d.]+)\s+(UNSAFE|SAFE)\s+\|\s+\d+-\s*\d+\s+\|"
                      r"\s+([-\d.]+)\s+([\d.]+)\s+([-\d.]+)\s+([\d.]+)", ln)
        if m6:
            cells[(float(m6.group(1)), m6.group(2))] = tuple(
                float(m6.group(i)) for i in (3, 4, 5, 6))
    print(f"\n   parsed 6-cell table: {len(cells)} cells")
    rates = {0.20: [0.1818] * 3 + [0.2182] * 3,
             0.50: [0.4545] * 3 + [0.5455] * 3,
             0.80: [0.7273] * 3 + [0.8727] * 3}
    print(f"\n   DERIVED 6-cell table (same machinery, same frozen tau ladder):")
    print(f"     {'p*':>5} {'dir':>7} | {'d_der':>7} {'d_meas':>7} {'SE':>6} "
          f"| {'c_der':>7} {'c_meas':>7} {'SE':>6}")
    der = {}
    for (ps, dr), taus in PDIR.items():
        po = Pool(rates[ps])
        if dr == "SAFE":
            po, taus = po.reflect(), [1.0 - t for t in taus]
        ms = [binding_m(t) for t in taus]
        Tmax = max(int(2.0 * mean_cross(po, m)) + 80 for m in ms)
        rb = rb_delta(po, ms, Tmax)
        rows = []
        for tau, m in zip(taus, ms):
            v = v_kelly(po, tau)
            dl, _s = rb[m]
            T = median_of(fp_cdf(po, m, Tmax, delta=dl)[0])
            rows.append((PDIR_K * T, PDIR_K * T * v - L))
        der[(ps, dr)] = fit_ladder(rows)
    for ps in (0.20, 0.50, 0.80):
        for dr in ("UNSAFE", "SAFE"):
            dd, dc = der[(ps, dr)]
            md_, sd_, mc_, sc_ = cells[(ps, dr)]
            print(f"     {ps:>5.2f} {dr:>7} | {dd:>7.3f} {md_:>7.3f} "
                  f"{sd_:>6.3f} | {dc:>7.3f} {mc_:>7.3f} {sc_:>6.3f}")
    within = sum(abs(der[k][j] - cells[k][2 * j]) <= cells[k][2 * j + 1]
                 for k in der for j in (0, 1))
    print(f"   POST-HOC, LABELLED, NOT SCORED (no predicate was pre-registered")
    print(f"   on the derived cell VALUES): {within}/12 derived cell constants")
    print(f"   land within one OLS SE of their measured counterpart.")
    print(f"\n   P5 (T1) anti-diagonal collapse of the MEASURED table:")
    print(f"     the reflection maps SAFE at p* onto UNSAFE at 1-p*, so each")
    print(f"     pair below must agree within its pooled OLS SE.")
    p5 = []
    for ps in (0.20, 0.50, 0.80):
        for j, lab in ((0, "d"), (2, "c")):
            a = cells[(ps, "SAFE")]
            b = cells[(round(1 - ps, 2), "UNSAFE")]
            diff = a[j] - b[j]
            pooled = math.hypot(a[j + 1], b[j + 1])
            p5.append(abs(diff) <= pooled)
            print(f"     {lab}: SAFE(p*={ps:.2f}) {a[j]:+.3f} vs "
                  f"UNSAFE(p*={1-ps:.2f}) {b[j]:+.3f}  diff {diff:+.3f}  "
                  f"pooled SE {pooled:.3f} -> "
                  f"{'HIT' if p5[-1] else 'MISS'}")
    print(f"     P5: {sum(p5)}/6 -> {'PASS' if all(p5) else 'FAIL'}")
    print(f"   for contrast, the SAME-p* direction contrast the artifact")
    print(f"   reported (SAFE minus UNSAFE at fixed p*), in pooled SE:")
    for ps in (0.20, 0.50, 0.80):
        a, b = cells[(ps, "SAFE")], cells[(ps, "UNSAFE")]
        print(f"     p*={ps:.2f}: d {a[0]-b[0]:+.3f} = "
              f"{abs(a[0]-b[0])/math.hypot(a[1], b[1]):.2f} SE")
    print(f"\n   P6 (T2) sign predicates of the skewness carrier:")
    dd_ = {ps: cells[(ps, "SAFE")][0] - cells[(ps, "UNSAFE")][0]
           for ps in (0.20, 0.50, 0.80)}
    dc_ = {ps: cells[(ps, "SAFE")][2] - cells[(ps, "UNSAFE")][2]
           for ps in (0.20, 0.50, 0.80)}
    pool5 = {ps: math.hypot(cells[(ps, "SAFE")][1], cells[(ps, "UNSAFE")][1])
             for ps in (0.20, 0.50, 0.80)}
    poolc = {ps: math.hypot(cells[(ps, "SAFE")][3], cells[(ps, "UNSAFE")][3])
             for ps in (0.20, 0.50, 0.80)}
    s1 = dd_[0.20] < 0 and dd_[0.80] > 0
    s2 = abs(abs(dd_[0.20]) - abs(dd_[0.80])) <= min(pool5.values())
    s3 = abs(dd_[0.50]) <= pool5[0.50] and abs(dc_[0.50]) <= poolc[0.50]
    s4 = all(dd_[ps] * dc_[ps] < 0 for ps in (0.20, 0.50, 0.80))
    print(f"     S1 dd odd in (p*-1/2): dd(.20) {dd_[0.20]:+.3f} < 0 and "
          f"dd(.80) {dd_[0.80]:+.3f} > 0 -> {'HIT' if s1 else 'MISS'}")
    print(f"     S2 |dd(.20)| = |dd(.80)| (the (1-2p)/pq antisymmetry): "
          f"{abs(dd_[0.20]):.3f} vs {abs(dd_[0.80]):.3f} -> "
          f"{'HIT' if s2 else 'MISS'}")
    print(f"     S3 both null at p*=1/2: dd {dd_[0.50]:+.3f} (SE "
          f"{pool5[0.50]:.3f}), dc {dc_[0.50]:+.3f} (SE {poolc[0.50]:.3f}) "
          f"-> {'HIT' if s3 else 'MISS'}")
    print(f"     S4 c moves opposite to d in every cell -> "
          f"{'HIT' if s4 else 'MISS'}")
    p6 = s1 and s2 and s3 and s4
    print(f"     P6: {'PASS' if p6 else 'FAIL'}")
    print(f"\n   QUANTITATIVE consequence of T1 (reported, folded into P5):")
    print(f"     the direction effect is PREDICTED from the UNSAFE row alone,")
    print(f"     dd(p*) = d_UNSAFE(1-p*) - d_UNSAFE(p*):")
    for ps in (0.20, 0.50, 0.80):
        pred = (cells[(round(1 - ps, 2), "UNSAFE")][0]
                - cells[(ps, "UNSAFE")][0])
        print(f"       p*={ps:.2f}: predicted {pred:+.3f}, measured "
              f"{dd_[ps]:+.3f}, diff {dd_[ps]-pred:+.3f} "
              f"(pooled SE {pool5[ps]:.3f})")
    print(f"   ASSUMPTION CARRIED, disclosed: reflecting an R=1.2 pool at p*")
    print(f"   gives R = {0.8182/0.7818:.3f} at 1-p*=0.80 and "
          f"{0.2727/0.1273:.3f} at 1-p*=0.20, not 1.2, so identifying the")
    print(f"   reflected cell with the MEASURED cell at 1-p* leans on the R")
    print(f"   null of results_wsr_rk.txt (a failure to detect, not a proof).")
    print(f"   At p*=0.50 the reflected pool IS the measured pool exactly, and")
    print(f"   the tau ladders still differ by ~0.001-0.004 in every cell.")

    # ---------------------------------------------------------- 8. summary
    print("\n" + "-" * 76)
    print("SUMMARY")
    print("-" * 76)
    print(f"  P1 {'HIT' if verdict['d_slope'] else 'MISS'} (d slope)  |  "
          f"P2 {'HIT' if verdict['d_int'] else 'MISS'} (d intercept)  |  "
          f"P3 {'HIT' if verdict['c_slope'] else 'MISS'}/"
          f"{'HIT' if verdict['c_int'] else 'MISS'} (c slope/intercept)")
    print(f"  P4 {'PASS' if p4 else 'FAIL'} (convexity)  |  "
          f"P5 {'PASS' if all(p5) else 'FAIL'} ({sum(p5)}/6 reflection)  |  "
          f"P6 {'PASS' if p6 else 'FAIL'} (skewness signs)")
    sd, idd, sc, ic = fits["P"]["ks"]
    print(f"  DERIVED   d = {sd:+.4f} K {idd:+.4f}   c = {sc:+.4f} K {ic:+.4f}")
    print(f"  MEASURED  d = {msd:+.4f} K {mid_:+.4f}   c = {msc:+.4f} K "
          f"{mic:+.4f}")
    print(f"  MECHANISM carrying the K-linearity: the schedule's warm-up length")
    print(f"  in BLOCKS, t0 = K/(4 p(1-p)) (the prior sq_0 = 1/4 divided by the")
    print(f"  block variance p(1-p)/K), together with T = n/K, are the two")
    print(f"  limits of the loglog Kelly-deficit integral G2 whose value IS the")
    print(f"  envelope slope. Both move with K in the same direction; the 1/K")
    print(f"  prefactor makes the true law convex, and the measured linear fit")
    print(f"  is its chord over K in [2, 8].")
    print("-" * 76)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_wsr_envelope.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_wsr_envelope.txt'}")
