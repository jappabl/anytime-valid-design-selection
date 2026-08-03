#!/usr/bin/env python3
"""Advanced offline experiments on cached real-LLM outcome pools.

E1  Peeking miscoverage: probability that a nominal-95% interval EVER
    excludes the true p during n = 1..200 of sequential evaluation.
    Fixed-n intervals (Wald, Wilson) vs the anytime-valid betting CS,
    on real GPT-4o-mini outcome pools. Motivates the entire method.

E2  Validity stress test: the betting CS assumes iid Bernoulli(p*) draws,
    but stratified round-robin sampling produces independent NON-identical
    draws whose block means equal p*. By convexity, mean_k p_k(1-p_k) <=
    p*(1-p*), so stratified streams are less variable than iid mixture
    streams and the CS should remain (conservatively) valid. This
    experiment measures uniform coverage under round-robin across
    heterogeneity configurations, including the worst case (all failure
    mass in one stratum).

E3  Allocation strategies for the mixture estimand via PER-STRATUM betting
    CSs combined with weighted Bonferroni (alpha/K each):
        CI(p*) = [sum_k w_k L_k, sum_k w_k U_k]
    This is anytime-valid for ANY data-dependent allocation across strata,
    because each per-stratum CS is time-uniform for p_k on its own stream.
    Compares: single-stream mixture CS (round-robin) vs stratified-CS with
    uniform allocation vs GREEDY allocation (next sample to the stratum
    with the largest weighted width contribution w_k * (U_k - L_k)).
    Metrics: time to reach precision targets, time-to-certify UNSAFE.

E4  Variance theory check: predicted vs observed stratified/naive MAE
    ratio at fixed n (no stopping), on the real pools.

All deterministic (BASE_SEED=42), zero API cost.
Writes results_advanced.txt with a checksum.
"""

import hashlib
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.fast_bounds import (
    betting_bounds,
    wald_interval,
    wilson_interval,
)

DATA = REPO / "data" / "llm_outcomes_diverse_json.jsonl"
BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]


def load_pools() -> dict:
    pools = {s: [] for s in STRATA}
    with open(DATA) as fh:
        for line in fh:
            rec = json.loads(line)
            pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def build_table(bound_fn, n_max: int, alpha: float = ALPHA) -> dict:
    return {(n, f): bound_fn(f, n - f, alpha)
            for n in range(1, n_max + 1) for f in range(0, n + 1)}


class LazyBounds:
    """Memoized bounds keyed by (n, f) — only visited states are computed."""

    def __init__(self, bound_fn, alpha):
        self.bound_fn = bound_fn
        self.alpha = alpha
        self.cache = {}

    def __getitem__(self, key):
        if key not in self.cache:
            n, f = key
            self.cache[key] = self.bound_fn(f, n - f, self.alpha)
        return self.cache[key]


# ---------------------------------------------------------------------------
# E1: Peeking miscoverage
# ---------------------------------------------------------------------------

def e1_peeking(pools, p_star):
    print("E1: PEEKING MISCOVERAGE (real GPT-4o-mini outcomes, naive sampling)")
    print("-" * 76)
    print("Metric: P(true p* outside the interval at ANY n in 1..200)")
    print("All intervals at nominal 95%. 2000 replications.\n")

    n_max, n_reps = 200, 2000
    tables = {
        "Wald (fixed-n)": build_table(wald_interval, n_max),
        "Wilson (fixed-n)": build_table(wilson_interval, n_max),
        "Betting CS (anytime)": build_table(betting_bounds, n_max),
    }

    all_outcomes = np.concatenate([pools[s] for s in STRATA])
    results = {name: 0 for name in tables}
    rng = np.random.default_rng(BASE_SEED)
    for rep in range(n_reps):
        draws = all_outcomes[rng.integers(0, len(all_outcomes), n_max)]
        fs = np.cumsum(draws)
        missed = {name: False for name in tables}
        for n in range(1, n_max + 1):
            f = int(fs[n - 1])
            for name, table in tables.items():
                if not missed[name]:
                    lo, hi = table[(n, f)]
                    if not (lo <= p_star <= hi):
                        missed[name] = True
        for name in tables:
            results[name] += missed[name]

    for name in tables:
        rate = results[name] / n_reps
        print(f"  {name:22s}: miscoverage {results[name]:4d}/{n_reps} = {rate:.3f} "
              f"{'(INVALID under peeking)' if rate > ALPHA + 0.02 else '(valid)'}")
    print()


# ---------------------------------------------------------------------------
# E2: Validity under stratified (non-iid) streams
# ---------------------------------------------------------------------------

