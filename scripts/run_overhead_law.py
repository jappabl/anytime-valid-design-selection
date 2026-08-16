#!/usr/bin/env python3
"""Measurement grid for the certification-overhead law.

CONJECTURE (motivated by mixture-regret theory; to be FITTED, not
assumed): the median time-to-certify n of an e-process certification
method satisfies approximately

    n * V(tau)  =  log(1/alpha) + (d_eff / 2) * log n + c,

where V(tau) is the max-min certification game value at the true rates
(the information rate of the problem) and d_eff is the effective
parametric dimension the statistic must learn. Theory suggests:
  single-stream mixture CS: d_eff ~ 1 (one free parameter)
  UI product e-process:     d_eff ~ K or K-1 (nuisance dimension)
  WSR on blocks:            d_eff ~ 1 (one bounded mean)
If the fitted d_eff recover interpretable integers across a margin sweep
and two models, the invention-round anomaly (sophisticated methods
losing until margins are extreme) becomes a predictive law.

This script produces the grid: median stopping times (200 reps) for the
three clean round-robin statistics across a tau sweep on the gpt-4o-mini
(UNSAFE direction) and gpt-4.1-nano (SAFE direction) pools, with the
game value V computed per point. Fitting happens in
scripts/fit_overhead_law.py. Writes results_overhead_law.txt.
"""

import hashlib
import io
import json
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.stats.wsr_block_cs import WSRBlockCS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 200
N_MAX = 6000


def load(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def run_single(pools, tau, truth, rng):
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        pool = pools[STRATA[(n - 1) % 4]]
        cs.update(0, bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0:
            if truth == "SAFE" and cs.rejects_ge(tau):
                return n
            if truth == "UNSAFE" and cs.rejects_le(tau):
                return n
    return None


def run_ui_rr(pools, tau, truth, rng):
    cs = StratifiedUICS(k=4, alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        pool = pools[STRATA[k]]
        cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0:
            if truth == "SAFE" and cs.rejects_ge(tau):
                return n
            if truth == "UNSAFE" and cs.rejects_le(tau):
                return n
    return None


def run_wsr(pools, tau, truth, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if truth == "SAFE" and hi <= tau:
                return 4 * b
            if truth == "UNSAFE" and lo > tau:
                return 4 * b
    return None


def main():
    print("=" * 76)
    print("MEASUREMENT GRID FOR THE CERTIFICATION-OVERHEAD LAW")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/point, n_max={N_MAX}, "
          f"BASE_SEED={BASE_SEED}")
    print("Columns: tau, margin, game value V, then per-method "
          "(median n | certified fraction).\n")

    print("NOTE (R4): this is a measurement grid; its frozen windows "
          "are scored in results_overhead_fit.txt (PASS/MISSED "
          "verdicts printed there).\n")
    settings = [
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", "UNSAFE",
         [0.145, 0.15, 0.16, 0.17, 0.175, 0.18]),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         "SAFE", [0.15, 0.13, 0.12, 0.11, 0.10, 0.095]),
    ]
    for model, fname, truth, taus in settings:
        pools = load(fname)
        rates = np.array([float(pools[s].mean()) for s in STRATA])
        p_star = float(rates.mean())
        print(f"  {model} (p* = {p_star:.4f}, truth {truth}):")
        print(f"  {'tau':>6} {'margin':>7} {'V_game':>8} {'V_pool':>8} "
              f"{'single':>16} {'UI+RR':>16} {'WSR':>16}")
        for tau in taus:
            if truth == "SAFE":
                _, v_game = bench.game_allocation(
                    1 - rates, np.full(4, 0.25), 1 - tau)
                v_pool = bench.kl_bern(p_star, tau)
            else:
                _, v_game = bench.game_allocation(
                    rates, np.full(4, 0.25), tau)
                v_pool = bench.kl_bern(p_star, tau)
            row = f"  {tau:>6.3f} {abs(p_star - tau):>7.3f} " \
                  f"{v_game:>8.4f} {v_pool:>8.4f}"
            for fn in [run_single, run_ui_rr, run_wsr]:
                rng = np.random.default_rng(BASE_SEED + 101)
                times = [fn(pools, tau, truth, rng) for _ in range(N_REPS)]
                done = [t for t in times if t is not None]
                frac = len(done) / N_REPS
                med = int(np.median(done)) if done else -1
                row += f" {med:>9d}|{frac:>5.2f}"
            print(row)
        print()


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_overhead_law.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_overhead_law.txt'}")
