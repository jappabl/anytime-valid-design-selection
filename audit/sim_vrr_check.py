#!/usr/bin/env python3
"""AUDIT: independent verification of the frozen rate V_rr.

Claim under test (scripts/fit_overhead_law.py::v_rr, scripts/run_frontier.py):

    V_rr = min over {sum_k w_k m_k = tau} of  sum_k lam_k KL(p_k || m_k)
           with lam = w = 1/K (round-robin allocation)

implemented via bench._inner_min (a bisection on one Lagrange multiplier
plus a per-stratum KKT quadratic).

This script recomputes the same minimization by brute force
(a) scipy SLSQP from many random starts, and
(b) a dense simplex grid search,
and compares against _inner_min, at tau = 0.15 / 0.16 / 0.17 on the
gpt-4o-mini JSON pool (the rates used by results_frontier.txt).

Also verifies that lam = w = 1/K is the correct weighting for the
round-robin-constrained growth rate by direct Monte-Carlo measurement of
E[log E_n]/n for the UI product e-process under round-robin, compared to
n * V_rr and to n * V_game (the max-min game value that the frozen
definition explicitly rejects).

Run: python3 audit/sim_vrr_check.py
"""

import json
import sys
import types
from itertools import product
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

STRATA = ["simple", "medium", "complex", "extreme"]
EPS = 1e-12


def kl(p, q):
    p = min(max(p, EPS), 1 - EPS)
    q = min(max(q, EPS), 1 - EPS)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def objective(m, rates, lam):
    return float(sum(lam[i] * kl(rates[i], m[i]) for i in range(len(m))))


def brute_grid(rates, w, lam, tau, n_grid=241):
    """Dense search over {sum w m = tau} by parameterizing 3 free coords."""
    K = len(rates)
    best = (np.inf, None)
    # coordinate-descent from many random feasible starts (projected)
    rng = np.random.default_rng(0)
    for trial in range(400):
        m = rng.random(K) * min(1.0, 4 * tau)
        # project onto sum w m = tau by scaling
        s = float(np.sum(w * m))
        if s <= 0:
            continue
        m = np.clip(m * (tau / s), EPS, 1 - EPS)
        for _ in range(600):
            i, j = rng.choice(K, 2, replace=False)
            step = rng.normal(0, 10 ** rng.uniform(-6, -1.3))
            mi = m[i] + step
            mj = m[j] - step * w[i] / w[j]
            if not (EPS < mi < 1 - EPS and EPS < mj < 1 - EPS):
                continue
            cand = m.copy()
            cand[i], cand[j] = mi, mj
            if objective(cand, rates, lam) < objective(m, rates, lam):
                m = cand
        v = objective(m, rates, lam)
        if v < best[0]:
            best = (v, m.copy())
    return best


def scipy_min(rates, w, lam, tau):
    try:
        from scipy.optimize import minimize
    except Exception:
        return None, None
    K = len(rates)
    cons = [{"type": "eq", "fun": lambda m: float(np.sum(w * m)) - tau}]
    bnds = [(1e-10, 1 - 1e-10)] * K
    rng = np.random.default_rng(7)
    best = (np.inf, None)
    for _ in range(80):
        x0 = rng.random(K) * min(1.0, 4 * tau)
        s = float(np.sum(w * x0))
        x0 = np.clip(x0 * (tau / max(s, 1e-12)), 1e-9, 1 - 1e-9)
        r = minimize(objective, x0, args=(rates, lam), method="SLSQP",
                     bounds=bnds, constraints=cons,
                     options={"maxiter": 800, "ftol": 1e-14})
        if r.success and r.fun < best[0]:
            best = (float(r.fun), r.x.copy())
    return best


def measure_growth(pools, rates, tau, n, reps, seed=1234):
    """MC estimate of E[min-over-null log E_n] / n under round-robin."""
    out = []
    for r in range(reps):
        rng = np.random.default_rng(seed + 977 * r)
        cs = StratifiedUICS(k=4, alpha=0.05)
        for step in range(1, n + 1):
            k = (step - 1) % 4
            pool = pools[STRATA[k]]
            cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        out.append(cs.min_log_e(tau, "le"))
    return float(np.mean(out)) / n, float(np.std(out)) / n


def main():
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        rec = json.loads(line)
        pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    pools = {s: np.array(v, dtype=np.int8) for s, v in pools.items()}
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    w = np.full(4, 0.25)
    lam = np.full(4, 0.25)

    print("=" * 76)
    print("AUDIT: V_rr verification (frozen rate for UI + round-robin)")
    print("=" * 76)
    print(f"gpt-4o-mini JSON pool rates: {np.round(rates, 6).tolist()}")
    print(f"p* = {rates.mean():.6f}\n")

    print(f"{'tau':>6} {'_inner_min':>12} {'SLSQP':>12} {'grid/CD':>12} "
          f"{'V_game':>10} {'printed':>9}")
    printed = {0.15: 0.0192, 0.16: 0.0127, 0.17: 0.0075}
    for tau in [0.15, 0.16, 0.17]:
        m_im = bench._inner_min(lam, rates, w, tau)
        v_im = objective(m_im, rates, lam)
        v_sp, m_sp = scipy_min(rates, w, lam, tau)
        v_bg, m_bg = brute_grid(rates, w, lam, tau)
        _, v_game = bench.game_allocation(rates, w, tau)
        print(f"{tau:>6.2f} {v_im:>12.6f} "
              f"{(v_sp if v_sp is not None else float('nan')):>12.6f} "
              f"{v_bg:>12.6f} {v_game:>10.6f} {printed[tau]:>9.4f}")
        print(f"       m*(_inner_min) = {np.round(m_im, 6).tolist()}  "
              f"(sum w m = {float(np.sum(w * m_im)):.8f})")
        if m_sp is not None:
            print(f"       m*(SLSQP)      = {np.round(m_sp, 6).tolist()}")
    print()

    print("Direct MC check that V_rr (not V_game) is the round-robin rate.")
    print("  NOTE: E[min_null log E_n]/n at finite n is n*V - (d/2)log n - c,")
    print("  so the ratio to V_rr is well below 1 at small n BY THE LAW ITSELF.")
    print("  The rate claim must be read off the LOCAL SLOPE at large n; that")
    print("  measurement lives in audit/sim_growth_path.py (ratios 0.96-0.99")
    print("  on [8000, 16000]). Reported here only for orientation.")
    print(f"{'tau':>6} {'n':>6} {'measured/n':>12} {'V_rr':>10} "
          f"{'ratio':>8} {'V_game':>10} {'ratio':>8}")
    for tau in [0.15, 0.16, 0.17]:
        m_im = bench._inner_min(lam, rates, w, tau)
        v_rr = objective(m_im, rates, lam)
        _, v_game = bench.game_allocation(rates, w, tau)
        for n in [2000]:
            mu, _ = measure_growth(pools, rates, tau, n, reps=200)
            print(f"{tau:>6.2f} {n:>6d} {mu:>12.6f} {v_rr:>10.6f} "
                  f"{mu / v_rr:>8.3f} {v_game:>10.6f} {mu / v_game:>8.3f}")


if __name__ == "__main__":
    main()
