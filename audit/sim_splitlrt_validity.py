#!/usr/bin/env python3
"""AUDIT: validity gate for the faithful split-LRT arm used in
audit/sim_frontier_splitlrt.py.

Before claiming that a discard-burn-in split arm falsifies the frontier's
conservation window, check that it is actually anytime-valid: under
H0 : p* <= tau it must certify UNSAFE at most alpha of the time, at ANY
stopping time.

Least-favourable configuration: p* set exactly at tau (the null
boundary), keeping the per-stratum profile of the real gpt-4o-mini JSON
pool. Checks at n >= 20, n % 4 == 0, up to n_max, exactly as the arm is
used.

Run: python3 audit/sim_splitlrt_validity.py
"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "audit"))

from sim_frontier_splitlrt import SplitLRT          # noqa: E402
from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402

ALPHA = 0.05
TAU = 0.16
N_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
BURNS = ([int(b) for b in sys.argv[3].split(",")]
         if len(sys.argv) > 3 else [25, 50, 100])
WITH_REF = len(sys.argv) <= 3
PROFILE = np.array([0.004, 0.000, 0.068, 0.736])


def run(rates, rng, make_cs, n_max=N_MAX):
    cs = make_cs()
    for n in range(1, n_max + 1):
        k = (n - 1) % 4
        cs.update(k, bool(rng.random() < rates[k]))
        if n >= 20 and n % 4 == 0 and cs.rejects_le(TAU):
            return n
    return None


def main():
    print("=" * 78)
    print("AUDIT: anytime-validity gate for the split-LRT arm")
    print(f"H0 boundary p* = tau = {TAU}; alpha = {ALPHA}; {REPS} reps; "
          f"n_max = {N_MAX}")
    print("=" * 78)
    rates = PROFILE * (TAU / PROFILE.mean())
    print(f"least-favourable rates {np.round(rates, 5).tolist()} "
          f"(p* = {rates.mean():.4f})\n")
    print(f"  {'arm':>26} {'false UNSAFE':>13} {'rate':>8} "
          f"{'95% upper':>10}")
    arms = ([("UI mixture (reference)",
              lambda: StratifiedUICS(k=4, alpha=ALPHA))] if WITH_REF else [])
    for b in BURNS:
        arms.append((f"split-LRT burn={b}", lambda b=b: SplitLRT(burn=b)))
    for name, mk in arms:
        rng = np.random.default_rng(20260812)
        hits = sum(1 for _ in range(REPS)
                   if run(rates, rng, mk) is not None)
        p = hits / REPS
        se = np.sqrt(max(p, 1e-6) * (1 - p) / REPS)
        print(f"  {name:>26} {hits:>8d}/{REPS} {p:>8.4f} "
              f"{p + 1.96 * se:>10.4f}")
    print(f"\n  A valid anytime procedure must keep these at or below "
          f"alpha = {ALPHA}.")


if __name__ == "__main__":
    main()
