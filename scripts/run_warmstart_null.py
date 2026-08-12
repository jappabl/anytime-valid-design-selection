#!/usr/bin/env python3
"""Adversarial null-coverage Monte Carlo for the warm-start UI e-processes.

WHY THIS EXISTS
---------------
The warm-start artifacts (results_warmstart.txt, results_warmstart_stress.txt,
results_warmstart_joint.txt) report "wrong 0" at tau in {0.15, 0.16, 0.17}
while the pooled truth is p* = 0.2020. Every replication in those artifacts is
therefore drawn from the ALTERNATIVE for the UNSAFE direction: the type-I error
of `rejects_le` -- the error the entire certification claim rests on -- is
never exercised. "Zero wrong certifications" measures the SAFE direction only,
at a truth 0.032-0.052 above the threshold. This script exercises the real
null.

CONSTRUCTION
------------
  * synthetic pools whose pooled rate is EXACTLY tau (the least-favourable
    null point: at p* = tau BOTH H0: p* <= tau and H0: p* >= tau are true, so
    a rejection in either direction is a type-I error);
  * the prior handed to TransferPriorUICS / TransferPriorJointUICS is
    ADVERSARIALLY WRONG in the direction that inflates the numerator toward
    the rejection the arm must not make;
  * the certification loop is the one in scripts/run_warmstart.py (round-robin
    k=(n-1)%4, checkpoints at n>=20 and n%4==0), with the estimator classes
    IMPORTED from the scripts under audit rather than reimplemented.

TWO NESTED TESTS (so a failure localises)
-----------------------------------------
  T1  Ville at the truth:   P( sup_n E(p_true) >= 1/alpha ) <= alpha.
      E(p_true) = exp(log_pred - loglik(p_true)) uses ONLY the numerator
      accumulator and the counts, so T1 isolates update()/contamination
      bookkeeping from the null-boundary optimisation.
  T2  The shipped procedure: P( rejects_le fires at any checkpoint ) <= alpha,
      and likewise for rejects_ge. T2 = T1 + the Lagrange-bisection min over
      the null boundary.
  T1 pass + T2 fail  =>  the boundary minimisation is unsound.
  T1 fail            =>  the numerator / mixture bookkeeping is unsound.
  A third diagnostic reports E[E_n(p_true)] at fixed n, which must be 1 for a
  true test martingale.

EXACT FAST PATH
---------------
Because sum_k w_k p_true_k == tau, p_true is feasible for BOTH null sets, so
        min_log_e(tau, side)  <=  log_e_at(p_true)     for side in {le, ge}.
Screening on log_e_at(p_true) is an EXACT necessary condition for a rejection,
not an approximation, and it is also exactly the T1 statistic. `--verify-screen`
re-runs replications with the screen disabled and asserts identical decisions.

Usage:
    python3 audit/sim_warmstart_null.py                        # 2000 reps
    python3 audit/sim_warmstart_null.py --reps 200 --verify-screen
Deterministic given --seed (each replication gets its own spawned seed, so the
result does not depend on the number of worker processes). Offline; writes
nothing.
"""

import argparse
import importlib.util
import math
import sys
import multiprocessing as _mp
from functools import partial
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402

STRATA = ["simple", "medium", "complex", "extreme"]
POOL_N = 250          # matches data/llm_outcomes_diverse_json.jsonl
ALPHA = 0.05
N_MAX = 4000
CLIP = 1e-12
E_SNAPSHOTS = (100, 400, 1600, 4000)


def _load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ws = _load_script("_audit_ws", REPO / "scripts" / "run_warmstart.py")
_wj = _load_script("_audit_wj", REPO / "scripts" / "run_warmstart_joint.py")
TransferPriorUICS = _ws.TransferPriorUICS
TransferPriorJointUICS = _wj.TransferPriorJointUICS


def make_cs(arm, prior, alpha=ALPHA):
    if arm == "cold UI mixture":
        return StratifiedUICS(k=4, alpha=alpha)
    if arm == "per-stratum warm":
        return TransferPriorUICS(np.asarray(prior, float), alpha=alpha)
    if arm == "joint warm":
        return TransferPriorJointUICS(np.asarray(prior, float), alpha=alpha)
    raise ValueError(arm)


