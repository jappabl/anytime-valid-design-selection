#!/usr/bin/env python3
"""Wald SPRT baseline vs betting-CS certification.

Wald's SPRT (1945) is the optimal sequential test between two SIMPLE
hypotheses p0 vs p1 and is the obvious classical baseline for
certification. This experiment quantifies the trade honestly:

  - When both hypotheses are correctly specified and the true rate sits at
    or beyond them, SPRT is faster (it is optimal; we measure how much).
  - SPRT's alpha/beta guarantees hold ONLY at p0 and p1. For a
    certification task "is p above or below tau?", a true rate between p0
    and p1 but on the safe side of tau can be declared 'unsafe' (or vice
    versa) with probability FAR above alpha. The betting CS certifies
    against tau itself (composite), so its false-certification rate stays
    below alpha at every true p, and it additionally provides an
    anytime-valid interval estimate, which SPRT does not.

Real pools (gpt-4o-mini JSON, p* = 0.208) for the well-specified case;
synthetic Bernoulli streams (labeled as such) for the misspecification
sweep, since the pool's p* is fixed. Deterministic (BASE_SEED = 42).
Writes results_sprt_comparison.txt.
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
TAU = 0.15
N_MAX = 2000
N_REPS = 1000
STRATA = ["simple", "medium", "complex", "extreme"]

A_HI = np.log((1 - ALPHA) / ALPHA)   # accept H1 when LLR >= A_HI
A_LO = np.log(ALPHA / (1 - ALPHA))   # accept H0 when LLR <= A_LO

_cache = {}


def cs_bounds(f, s):
    if (f, s) not in _cache:
        _cache[(f, s)] = betting_bounds(f, s, ALPHA)
    return _cache[(f, s)]


def sprt_step(llr, x, p0, p1):
    if x:
        return llr + np.log(p1 / p0)
    return llr + np.log((1 - p1) / (1 - p0))


def run_sprt(draws, p0, p1):
    """Returns ('H0'|'H1'|'ABSTAIN', n)."""
    llr = 0.0
    for n, x in enumerate(draws, 1):
        llr = sprt_step(llr, x, p0, p1)
        if llr >= A_HI:
            return "H1", n
        if llr <= A_LO:
            return "H0", n
    return "ABSTAIN", len(draws)


def run_cs(draws):
    """Certify vs TAU with the betting CS. Returns ('SAFE'|'UNSAFE'|'ABSTAIN', n)."""
    f = 0
    for n, x in enumerate(draws, 1):
        f += int(x)
        if n >= 20 and n % 4 == 0:
            lo, hi = cs_bounds(f, n - f)
            if hi <= TAU:
                return "SAFE", n
            if lo > TAU:
                return "UNSAFE", n
    return "ABSTAIN", len(draws)


def main():
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        rec = json.loads(line)
        pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    pools = {s: np.array(v, dtype=np.int8) for s, v in pools.items()}
    p_star = float(np.mean([pools[s].mean() for s in STRATA]))

    print("=" * 76)
    print("WALD SPRT BASELINE vs BETTING-CS CERTIFICATION")
    print("=" * 76)
    print(f"tau = {TAU}, alpha = beta = {ALPHA}, n_max = {N_MAX}, "
          f"{N_REPS} reps, BASE_SEED = {BASE_SEED}\n")

    # ------------------------------------------------------------------
    # Part 1: well-specified case on REAL pools (p* = 0.208, truth UNSAFE)
    # ------------------------------------------------------------------
    print(f"PART 1 - Real gpt-4o-mini pools (p* = {p_star:.4f}, truth UNSAFE)")
    print("-" * 76)
    rng = np.random.default_rng(BASE_SEED + 41)

    def pool_stream(rng):
        # round-robin strata (same sampling design as the CS experiments)
        return [int(pools[STRATA[i % 4]][int(rng.integers(0, 250))])
                for i in range(N_MAX)]

    for label, p0, p1 in [("well-specified (p0=0.10, p1=0.25)", 0.10, 0.25),
                          ("tight brackets  (p0=0.14, p1=0.16)", 0.14, 0.16)]:
        rng = np.random.default_rng(BASE_SEED + 42)
        sprt_times, sprt_wrong, sprt_abstain = [], 0, 0
        for _ in range(N_REPS):
            d, n = run_sprt(pool_stream(rng), p0, p1)
            if d == "H1":
                sprt_times.append(n)
            elif d == "H0":
                sprt_wrong += 1
            else:
                sprt_abstain += 1
        med = int(np.median(sprt_times)) if sprt_times else None
        print(f"  SPRT {label}: correct {len(sprt_times)}/{N_REPS}, "
              f"wrong {sprt_wrong}, abstain {sprt_abstain}, median n {med}")

    rng = np.random.default_rng(BASE_SEED + 43)
    cs_times, cs_wrong, cs_abstain = [], 0, 0
    for _ in range(N_REPS):
        d, n = run_cs(pool_stream(rng))
        if d == "UNSAFE":
            cs_times.append(n)
        elif d == "SAFE":
            cs_wrong += 1
        else:
            cs_abstain += 1
    print(f"  Betting CS (composite, vs tau itself): "
          f"correct {len(cs_times)}/{N_REPS}, wrong {cs_wrong}, "
          f"abstain {cs_abstain}, median n {int(np.median(cs_times))}")
    print("""
  Reading: with a generous, correctly-placed bracket the SPRT is faster --
  it is the optimal simple-vs-simple test and pays for neither
  composite validity nor an interval estimate.""")

    # ------------------------------------------------------------------
    # Part 2: misspecification sweep (synthetic Bernoulli, labeled)
    # ------------------------------------------------------------------
    print("\nPART 2 - Misspecification sweep (SYNTHETIC Bernoulli streams)")
    print("-" * 76)
    print(f"SPRT uses p0=0.10, p1=0.25; certification question is p vs "
          f"tau={TAU}.")
    print("True p varies BETWEEN the hypotheses. 'False unsafe' = declaring")
    print("H1/UNSAFE when truth is p <= tau; 'false safe' symmetric.\n")
    print(f"  {'true p':>7} {'truth':>7} | {'SPRT false':>11} {'decided':>8} "
          f"{'med n':>6} | {'CS false':>9} {'decided':>8} {'med n':>6}")

    for p_true in [0.11, 0.13, 0.145, 0.155, 0.17, 0.20]:
        truth_unsafe = p_true > TAU
        rng = np.random.default_rng(BASE_SEED + 44)
        sprt_false = 0
        sprt_times = []
        cs_false = 0
        cs_times = []
        for _ in range(N_REPS):
            draws = (rng.random(N_MAX) < p_true).astype(int)
            d, n = run_sprt(draws, 0.10, 0.25)
            if d != "ABSTAIN":
                declared_unsafe = d == "H1"
                if declared_unsafe != truth_unsafe:
                    sprt_false += 1
                sprt_times.append(n)
            d, n = run_cs(draws)
            if d != "ABSTAIN":
                declared_unsafe = d == "UNSAFE"
                if declared_unsafe != truth_unsafe:
                    cs_false += 1
                cs_times.append(n)
        sprt_med = int(np.median(sprt_times)) if sprt_times else -1
        cs_med = int(np.median(cs_times)) if cs_times else -1
        print(f"  {p_true:>7.3f} {'UNSAFE' if truth_unsafe else 'SAFE':>7} | "
              f"{sprt_false / N_REPS:>10.1%} "
              f"{len(sprt_times) / N_REPS:>8.0%} {sprt_med:>6d} | "
              f"{cs_false / N_REPS:>8.1%} "
              f"{len(cs_times) / N_REPS:>8.0%} {cs_med:>6d}")

    print("""
  Reading: near tau the CS mostly abstains within budget (low decided%),
  which is the honest behavior for a boundary case -- while between its
  hypotheses the SPRT always terminates but its
  declarations carry NO error control relative to tau -- near tau it is
  close to a coin flip, and even clearly-safe rates (p=0.13) are declared
  unsafe at rates far above alpha. The betting CS certifies against tau
  itself: it may abstain near the boundary (honesty), but its
  false-certification rate stays below alpha at EVERY true p, and it
  returns an anytime-valid interval throughout. For regulatory-style
  claims ("the failure rate is below tau"), composite anytime validity is
  the requirement and SPRT does not provide it.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_sprt_comparison.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_sprt_comparison.txt'}")
