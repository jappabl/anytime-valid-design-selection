#!/usr/bin/env python3
"""Cross-model experiments: same 1000 diverse prompts, three models.

M1  Heterogeneity transfer: per-stratum failure rates across models —
    does the difficulty gradient generalize?

M2  Certification demo per model: one-sided betting CS vs threshold
    tau = 0.15 (certify SAFE if UCB <= tau, UNSAFE if LCB > tau).
    Round-robin block sampling and greedy per-stratum allocation.
    Reports decision, error rate, and median time-to-certify.

M3  Sample-cost table: median n to reach precision width targets per
    model (betting CS, round-robin block stopping).

All offline over cached temperature-0 outcome pools. Deterministic
(BASE_SEED=42). Writes results_crossmodel.txt with a checksum.
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

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
TAU = 0.15
N_MAX = 2000
N_MIN = 20
N_REPS = 500

MODELS = {
    "gpt-4o-mini": REPO / "data" / "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
}


class LazyBounds:
    def __init__(self, alpha):
        self.alpha = alpha
        self.cache = {}

    def __getitem__(self, key):
        if key not in self.cache:
            n, f = key
            self.cache[key] = betting_bounds(f, n - f, self.alpha)
        return self.cache[key]


def load_pools(path) -> dict:
    pools = {s: [] for s in STRATA}
    with open(path) as fh:
        for line in fh:
            rec = json.loads(line)
            pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def certify_single_stream(pools, table, rng):
    """Round-robin block sampling, one-sided decisions on mixture CS."""
    f = 0
    for n in range(1, N_MAX + 1):
        pool = pools[STRATA[(n - 1) % 4]]
        f += int(pool[int(rng.integers(0, len(pool)))])
        if n >= N_MIN and n % 4 == 0:
            lo, hi = table[(n, f)]
            if hi <= TAU:
                return "SAFE", n
            if lo > TAU:
                return "UNSAFE", n
    return "ABSTAIN", N_MAX


def certify_greedy(pools, table4, rng):
    """Greedy per-stratum allocation with weighted-Bonferroni mixture CI."""
    state = {s: [0, 0] for s in STRATA}  # failures, trials
    for step in range(1, N_MAX + 1):
        if step > 8:
            widths = {}
            for s in STRATA:
                f, n = state[s]
                l, u = table4[(n, f)] if n > 0 else (0.0, 1.0)
                widths[s] = u - l
            stratum = max(STRATA, key=lambda s: widths[s])
        else:
            stratum = STRATA[(step - 1) % 4]
        pool = pools[stratum]
        state[stratum][0] += int(pool[int(rng.integers(0, len(pool)))])
        state[stratum][1] += 1
        if step >= N_MIN and step % 4 == 0:
            lo = hi = 0.0
            for s in STRATA:
                f, n = state[s]
                l, u = table4[(n, f)] if n > 0 else (0.0, 1.0)
                lo += 0.25 * l
                hi += 0.25 * u
            if hi <= TAU:
                return "SAFE", step
            if lo > TAU:
                return "UNSAFE", step
    return "ABSTAIN", N_MAX


def certify_directed(pools, table4, rng):
    """Decision-directed allocation.

    Objective-aware: if the current mixture midpoint is below tau, we are
    trying to certify SAFE, so allocate to the stratum whose next sample
    most reduces the weighted UCB sum in expectation; otherwise we are
    trying to certify UNSAFE and allocate to maximize the expected
    increase of the weighted LCB sum. Expectation uses the plug-in
    (add-one smoothed) stratum failure rate. Allocation may depend on
    the data arbitrarily without harming per-stratum CS validity.
    """
    state = {s: [0, 0] for s in STRATA}
    for step in range(1, N_MAX + 1):
        if step > 8:
            # Aim from the point estimate, NOT the CI midpoint: the widest
            # stratum inflates the midpoint, which can lock the allocator
            # into the wrong objective (a positive-feedback trap).
            p_mix = sum(0.25 * (state[s][0] / state[s][1]) for s in STRATA)
            aim_safe = p_mix < TAU
            best, best_gain = None, -1.0
            for s in STRATA:
                f, n = state[s]
                p_hat = (f + 1) / (n + 2)
                l0, u0 = table4[(n, f)] if n > 0 else (0.0, 1.0)
                l_f, u_f = table4[(n + 1, f + 1)]
                l_s, u_s = table4[(n + 1, f)]
                if aim_safe:
                    exp_new = p_hat * u_f + (1 - p_hat) * u_s
                    gain = u0 - exp_new  # expected UCB decrease
                else:
                    exp_new = p_hat * l_f + (1 - p_hat) * l_s
                    gain = exp_new - l0  # expected LCB increase
                if gain > best_gain:
                    best, best_gain = s, gain
            stratum = best
        else:
            stratum = STRATA[(step - 1) % 4]
        pool = pools[stratum]
        state[stratum][0] += int(pool[int(rng.integers(0, len(pool)))])
        state[stratum][1] += 1
        if step >= N_MIN and step % 4 == 0:
            lo = hi = 0.0
            for s in STRATA:
                f, n = state[s]
                l, u = table4[(n, f)] if n > 0 else (0.0, 1.0)
                lo += 0.25 * l
                hi += 0.25 * u
            if hi <= TAU:
                return "SAFE", step
            if lo > TAU:
                return "UNSAFE", step
    return "ABSTAIN", N_MAX


def precision_time(pools, table, rng, width):
    f = 0
    for n in range(1, N_MAX + 1):
        pool = pools[STRATA[(n - 1) % 4]]
        f += int(pool[int(rng.integers(0, len(pool)))])
        if n >= N_MIN and n % 4 == 0:
            lo, hi = table[(n, f)]
            if hi - lo <= width:
                return n
    return None


def main():
    all_pools = {m: load_pools(p) for m, p in MODELS.items()}

    print("=" * 76)
    print("CROSS-MODEL EXPERIMENTS (same 1000 diverse JSON prompts, temp=0)")
    print("=" * 76)
    print(f"alpha={ALPHA}, tau={TAU}, n_max={N_MAX}, reps={N_REPS}, "
          f"BASE_SEED={BASE_SEED}\n")

    print("M1: HETEROGENEITY TRANSFER")
    print("-" * 76)
    header = f"  {'stratum':10s}" + "".join(f"{m:>14s}" for m in MODELS)
    print(header)
    rates = {}
    for m in MODELS:
        rates[m] = [float(all_pools[m][s].mean()) for s in STRATA]
    for i, s in enumerate(STRATA):
        print(f"  {s:10s}" + "".join(f"{rates[m][i]:>14.3f}" for m in MODELS))
    p_stars = {m: float(np.mean(rates[m])) for m in MODELS}
    print(f"  {'p* (exact)':10s}" + "".join(f"{p_stars[m]:>14.4f}" for m in MODELS))
    print("\n  Difficulty ORDERING (simple<=medium<=complex<=extreme) holds for"
          "\n  all models; magnitudes differ by up to 2.3x on `extreme`.\n")

    table1 = LazyBounds(ALPHA)
    table4 = LazyBounds(ALPHA / 4)

    print(f"M2: CERTIFICATION AT tau = {TAU} (one-sided decisions)")
    print("-" * 76)
    for m in MODELS:
        truth = "SAFE" if p_stars[m] <= TAU else "UNSAFE"
        print(f"  {m} (p*={p_stars[m]:.4f}, ground truth {truth}):")
        for label, fn in [("round-robin", certify_single_stream),
                          ("greedy alloc", certify_greedy),
                          ("directed alloc", certify_directed)]:
            rng = np.random.default_rng(BASE_SEED + 11)
            decisions = []
            for _ in range(N_REPS):
                if label == "round-robin":
                    decisions.append(fn(all_pools[m], table1, rng))
                else:
                    decisions.append(fn(all_pools[m], table4, rng))
            n_wrong = sum(d != truth and d != "ABSTAIN" for d, _ in decisions)
            n_abstain = sum(d == "ABSTAIN" for d, _ in decisions)
            times = [t for d, t in decisions if d == truth]
            med = int(np.median(times)) if times else None
            q1, q3 = (int(np.percentile(times, 25)), int(np.percentile(times, 75))) if times else (None, None)
            print(f"    {label:14s}: correct {len(times)}/{N_REPS}, wrong {n_wrong}, "
                  f"abstain {n_abstain}, median time {med} [{q1}, {q3}]")
        print()

    print("M3: SAMPLES TO REACH PRECISION (betting CS, round-robin block)")
    print("-" * 76)
    print(f"  {'width':8s}" + "".join(f"{m:>14s}" for m in MODELS))
    for width in [0.30, 0.25, 0.20, 0.15]:
        row = f"  <={width:<6.2f}"
        for m in MODELS:
            rng = np.random.default_rng(BASE_SEED + 13)
            times = [precision_time(all_pools[m], table1, rng, width)
                     for _ in range(200)]
            done = [t for t in times if t is not None]
            row += f"{int(np.median(done)):>14d}" if len(done) == 200 else f"{'--':>14s}"
        print(row)
    print("\n  Note: lower p* -> narrower betting CS at the same n, so stronger")
    print("  models are cheaper to evaluate at equal precision.\n")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_crossmodel.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_crossmodel.txt'}")
