#!/usr/bin/env python3
"""Real-LLM sequential evaluation experiments over cached GPT-4o-mini outcomes.

Data: data/llm_outcomes_diverse_json.jsonl — one temperature-0 outcome per
distinct prompt (250 per stratum, 4 strata). Sampling with replacement from
these pools is an iid draw from the empirical distribution of the model's
behavior on the prompt pool, so the estimand (uniform-mixture failure rate
p*) is exact FOR THE POOL SNAPSHOT. Temperature-0 decoding is only
near-deterministic (~1-2%% of prompts flip outcome on re-query, measured),
so pools are single-epoch snapshots; see AUDIT_PREP.md.

Experiments (all deterministic, BASE_SEED=42, zero API cost):
  R1: Naive vs stratified sampling under precision stopping with the betting
      CS — conditional bias at the stopping time on real-model outcomes.
  R2: Same design with the Hoeffding/Bernstein intersection CS — shows the
      original real-LLM experiment could never stop within its budget.
  R3: Certification (one-sided betting UCB/LCB vs threshold tau) — decision
      errors and time-to-certify, betting vs intersection.

Writes results_realllm_betting.txt with a checksum.
"""

import hashlib
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.special import betaln

REPO = Path(__file__).parent.parent
DATA = REPO / "data" / "llm_outcomes_diverse_json.jsonl"

BASE_SEED = 42
ALPHA = 0.05
N_MAX = 200
N_MIN = 20
N_REPS = 1000
WIDTHS = [0.25, 0.30, 0.35, 0.40]
STRATA = ["simple", "medium", "complex", "extreme"]

LOG_THRESH = np.log(1.0 / ALPHA)
LOG_THRESH_1SIDED = np.log(1.0 / ALPHA)  # one-sided uses full alpha


# ---------------------------------------------------------------------------
# Betting CS bounds (closed form; equals BernoulliCSBetting, see
# scripts/validate_betting_cs.py for the equivalence and coverage checks)
# ---------------------------------------------------------------------------

def _log_e(f: int, s: int, p0: float) -> float:
    p0 = min(max(p0, 1e-12), 1 - 1e-12)
    return (betaln(1 + f, 1 + s) - betaln(1, 1)) - (
        f * np.log(p0) + s * np.log(1 - p0)
    )


def _betting_bounds(f: int, s: int, thresh: float) -> tuple:
    n = f + s
    if n == 0:
        return 0.0, 1.0
    p_hat = f / n

    if _log_e(f, s, 1 - 1e-9) < thresh:
        ucb = 1.0
    else:
        lo, hi = p_hat, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if _log_e(f, s, mid) >= thresh:
                hi = mid
            else:
                lo = mid
        ucb = hi

    if _log_e(f, s, 1e-9) < thresh:
        lcb = 0.0
    else:
        lo, hi = 0.0, p_hat
        for _ in range(50):
            mid = (lo + hi) / 2
            if _log_e(f, s, mid) >= thresh:
                lo = mid
            else:
                hi = mid
        lcb = lo

    return lcb, ucb


# ---------------------------------------------------------------------------
# Intersection CS bounds (closed form; mirrors BernoulliCSIntersection)
# ---------------------------------------------------------------------------

def _intersection_bounds(f: int, s: int, alpha: float = ALPHA) -> tuple:
    n = f + s
    if n == 0:
        return 0.0, 1.0
    p_hat = f / n
    delta_n = (alpha / 2) / (n * (n + 1))  # alpha/2 per bound family
    log_term = np.log(2.0 / delta_n)

    eps_h = np.sqrt(log_term / (2 * n))

    if n > 1:
        var_hat = p_hat * (1 - p_hat)
        eps_b = np.sqrt(2 * var_hat * log_term / n) + (7 / 3) * log_term / (n - 1)
    else:
        eps_b = 1.0

    lower = max(0.0, p_hat - eps_h, p_hat - eps_b)
    upper = min(1.0, p_hat + eps_h, p_hat + eps_b)
    return lower, upper


# ---------------------------------------------------------------------------
# Precomputed bound tables: bounds[(n, f)] -> (lcb, ucb)
# ---------------------------------------------------------------------------

def build_table(bound_fn) -> dict:
    table = {}
    for n in range(1, N_MAX + 1):
        for f in range(0, n + 1):
            table[(n, f)] = bound_fn(f, n - f)
    return table


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pools() -> dict:
    pools = {s: [] for s in STRATA}
    with open(DATA) as fh:
        for line in fh:
            rec = json.loads(line)
            pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


# ---------------------------------------------------------------------------
# One sequential replication over the outcome pools
# ---------------------------------------------------------------------------

def run_replication(pools, method, width, rep, table):
    rng = np.random.default_rng(
        BASE_SEED + rep * 17 + WIDTHS.index(width) * 100003
        + (0 if method == "naive" else 50021)
    )
    counts = {s: 0 for s in STRATA}
    failures = 0
    n_stop, stopped = N_MAX, False

    for n in range(1, N_MAX + 1):
        if method.startswith("stratified"):
            stratum = STRATA[(n - 1) % 4]
        else:
            stratum = STRATA[int(rng.integers(0, 4))]
        counts[stratum] += 1
        pool = pools[stratum]
        failures += int(pool[int(rng.integers(0, len(pool)))])

        # 'stratified_block' evaluates the stopping rule only at complete
        # round-robin blocks (n divisible by K), so the stratum composition
        # is exactly balanced at every possible stopping time. Plain
        # 'stratified' can stop mid-block, systematically undersampling the
        # strata later in the rotation order.
        can_stop = n >= N_MIN
        if method == "stratified_block":
            can_stop = can_stop and n % len(STRATA) == 0

        if can_stop:
            lcb, ucb = table[(n, failures)]
            if ucb - lcb <= width:
                n_stop, stopped = n, True
                break

    n = n_stop
    lcb, ucb = table[(n, failures)]
    fracs = np.array([counts[s] / n for s in STRATA])
    drift = float(np.var(fracs - 0.25) * 1e4)
    return {
        "p_hat": failures / n,
        "n_stop": n,
        "stopped": stopped,
        "lcb": lcb,
        "ucb": ucb,
        "drift": drift,
    }


