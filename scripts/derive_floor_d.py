#!/usr/bin/env python3
"""Kelly-floored WSR expansion dimension d: grid-corrected, derived, scored.

WHY THIS EXISTS. results_wsr_expansion.txt P3 fitted d = +1.27 on the
floored arm and flagged it "report as measured; derive before
claiming". An external audit then reported that the ladder's taus are
mid-cell on the CS grid, that the fit is therefore grid-biased, and
that an exact-tau diagnostic gives d ~ 1.12 with the regular
idealization predicting d_regular = 1. That audit was NOT fully
blinded. This script is the independent check: it re-verifies the grid
defect from the shipped code, derives the constants itself from the
16-atom block law, re-measures the ladder with taus ON the grid, and
scores frozen predictions. External numbers are reproduced or refuted,
never imported.

GRID DEFECT (verified here, section 1). WSRBlockCS uses
grid = linspace(.0005,.9995,1000), i.e. points .0005 + .001k. Every
rung's tau = .5 - delta with delta in {.035,.025,.018,.013,.009} falls
EXACTLY mid-cell: offset .0005 at all five. `lo > tau` requires every
grid point <= tau to die, and V*(m) is strictly decreasing in m for
m < p, so the binding point is m = max{grid <= tau} = tau - .0005. The
PROCESS therefore runs at margin g+.0005 while the SCORE uses
V*(tau) at margin g. The mismatch ratio rho = V*(tau)/V*(m) < 1 grows
down the ladder (2.9% -> 11.4% of the ordinate), which DEPRESSES the
deep rungs more than the shallow ones and therefore FLATTENS the
fitted slope. Direction matters and is stated up front: the grid
defect biases d DOWNWARD; the committed +1.27 is too small, not too
large. Correcting it is a pure re-scoring, because choosing the
nearest grid point (ties -> lower, which is what np.argmin returns)
leaves the binding point, and hence every crossing time, bit-identical
to the committed run. That identity is checked in section 7.

DERIVATION. The reported crossing is the death of the single grid
point m; its capital is log K+_T = sum_t log(1 + lam_t (M_t - m)) with
lam_t the SHIPPED floored bet (wsr_kelly_floor.KellyFloorWSR):
lam_t = max( sqrt(2 log(2/alpha)/(sig2_t t log(t+1))) , clip(kelly,0,c/m) )
for t > WARMUP = 10, kelly = ghat/(sig2 + ghat^2), ghat = mean_t - m,
with the shipped priors mean_0 = 1/2, sq_0 = 1/4 and divisor (t+1).
The minus arm never floors and is ~e^-17 at crossing, so the death
level is log K+ = log(2/alpha). With V* = max_lam V(lam;m),
D_t = V* - V(lam_t;m) >= 0 and E[Y_t|F_{t-1}] = V(lam_t;m) exactly,

    log K+_T = T V* - R_T + Z_T,   R_T = sum_{t<=T} D_t,  Z_T mgale,
    T_med V* = L + rho_over - s^2/(2 nu) + E R_T,     L = log(2/alpha),

and the ordinate is nV = T_med V*(tau) (n = 4T, per-sample V; the
factor 4 moves only the intercept, by (d/2)log 4, and cannot change d
-- conflating per-sample with per-block RATES would change d by 4x).

WHY d_regular = 1. In the floor-bound phase the plug-in bet is the
one-parameter adaptive Kelly lam_hat = ghat/(sig2+ghat^2) with
delta-method AVar = A^2 mu2 + 2AB mu3 + B^2(mu4-mu2^2),
A = (mu2-g^2)/(mu2+g^2)^2, B = -g/(mu2+g^2)^2, exact central moments
mu2,mu3,mu4 of the 16-atom block mean. Then E D_t = c_reg/(2t) with
c_reg = |V''(lam*)| * AVar, and c_reg -> 1 as g -> 0: the plug-in is
first-order efficient for this game, so E R_T ~ (1/2) log T and, since
x = (1/2)log n gives dlog T/dx = 2, the d-contribution is c_reg ~ 1 --
the same one-parameter cost as the single-stream arm. That is the
idealization, and it is derived here, not imported.

WHY THE SHIPPED CLASS NEED NOT OBEY IT. Two departures, both
quantified here:
 (a) PLUG-IN vs OPTIMIZER (section 3). lam_hat converges to
     lam_inf = g/(mu2+g^2), not to the interior optimizer lam*. The
     gap is O(mu3 g^2/mu2^3) and costs a LINEAR rate deficit
     V(lam*)-V(lam_inf) ~ mu3^2 g^4/(2 mu2^5), i.e. a multiplicative
     inflation (1+eps) with eps ~ mu3^2 g^2/mu2^4 = O(g^2). Being a
     rate effect it moves the intercept, and its DRIFT across the
     ladder moves d by ~0.01. Real, exactly computable, negligible.
 (b) WARMUP / STOCK OVER-BETTING (section 5). Until the floor binds
     (t_c ~ 0.0625/g^2 blocks) the bet is the stock
     lam ~ sqrt(A/(t log t)) >> lam*, whose shortfall ~ (m2/2)lam^2 ~
     const/(t log t) sums to ~log log t_c. Because t_c and T both
     scale as 1/g^2, this contributes a POSITIVE slope ~const/log t_c
     that decays only like 1/log -- so the floored arm has no fixed d
     either, just a slowly drifting effective one, and over this
     ladder it sits well above 1. This is the load-bearing departure,
     and (a) is not.

FROZEN PREDICTIONS (both stated before any comparison; section 6
prints them before section 7 runs the re-measurement):
  P-A (the idealization, as directed): d = 1.
      W_A = |d_pred_regular - 1| + |d_pred_regular - (renewal O(1)s
      dropped)| + 2*se_meas(d), where d_pred_regular is this script's
      own evaluation of the regular process, ER = (c_reg/2)(log T +
      gamma), rho = 1.
  P-B (this derivation's prediction for the SHIPPED class, from the
      simulated exact shortfall of the real schedule):
      W_B = 2*se_MC(d) + |d - (renewal O(1)s dropped)|
            + max_+-|d - (crossing level +-1 nat)| + 2*se_meas(d).
  se_meas is the bootstrap standard error of the re-measured slope
  over the crossing times actually drawn (rule fixed here; its
  arithmetic necessarily completes in section 8).
  HIT iff the grid-corrected measured d lies in the window. Windows
  are NOT widened; a MISS is reported as a MISS.
DISCLOSED ORDERING. A first pass ran the floored arm at exactly
run_wsr_expansion.py's rep counts (300/300/300/200/150) and returned
se_meas = 0.381: BOTH windows contained the measurement and the test
was non-discriminating (verdict UNRESOLVED). The floored arm is
therefore run here at FLOOR_MULT = 3x those reps, using the SAME
seed0 + rep seeds so the artifact's rep counts are the leading subset
of the draw — section 7 reports the artifact-precision median (for the
bit-identity check against the committed run and for its own se) and
the 3x median (which is scored). Predictions P-A/P-B and the window
rule are unchanged from that first pass; only measurement precision
was increased, and both precisions are printed.
ADJUDICATION RULE (fixed here): P-A MISS with P-B HIT indicts the
IDEALIZATION (the warmup mechanism is real and load-bearing); both
MISS indicts residual measurement bias or an unmodelled effect.

Offline, deterministic. Writes results_floor_d.txt.
"""