def e2_validity_stress(pools):
    print("E2: PER-SAMPLE MIXTURE CS UNDER STRATIFIED (NON-IID) STREAMS")
    print("-" * 76)
    print("""Round-robin draws are independent but NOT identically distributed, so
the iid-Bernoulli(p*) betting CS has NO general guarantee on the raw
stream. Uniform coverage is computed EXACTLY by dynamic programming
(no Monte Carlo error) for two peeking disciplines:
  every-n     : bounds checked at every sample (NOT what the pipeline does)
  block-gated : bounds checked only at complete blocks (n %% K == 0),
                matching the pipeline's stopping rules.
Adversarial configurations (failure mass split across a SUBSET of early
strata) BREAK every-n peeking; block gating repairs every case found.
A provably-valid route that needs no such caveat is the WSR CS on block
means (results_block_reduction.txt).\n""")

    from scipy.special import betaln as _betaln

    def exact_coverage(rates, n_max=200, block_only=False):
        thresh = np.log(1 / ALPHA)
        K = len(rates)
        p_star = float(np.mean(rates))
        prob = np.array([1.0])
        for n in range(1, n_max + 1):
            p = rates[(n - 1) % K]
            nx = np.zeros(n + 1)
            nx[:n] += prob * (1 - p)
            nx[1:] += prob * p
            if (not block_only) or n % K == 0:
                f = np.arange(n + 1)
                s = n - f
                log_e = (_betaln(1.0 + f, 1.0 + s)
                         - (f * np.log(p_star) + s * np.log(1 - p_star)))
                nx = nx * (log_e < thresh)
            prob = nx
        return float(prob.sum())

    real_rates = [float(pools[s].mean()) for s in STRATA]
    configs = {
        "iid (control)": [0.202] * 4,
        "real pools": real_rates,
        "all mass in one stratum (0,0,0,0.808)": [0.0, 0.0, 0.0, 0.808],
        "ADVERSARIAL (0.258,0.2577,0,0)": [0.258, 0.2577, 0.0, 0.0],
        "ADVERSARIAL K=8 (0.2,0,...,0)": [0.2] + [0.0] * 7,
    }

    print(f"  {'config':40s} {'p*':>6} {'every-n':>9} {'block-gated':>12}")
    for name, rates in configs.items():
        p_star = float(np.mean(rates))
        cov_every = exact_coverage(rates)
        cov_block = exact_coverage(rates, block_only=True)
        flag = "  <- FAILS" if cov_every < 1 - ALPHA else ""
        print(f"  {name:40s} {p_star:>6.3f} {cov_every:>9.4f} "
              f"{cov_block:>12.4f}{flag}")
    print("""
  Reading: the per-sample mixture CS on a raw stratified stream is NOT
  generally valid -- mid-block peeking can push uniform coverage as low
  as 0.75 in adversarial configurations. Complete-block gating (which
  the pipeline uses) restored >= 0.995 coverage in every configuration
  tested, and mid-block peeking is also the mechanism behind the
  partial-block bias artifact: the unified rule is NEVER PEEK MID-BLOCK.
  For a guarantee rather than an empirical observation, use the WSR CS
  on block means, which is exactly valid because blocks are iid.\n""")


# ---------------------------------------------------------------------------
# E3: Allocation strategies with per-stratum CSs
# ---------------------------------------------------------------------------

def _mixture_ci(stratum_cs, table):
    lo = hi = 0.0
    for f, n in stratum_cs:
        l, u = table[(n, f)] if n > 0 else (0.0, 1.0)
        lo += 0.25 * l
        hi += 0.25 * u
    return lo, hi


