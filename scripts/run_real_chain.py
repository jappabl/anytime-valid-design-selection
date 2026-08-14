#!/usr/bin/env python3
"""Warm-start chaining on REAL release trajectories (ISEF_PLAN 1.2).

Replaces the synthetic 6-epoch trajectory with actual model version
history collected on the same prompts and validator:

  Meta:    llama3-8b (.609) -> llama3.1-8b (.267) -> llama3.2-3b (.483)
  Alibaba: qwen2-7b (.389)  -> qwen2.5-7b (.297)

Measured real inter-release drifts are 0.09-0.34 pooled — an order of
magnitude beyond the +/-0.015-0.03 staleness budget measured in
results_warmstart_drift.txt. This experiment therefore tests the
warm-start arc's honest SCOPE, not its best case.

Arms per lineage (same protocol as run_warmstart_chain.py: epoch 1
cold, later epochs warm from the previous epoch's own stopped-run
estimates; per-rep CRN; both decision directions active):
  cold UI, chain-warm, chain-warm+shade(0.015), WSR blocks.
Thresholds chosen so the truth flips inside each chain:
  Meta tau = 0.35  (UNSAFE -> SAFE -> UNSAFE)
  Qwen tau = 0.34  (UNSAFE -> SAFE)

PRE-REGISTERED PREDICTIONS (from the drift table + contamination
floor; stated before running):
  P1 zero wrong certifications, all arms, all epochs (validity is
     prior-independent).
  P2 SCOPE RESULT: at these drifts the warm prior is saturated —
     chain-warm (shaded or not) within [0.9, 1.4]x of COLD at every
     post-jump epoch (the eps floor caps damage; no real help).
  P3 shade changes little here: |shaded/unshaded - 1| <= 0.10 at every
     epoch (drift >> shade size).
  P4 WSR wins every lineage total (its trajectory robustness held on
     synthetic chains at a fraction of these drifts).

Offline, deterministic. Writes results_real_chain.txt.
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

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402

_src = open(REPO / "scripts" / "run_warmstart_chain.py").read()
wc = types.ModuleType("wc")
wc.__dict__["__file__"] = str(REPO / "scripts" / "run_warmstart_chain.py")
exec(_src.rsplit('if __name__', 1)[0], wc.__dict__)

_r1 = open(REPO / "scripts" / "run_router.py").read()
r1 = types.ModuleType("r1")
r1.__dict__["__file__"] = str(REPO / "scripts" / "run_router.py")
exec(_r1.rsplit('if __name__', 1)[0], r1.__dict__)

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 200
STRATA = ["simple", "medium", "complex", "extreme"]
SHADE = 0.015
CHAINS = {
    "Meta (tau=0.35)": (0.35, [
        "llm_outcomes_diverse_json_llama3-8b.jsonl",
        "llm_outcomes_diverse_json_llama3.1-8b.jsonl",
        "llm_outcomes_diverse_json_llama3.2-3b.jsonl"]),
    "Alibaba (tau=0.34)": (0.34, [
        "llm_outcomes_diverse_json_qwen2-7b.jsonl",
        "llm_outcomes_diverse_json_qwen2.5-7b.jsonl"]),
}


def load(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def run_epoch(pools_e, tau, rng, make_cs, n_max=6000):
    cs = make_cs()
    nk = np.zeros(4, dtype=int)
    fk = np.zeros(4, dtype=int)
    for n in range(1, n_max + 1):
        k = (n - 1) % 4
        s = STRATA[k]
        y = bool(pools_e[s][int(rng.integers(0, len(pools_e[s])))])
        cs.update(k, y)
        nk[k] += 1
        fk[k] += int(y)
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(tau):
                return "UNSAFE", n, nk, fk
            if cs.rejects_ge(tau):
                return "SAFE", n, nk, fk
    return "ABSTAIN", n_max, nk, fk


def run_wsr(pools_e, tau, rng, n_max=6000):
    from eval_harness.stats.wsr_block_cs import WSRBlockCS
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, n_max // 4 + 1):
        m = float(np.mean([pools_e[s][int(rng.integers(0, len(pools_e[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > tau:
                return "UNSAFE", 4 * b
            if hi <= tau:
                return "SAFE", 4 * b
    return "ABSTAIN", n_max


def main():
    print("=" * 76)
    print("WARM-START ON REAL RELEASE TRAJECTORIES (predictions "
          "pre-registered in header)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps, n_max=6000, shade={SHADE}, "
          f"BASE_SEED={BASE_SEED}\n")

    total_wrong = 0
    for label, (tau, files) in CHAINS.items():
        chain_pools = [load(f) for f in files]
        emp = [np.array([float(p[s].mean()) for s in STRATA])
               for p in chain_pools]
        truths = ["UNSAFE" if float(r.mean()) > tau else "SAFE"
                  for r in emp]
        n_epochs = len(chain_pools)
        print(f"  {label}: pooled "
              f"{[round(float(r.mean()), 3) for r in emp]} "
              f"truths {truths}")

        arms = ["cold UI", "chain-warm", "chain-warm shaded", "WSR"]
        stats = {a: [[] for _ in range(n_epochs)] for a in arms}
        for rep in range(N_REPS):
            rngs = {a: np.random.default_rng(BASE_SEED + 104729 + rep)
                    for a in arms}
            state = {a: (None, None) for a in
                     ["chain-warm", "chain-warm shaded"]}
            for e in range(n_epochs):
                d, n, _, _ = run_epoch(
                    chain_pools[e], tau, rngs["cold UI"],
                    lambda: StratifiedUICS(k=4, alpha=ALPHA))
                stats["cold UI"][e].append((d, n))
                for a in ["chain-warm", "chain-warm shaded"]:
                    pr, pk = state[a]
                    if pr is None:
                        mk = lambda: StratifiedUICS(k=4, alpha=ALPHA)
                    else:
                        center = pr if a == "chain-warm" else np.clip(
                            pr - SHADE, 1e-3, 1 - 1e-3)
                        mk = (lambda c_=center, k_=pk:
                              wc.wj.TransferPriorJointUICS(
                                  c_, kappa=np.minimum(k_, 200.0)))
                    d2, n2, nk2, fk2 = run_epoch(
                        chain_pools[e], tau, rngs[a], mk)
                    stats[a][e].append((d2, n2))
                    state[a] = ((fk2 + 0.5) / (nk2 + 1.0),
                                nk2.astype(float))
                stats["WSR"][e].append(
                    run_wsr(chain_pools[e], tau, rngs["WSR"]))

        meds = {a: [] for a in arms}
        for e in range(n_epochs):
            print(f"    epoch {e + 1} (truth {truths[e]}, pooled "
                  f"{emp[e].mean():.3f}):")
            for a in arms:
                outs = stats[a][e]
                dec = [n for d, n in outs if d == truths[e]]
                wrong = sum(1 for d, _ in outs
                            if d not in (truths[e], "ABSTAIN"))
                ab = sum(1 for d, _ in outs if d == "ABSTAIN")
                total_wrong += wrong
                med = int(np.median(dec)) if dec else None
                meds[a].append(med)
                print(f"      {a:18s}: correct {len(dec):3d}/{N_REPS}, "
                      f"wrong {wrong}, abstain {ab:3d}, median "
                      f"{med if med else '--'}")
        print("    scoring:")
        for e in range(1, n_epochs):
            for a in ["chain-warm", "chain-warm shaded"]:
                if meds[a][e] and meds["cold UI"][e]:
                    r = meds[a][e] / meds["cold UI"][e]
                    print(f"      epoch {e + 1} {a}/cold = {r:.2f} "
                          f"(P2 window [0.9, 1.4]: "
                          f"{'PASS' if 0.9 <= r <= 1.4 else 'FAIL'})")
            if meds["chain-warm shaded"][e] and meds["chain-warm"][e]:
                rs = meds["chain-warm shaded"][e] / meds["chain-warm"][e]
                print(f"      epoch {e + 1} shade effect {rs:.2f} "
                      f"(P3 |r-1| <= 0.10: "
                      f"{'PASS' if abs(rs - 1) <= 0.10 else 'FAIL'})")
        tot = {a: sum(m for m in meds[a] if m) for a in arms}
        best = min(tot, key=tot.get)
        print(f"    totals {tot} -> best: {best} (P4 WSR wins: "
              f"{'PASS' if best == 'WSR' else 'FAIL'})")
        print()

    print(f"  P1 wrong certifications, all chains/arms/epochs: "
          f"{total_wrong}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_real_chain.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_real_chain.txt'}")
