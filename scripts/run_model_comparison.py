#!/usr/bin/env python3
"""Anytime-valid sequential model comparison (paired, same prompts).

Because all models were evaluated on the SAME 1000 prompts, we can run a
paired sequential comparison — an anytime-valid analogue of McNemar's
test. At each step a prompt is drawn uniformly at random; if the two
models disagree on it (exactly one fails), the discordant outcome updates
a betting CS on

    theta = P(model A fails and B passes | models disagree).

Certify "B better than A" when LCB(theta) > 0.5, "A better" when
UCB(theta) < 0.5. Concordant prompts carry no information and only cost
sampling budget. Ground truth theta is computed exactly from the pools.

Pairs tested:
  gpt-4o-mini vs gpt-4.1-nano  (expected: nano better)
  gpt-4o-mini vs gpt-4.1-mini  (expected: mini better)
  gpt-4.1-nano vs gpt-4.1-mini (near-identical: the method SHOULD abstain
                                rather than manufacture a difference)

Offline, deterministic (BASE_SEED=42). Writes results_model_comparison.txt.
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
N_REPS = 500
MAX_DRAWS = 4000
MIN_DISCORDANT = 5

MODELS = {
    "gpt-4o-mini": REPO / "data" / "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
}


def load_outcomes(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            rec = json.loads(line)
            out[rec["id"]] = 0 if rec["passed"] else 1  # 1 = failure
    return out


_cache = {}


def bounds(f, s):
    if (f, s) not in _cache:
        _cache[(f, s)] = betting_bounds(f, s, ALPHA)
    return _cache[(f, s)]


def compare(ids, out_a, out_b, label_a, label_b):
    # Exact ground truth over the pool
    a_only = sum(1 for i in ids if out_a[i] == 1 and out_b[i] == 0)
    b_only = sum(1 for i in ids if out_a[i] == 0 and out_b[i] == 1)
    disc = a_only + b_only
    theta = a_only / disc if disc else 0.5
    if theta > 0.5:
        truth = f"{label_b} better"
    elif theta < 0.5:
        truth = f"{label_a} better"
    else:
        truth = "tie"

    print(f"{label_a} vs {label_b}:")
    print(f"  pool ground truth: {label_a} uniquely fails {a_only}, "
          f"{label_b} uniquely fails {b_only} "
          f"(theta={theta:.3f}, {disc} discordant prompts of {len(ids)})")

    decisions = {}
    times, disc_counts = [], []
    wrong = 0
    rng = np.random.default_rng(BASE_SEED + 21)
    id_list = list(ids)
    for rep in range(N_REPS):
        f = s = 0  # f = A-fails-B-passes count, s = B-fails-A-passes count
        decision, t = "ABSTAIN", MAX_DRAWS
        for n in range(1, MAX_DRAWS + 1):
            pid = id_list[int(rng.integers(0, len(id_list)))]
            xa, xb = out_a[pid], out_b[pid]
            if xa == xb:
                continue
            if xa == 1:
                f += 1
            else:
                s += 1
            if f + s >= MIN_DISCORDANT:
                lo, hi = bounds(f, s)
                if lo > 0.5:
                    decision, t = f"{label_b} better", n
                    break
                if hi < 0.5:
                    decision, t = f"{label_a} better", n
                    break
        decisions[decision] = decisions.get(decision, 0) + 1
        if decision != "ABSTAIN":
            times.append(t)
            disc_counts.append(f + s)
            if truth != "tie" and decision != truth:
                wrong += 1

    for d, c in sorted(decisions.items()):
        print(f"  decision '{d}': {c}/{N_REPS}")
    if times:
        print(f"  median prompts examined: {int(np.median(times))}, "
              f"median discordant used: {int(np.median(disc_counts))}")
    print(f"  wrong decisions: {wrong}")
    print()


def main():
    outcomes = {m: load_outcomes(p) for m, p in MODELS.items()}
    ids = sorted(set.intersection(*[set(v) for v in outcomes.values()]))

    print("=" * 76)
    print("ANYTIME-VALID PAIRED MODEL COMPARISON (sequential McNemar)")
    print("=" * 76)
    print(f"Shared prompts: {len(ids)}; alpha={ALPHA}; "
          f"max draws {MAX_DRAWS}; {N_REPS} reps; BASE_SEED={BASE_SEED}")
    print("Certify only when LCB>0.5 or UCB<0.5 on the discordant stream.\n")

    compare(ids, outcomes["gpt-4o-mini"], outcomes["gpt-4.1-nano"],
            "gpt-4o-mini", "gpt-4.1-nano")
    compare(ids, outcomes["gpt-4o-mini"], outcomes["gpt-4.1-mini"],
            "gpt-4o-mini", "gpt-4.1-mini")
    compare(ids, outcomes["gpt-4.1-nano"], outcomes["gpt-4.1-mini"],
            "gpt-4.1-nano", "gpt-4.1-mini")

    # Constructed EXACT tie (synthetic, labeled): start from the gpt-4o-mini
    # outcomes and build a counterpart that disagrees on 60 prompts, 30 in
    # each direction (theta = 0.5 exactly). Tests that the procedure
    # abstains rather than manufacturing a winner on a true tie.
    base = outcomes["gpt-4o-mini"]
    fails = [i for i in ids if base[i] == 1][:30]
    passes = [i for i in ids if base[i] == 0][:30]
    twin = dict(base)
    for i in fails:
        twin[i] = 0   # twin passes where base fails (30 prompts)
    for i in passes:
        twin[i] = 1   # twin fails where base passes (30 prompts)
    compare(ids, base, twin, "base", "twin (synthetic exact tie)")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_model_comparison.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_model_comparison.txt'}")