def e3_allocation(pools, p_star):
    print("E3: ALLOCATION STRATEGIES (per-stratum betting CSs, weighted Bonferroni)")
    print("-" * 76)
    print("CI(p*) = [sum w_k L_k, sum w_k U_k], each stratum CS at alpha/4.")
    print("Valid for ANY data-dependent allocation. 500 reps, n_max=2000.\n")

    n_max = 2000
    # Per-stratum CSs run at alpha/4 (Bonferroni across 4 strata)
    table4 = LazyBounds(betting_bounds, ALPHA / 4)
    # Single-stream mixture CS at full alpha (round-robin block stopping)
    table1 = LazyBounds(betting_bounds, ALPHA)

    def run_single_stream(rng, width_target=None, tau=None):
        f = 0
        for n in range(1, n_max + 1):
            pool = pools[STRATA[(n - 1) % 4]]
            f += int(pool[int(rng.integers(0, len(pool)))])
            if n >= 20 and n % 4 == 0:
                lo, hi = table1[(n, f)]
                if width_target and hi - lo <= width_target:
                    return n
                if tau and lo > tau:
                    return n
        return None

    def run_stratified_cs(rng, greedy, width_target=None, tau=None):
        state = {s: [0, 0] for s in STRATA}  # f, n per stratum
        for step in range(1, n_max + 1):
            if greedy and step > 8:
                # widest weighted contribution gets the next sample
                widths = {}
                for s in STRATA:
                    f, n = state[s]
                    l, u = table4[(n, f)] if n > 0 else (0.0, 1.0)
                    widths[s] = 0.25 * (u - l)
                stratum = max(STRATA, key=lambda s: widths[s])
            else:
                stratum = STRATA[(step - 1) % 4]
            pool = pools[stratum]
            state[stratum][0] += int(pool[int(rng.integers(0, len(pool)))])
            state[stratum][1] += 1
            if step >= 20 and step % 4 == 0:
                lo, hi = _mixture_ci(
                    [(state[s][0], state[s][1]) for s in STRATA], table4)
                if width_target and hi - lo <= width_target:
                    return step
                if tau and lo > tau:
                    return step
        return None

    strategies = {
        "single-stream (round-robin)": lambda rng, **kw: run_single_stream(rng, **kw),
        "stratified-CS uniform": lambda rng, **kw: run_stratified_cs(rng, False, **kw),
        "stratified-CS greedy": lambda rng, **kw: run_stratified_cs(rng, True, **kw),
    }

    n_reps = 500
    print("Time to reach precision (CI width <= target), median [IQR]:")
    for target in [0.30, 0.20, 0.15]:
        print(f"  width <= {target}:")
        for name, fn in strategies.items():
            rng = np.random.default_rng(BASE_SEED + 2)
            times = [fn(rng, width_target=target) for _ in range(n_reps)]
            done = [t for t in times if t is not None]
            if len(done) < n_reps:
                print(f"    {name:28s}: reached in {len(done)}/{n_reps} runs")
            else:
                q1, q2, q3 = np.percentile(done, [25, 50, 75])
                print(f"    {name:28s}: {q2:.0f} [{q1:.0f}, {q3:.0f}]")
        print()

    print(f"Time to certify UNSAFE at tau=0.15 (true p*={p_star:.3f}), median [IQR]:")
    for name, fn in strategies.items():
        rng = np.random.default_rng(BASE_SEED + 3)
        times = [fn(rng, tau=0.15) for _ in range(n_reps)]
        done = [t for t in times if t is not None]
        if len(done) < n_reps:
            print(f"    {name:28s}: certified in {len(done)}/{n_reps} runs")
        else:
            q1, q2, q3 = np.percentile(done, [25, 50, 75])
            print(f"    {name:28s}: {q2:.0f} [{q1:.0f}, {q3:.0f}]")
    print()


# ---------------------------------------------------------------------------
# E4: Variance theory check
# ---------------------------------------------------------------------------

def e4_variance_theory(pools, p_star):
    print("E4: VARIANCE THEORY CHECK (fixed n, no stopping)")
    print("-" * 76)
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    var_naive = p_star * (1 - p_star)
    var_strat = float(np.mean(rates * (1 - rates)))
    pred_ratio = np.sqrt(var_strat / var_naive)
    print(f"  Per-stratum p_k: {[f'{r:.3f}' for r in rates]}")
    print(f"  Naive per-sample variance p*(1-p*):        {var_naive:.4f}")
    print(f"  Stratified per-sample variance mean p_kq_k: {var_strat:.4f}")
    print(f"  Predicted MAE ratio (stratified/naive):     {pred_ratio:.3f}")

    n, n_reps = 100, 4000
    rng = np.random.default_rng(BASE_SEED + 4)
    all_outcomes = np.concatenate([pools[s] for s in STRATA])
    naive_err, strat_err = [], []
    for rep in range(n_reps):
        draws = all_outcomes[rng.integers(0, len(all_outcomes), n)]
        naive_err.append(abs(draws.mean() - p_star))
        f = 0
        for i in range(n):
            pool = pools[STRATA[i % 4]]
            f += int(pool[int(rng.integers(0, len(pool)))])
        strat_err.append(abs(f / n - p_star))
    obs_ratio = np.mean(strat_err) / np.mean(naive_err)
    print(f"  Observed MAE ratio at n={n} ({n_reps} reps):     {obs_ratio:.3f}")
    print(f"  Agreement: {'GOOD' if abs(obs_ratio - pred_ratio) < 0.08 else 'CHECK'}")
    print()


def main():
    pools = load_pools()
    rates = {s: float(pools[s].mean()) for s in STRATA}
    p_star = float(np.mean(list(rates.values())))

    print("=" * 76)
    print("ADVANCED EXPERIMENTS ON REAL GPT-4o-mini OUTCOME POOLS")
    print("=" * 76)
    print(f"Pools: 250/stratum, p* = {p_star:.4f}, "
          f"alpha = {ALPHA}, BASE_SEED = {BASE_SEED}\n")

    e1_peeking(pools, p_star)
    e2_validity_stress(pools)
    e3_allocation(pools, p_star)
    e4_variance_theory(pools, p_star)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_advanced.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_advanced.txt'}")
