#!/usr/bin/env python3
"""Finer-K optimal stratification on REAL per-prompt rates (temp>0 pools).

F14's K<=4 ceiling came from temp-0 degeneracy. The temp>0 pools
(collect_temp_pools.py: 200 prompts x 24 seeded draws at temp 0.7)
give real per-prompt rates, so quantile stratification is honest up to
K ~ 12. This is the proper test of the finite-interior-K* mechanism.

SPLIT-DRAWS RULE (frozen at collection): EVEN draw indices are the
STRATIFICATION SIGNAL, ODD draws are the EVALUATION pool. The signal
is an independent noisy difficulty estimate; stratifying and
evaluating on the same draws would self-select.

METHOD per model: signal rate per prompt from even draws (12); prompts
quantile-binned into K equal groups by signal rate; stratum rates
computed from ODD draws only; V_rr(K) at the canonical margin 0.045
below the evaluation-pool mean; crossing n(K) from the expansion with
d = K; K* = argmin over K in {1, 2, 3, 4, 6, 8, 12}.

PRE-REGISTERED (mechanism expectations from F14, stated before any
table):
  P1 SIGNAL VALIDITY: per-prompt signal-vs-evaluation rate correlation
     r > 0.5 on both pools (else the quantile strata are noise and the
     sweep is vacuous — artifact declares itself INVALID for that
     pool).
  P2 FINITE INTERIOR K*: 1 < K* < 12 on both pools — the tax-vs-
     saturating-gain mechanism predicts stratification pays at genuine
     per-prompt resolution but the (K/2)log n tax still forces a
     finite optimum. K* = 1 or K* = 12 (range edge) scores a MISS.
REPORTED, NOT SCORED (cross-population, temp and subset differ): how
K* and the gain compare to the designed-strata census (llama3.2 was
K* = 2, qwen2.5 K* = 4 at the K<=4 ceiling).

Offline, deterministic. Writes results_temp_k.txt.
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
KS = [1, 2, 3, 4, 6, 8, 12]
POOLS = [("llama3.2-3b", "llm_temp_outcomes_llama3.2-3b.jsonl"),
         ("qwen2.5-7b", "llm_temp_outcomes_qwen2.5-7b.jsonl")]


def crossing_n(V, d):
    if V <= 0:
        return np.inf
    try:
        return brentq(lambda n: n * V - L - 0.5 * d * np.log(n),
                      4.0, 1e9)
    except ValueError:
        return np.inf


def load(fname):
    sig, ev = {}, {}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        d = sig if r["draw"] % 2 == 0 else ev
        d.setdefault(r["id"], []).append(0 if r["passed"] else 1)
    ids = sorted(set(sig) & set(ev))
    s = np.array([np.mean(sig[i]) for i in ids])
    e = np.array([np.mean(ev[i]) for i in ids])
    return ids, s, e


def main():
    print("=" * 76)
    print("FINER-K OPTIMAL STRATIFICATION ON TEMP>0 PER-PROMPT RATES")
    print("=" * 76)
    print(f"margin {MARGIN}, split-draws (even=signal, odd=eval), "
          f"K grid {KS}\n")
    p1_all, p2_all = True, True
    for name, fname in POOLS:
        ids, s, e = load(fname)
        r = float(np.corrcoef(s, e)[0, 1])
        mu = float(e.mean())
        tau = mu - MARGIN
        print(f"  {name}: {len(ids)} prompts, eval mu = {mu:.4f}, "
              f"signal-vs-eval corr r = {r:.3f} "
              f"({'P1 PASS' if r > 0.5 else 'P1 FAIL — INVALID pool'})")
        p1_all &= (r > 0.5)
        if r <= 0.5 or tau <= 0.005:
            if tau <= 0.005:
                print(f"    margin exceeds mu — skipped")
            continue
        order = np.argsort(s)
        ns = {}
        print(f"    {'K':>3} {'V(K)':>9} {'gain':>6} {'n(K)':>9}")
        v1 = bench.kl_bern(mu, tau)
        for K in KS:
            if K == 1:
                V = v1
            else:
                groups = np.array_split(order, K)
                rates = np.array([float(e[g].mean()) for g in groups])
                w = np.array([len(g) / len(order) for g in groups])
                rates = np.clip(rates, 1e-4, 1 - 1e-4)
                V = ok.v_rr_K(rates, w, tau)
            ns[K] = crossing_n(V, K)
            print(f"    {K:>3} {V:>9.5f} {V / v1:>6.3f} {ns[K]:>9.0f}")
        kstar = min(ns, key=ns.get)
        interior = 1 < kstar < 12
        p2_all &= interior
        print(f"    -> K* = {kstar} "
              f"({'P2 PASS: finite interior' if interior else 'P2 MISS: range edge'}); "
              f"designed-strata census gave "
              f"{'K*=2' if 'llama' in name else 'K*=4 (at the K<=4 ceiling)'} "
              f"[reported, not scored — different temp/subset]\n")

    print(f"  P1 signal validity both pools: "
          f"{'PASS' if p1_all else 'FAIL'}")
    print(f"  P2 finite interior K* both pools: "
          f"{'PASS' if p2_all else 'MISS — reportable'}")
    print("""
  READING: with genuine per-prompt rates and an independent
  stratification signal, this is the clean form of the F14 question.
  A finite interior K* here is the mechanism's honest confirmation at
  real resolution; a range-edge K* is a reportable miss. Scope: two
  models, one task family, temp 0.7, 200-prompt subset.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_temp_k.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_temp_k.txt'}")
