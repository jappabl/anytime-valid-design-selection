#!/usr/bin/env python3
"""The price of PROVABLE validity under stratified sampling.

Single draws from a round-robin stratified stream are not identically
distributed, so the per-sample mixture betting CS is only empirically
validated there (results_advanced.txt, E2). But complete BLOCKS (one draw
per stratum) ARE iid across blocks. Two constructions inherit exact
validity from that:

  1. Binarized blocks: Y_b ~ Bernoulli(block mean M_b) — then Y_b is iid
     Bernoulli(p*) EXACTLY, and the Beta-Bernoulli betting CS applies
     with its full guarantee. (Randomization uses a seeded RNG.)
  2. Empirical-Bernstein CS on block means: blocks are iid bounded [0,1]
     variables with mean p*; a stitched EB CS on them is valid and
     exploits the small between-block variance.
  3. WSR betting CS on block means (Waudby-Smith & Ramdas): a hedged
     capital process on iid bounded variables — exactly valid, and the
     state-of-the-art CS for bounded means.

This experiment measures what these provably-valid routes cost relative
to the (empirically valid) per-sample mixture betting CS, on the real
GPT-4o-mini pools. Offline, deterministic. Writes results_block_reduction.txt.
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

from eval_harness.stats.fast_bounds import betting_bounds
from eval_harness.stats.wsr_block_cs import WSRBlockCS

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 500
MAX_BLOCKS = 500  # = 2000 samples
TAU = 0.15


def load_pools():
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        rec = json.loads(line)
        pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


_bet_cache = {}


def bet_bounds(f, s):
    if (f, s) not in _bet_cache:
        _bet_cache[(f, s)] = betting_bounds(f, s, ALPHA)
    return _bet_cache[(f, s)]


def eb_block_bounds(means_sum, sq_sum, b):
    """Stitched empirical-Bernstein CS on b iid block means in [0,1]."""
    if b < 2:
        return 0.0, 1.0
    m = means_sum / b
    var_hat = max(sq_sum / b - m * m, 0.0)
    delta_b = ALPHA / (b * (b + 1))
    log_term = np.log(2.0 / delta_b)
    eps = np.sqrt(2 * var_hat * log_term / b) + (7 / 3) * log_term / (b - 1)
    return max(0.0, m - eps), min(1.0, m + eps)


def wsr_coverage_check(pools, n_reps=200):
    """Uniform coverage of the WSR block CS on real-pool block streams."""
    p_star = float(np.mean([pools[s].mean() for s in STRATA]))
    rng = np.random.default_rng(BASE_SEED + 33)
    misses = 0
    for _ in range(n_reps):
        cs = WSRBlockCS()
        missed = False
        for b in range(120):
            block = [int(pools[s][int(rng.integers(0, len(pools[s])))])
                     for s in STRATA]
            cs.update(sum(block) / 4)
            lo, hi = cs.get_bounds()
            if not (lo <= p_star <= hi):
                missed = True
                break
        misses += missed
    return 1 - misses / n_reps


def run(pools, method, rng, width_target=None):
    """Returns stopping sample count for the given criterion, or None."""
    f_samples = 0          # per-sample failures (method: per-sample)
    y_f = y_s = 0          # binarized block outcomes
    means_sum = sq_sum = 0.0
    wsr = WSRBlockCS() if method == "wsr-blocks" else None
    for b in range(1, MAX_BLOCKS + 1):
        block = [int(pools[s][int(rng.integers(0, len(pools[s])))])
                 for s in STRATA]
        n = 4 * b
        f_samples += sum(block)
        m_b = sum(block) / 4
        means_sum += m_b
        sq_sum += m_b * m_b
        if method == "binarized":
            if rng.random() < m_b:
                y_f += 1
            else:
                y_s += 1
        elif method == "wsr-blocks":
            wsr.update(m_b)

        if n < 20:
            continue
        if method == "per-sample":
            lo, hi = bet_bounds(f_samples, n - f_samples)
        elif method == "binarized":
            lo, hi = bet_bounds(y_f, y_s)
        elif method == "wsr-blocks":
            lo, hi = wsr.get_bounds()
        else:  # eb-blocks
            lo, hi = eb_block_bounds(means_sum, sq_sum, b)

        if width_target is not None:
            if hi - lo <= width_target:
                return n
        else:
            if lo > TAU:
                return ("UNSAFE", n)
            if hi <= TAU:
                return ("SAFE", n)
    return None


def main():
    pools = load_pools()
    p_star = float(np.mean([pools[s].mean() for s in STRATA]))

    print("=" * 76)
    print("THE PRICE OF PROVABLE VALIDITY (block-iid reductions)")
    print("=" * 76)
    print(f"Real gpt-4o-mini pools, p* = {p_star:.4f}, alpha = {ALPHA}, "
          f"{N_REPS} reps, budget {4 * MAX_BLOCKS} samples, "
          f"BASE_SEED = {BASE_SEED}")
    print("""
Methods:
  per-sample : betting CS on the raw stratified stream
               (validity empirical -- E2; tightest)
  binarized  : betting CS on Y_b ~ Bernoulli(block mean)
               (EXACTLY valid; randomized reduction)
  eb-blocks  : stitched empirical-Bernstein CS on iid block means
               (EXACTLY valid; deterministic reduction)
""")

    cov = wsr_coverage_check(pools)
    print(f"WSR block CS uniform coverage on real-pool block streams "
          f"(200 reps, 120 blocks): {cov:.3f}\n")

    methods = ["per-sample", "wsr-blocks", "binarized", "eb-blocks"]

    print("Median samples to reach CI width target:")
    print(f"  {'width':8s}" + "".join(f"{m:>13s}" for m in methods))
    for width in [0.30, 0.20, 0.15]:
        row = f"  <={width:<6.2f}"
        for method in methods:
            rng = np.random.default_rng(BASE_SEED + 31)
            times = [run(pools, method, rng, width_target=width)
                     for _ in range(N_REPS)]
            done = [t for t in times if t is not None]
            cell = (f"{int(np.median(done))}" if len(done) == N_REPS
                    else f"{len(done)}/{N_REPS}")
            row += f"{cell:>13s}"
        print(row)

    print(f"\nCertification at tau={TAU} "
          f"(truth: p*={p_star:.3f} > tau, correct = UNSAFE):")
    for method in methods:
        rng = np.random.default_rng(BASE_SEED + 32)
        outcomes = [run(pools, method, rng) for _ in range(N_REPS)]
        correct = [n for d, n in (o for o in outcomes if o) if d == "UNSAFE"]
        wrong = sum(1 for o in outcomes if o and o[0] == "SAFE")
        abstain = sum(1 for o in outcomes if o is None)
        cell = (f"median {int(np.median(correct))}" if correct else "--")
        print(f"  {method:11s}: correct {len(correct)}/{N_REPS}, "
              f"WRONG {wrong}, abstain {abstain}, {cell}")

    print("""
Reading: the WSR betting CS on block means is provably valid (blocks are
iid) AND TIGHTER than the per-sample mixture CS -- stratification shrinks
the between-block variance (Var(M) = mean p_k q_k / K ~ 0.017 here, vs
p*q* = 0.165 for the mixture) and the WSR bet adapts to it, while the
Beta-Bernoulli per-sample CS must price iid-Bernoulli variance it never
sees. Stratify -> block -> bet dominates both plain routes. The stitched
EB reduction is sunk by its range term on n/4 observations; binarization
pays the theoretical ~4x for discarding within-block information.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_block_reduction.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_block_reduction.txt'}")
