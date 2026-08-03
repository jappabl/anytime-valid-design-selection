#!/usr/bin/env python3
"""Predictable-prior ("sharp") bets: does cutting mixture overhead make
TaSC competitive on easy instances while keeping the hard-margin regime?

Mechanism: an e-process factor may be ANY predictable predictive; after a
10-observation warmup each stratum's prior recenters on its running
estimate (kappa=16 pseudo-counts) — validity unchanged, mixture overhead
reduced. kappa and warmup were fixed a priori (no tuning sweep; a two-
point sensitivity row is reported for transparency).

PREDICTION (stated before running): sharp priors save ~1-1.5 nats per
active stratum (~4-6 total for TaSC, ~1-1.5 for single-stream), so
TaSC-sharp at tau=0.15 on gpt-4o-mini should land ~200-230 (vs 324
laplace; champion bonf+directed = 190), and hard-margin times should
shrink ~15-30%.

Arms (like-for-like: same class, only prior_mode differs):
  single-laplace / single-sharp : UICS k=1 on the pooled stream
                                  (iid-mixture assumption, as before)
  TaSC-laplace  / TaSC-sharp    : game allocation + UI stopping

Offline, deterministic. Writes results_sharp.txt.
"""

import hashlib
import io
import os
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

_src = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
mod = types.ModuleType("bench")
mod.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_src, mod.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = mod.STRATA


def run_single(pools, tau, rng, n_max, prior_mode):
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA,
                        prior_mode=prior_mode)
    for n in range(1, n_max + 1):
        pool = pools[STRATA[(n - 1) % 4]]
        cs.update(0, bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0:
            if cs.rejects_ge(tau):
                return "SAFE", n
            if cs.rejects_le(tau):
                return "UNSAFE", n
    return "ABSTAIN", n_max


def run_tasc(pools, tau, rng, n_max, prior_mode, kappa=16.0):
    cs = StratifiedUICS(k=4, alpha=ALPHA, prior_mode=prior_mode,
                        kappa=kappa)
    lam_star = np.full(4, 0.25)
    for step in range(1, n_max + 1):
        n = cs.f + cs.s
        if step <= 8:
            k = (step - 1) % 4
        elif int(np.min(n)) < np.sqrt(step):
            k = int(np.argmin(n))
        else:
            if step % 16 == 0 or step == 9:
                p_hat = (cs.f + 0.5) / (n + 1.0)
                lam_star, _ = mod.game_allocation(p_hat, cs.w, tau)
            k = int(np.argmax(lam_star * step - n))
        pool = pools[STRATA[k]]
        cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        if step >= 20 and step % 4 == 0:
            if cs.rejects_ge(tau):
                return "SAFE", step
            if cs.rejects_le(tau):
                return "UNSAFE", step
    return "ABSTAIN", n_max


def bench(model, fname, tau, truth, n_reps, n_max, sensitivity=False):
    pools = mod.load_pools(fname)
    rates = [float(pools[s].mean()) for s in STRATA]
    p_star = float(np.mean(rates))
    print(f"\n  {model}, tau={tau} (p*={p_star:.4f}, truth {truth}, "
          f"margin {abs(p_star - tau):.3f}):")
    arms = [
        ("single-laplace", lambda p, t, r: run_single(p, t, r, n_max, "laplace")),
        ("single-sharp", lambda p, t, r: run_single(p, t, r, n_max, "sharp")),
        ("TaSC-laplace", lambda p, t, r: run_tasc(p, t, r, n_max, "laplace")),
        ("TaSC-sharp", lambda p, t, r: run_tasc(p, t, r, n_max, "sharp")),
    ]
    if sensitivity:
        arms += [
            ("TaSC-sharp k=8", lambda p, t, r: run_tasc(p, t, r, n_max, "sharp", kappa=8.0)),
            ("TaSC-sharp k=32", lambda p, t, r: run_tasc(p, t, r, n_max, "sharp", kappa=32.0)),
        ]
    for name, fn in arms:
        rng = np.random.default_rng(BASE_SEED + 91)
        outs = [fn(pools, tau, rng) for _ in range(n_reps)]
        correct = [n for d, n in outs if d == truth]
        wrong = sum(1 for d, _ in outs if d not in (truth, "ABSTAIN"))
        abstain = sum(1 for d, _ in outs if d == "ABSTAIN")
        med = int(np.median(correct)) if correct else None
        print(f"    {name:16s}: correct {len(correct)}/{n_reps}, "
              f"wrong {wrong}, abstain {abstain}, median {med}")


def main():
    print("=" * 76)
    print("PREDICTABLE-PRIOR (SHARP) BETS — overhead reduction benchmark")
    print("=" * 76)
    print(f"alpha={ALPHA}, BASE_SEED={BASE_SEED}; kappa=16, warmup=10 "
          "(fixed a priori)")
    print("Reference champions at tau=0.15 (results_ui_grow.txt): "
          "bonf+directed 190 (4o-mini UNSAFE); prior WSR-blocks/single "
          "numbers in results_*.txt.")
    bench("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl",
          0.15, "UNSAFE", 200, 2000, sensitivity=True)
    bench("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
          0.15, "SAFE", 200, 2000)
    bench("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl",
          0.17, "UNSAFE", 100, 4000)
    bench("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl",
          0.18, "UNSAFE", 100, 4000)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_sharp.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_sharp.txt'}")