def exact_pools(rates):
    """Pools of POOL_N draws with EXACTLY the requested per-stratum rates."""
    pools = {}
    for s, p in zip(STRATA, rates):
        n_fail = round(p * POOL_N)
        if abs(n_fail / POOL_N - p) > 1e-12:
            raise ValueError(f"rate {p} not representable with n={POOL_N}")
        v = np.zeros(POOL_N, dtype=np.int8)
        v[:n_fail] = 1
        pools[s] = v
    return pools


def run_rep(seed, arm, prior, pools, tau, p_true, screen=True):
    """One replication of the certification loop of scripts/run_warmstart.py.

    Returns (decision, n, sup_log_e_at_truth, {n: log_e_at_truth}).
    """
    rng = np.random.default_rng(seed)
    cs = make_cs(arm, prior)
    thresh = cs.log_thresh
    mc = np.clip(np.asarray(p_true, float), CLIP, 1 - CLIP)
    lp, l1p = np.log(mc), np.log(1 - mc)
    sup_e = -np.inf
    snaps = {}
    decision, stop_n = "ABSTAIN", N_MAX
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        pool = pools[STRATA[k]]
        cs.update(k if cs.k == 4 else 0,
                  bool(pool[int(rng.integers(0, len(pool)))]))
        e_true = cs.log_pred - float(np.dot(cs.f, lp) + np.dot(cs.s, l1p))
        if e_true > sup_e:
            sup_e = e_true
        if n in E_SNAPSHOTS:
            snaps[n] = e_true
        if decision == "ABSTAIN" and n >= 20 and n % 4 == 0:
            if screen and e_true < thresh - 1e-9:
                continue
            if cs.rejects_le(tau):
                decision, stop_n = "UNSAFE", n
            elif cs.rejects_ge(tau):
                decision, stop_n = "SAFE", n
    return decision, stop_n, sup_e, snaps


def _worker(seed, arm, prior, pools, tau, p_true, screen):
    return run_rep(seed, arm, prior, pools, tau, p_true, screen)


def wilson_upper(x, n, z=1.959963985):
    if n == 0:
        return float("nan")
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c + h) / d


def excess_p(x, n, alpha=ALPHA):
    """One-sided exact binomial p-value for H0: rate <= alpha."""
    return binomtest(x, n, alpha, alternative="greater").pvalue