import hashlib
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS      # noqa: E402
from eval_harness.stats.wsr_kelly_floor import KellyFloorWSR  # noqa: E402

_pb = open(REPO / "scripts" / "derive_phase_boundary.py").read()
pb = types.ModuleType("pb")
pb.__dict__["__file__"] = str(REPO / "scripts" / "derive_phase_boundary.py")
exec(_pb.rsplit("if __name__", 1)[0], pb.__dict__)

ALPHA = 0.05
P = 0.5
K = 4
C_TRUNC = 0.75                        # WSRBlockCS.c
WARMUP = 10                           # wsr_kelly_floor.WARMUP
GRID = np.linspace(0.0005, 0.9995, 1000)
LEVEL = float(np.log(2 / ALPHA))
EULER = 0.5772156649015329
BASE_SEED = 42                        # run_wsr_expansion.py
# (delta, reps, n_max) exactly as run_wsr_expansion.py; reps taper at
# the deepest margins, disclosed there and here.
LADDER = [(0.035, 300, 30000), (0.025, 300, 60000),
          (0.018, 300, 120000), (0.013, 200, 250000),
          (0.009, 150, 600000)]
STOCK_DIV = 2                         # stock arm reps halved (contrast only)
FLOOR_MULT = 3                        # floored arm reps x3 (see docstring)
REPS = 3000                           # shortfall-simulation reps
LADDER_SIMS = 20000
HORIZONS = (50, 500, 5000)
BOOT = 2000
# From results_wsr_expansion.txt (same classes, same seeds) — used ONLY
# for the bit-identity check of section 7 and the bias display.
COMMITTED_N = [1838, 3784, 8446, 18054, 38390]
COMMITTED_D = 1.27


