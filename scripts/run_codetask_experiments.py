#!/usr/bin/env python3
"""Second task family: sequential evaluation on cached code-generation outcomes.

Confirms the JSON-task findings generalize: heterogeneity, precision
stopping with the betting CS, and SAFE certification (the code task puts
GPT-4o-mini in the strong-model regime, p* ~ 0.05).

Offline, deterministic. Writes results_codetask.txt with a checksum.
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

from eval_harness.stats.fast_bounds import betting_bounds, intersection_bounds

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 500
N_MIN = 20
N_MAX = 2000
DATA = REPO / "data" / "llm_outcomes_diverse_code_gpt-4o-mini.jsonl"


class LazyBounds:
    def __init__(self, bound_fn, alpha):
        self.bound_fn = bound_fn
        self.alpha = alpha
        self.cache = {}

    def __getitem__(self, key):
        if key not in self.cache:
            n, f = key
            self.cache[key] = self.bound_fn(f, n - f, self.alpha)
        return self.cache[key]


def main():
    pools = {s: [] for s in STRATA}
    with open(DATA) as fh:
        for line in fh:
            rec = json.loads(line)
            pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    pools = {s: np.array(v, dtype=np.int8) for s, v in pools.items()}
    rates = {s: float(pools[s].mean()) for s in STRATA}
    p_star = float(np.mean(list(rates.values())))

    print("=" * 76)
    print("SECOND TASK FAMILY: CODE GENERATION (gpt-4o-mini, temp=0)")
    print("=" * 76)
    print("Task: write a Python function matching a parametrized spec;")
    print("pass iff outputs equal the reference on all held tests.")
    print(f"Pools: 80/stratum. BASE_SEED={BASE_SEED}, alpha={ALPHA}\n")
    print("Per-stratum failure rates (real, measured):")
    for s in STRATA:
        print(f"  {s:8s}: {rates[s]:.4f}")
    print(f"\nExact uniform-mixture estimand: p* = {p_star:.4f}\n")

    bet = LazyBounds(betting_bounds, ALPHA)
    inter = LazyBounds(intersection_bounds, ALPHA)

    print("Samples to reach precision (round-robin block stopping, median of "
          f"{N_REPS} reps):")
    print(f"  {'width':8s} {'betting':>10s} {'intersection':>14s}")
    for width in [0.20, 0.15, 0.10]:
        row = f"  <={width:<6.2f}"
        for table in [bet, inter]:
            rng = np.random.default_rng(BASE_SEED + 5)
            times = []
            for _ in range(N_REPS):
                f = 0
                t = None
                for n in range(1, N_MAX + 1):
                    pool = pools[STRATA[(n - 1) % 4]]
                    f += int(pool[int(rng.integers(0, len(pool)))])
                    if n >= N_MIN and n % 4 == 0:
                        lo, hi = table[(n, f)]
                        if hi - lo <= width:
                            t = n
                            break
                times.append(t)
            done = [t for t in times if t is not None]
            cell = f"{int(np.median(done))}" if len(done) == N_REPS else \
                f"{len(done)}/{N_REPS} runs"
            row += f"{cell:>{10 if table is bet else 14}s}"
        print(row)

    print(f"\nSAFE certification at tau=0.10 (true p*={p_star:.4f}, "
          "ground truth SAFE):")
    for name, table in [("betting", bet), ("intersection", inter)]:
        rng = np.random.default_rng(BASE_SEED + 6)
        times, wrong, abstain = [], 0, 0
        for _ in range(N_REPS):
            f = 0
            decided = None
            for n in range(1, N_MAX + 1):
                pool = pools[STRATA[(n - 1) % 4]]
                f += int(pool[int(rng.integers(0, len(pool)))])
                if n >= N_MIN and n % 4 == 0:
                    lo, hi = table[(n, f)]
                    if hi <= 0.10:
                        decided = ("SAFE", n)
                        break
                    if lo > 0.10:
                        decided = ("UNSAFE", n)
                        break
            if decided is None:
                abstain += 1
            elif decided[0] != "SAFE":
                wrong += 1
            else:
                times.append(decided[1])
        med = int(np.median(times)) if times else None
        q = ([int(np.percentile(times, 25)), int(np.percentile(times, 75))]
             if times else None)
        print(f"  {name:12s}: correct {len(times)}/{N_REPS}, wrong {wrong}, "
              f"abstain {abstain}, median time {med} {q}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_codetask.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_codetask.txt'}")