def summarize(results, p_star):
    p_hats = np.array([r["p_hat"] for r in results])
    bias = p_hats.mean() - p_star
    se = p_hats.std(ddof=1) / np.sqrt(len(p_hats))
    return {
        "bias": bias,
        "se": se,
        "mae": np.abs(p_hats - p_star).mean(),
        "n_stop_mean": np.mean([r["n_stop"] for r in results]),
        "n_stop_median": np.median([r["n_stop"] for r in results]),
        "stopped_frac": np.mean([r["stopped"] for r in results]),
        "drift": np.mean([r["drift"] for r in results]),
        "coverage": np.mean([r["lcb"] <= p_star <= r["ucb"] for r in results]),
    }


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

def experiment_precision(pools, p_star, table, cs_name):
    print(f"--- Precision stopping with {cs_name} CS "
          f"({N_REPS} reps/condition, n_max={N_MAX}, min n={N_MIN}) ---\n")
    for width in WIDTHS:
        rows = {}
        for method in ["naive", "stratified", "stratified_block"]:
            results = [run_replication(pools, method, width, rep, table)
                       for rep in range(N_REPS)]
            rows[method] = summarize(results, p_star)
        na, st = rows["naive"], rows["stratified_block"]
        z = (na["bias"] - st["bias"]) / np.sqrt(na["se"] ** 2 + st["se"] ** 2)
        print(f"width<={width:.2f}:")
        for m in ["naive", "stratified", "stratified_block"]:
            r = rows[m]
            print(f"  {m:16s}: bias {r['bias']:+.4f} (SE {r['se']:.4f}), "
                  f"MAE {r['mae']:.4f}, median n_stop {r['n_stop_median']:.0f}, "
                  f"stopped {r['stopped_frac']*100:.0f}%, "
                  f"drift {r['drift']:.2f}e-4, coverage {r['coverage']:.3f}")
        print(f"  bias difference (naive vs stratified_block) z = {z:+.2f}\n")


def experiment_certification(pools, p_star, tables):
    print("--- Certification stopping (one-sided vs tau) ---")
    print(f"True mixture p* = {p_star:.4f}; "
          f"certify SAFE if UCB<=tau, UNSAFE if LCB>tau; n_max=1000\n")
    for tau, truth in [(0.25, "SAFE"), (0.15, "UNSAFE")]:
        print(f"tau = {tau} (ground truth: {truth})")
        for cs_name, bound_fn in tables.items():
            n_certs, wrong = [], 0
            for rep in range(400):
                rng = np.random.default_rng(BASE_SEED + 7919 * rep + int(tau * 1000))
                failures = 0
                decided = None
                for n in range(1, 1001):
                    stratum = STRATA[(n - 1) % 4]
                    pool = pools[stratum]
                    failures += int(pool[int(rng.integers(0, len(pool)))])
                    if n >= N_MIN and n % 5 == 0:
                        lcb, ucb = bound_fn(failures, n - failures)
                        if ucb <= tau:
                            decided = ("SAFE", n)
                            break
                        if lcb > tau:
                            decided = ("UNSAFE", n)
                            break
                if decided:
                    n_certs.append(decided[1])
                    wrong += decided[0] != truth
            certified = len(n_certs)
            med = int(np.median(n_certs)) if n_certs else None
            print(f"  {cs_name:12s}: certified {certified}/400, "
                  f"wrong {wrong}, median time-to-certify {med}")
        print()


def main():
    pools = load_pools()
    rates = {s: float(pools[s].mean()) for s in STRATA}
    p_star = float(np.mean(list(rates.values())))

    print("=" * 80)
    print("REAL-LLM SEQUENTIAL EVALUATION ON CACHED GPT-4o-mini OUTCOMES")
    print("=" * 80)
    print(f"\nModel: gpt-4o-mini, temperature=0, one call per distinct prompt")
    print(f"Pools: " + ", ".join(f"{s}={len(pools[s])}" for s in STRATA))
    print("Per-stratum failure rates (real, measured):")
    for s in STRATA:
        print(f"  {s:8s}: {rates[s]:.4f}")
    print(f"\nExact uniform-mixture estimand: p* = {p_star:.4f}")
    print(f"BASE_SEED = {BASE_SEED}, alpha = {ALPHA}\n")

    betting_table = build_table(lambda f, s: _betting_bounds(f, s, LOG_THRESH))
    intersection_table = build_table(_intersection_bounds)

    print("=" * 80)
    print("R1: BETTING CS")
    print("=" * 80)
    experiment_precision(pools, p_star, betting_table, "betting")

    print("=" * 80)
    print("R2: INTERSECTION CS (the bounds used in the failed live experiment)")
    print("=" * 80)
    experiment_precision(pools, p_star, intersection_table, "intersection")

    print("=" * 80)
    print("R3: CERTIFICATION")
    print("=" * 80)
    experiment_certification(
        pools, p_star,
        {
            "betting": lambda f, s: _betting_bounds(f, s, LOG_THRESH_1SIDED),
            "intersection": _intersection_bounds,
        },
    )


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 80 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 80 + "\n"
    print(content, end="")
    (REPO / "results_realllm_betting.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_realllm_betting.txt'}")