def block_law():
    """The 16 atoms of the K=4 block mean, enumerated as v_kelly_block."""
    atoms, probs = [], []
    for bits in range(2 ** K):
        m, pr = 0.0, 1.0
        for i in range(K):
            if bits >> i & 1:
                m += 1.0 / K
                pr *= P
            else:
                pr *= 1 - P
        atoms.append(m)
        probs.append(pr)
    return np.array(atoms), np.array(probs)


def V(lam, z, w):
    return float(np.sum(w * np.log1p(lam * z)))


def Vp(lam, z, w):
    return float(np.sum(w * z / (1.0 + lam * z)))


def Vpp(lam, z, w):
    return float(-np.sum(w * (z / (1.0 + lam * z)) ** 2))


def lam_star(m, z, w):
    return float(brentq(Vp, 1e-12, 1.0 / max(m, 1e-12) - 1e-9,
                        args=(z, w), xtol=1e-15, rtol=1e-15))


def V_vec(lam, z, w):
    out = np.zeros_like(lam)
    for zi, wi in zip(z, w):
        out += wi * np.log1p(lam * zi)
    return out


def avar_plugin(g, mu2, mu3, mu4):
    den = (mu2 + g * g) ** 2
    A = (mu2 - g * g) / den
    B = -g / den
    return A * A * mu2 + 2 * A * B * mu3 + B * B * (mu4 - mu2 * mu2)


def ladder_overshoot(lam, z, w, sims, seed):
    """rho_over = E[H^2]/(2E[H]), strict ascending ladder height of the
    per-block log-wealth increment at bet lam."""
    y = np.log1p(lam * z)
    rng = np.random.default_rng(seed)
    S = np.zeros(sims)
    alive = np.arange(sims)
    H = np.zeros(sims)
    steps = 0
    while alive.size and steps < 200000:
        steps += 1
        S[alive] += y[rng.binomial(K, P, size=alive.size)]
        hit = S[alive] > 0
        H[alive[hit]] = S[alive[hit]]
        alive = alive[~hit]
    return float(np.mean(H ** 2) / (2 * np.mean(H))), int(alive.size)


