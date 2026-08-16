#!/usr/bin/env python3
"""Stratification rate gain(K) on the ACTUAL committed pools.

Peer correction to F14's quoted magnitude: the commit said V_rr "rises
only ~50% across K=1..24". That figure is real but belongs to the
SYNTHETIC Beta(0.35,1.4) population in derive_optimal_k.py; the peer
measures +7% on a different synthetic population. The magnitude is
population-dependent, so the paper-facing number must come from the
committed pools, reported as a RANGE with each figure attributed.

WHAT IS COMPUTABLE ON REAL POOLS: the committed pools are temp-0 —
per-prompt rates are degenerate 0/1 — so the finest honest
stratification is the four DESIGNED strata. gain(K) is therefore
measured at K in {1, 2, 4}: K=2 merges the two easier and two harder
designed strata (rate-sorted); K=4 is the designed partition. Finer K
needs the temp>0 per-prompt collection (the standing scope caveat,
which this limitation is the concrete form of).

TWO GAINS, both reported:
  - KL gain: V_rr(K) / V_pool at the canonical margin 0.045 (the
    mixture-arm rate object driving K*).
  - variance gain: pbar(1-pbar) / sum_k w_k p_k(1-p_k) (the peer's
    exact decomposition; the WSR-relevant object).
Size-proportional weights throughout (population-mean estimand, K
genuinely free).

WHAT THIS MEASUREMENT OVERTURNED (recorded as the error it caught):
F14's committed claim was UNIVERSAL mixture K* = 1 ("don't stratify"),
generalized from one synthetic Beta(0.35,1.4) population. On the real
pools that claim FAILS on 6 of 10: near-degenerate strata (rates near
0 or 1) carry almost no Bernoulli variance, so real gains run to 4.3x
-- far beyond both synthetic figures (+50% mine, +7% peer's) -- and
the tax no longer always wins. Direct n(K) computation per pool gives
K* = 1 on 4 pools, K* = 2 on 4 (llama3.2-3b certifies 2.8x faster
stratified: 1638 -> 593), K* = 4 on 2. The ORIGINAL pre-registered
finite-interior-K* prediction is thereby CONFIRMED on the four K*=2
pools after being declared failed on the synthetic population. What
survives of F14: the arm-specific tax structure and the tax-vs-
saturating-gain mechanism; where the balance tips is a property of the
POPULATION (its rate dispersion, especially near-boundary mass), not
of the arm alone. RETRACTED: "mixture K*=1 mechanistically explains
UI-domination" -- UI beats single on 6/10 real pools; UI is dominated
in the partition because WSR beats it everywhere measured (the WSR
anti-result), not because single does.

Offline, deterministic. Writes results_gain.txt.
"""

import hashlib
import io
import json
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

_ug = open(REPO / "scripts" / "run_ui_grow.py").read()
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug.rsplit("if __name__", 1)[0], bench.__dict__)

_ok = open(REPO / "scripts" / "derive_optimal_k.py").read()
ok = types.ModuleType("ok")
ok.__dict__["__file__"] = str(REPO / "scripts" / "derive_optimal_k.py")
exec(_ok.rsplit("def main", 1)[0], ok.__dict__)

MARGIN = 0.045
L = float(np.log(1 / 0.05))


def crossing_n(V, d):
    if V <= 0:
        return np.inf
    try:
        return brentq(lambda n: n * V - L - 0.5 * d * np.log(n),
                      4.0, 1e9)
    except ValueError:
        return np.inf

POOLS = [
    ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl"),
    ("llama3.2-3b", "llm_outcomes_diverse_json_llama3.2-3b.jsonl"),
    ("qwen2.5-7b", "llm_outcomes_diverse_json_qwen2.5-7b.jsonl"),
    ("llama3.1-8b", "llm_outcomes_diverse_json_llama3.1-8b.jsonl"),
    ("llama3-8b", "llm_outcomes_diverse_json_llama3-8b.jsonl"),
    ("qwen2-7b", "llm_outcomes_diverse_json_qwen2-7b.jsonl"),
    ("mistral-7b", "llm_outcomes_diverse_json_mistral-7b.jsonl"),
    ("gemma2-9b", "llm_outcomes_diverse_json_gemma2-9b.jsonl"),
    ("phi3.5-3.8b", "llm_outcomes_diverse_json_phi3.5-3.8b.jsonl"),
    ("deepseek-7b", "llm_outcomes_diverse_json_deepseek-llm-7b.jsonl"),
]


