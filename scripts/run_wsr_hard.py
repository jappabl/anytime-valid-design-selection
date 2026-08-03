#!/usr/bin/env python3
"""WSR-on-blocks at the hard-margin certification instances.

Companion artifact to results_tasc_hard.txt: the stratify->block->bet
construction (provably valid, results_block_reduction.txt) evaluated on
the same hard instances, same budget, same alpha, so the cross-method
table in FINDINGS can cite checksummed numbers for every arm.

Offline, deterministic. Writes results_wsr_hard.txt.
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

from eval_harness.stats.wsr_block_cs import WSRBlockCS

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 200
N_MAX = 4000


def load(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def certify(pools, tau, truth, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if hi <= tau:
                return "SAFE", 4 * b
            if lo > tau:
                return "UNSAFE", 4 * b
    return "ABSTAIN", N_MAX


def main():
    print("=" * 76)
    print("WSR-ON-BLOCKS AT THE HARD-MARGIN INSTANCES")
    print("=" * 76)
    print(f"alpha={ALPHA}, n_max={N_MAX}, {N_REPS} reps, "
          f"BASE_SEED={BASE_SEED} (rng seed BASE_SEED+71, matching "
          "results_tasc_hard.txt arms)")
    conditions = [
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.17, "UNSAFE"),
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.18, "UNSAFE"),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         0.11, "SAFE"),
    ]
    for model, fname, tau, truth in conditions:
        pools = load(fname)
        p_star = float(np.mean([pools[s].mean() for s in STRATA]))
        rng = np.random.default_rng(BASE_SEED + 71)
        outs = [certify(pools, tau, truth, rng) for _ in range(N_REPS)]
        correct = [n for d, n in outs if d == truth]
        wrong = sum(1 for d, _ in outs if d not in (truth, "ABSTAIN"))
        abstain = sum(1 for d, _ in outs if d == "ABSTAIN")
        med = int(np.median(correct)) if correct else None
        q = ([int(np.percentile(correct, 25)),
              int(np.percentile(correct, 75))] if correct else None)
        print(f"\n  {model}, tau={tau} (p*={p_star:.4f}, truth {truth}): "
              f"correct {len(correct)}/{N_REPS}, wrong {wrong}, "
              f"abstain {abstain}, median {med} {q}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_wsr_hard.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_wsr_hard.txt'}")