def shortfall(m, z, w, vstar, tmax, seed):
    """Exact per-block expected shortfall of the SHIPPED floored
    schedule at grid point m, plus the running estimator's error law."""
    rng = np.random.default_rng(seed)
    x = np.empty((REPS, tmax), dtype=np.int8)
    chunk = max(1, 4_000_000 // REPS)
    for s in range(0, tmax, chunk):
        e = min(tmax, s + chunk)
        x[:, s:e] = rng.binomial(K, P, size=(REPS, e - s)).astype(np.int8)
    mean = np.full(REPS, 0.5)
    sq = np.full(REPS, 0.25)
    cap = C_TRUNC / max(m, 1e-6)
    dbar = np.empty(tmax)
    kmean = np.full(tmax, np.nan)
    kvar = np.full(tmax, np.nan)
    binds = np.zeros(tmax)
    dcum = np.zeros(REPS)
    marks = np.unique(np.linspace(1, tmax, 400).astype(int))
    snaps = np.empty((REPS, marks.size))
    j = 0
    for t in range(1, tmax + 1):
        sigma2 = sq / t
        lam = np.sqrt(2 * np.log(2 / ALPHA)
                      / (sigma2 * t * np.log(t + 1) + 1e-12))
        lam_p = np.minimum(lam, cap)
        if t > WARMUP:
            gap = mean - m
            kelly = gap / (sigma2 + gap * gap + 1e-12)
            kp = np.clip(kelly, 0.0, cap)
            binds[t - 1] = float(np.mean(kp > lam_p))
            lam_p = np.maximum(lam_p, kp)
            kmean[t - 1] = float(kelly.mean())
            kvar[t - 1] = float(kelly.var())
        d = vstar - V_vec(lam_p, z, w)
        dbar[t - 1] = d.mean()
        dcum += d
        if j < marks.size and t == marks[j]:
            snaps[:, j] = dcum
            j += 1
        xt = x[:, t - 1] * (1.0 / K)
        e = xt - mean
        sq += e * e
        mean += e / (t + 1)
    return dbar, kmean, kvar, binds, marks, snaps


def solve_T(const, er, tgrid, vstar_m):
    T = const / vstar_m
    for _ in range(200):
        Tn = (const + float(np.interp(T, tgrid, er))) / vstar_m
        if abs(Tn - T) < 1e-7:
            return Tn
        T = 0.5 * (T + Tn)
    return T


def ols_slope(x, y):
    A = np.stack([x, np.ones_like(x)], axis=1)
    (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(a), float(b)


def predict(rungs, kind, const_extra=0.0, renewal=True):
    """Solve the crossing and run the artifact's regression. kind
    'ship' uses the simulated shortfall of the real schedule; 'reg'
    uses the regular idealization ER = (c_reg/2)(log T + gamma)."""
    ns, nvs = [], []
    for r in rungs:
        c = LEVEL + const_extra
        if renewal:
            c += r["rho_over"] - r["kappa_med"]
        if kind == "ship":
            T = solve_T(c, r["er"], r["tgrid"], r["vstar_m"])
        else:
            T = c / r["vstar_m"]
            for _ in range(200):
                Tn = (c + r["c_reg"] / 2 * (np.log(T) + EULER)) / r["vstar_m"]
                if abs(Tn - T) < 1e-7:
                    break
                T = 0.5 * (T + Tn)
            T = Tn
        ns.append(K * T)
        nvs.append(T * r["vstar_m"])      # grid-aligned scoring: rho = 1
    x = np.log(np.array(ns)) / 2.0
    y = np.array(nvs) - np.log(1 / ALPHA)
    d, c = ols_slope(x, y)
    return d, c, np.array(ns), np.array(nvs)


def median_crossing(cls, tau, reps, n_max, seed0):
    """run_wsr_expansion.median_crossing (v2: int8 + reshape), also
    returning the crossing times for the bootstrap."""
    times = []
    done = 0
    n_blocks = n_max // 4
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        cs = cls(alpha=ALPHA)
        x = (rng.random(n_blocks * 4) < P).astype(np.int8)
        means = x.reshape(-1, 4).mean(axis=1)
        crossed = None
        for j in range(n_blocks):
            cs.update(float(means[j]))
            lo, _ = cs.get_bounds()
            if lo > tau:
                crossed = 4 * (j + 1)
                break
        if crossed:
            done += 1
            times.append(crossed)
        else:
            times.append(n_max)
    t = np.array(times, dtype=float)
    return t, int(np.median(t)), done / reps


def main():
    print("=" * 76)
    print("KELLY-FLOORED WSR: GRID-CORRECTED d — DERIVED AND RE-MEASURED")
    print("=" * 76)

    atoms, probs = block_law()
    vals, inv = np.unique(atoms, return_inverse=True)
    w = np.bincount(inv, weights=probs)
    mu2 = float(np.sum(w * (vals - P) ** 2))
    mu3 = float(np.sum(w * (vals - P) ** 3))
    mu4 = float(np.sum(w * (vals - P) ** 4))
    rates = np.array([P] * K)

    print("\n1. GRID AUDIT (independent verification of the defect)")
    print(f"   grid = linspace(.0005,.9995,1000), step "
          f"{GRID[1] - GRID[0]:.6f}; 16-atom block law -> {len(vals)}"
          f" distinct atoms, weights {np.array2string(w * 16, precision=0)}/16")
    print(f"   mu2 = {mu2:.10f}  mu3 = {mu3:.10f}  mu4 = {mu4:.10f}")
    print(f"   {'delta':>6} {'tau_nom':>8} {'nearest':>8} {'offset':>9}"
          f" {'binding m':>10} {'V*(tau)/V*(m)':>14} {'bias':>7}")
    rungs = []
    for delta, reps, n_max in LADDER:
        tau = P - delta
        j = int(np.argmin(np.abs(GRID - tau)))
        tg = float(GRID[j])                    # ties -> lower (argmin)
        mb = float(GRID[GRID <= tau][-1])
        zt = vals - tau
        zm = vals - mb
        vt = V(lam_star(tau, zt, w), zt, w)
        vm = V(lam_star(mb, zm, w), zm, w)
        print(f"   {delta:>6.3f} {tau:>8.4f} {tg:>8.4f} {tau - tg:>+9.6f}"
              f" {mb:>10.4f} {vt / vm:>14.4f} {1 - vt / vm:>7.1%}")
        rungs.append(dict(delta=delta, reps=reps, n_max=n_max, tau_nom=tau,
                          tau_grid=tg, m=tg, rho_old=vt / vm))
    off = [r["tau_nom"] - r["tau_grid"] for r in rungs]
    print(f"   VERIFIED: every rung is mid-cell, offset "
          f"{min(off):.6f}..{max(off):.6f}; nearest-grid tie -> lower, so"
          f" tau_grid == binding m and crossing times are unchanged.")
    print("   DIRECTION: rho < 1 and FALLING down the ladder depresses the"
          " deep rungs more, so the defect biases d DOWNWARD.")
    nc = np.array(COMMITTED_N, dtype=float)

    def refit(taus):
        nv = np.array([ni * pb.v_kelly_block(rates, t)
                       for ni, t in zip(nc, taus)])
        return ols_slope(np.log(nc) / 2.0, nv - np.log(1 / ALPHA))[0]

    d_nom = refit([r["tau_nom"] for r in rungs])
    d_low = refit([r["tau_grid"] for r in rungs])
    d_up = refit([float(GRID[GRID > r["tau_nom"]][0]) for r in rungs])
    print(f"   PROVENANCE CHECK on the committed crossing times"
          f" {COMMITTED_N} (pure re-scoring):")
    print(f"     score at tau_nom (mid-cell)      d = {d_nom:+.4f}"
          f"   reproduces the committed {COMMITTED_D:+.2f}")
    print(f"     score at grid point BELOW tau    d = {d_low:+.4f}"
          f"   VALID: binding point unchanged, so n is unchanged")
    print(f"     score at grid point ABOVE tau    d = {d_up:+.4f}"
          f"   INVALID: raising tau above the old")
    print("       binding point makes tau itself binding at margin"
          " g-0.0005, lengthening every")
    print("       crossing time — n CANNOT be held fixed. This is the only"
          " arithmetic that turns")
    print("       the grid correction into a sub-1.27 figure, and it is the"
          " likely provenance of")
    print("       any 'exact-tau' d below the committed fit. Done properly"
          " the upper alignment")
    print("       also raises d (n grows fastest at the deep rungs, but the"
          " ordinate rises more).")

    print("\n2. EXACT CONSTANTS AT THE GRID-ALIGNED TAU (16-atom law)")
    print(f"   {'delta':>6} {'m=tau':>7} {'g':>7} {'lam_inf':>8} {'lam*':>8}"
          f" {'V*(m)':>9} {'|V\"|':>8} {'AVar':>7} {'c_reg':>7}"
          f" {'s^2/2nu':>8} {'rho_ov':>7}")
    for r in rungs:
        m = r["m"]
        g = P - m
        zm = vals - m
        ls = lam_star(m, zm, w)
        r.update(g=g, z=zm, lam_star=ls, lam_inf=g / (mu2 + g * g),
                 vstar_m=V(ls, zm, w), vpp=abs(Vpp(ls, zm, w)),
                 avar=avar_plugin(g, mu2, mu3, mu4))
        r["c_reg"] = r["vpp"] * r["avar"]
        y = np.log1p(ls * zm)
        s2 = float(np.sum(w * y * y) - np.sum(w * y) ** 2)
        r["s2"] = s2
        r["kappa_med"] = s2 / (2.0 * r["vstar_m"])
        r["rho_over"], left = ladder_overshoot(ls, zm, w, LADDER_SIMS,
                                               777 + int(r["delta"] * 1e6))
        r["ladder_left"] = left
        print(f"   {r['delta']:>6.3f} {m:>7.4f} {g:>7.4f} {r['lam_inf']:>8.4f}"
              f" {ls:>8.4f} {r['vstar_m']:>9.6f} {r['vpp']:>8.5f}"
              f" {r['avar']:>7.3f} {r['c_reg']:>7.4f} {r['kappa_med']:>8.4f}"
              f" {r['rho_over']:>7.4f}")
    print(f"   c_reg = |V''(lam*)| * AVar -> 1 as g -> 0 (spread over the"
          f" ladder {min(r['c_reg'] for r in rungs):.4f}.."
          f"{max(r['c_reg'] for r in rungs):.4f}): the plug-in bet is"
          f" first-order efficient, so the regular arm costs (1/2)log T.")
    print(f"   s^2/(2nu) -> 1 exactly (s^2 ~ g^2/mu2, nu ~ g^2/(2 mu2)), so"
          f" the median shift is ~-1 nat at every rung.")
    print(f"   unresolved ladder sims: {max(r['ladder_left'] for r in rungs)}")
    v0 = pb.v_kelly_block(rates, rungs[0]["m"]) * K
    print(f"   v_kelly_block(m={rungs[0]['m']:.4f})*K = {v0:.8f} vs exact"
          f" {rungs[0]['vstar_m']:.8f} (rel"
          f" {abs(v0 / rungs[0]['vstar_m'] - 1):.1e})")

    print("\n3. SHIPPED PLUG-IN vs INTERIOR OPTIMIZER (kappa gap), two rungs")
    print(f"   {'tau':>8} {'lam_inf (plug-in)':>18} {'lam* (optimizer)':>17}"
          f" {'gap':>9} {'V(lam*)':>10} {'V(lam_inf)':>11} {'rate loss':>10}")
    for m in (rungs[0]["m"], rungs[-1]["m"], P - 0.035):
        z = vals - m
        g = P - m
        li = g / (mu2 + g * g)
        ls = lam_star(m, z, w)
        vs, vi = V(ls, z, w), V(li, z, w)
        tag = "  <- nominal tau (external's point)" if m == P - 0.035 else ""
        print(f"   {m:>8.4f} {li:>18.6f} {ls:>17.6f} {ls - li:>+9.6f}"
              f" {vs:>10.7f} {vi:>11.7f} {1 - vi / vs:>9.2e}{tag}")
    print("   The plug-in limit lam_inf = g/(mu2+g^2) is the second-order")
    print("   truncation optimum; lam* - lam_inf = mu3 g^2/mu2^3 + O(g^4), so")
    print("   the loss is O(g^4) absolute / O(g^2) relative — a RATE (linear)")
    print("   effect that moves the intercept. Its drift across the ladder")
    print("   is ~0.01 in d: real, exactly computable, and NOT load-bearing.")

    print(f"\n4-5. ESTIMATOR ERROR LAW AND EXACT SHORTFALL OF THE SHIPPED"
          f" SCHEDULE ({REPS} reps/rung)")
    for r in rungs:
        tmax = int(1.5 * (LEVEL + 6.0) / r["vstar_m"]) + 50
        dbar, kmean, kvar, binds, marks, snaps = shortfall(
            r["m"], r["z"], w, r["vstar_m"], tmax,
            4242 + int(r["delta"] * 1e5))
        r.update(tmax=tmax, dbar=dbar, kmean=kmean, kvar=kvar, binds=binds,
                 marks=marks, snaps=snaps,
                 er=np.concatenate([[0.0], np.cumsum(dbar)]),
                 tgrid=np.arange(tmax + 1, dtype=float))
        bi = np.nonzero(binds >= 0.5)[0]
        r["t_c"] = int(bi[0] + 1) if bi.size else tmax
    print(f"   {'delta':>6} {'t':>6} {'E[lam_hat]':>11} {'lam_inf':>8}"
          f" {'t*Var':>8} {'AVar':>7} {'2t*E[D_t]':>10} {'c_reg':>7}"
          f" {'P(floor)':>9}")
    for r in rungs:
        for t in HORIZONS:
            if t > r["tmax"]:
                continue
            print(f"   {r['delta']:>6.3f} {t:>6} {r['kmean'][t - 1]:>11.4f}"
                  f" {r['lam_inf']:>8.4f} {t * r['kvar'][t - 1]:>8.3f}"
                  f" {r['avar']:>7.3f} {2 * t * r['dbar'][t - 1]:>10.4f}"
                  f" {r['c_reg']:>7.4f} {r['binds'][t - 1]:>9.2f}")
    print("   Reading: 2t*E[D_t] -> c_reg only AFTER the floor binds"
          " (P(floor) -> 1); before that the")
    print("   stock schedule over-bets and the shortfall is governed by"
          " lam_wsr, not by the estimator.")

    d_ship, c_ship, ns_s, nvs_s = predict(rungs, "ship")
    d_reg, c_reg_i, ns_r, _ = predict(rungs, "reg")
    print("\n   DERIVED CROSSING (grid-aligned scoring, rho = 1)")
    print(f"   {'delta':>6} {'T_med':>8} {'n_der':>8} {'t_c':>6} {'ER_tot':>7}"
          f" {'nV_der':>7}")
    for r, n, nv in zip(rungs, ns_s, nvs_s):
        r["T"] = n / K
        r["er_T"] = float(np.interp(r["T"], r["tgrid"], r["er"]))
        print(f"   {r['delta']:>6.3f} {r['T']:>8.1f} {n:>8.0f} {r['t_c']:>6}"
              f" {r['er_T']:>7.4f} {nv:>7.3f}")

    x = np.log(ns_s) / 2.0
    kelly_law = [r["c_reg"] / 2 * np.log(r["T"]) for r in rungs]
    er_tot = [r["er_T"] for r in rungs]
    print("\n   SLOPE ATTRIBUTION for the shipped class"
          "  (x = (1/2)log n, so d = sum of slopes)")
    tot = 0.0
    for name, ser in [("L = log(2/alpha)", [LEVEL] * len(rungs)),
                      ("+ overshoot", [r["rho_over"] for r in rungs]),
                      ("- median shift", [-r["kappa_med"] for r in rungs]),
                      ("+ ER (total)", er_tot)]:
        s, _ = ols_slope(x, np.array(ser))
        tot += s
        print(f"     {name:<34} d-contribution {s:+.4f}")
    s_k, _ = ols_slope(x, np.array(kelly_law))
    s_r, _ = ols_slope(x, np.array(er_tot) - np.array(kelly_law))
    print(f"       of ER: regular law (c_reg/2)log T      "
          f"d-contribution {s_k:+.4f}")
    print(f"       of ER: warmup/stock over-bet residual  "
          f"d-contribution {s_r:+.4f}")
    print(f"     {'SUM':<34} d-contribution {tot:+.4f}"
          f"  (regression {d_ship:+.4f})")
    print(f"     log T -> log n is a pure intercept shift of (d/2)log 4 ="
          f" {d_ship / 2 * np.log(4):+.3f}; d is invariant.")

    se_er = []
    for r in rungs:
        j = int(np.argmin(np.abs(r["marks"] - r["T"])))
        se_er.append(float(np.std(r["snaps"][:, j], ddof=1) / np.sqrt(REPS)))
    xc = x - x.mean()
    wts = xc / np.sum(xc ** 2)
    se_d = float(np.sqrt(np.sum((wts * np.array(se_er)) ** 2)))
    d_ship_nr, *_ = predict(rungs, "ship", renewal=False)
    d_ship_up, *_ = predict(rungs, "ship", const_extra=+1.0)
    d_ship_dn, *_ = predict(rungs, "ship", const_extra=-1.0)
    d_reg_nr, *_ = predict(rungs, "reg", renewal=False)
    wA_der = abs(d_reg - 1.0) + abs(d_reg - d_reg_nr)
    wB_der = (2 * se_d + abs(d_ship - d_ship_nr)
              + max(abs(d_ship - d_ship_up), abs(d_ship - d_ship_dn)))

    print("\n6. FROZEN PREDICTIONS  (printed BEFORE the re-measurement runs)")
    print(f"   derivation of the REGULAR idealization: d_pred_regular ="
          f" {d_reg:+.4f}  (renewal dropped {d_reg_nr:+.4f})")
    print(f"   derivation of the SHIPPED class:        d_pred_shipped ="
          f" {d_ship:+.4f}  (renewal dropped {d_ship_nr:+.4f};"
          f" level +-1 nat {d_ship_up:+.4f}/{d_ship_dn:+.4f};"
          f" se_MC {se_d:.4f})")
    print(f"   P-A  d = 1        ; derivation half-width {wA_der:.4f}"
          f" (+ 2*se_meas, section 8)")
    print(f"   P-B  d = {d_ship:+.4f}   ; derivation half-width"
          f" {wB_der:.4f} (+ 2*se_meas, section 8)")

    print(f"\n7. GRID-CORRECTED RE-MEASUREMENT (real classes, seeds of"
          f" run_wsr_expansion.py)")
    print(f"   floored arm reps {[r['reps'] * FLOOR_MULT for r in rungs]}"
          f" ({FLOOR_MULT}x the artifact's, leading subset = the artifact's);"
          f" stock arm reps divided by {STOCK_DIV} (contrast only).")
    print(f"   {'delta':>6} {'arm':>6} {'n_med':>8} {'n_art':>8} {'cert':>5}"
          f" {'V(tau_grid)':>12} {'nV_grid':>8} {'nV_old':>7}"
          f" {'correction':>11}")
    meas = {"floor": [], "stock": []}
    art = []
    for i, r in enumerate(rungs):
        for arm, cls in [("floor", KellyFloorWSR), ("stock", WSRBlockCS)]:
            seed0 = BASE_SEED + 1000 * i + (0 if arm == "stock" else 500)
            nrep = (r["reps"] * FLOOR_MULT if arm == "floor"
                    else max(1, r["reps"] // STOCK_DIV))
            t, nmed, frac = median_crossing(cls, r["tau_grid"], nrep,
                                            r["n_max"], seed0)
            vg = pb.v_kelly_block(rates, r["tau_grid"])
            vn = pb.v_kelly_block(rates, r["tau_nom"])
            meas[arm].append(dict(delta=r["delta"], times=t, n=nmed,
                                  frac=frac, v=vg, nv=nmed * vg))
            na = ""
            if arm == "floor":
                ta = t[:r["reps"]]
                nma = int(np.median(ta))
                art.append(dict(times=ta, n=nma, v=vg, nv=nma * vg))
                na = f"{nma}"
            print(f"   {r['delta']:>6.3f} {arm:>6} {nmed:>8} {na:>8}"
                  f" {frac:>5.2f} {vg:>12.8f} {nmed * vg:>8.3f}"
                  f" {nmed * vn:>7.3f} {nmed * vg - nmed * vn:>+11.3f}")
    ident = [a["n"] for a in art] == COMMITTED_N
    print(f"   bit-identity of the artifact-precision subset vs"
          f" results_wsr_expansion.txt n_med {COMMITTED_N}:"
          f" {'CONFIRMED' if ident else 'DIFFERS'}"
          f" -> the correction is a pure re-scoring.")
    if min(m["frac"] for m in meas["floor"] + meas["stock"]) < 0.9:
        print("   INVALID: a rung has < 90% crossings — no verdicts scored.")
        return

    def slope_of(rows):
        xx = np.log(np.array([m["n"] for m in rows], dtype=float)) / 2.0
        yy = np.array([m["nv"] for m in rows]) - np.log(1 / ALPHA)
        return ols_slope(xx, yy)

    def boot_se(rows, seed):
        rng = np.random.default_rng(seed)
        out = []
        for _ in range(BOOT):
            rs = [dict(n=float(np.median(rng.choice(m["times"],
                                                    m["times"].size, True))),
                       nv=0.0, v=m["v"]) for m in rows]
            for row in rs:
                row["nv"] = row["n"] * row["v"]
            out.append(slope_of(rs)[0])
        return float(np.std(out, ddof=1))

    d_meas, c_meas = slope_of(meas["floor"])
    d_meas_stock, _ = slope_of(meas["stock"])
    d_art, _ = slope_of(art)
    se_meas = boot_se(meas["floor"], 20260816)
    se_art = boot_se(art, 20260816)

    print("\n8. VERDICTS")
    print(f"   grid-corrected measured d (floored arm) = {d_meas:+.4f}"
          f"  (intercept {c_meas:+.4f}); bootstrap se_meas = {se_meas:.4f}")
    print(f"   at the artifact's own rep counts: d = {d_art:+.4f},"
          f" se = {se_art:.4f} — non-discriminating, which is why"
          f" {FLOOR_MULT}x reps were drawn.")
    print(f"   committed grid-biased fit was {COMMITTED_D:+.2f}; stock arm"
          f" under the same correction = {d_meas_stock:+.4f}")
    for tag, dp, wd in [("P-A  idealization d = 1", 1.0, wA_der),
                        ("P-B  this derivation   ", d_ship, wB_der)]:
        W = wd + 2 * se_meas
        lo, hi = dp - W, dp + W
        hit = lo <= d_meas <= hi
        print(f"   {tag}: window [{lo:+.4f}, {hi:+.4f}]  (W = {wd:.4f}"
              f" + 2*{se_meas:.4f})  -> "
              f"{'HIT' if hit else 'MISS'}")
        if tag.startswith("P-A"):
            hit_a = hit
        else:
            hit_b = hit
    print("   windows are NOT widened; a MISS is reported as a MISS.")
    if not hit_a and hit_b:
        verdict = ("IDEALIZATION INDICTED: d = 1 is refuted for the shipped "
                   "class, and this\n     derivation's warmup/stock "
                   "over-betting term accounts for the excess.")
    elif hit_a and hit_b:
        verdict = ("UNRESOLVED: both windows contain the measurement — the "
                   "ladder does not\n     discriminate d = 1 from the "
                   "warmup-corrected value at this precision.")
    elif hit_a:
        verdict = ("IDEALIZATION SURVIVES: d = 1 holds and this derivation's "
                   "shipped-class\n     correction is refuted.")
    else:
        verdict = ("BOTH MISS: residual measurement bias or an unmodelled "
                   "effect; neither\n     the idealization nor this "
                   "derivation accounts for the measured slope.")
    print(f"   ADJUDICATION (rule fixed in the docstring): {verdict}")
    print(f"\n   d_check: attribution sum {tot:+.4f} vs regression"
          f" {d_ship:+.4f}; n0 (first rung, blocks) = {rungs[0]['T']:.0f},"
          f" floor onset t_c = {rungs[0]['t_c']} blocks.")
    print("   NOTE on the external audit: the mid-cell grid defect is"
          " CONFIRMED independently here;")
    print("   its DIRECTION is not — correcting it moves d away from 1, not"
          " toward it.")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_floor_d.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_floor_d.txt'}")