def load(fname):
    path = REPO / "data" / fname
    if not path.exists():
        return None
    pools = {}
    for line in open(path):
        r = json.loads(line)
        pools.setdefault(r["stratum"], []).append(0 if r["passed"] else 1)
    return pools


def merged(rates, weights, K):
    """Merge rate-sorted strata into K groups (size-weighted)."""
    order = np.argsort(rates)
    groups = np.array_split(order, K)
    r, w = [], []
    for g in groups:
        wt = weights[g].sum()
        r.append(float(np.sum(rates[g] * weights[g]) / wt))
        w.append(float(wt))
    return np.array(r), np.array(w)


def main():
    print("=" * 76)
    print("STRATIFICATION GAIN ON THE COMMITTED POOLS (peer correction "
          "to F14's magnitude)")
    print("=" * 76)
    print(f"margin {MARGIN}, size-proportional weights, K in {{1,2,4}} "
          f"(temp-0 pools: designed strata are the finest honest "
          f"partition)\n")
    print(f"  {'pool':<13} {'mu':>7} {'KLg(2)':>7} {'KLg(4)':>7} "
          f"{'varg(4)':>8}   n(K) and K*")
    kl4s, var4s, kstars = [], [], []
    for name, fname in POOLS:
        pools = load(fname)
        if pools is None:
            print(f"  {name:<13} — not collected, skipped")
            continue
        rates = np.array([np.mean(v) for v in pools.values()])
        sizes = np.array([len(v) for v in pools.values()], dtype=float)
        w = sizes / sizes.sum()
        mu = float(np.sum(w * rates))
        tau = mu - MARGIN
        if tau <= 0.005:
            print(f"  {name:<13} {mu:>7.4f} — margin exceeds mu, skipped")
            continue
        v_pool = bench.kl_bern(mu, tau)
        gains_kl = {}
        for K in (2, 4):
            r, wk = merged(rates, w, K)
            gains_kl[K] = ok.v_rr_K(r, wk, tau) / v_pool
        var_pool = mu * (1 - mu)
        var_within = float(np.sum(w * rates * (1 - rates)))
        var_gain = var_pool / var_within
        kl4s.append(gains_kl[4])
        var4s.append(var_gain)
        ns = {}
        for K in (1, 2, 4):
            if K == 1:
                V = v_pool
            else:
                r2, w2 = merged(rates, w, K)
                V = ok.v_rr_K(r2, w2, tau)
            ns[K] = crossing_n(V, K)
        kstar = min(ns, key=ns.get)
        kstars.append(kstar)
        print(f"  {name:<13} {mu:>7.4f} {gains_kl[2]:>7.3f} "
              f"{gains_kl[4]:>7.3f} {var_gain:>8.3f}  "
              f"n(1/2/4)={ns[1]:.0f}/{ns[2]:.0f}/{ns[4]:.0f} K*={kstar}")

    from collections import Counter
    kc = Counter(kstars)
    print(f"""
  RANGE across committed pools (K=4 vs pooled):
    KL gain  V_rr/V_pool: {min(kl4s):.3f} - {max(kl4s):.3f}
    variance gain:        {min(var4s):.3f} - {max(var4s):.3f}
  Saturation: NOT uniform — most gain arrives by K=2 on some pools
  (llama3.2: 3.87 of 4.31) but between K=2 and K=4 on others
  (qwen2.5: 1.51 -> 3.33; gemma2: 1.63 -> 3.25). Finer-K behavior
  needs temp>0 per-prompt rates (standing scope caveat; the temp-0
  degeneracy is its concrete form).

  K* CENSUS (mixture arm, real pools): {dict(kc)} — K* = 1 on
  {kc[1]}/10, INTERIOR K* = 2 on {kc[2]}/10, K* = 4 (range boundary)
  on {kc[4]}/10.

  VERDICT: F14's universal "mixture K* = 1" is REFUTED on 6 of 10
  committed pools — it was a synthetic-population artifact (both the
  +50% and +7% synthetic gains are far below the real 1.06-4.31 range,
  because real pools concentrate mass in near-boundary strata that
  carry almost no variance). The pre-registered finite-interior-K*
  prediction is CONFIRMED on the 4 pools with K* = 2. The arm-specific
  tax structure survives; where the tax-vs-gain balance tips is a
  POPULATION property. RETRACTED: "K*=1 explains UI-domination" — UI
  beats single on 6/10 real pools; UI is dominated because WSR beats
  it everywhere measured, not because single does.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_gain.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_gain.txt'}")