CONFIGS = [
    # name, tau, true per-stratum rates (mean == tau), adversarial prior
    ("A real-shape / prior says UNSAFE", 0.16,
     [0.004, 0.000, 0.068, 0.568], [0.30, 0.40, 0.60, 0.95]),
    ("B real-shape / prior right on 3, extreme inflated", 0.16,
     [0.004, 0.000, 0.068, 0.568], [0.004, 0.000, 0.068, 0.980]),
    ("C real-shape / prior right on 3, extreme maximal", 0.16,
     [0.004, 0.000, 0.068, 0.568], [0.004, 0.000, 0.068, 0.999]),
    ("D homogeneous / prior says UNSAFE", 0.16,
     [0.160, 0.160, 0.160, 0.160], [0.70, 0.70, 0.70, 0.70]),
    ("E skewed / prior says UNSAFE", 0.16,
     [0.012, 0.024, 0.152, 0.452], [0.90, 0.90, 0.90, 0.90]),
    ("F real-shape / prior says SAFE", 0.16,
     [0.004, 0.000, 0.068, 0.568], [0.001, 0.001, 0.001, 0.001]),
    ("G homogeneous / prior says SAFE", 0.16,
     [0.160, 0.160, 0.160, 0.160], [0.002, 0.002, 0.002, 0.002]),
    ("H real-shape tau=0.20 / prior says UNSAFE", 0.20,
     [0.004, 0.000, 0.068, 0.728], [0.40, 0.50, 0.70, 0.98]),
]
ARMS = ["cold UI mixture", "per-stratum warm", "joint warm"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260811)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--verify-screen", action="store_true")
    ap.add_argument("--only", type=str, default=None,
                    help="run only configs whose name starts with this letter")
    args = ap.parse_args()

    print("=" * 96)
    print("ADVERSARIAL NULL-COVERAGE MC FOR WARM-START UI E-PROCESSES  "
          "(audit/sim_warmstart_null.py)")
    print("=" * 96)
    print(f"alpha = {ALPHA}, reps = {args.reps}, n_max = {N_MAX}, "
          f"pool = {POOL_N}/stratum, seed = {args.seed}")
    print("p* sits EXACTLY at tau: both one-sided nulls are true, so a "
          "rejection either way is a type-I error.")
    print("T1 = P(sup_n E(p_true) >= 1/alpha)  [numerator only];  "
          "T2 = P(shipped rejects_* fires)  [+ boundary min].")
    print("'!!' marks a one-sided exact-binomial p < 0.05 against H0: "
          "rate <= alpha.\n")

    ss = np.random.SeedSequence(args.seed)
    worst = {"T1": 0.0, "T2u": 0.0, "T2s": 0.0}
    configs = [c for c in CONFIGS
               if args.only is None or c[0].startswith(args.only)]
    # One persistent fork-based pool: re-spawning per arm dominated runtime.
    ctx = _mp.get_context("fork")
    pool_ = ctx.Pool(args.procs)

    for name, tau, rates, prior in configs:
        pools = exact_pools(rates)
        p_true = np.asarray(rates, float)
        assert abs(p_true.mean() - tau) < 1e-12, (p_true.mean(), tau)
        print(f"--- {name}")
        print(f"    tau={tau}  p_true={rates}  prior={prior}")
        for arm in ARMS:
            seeds = ss.spawn(args.reps)
            fn = partial(_worker, arm=arm, prior=prior, pools=pools, tau=tau,
                         p_true=p_true, screen=True)
            out = pool_.map(fn, seeds, chunksize=8)
            nu = sum(d == "UNSAFE" for d, _, _, _ in out)
            nsafe = sum(d == "SAFE" for d, _, _, _ in out)
            t1 = sum(1 for _, _, se, _ in out if se >= math.log(1 / ALPHA))
            R = args.reps
            worst["T1"] = max(worst["T1"], t1 / R)
            worst["T2u"] = max(worst["T2u"], nu / R)
            worst["T2s"] = max(worst["T2s"], nsafe / R)
            f = lambda x: "!!" if excess_p(x, R) < 0.05 else "OK"  # noqa: E731
            means = {n: np.mean([math.exp(min(s[n], 700)) for _, _, _, s in out])
                     for n in E_SNAPSHOTS}
            print(f"      {arm:17s} T1 sup-E {t1:4d}/{R}={t1/R:.4f} {f(t1)} | "
                  f"T2 false-UNSAFE {nu:4d}/{R}={nu/R:.4f} {f(nu)} | "
                  f"T2 false-SAFE {nsafe:4d}/{R}={nsafe/R:.4f} {f(nsafe)}")
            print("      " + " " * 17 + "  MC mean of E_n(p_true) at n="
                  + ", ".join(f"{n}:{means[n]:.3f}" for n in E_SNAPSHOTS)
                  + "   (true value 1.000; heavy-tailed, so <1 is "
                    "undersampling, >>1 would be the bug)")
            sys.stdout.flush()
        print()
    pool_.close()
    pool_.join()

    print(f"WORST over all configs/arms:  T1 = {worst['T1']:.4f},  "
          f"T2 false-UNSAFE = {worst['T2u']:.4f},  "
          f"T2 false-SAFE = {worst['T2s']:.4f}   (alpha = {ALPHA})")

    if args.verify_screen:
        print("\n--- screen-equivalence check (screen ON vs OFF, 40 reps/arm)")
        name, tau, rates, prior = configs[0]
        pools = exact_pools(rates)
        p_true = np.asarray(rates, float)
        bad = 0
        for arm in ARMS:
            seeds = np.random.SeedSequence(999).spawn(40)
            a = [run_rep(s, arm, prior, pools, tau, p_true, True)[:2]
                 for s in seeds]
            b = [run_rep(s, arm, prior, pools, tau, p_true, False)[:2]
                 for s in seeds]
            bad += a != b
            print(f"      {arm:17s} identical: {a == b}")
        print(f"    screen equivalence: {'PASS' if bad == 0 else 'FAIL'}")


if __name__ == "__main__":
    import hashlib
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_warmstart_null.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_warmstart_null.txt'}")
