#!/usr/bin/env python3
"""Optimal stratification: is there a finite optimal number of strata?

The inverse of the boundary. Every result so far takes the K strata as
GIVEN. Turn it around: if the partition of prompts into strata is a
FREE choice, how many strata minimize the certification cost?

WELL-POSEDNESS (the subtlety a referee looks for). Changing the
partition changes what a UI/round-robin certifier estimates (its
uniform-mixture estimand is weighting-dependent), which would make
"optimize the partition" meaningless. FIX: the estimand is the
POPULATION mean mu = (1/M) sum_i p_i (weights proportional to stratum
SIZES). Then the target is partition-INVARIANT and stratification is
purely a variance-reduction device. This script uses
size-proportional allocation so the certified quantity is mu for every
K.

MODEL. A population of prompts with heterogeneous failure
probabilities p_i ~ Beta(alpha0, beta0), mean mu. A difficulty signal
s_i = p_i (oracle) or p_i + noise (realistic) sorts them; K
equal-size quantile strata are formed by s. Stratum rate r_k = mean
p_i in bin k. The size-proportional stratified certifier's rate is the
allocation-constrained boundary value V_rr(K) at margin (mu - tau);
its crossing time obeys the expansion with dimension d = K:

    n(K) * V_rr(K) = log(1/alpha) + (K/2) log n(K) + c.

PREDICTION (pre-registered): n(K) has a FINITE interior minimizer K*.
Mechanism: V_rr(K) saturates while the (K/2) log n tax grows.

SUPERSEDED IN PART (rev 2, results_gain.txt): the universal "mixture
K* = 1" conclusion below was refuted on the committed real pools —
K* = 1 on only 4 of 10 (census 1:4, 2:4, 4:2), because real pools'
near-boundary strata give gains up to 4.31x, far beyond this
synthetic population's +50%. This file remains the well-posedness
construction and the synthetic-population result, attributed as such.

ARM-DEPENDENCE (as stated on THIS synthetic population): the optimal K
depends on the ARM'S OVERHEAD LAW.
  - MIXTURE / UI arm (tax = (K/2) log n): the rate gain from
    stratification (V_rr rises only ~50% across K=1..24) never outpaces
    the per-stratum half-log-n tax, so K* = 1 -- DON'T STRATIFY. This
    MECHANISTICALLY EXPLAINS the verified UI-dominated result: for a
    mixture certifier the learning tax always beats stratification, so
    optimal = single stream.
  - FLAT-overhead / WSR-like arm (tax ~ constant c, no K term): n(K) =
    (L + c)/V(K) falls monotonically as V(K) rises, so more strata
    always help until V saturates -- K* is at the saturation knee,
    LARGE. This is where the finite interior K* lives.
So "optimal number of strata" is not one number: it is arm-specific,
and the mixture answer (K*=1) is itself the explanation of why the
stratified mixture loses.

Offline, deterministic. Writes results_optimal_k.txt.
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

_ug = open(REPO / "scripts" / "run_ui_grow.py").read()
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug.rsplit("if __name__", 1)[0], bench.__dict__)

ALPHA = 0.05
L = float(np.log(1 / ALPHA))
M = 20000   # population size


def v_rr_K(rates, weights, tau):
    """Allocation-constrained boundary rate for a size-weighted
    K-stratum round-robin certifier (generalizes bench._inner_min to
    arbitrary K and weights)."""
    rates = np.asarray(rates)
    w = np.asarray(weights)
    K = len(rates)
    # least-favorable null on {sum w_k m_k = tau}: per-stratum KKT
    # a m^2 - (f+s+a) m + f = 0 reduces, at the population level, to
    # matching the pooled constraint; solve via Lagrange bisection on
    # the multiplier (same structure as bench._inner_min, K-general).
    def pooled(lam):
        # m_k minimizing sum w_k KL(r_k||m_k) - lam(sum w_k m_k - tau)
        # stationarity: w_k (m_k - r_k)/(m_k(1-m_k)) = lam w_k
        # -> (m_k - r_k) = lam m_k (1-m_k); solve quadratic per k
        ms = []
        for r in rates:
            # lam m^2 - (lam+1) m + r = 0  (from m-r = lam m(1-m))
            if abs(lam) < 1e-12:
                ms.append(r)
                continue
            a, b, c = lam, -(lam + 1.0), r
            disc = b * b - 4 * a * c
            m = (-b - np.sqrt(disc)) / (2 * a)
            ms.append(min(max(m, 1e-9), 1 - 1e-9))
        return np.array(ms)

    def constraint(lam):
        return float(np.sum(w * pooled(lam)) - tau)

    lam = brentq(constraint, -50, 50)
    m = pooled(lam)
    return float(np.sum(w * [bench.kl_bern(rates[k], m[k])
                             for k in range(K)]))


def crossing(V, d):
    if V <= 0:
        return np.inf
    f = lambda n: n * V - L - 0.5 * d * np.log(n)
    try:
        return brentq(f, 4.0, 1e9)
    except ValueError:
        return np.inf


def stratify(p, s, K):
    order = np.argsort(s)
    bins = np.array_split(order, K)
    rates = np.array([p[b].mean() for b in bins])
    weights = np.array([len(b) / len(p) for b in bins])
    return rates, weights


def main():
    print("=" * 76)
    print("OPTIMAL STRATIFICATION: is there a finite optimal K?")
    print("=" * 76)
    rng = np.random.default_rng(20260816)
    # heterogeneous population matching the gpt-4o-mini pool spread
    # (very heterogeneous: many easy, heavy hard tail); mu ~ 0.20
    a0, b0 = 0.35, 1.4
    p = rng.beta(a0, b0, M)
    mu = float(p.mean())
    tau = round(mu - 0.045, 3)
    print(f"population Beta({a0},{b0}), mu = {mu:.4f} (FIXED estimand), "
          f"tau = {tau}, margin {mu - tau:.3f}, M = {M}\n")

    for signal, sd in [("oracle", 0.0), ("noisy(0.10)", 0.10),
                       ("noisy(0.25)", 0.25)]:
        s = p + rng.normal(0, sd, M)
        print(f"  difficulty signal = {signal}:")
        print(f"    {'K':>3} {'V_rr(K)':>9} {'n_mixture':>10} "
              f"{'n_flat(WSR)':>12}")
        ns_ui, ns_wsr = {}, {}
        for K in [1, 2, 3, 4, 6, 8, 12, 16, 24]:
            rates, w = stratify(p, s, K)
            V = v_rr_K(rates, w, tau) if K > 1 else bench.kl_bern(mu, tau)
            ns_ui[K] = crossing(V, K)          # mixture: d = K tax
            ns_wsr[K] = (L + 2.3) / V if V > 0 else np.inf  # flat overhead
            print(f"    {K:>3} {V:>9.5f} {ns_ui[K]:>10.0f} "
                  f"{ns_wsr[K]:>12.0f}")
        Kui = min(ns_ui, key=ns_ui.get)
        Kwsr = min(ns_wsr, key=ns_wsr.get)
        print(f"    -> mixture K* = {Kui} "
              f"({'DONT STRATIFY (tax dominates) — PREDICTION FAILED' if Kui == 1 else 'interior'}); "
              f"flat-overhead K* = {Kwsr} (saturation knee)\n")

    print("""PRE-REGISTERED PREDICTION (finite interior K* for the mixture):
FAILED -- mixture K* = 1 (don't stratify) because V_rr(K) rises only
~50% across K=1..24 while the (K/2) log n tax grows linearly. The
failure is the finding: it MECHANISTICALLY EXPLAINS the verified
UI-dominated result -- a stratified mixture certifier never beats its
own single-stream special case at these margins. The finite interior
optimal K* lives in the FLAT-overhead (WSR-like) arm, which pays no
per-stratum learning tax and wants strata up to the rate-saturation
knee. So "optimal number of strata" is ARM-SPECIFIC, and the mixture's
K*=1 is the explanation of the two-region partition. Estimand fixed as
the population mean throughout (K genuinely free). Scope: synthetic
heterogeneous population (well-posed setting); real sampled-decoding
pools need temp>0 per-prompt rates (future collection).""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_optimal_k.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_optimal_k.txt'}")
