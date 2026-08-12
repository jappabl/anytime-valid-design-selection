#!/usr/bin/env python3
"""Brute-force verification of the TransferPrior* mixture bookkeeping.

Checks, on short sequences, that the incremental posterior-weighted
predictive recursion in TransferPriorUICS.update / TransferPriorJointUICS.update
telescopes to the closed-form two-component Beta-Bernoulli marginal:

  per-stratum   M = prod_k [ (1-e) B(a_k,b_k;f_k,s_k) + e B(1,1;f_k,s_k) ]
  joint         M = (1-e) prod_k B(a_k,b_k;f_k,s_k) + e prod_k B(1,1;f_k,s_k)

with B(a,b;f,s) = Beta(a+f, b+s)/Beta(a,b) the Beta-Bernoulli marginal.

Also checks:
  * the numerator is a PROBABILITY over sequences (predictives sum to 1 at
    every step), which is exactly the martingale property E[M/L(.;p)] = 1;
  * the pathwise eps-contamination premium
        per-stratum:  log E >= log E_cold - K log(1/eps)
        joint:        log E >= log E_cold -     log(1/eps)
    at every prefix and after the min over the null boundary;
  * StratifiedUICS.min_log_e does not UNDER-minimise. An inf that comes out
    too high is anti-conservative (it rejects when the true inf would not),
    so the Lagrange-bisection/KKT-quadratic result is compared against a
    brute-force constrained minimisation on the same null set.

Deterministic. Prints PASS/FAIL lines only.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
from scipy.special import betaln

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ws = _load("_ws", REPO / "scripts" / "run_warmstart.py")
_wj = _load("_wj", REPO / "scripts" / "run_warmstart_joint.py")
TransferPriorUICS = _ws.TransferPriorUICS
TransferPriorJointUICS = _wj.TransferPriorJointUICS


def beta_bernoulli_logmarginal(a, b, f, s):
    """log P(f failures, s successes | Beta(a,b)) for an exchangeable order."""
    return betaln(a + f, b + s) - betaln(a, b)


def closed_form(prior_rates, f, s, kappa, eps, joint):
    pr = np.asarray(prior_rates, dtype=float)
    a1, b1 = 1.0 + kappa * pr, 1.0 + kappa * (1 - pr)
    a2 = b2 = np.ones_like(pr)
    lm1 = np.array([beta_bernoulli_logmarginal(a1[k], b1[k], f[k], s[k])
                    for k in range(len(pr))])
    lm2 = np.array([beta_bernoulli_logmarginal(a2[k], b2[k], f[k], s[k])
                    for k in range(len(pr))])
    lw = np.log([1 - eps, eps])
    if joint:
        return float(np.logaddexp(lw[0] + lm1.sum(), lw[1] + lm2.sum()))
    return float(sum(np.logaddexp(lw[0] + lm1[k], lw[1] + lm2[k])
                     for k in range(len(pr))))


def check_normalisation(cls, prior_rates, kappa, eps, K, rng, n=40):
    """The numerator M must be a PROBABILITY over sequences.

    Sufficient and necessary: at every step the mixture predictive must
    satisfy  mix_pred(failure) + mix_pred(success) = 1.  If it does, M
    telescopes to a probability mass function and E[M/L(.;p)] = 1 exactly
    under p, which is the whole martingale property.  This is a far sharper
    test than a Monte-Carlo mean of a heavy-tailed martingale.
    """
    import copy
    cs = cls(prior_rates, k=K, kappa=kappa, eps=eps)
    worst = 0.0
    for _ in range(n):
        kk = int(rng.integers(0, K))
        base = cs.log_pred
        a, b = copy.deepcopy(cs), copy.deepcopy(cs)
        a.update(kk, True)
        b.update(kk, False)
        total = np.exp(a.log_pred - base) + np.exp(b.log_pred - base)
        worst = max(worst, abs(total - 1.0))
        cs.update(kk, bool(rng.integers(0, 2)))
    return worst


def brute_force_min_log_e(cs, tau, side, n_restart=25, rng=None):
    """Independent constrained minimisation of log_e_at over the null set.

    Uses SLSQP from random feasible starts -- a completely different algorithm
    from the Lagrange bisection + KKT quadratic under test. The code's own
    answer is never used as a starting point, so this is an independent
    witness for the true infimum. Returns the lowest value found.
    """
    from scipy.optimize import minimize
    K, w = cs.k, cs.w
    sgn = 1.0 if side == "le" else -1.0          # sgn*(tau - w.m) >= 0
    cons = [{"type": "ineq",
             "fun": lambda m: sgn * (tau - float(np.sum(w * m)))}]
    bnds = [(1e-9, 1 - 1e-9)] * K
    best = np.inf
    starts = [np.full(K, tau)]
    for _ in range(n_restart):
        m = rng.uniform(1e-4, 1 - 1e-4, K)
        s = float(np.sum(w * m))
        if sgn * (tau - s) < 0:                  # nudge into the null set
            m = np.clip(m * (tau / max(s, 1e-9)), 1e-9, 1 - 1e-9) \
                if side == "le" else \
                np.clip(1 - (1 - m) * ((1 - tau) / max(1 - s, 1e-9)),
                        1e-9, 1 - 1e-9)
        starts.append(m)
    for m0 in starts:
        r = minimize(lambda m: cs.log_e_at(m), m0, method="SLSQP",
                     bounds=bnds, constraints=cons,
                     options={"maxiter": 400, "ftol": 1e-14})
        if r.x is not None:
            m = np.clip(r.x, 1e-9, 1 - 1e-9)
            if sgn * (tau - float(np.sum(w * m))) >= -1e-9:
                best = min(best, cs.log_e_at(m))
    return best


def main():
    rng = np.random.default_rng(20260811)
    kappa, eps, K = 200.0, 0.10, 4
    fails = 0

    # --- min_log_e must not come out ABOVE the true constrained infimum ----
    brng = np.random.default_rng(4242)
    for trial in range(12):
        pr = brng.uniform(0.01, 0.95, size=K)
        cls = (TransferPriorUICS, TransferPriorJointUICS, None)[trial % 3]
        cs = (StratifiedUICS(k=K) if cls is None
              else cls(pr, k=K, kappa=kappa, eps=eps))
        for _ in range(int(brng.integers(40, 200))):
            cs.update(int(brng.integers(0, K)), bool(brng.integers(0, 2)))
        for tau in (0.10, 0.16, 0.30, 0.55):
            for side in ("le", "ge"):
                code = cs.min_log_e(tau, side)
                ref = brute_force_min_log_e(cs, tau, side, rng=brng)
                if code > ref + 1e-6:
                    print(f"FAIL boundary-min trial={trial} "
                          f"{type(cs).__name__} tau={tau} side={side}: "
                          f"code={code:.9f} > brute-force={ref:.9f} "
                          f"(anti-conservative by {code-ref:.2e})")
                    fails += 1

    # --- numerator is a probability measure over sequences ---------------
    for cls in (TransferPriorUICS, TransferPriorJointUICS, None):
        for _ in range(30):
            pr = rng.uniform(0.01, 0.95, size=K)
            if cls is None:
                w = check_normalisation(
                    lambda p, k, kappa, eps: StratifiedUICS(k=k),
                    pr, kappa, eps, K, rng)
                nm = "StratifiedUICS(cold)"
            else:
                w = check_normalisation(cls, pr, kappa, eps, K, rng)
                nm = cls.__name__
            if w > 1e-12:
                print(f"FAIL normalisation {nm}: |sum pred - 1| = {w:.3e}")
                fails += 1
                break

    for trial in range(200):
        prior_rates = rng.uniform(0.01, 0.95, size=K)
        n = 20
        strata = rng.integers(0, K, size=n)
        outcomes = rng.integers(0, 2, size=n).astype(bool)

        for joint, cls in ((False, TransferPriorUICS), (True, TransferPriorJointUICS)):
            cs = cls(prior_rates, k=K, kappa=kappa, eps=eps)
            cold = StratifiedUICS(k=K)
            for i, (kk, o) in enumerate(zip(strata, outcomes)):
                cs.update(int(kk), bool(o))
                cold.update(int(kk), bool(o))
                ref = closed_form(prior_rates, cs.f, cs.s, kappa, eps, joint)
                if abs(cs.log_pred - ref) > 1e-9:
                    print(f"FAIL recursion joint={joint} trial={trial} "
                          f"step={i}: acc={cs.log_pred:.12f} ref={ref:.12f}")
                    fails += 1
                    break
                # pathwise eps-contamination premium vs the cold Beta(1,1) mixture
                cap = (1 if joint else K) * np.log(1 / eps)
                if cs.log_pred < cold.log_pred - cap - 1e-9:
                    print(f"FAIL premium joint={joint} trial={trial} step={i}: "
                          f"{cold.log_pred - cs.log_pred:.4f} > cap {cap:.4f}")
                    fails += 1
                    break
                for tau in (0.15, 0.25, 0.5):
                    for side in ("le", "ge"):
                        d = cold.min_log_e(tau, side) - cs.min_log_e(tau, side)
                        if d > cap + 1e-7:
                            print(f"FAIL min-premium joint={joint} tau={tau} "
                                  f"side={side} step={i}: {d:.4f} > {cap:.4f}")
                            fails += 1

    # Order-invariance of the accumulated marginal (exchangeability sanity).
    for trial in range(50):
        prior_rates = rng.uniform(0.01, 0.95, size=K)
        n = 24
        strata = rng.integers(0, K, size=n)
        outcomes = rng.integers(0, 2, size=n).astype(bool)
        perm = rng.permutation(n)
        for cls in (TransferPriorUICS, TransferPriorJointUICS):
            a = cls(prior_rates, k=K, kappa=kappa, eps=eps)
            b = cls(prior_rates, k=K, kappa=kappa, eps=eps)
            for kk, o in zip(strata, outcomes):
                a.update(int(kk), bool(o))
            for j in perm:
                b.update(int(strata[j]), bool(outcomes[j]))
            if abs(a.log_pred - b.log_pred) > 1e-9:
                print(f"FAIL exchangeability {cls.__name__} trial={trial}: "
                      f"{a.log_pred} vs {b.log_pred}")
                fails += 1

    print(f"mixture-recursion / premium / exchangeability checks: "
          f"{'PASS' if fails == 0 else str(fails) + ' FAILURES'}")


if __name__ == "__main__":
    main()
