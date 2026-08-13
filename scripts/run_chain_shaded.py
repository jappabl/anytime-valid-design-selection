#!/usr/bin/env python3
"""Shade deployed in the epoch chain (the win's natural habitat).

Measured basis: the 6-epoch improving-model chain makes every prior
systematically ALARMIST (each epoch's estimates overstate the next
epoch's rates by ~0.03 pooled — exactly the expensive direction per
the drift table), and the flat-shade win halves the cost of that
direction. Deployment claim to test: shading the chained estimates
recovers most of the alarmist tax.

Arms (same trajectory/protocol as run_warmstart_chain.py):
  chain-warm            unshaded chained estimates (control; banked)
  chain-warm shaded     estimates shaded down 0.015
  chain-extrap shaded   epoch >= 3 centers on the one-step drift
                        extrapolation, then shades 0.015 (router v2
                        showed extrapolation fails for ROUTING under
                        cliffs; as a PRIOR CENTER on this smooth
                        trajectory it should help — stated as a
                        genuine risk, this trajectory has no cliff).

PRE-REGISTERED PREDICTIONS (from the drift table arithmetic):
  P1 zero wrong certifications, all arms, all epochs.
  P2 shaded beats unshaded chain-warm at every epoch >= 2 (median
     among correct), and by >= 1.5x at epoch 3 (where the alarmist
     prior points hardest against the drift).
  P3 flip-epoch deciding power: shaded correct counts at epochs 3-4
     each >= 1.3x unshaded's.
  P4 extrap-shaded <= 0.90x shaded medians at epochs 3-4 (drift
     tracking helps most near the boundary), and never worse than
     1.10x shaded at epochs 5-6.

Offline, deterministic. Writes results_chain_shaded.txt.
"""

import hashlib
import io
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

BASE_SEED = wc.BASE_SEED
ALPHA = wc.ALPHA
TAU = wc.TAU
N_REPS = 200
N_EPOCHS = wc.N_EPOCHS
STRATA = wc.STRATA
SHADE = 0.015


def main():
    pool_rng = np.random.default_rng(BASE_SEED + 271828)
    pools, emp_rates = wc.make_pools(pool_rng)
    truths = ["UNSAFE" if float(r.mean()) > TAU else "SAFE"
              for r in emp_rates]

    print("=" * 76)
    print("SHADED CHAIN WARM-START (predictions pre-registered in header)")
    print("=" * 76)
    print(f"tau={TAU}, alpha={ALPHA}, shade={SHADE}, {N_REPS} reps, "
          f"n_max={wc.N_MAX}, pools {wc.POOL_N}/stratum, "
          f"BASE_SEED={BASE_SEED}\n")

    arms = ["chain-warm", "shaded", "extrap-shaded"]
    stats = {a: [[] for _ in range(N_EPOCHS)] for a in arms}

    for rep in range(N_REPS):
        rngs = {a: np.random.default_rng(BASE_SEED + 104729 + rep)
                for a in arms}
        state = {a: {"rates": None, "kappa": None, "hist": []}
                 for a in arms}
        for e in range(N_EPOCHS):
            for a in arms:
                st = state[a]
                if st["rates"] is None:
                    mk = lambda: StratifiedUICS(k=4, alpha=ALPHA)
                else:
                    center = st["rates"]
                    if a == "extrap-shaded" and len(st["hist"]) >= 2:
                        center = np.clip(
                            st["hist"][-1]
                            + (st["hist"][-1] - st["hist"][-2]),
                            1e-3, 1 - 1e-3)
                    if a in ("shaded", "extrap-shaded"):
                        center = np.clip(center - SHADE, 1e-3, 1 - 1e-3)
                    pr, pk = center, st["kappa"]
                    mk = lambda p_=pr, k_=pk: wc.wj.TransferPriorJointUICS(
                        p_, kappa=np.minimum(k_, 200.0))
                d, n, nk, fk = wc.run_epoch(pools[e], rngs[a], mk)
                stats[a][e].append((d, n))
                est = (fk + 0.5) / (nk + 1.0)
                st["hist"].append(est)
                st["rates"] = est
                st["kappa"] = nk.astype(float)

    total_wrong = 0
    meds = {a: [] for a in arms}
    corr = {a: [] for a in arms}
    for e in range(N_EPOCHS):
        print(f"  epoch {e+1} (truth {truths[e]}, pooled "
              f"{emp_rates[e].mean():.4f}):")
        for a in arms:
            outs = stats[a][e]
            dec = [n for d, n in outs if d == truths[e]]
            wrong = sum(1 for d, _ in outs
                        if d not in (truths[e], "ABSTAIN"))
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            total_wrong += wrong
            med = int(np.median(dec)) if dec else None
            meds[a].append(med)
            corr[a].append(len(dec))
            print(f"    {a:14s}: correct {len(dec):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median "
                  f"{med if med else '--'}")
        print()

    print("PRE-REGISTERED SCORING:")
    p2 = all(meds["shaded"][e] < meds["chain-warm"][e]
             for e in range(1, N_EPOCHS)
             if meds["shaded"][e] and meds["chain-warm"][e])
    r3 = (meds["chain-warm"][2] / meds["shaded"][2]
          if meds["shaded"][2] and meds["chain-warm"][2] else None)
    print(f"  P2 shaded < unshaded at every epoch >= 2? "
          f"{'PASS' if p2 else 'FAIL'}; epoch-3 speedup "
          f"{r3:.2f}x (>=1.5? "
          f"{'PASS' if r3 and r3 >= 1.5 else 'FAIL'})")
    ok3 = corr["shaded"][2] >= 1.3 * corr["chain-warm"][2]
    ok4 = corr["shaded"][3] >= 1.3 * corr["chain-warm"][3]
    print(f"  P3 flip-epoch correct counts: e3 {corr['shaded'][2]} vs "
          f"{corr['chain-warm'][2]} ({'PASS' if ok3 else 'FAIL'}); "
          f"e4 {corr['shaded'][3]} vs {corr['chain-warm'][3]} "
          f"({'PASS' if ok4 else 'FAIL'})")
    r34 = [meds["extrap-shaded"][e] / meds["shaded"][e]
           for e in (2, 3) if meds["extrap-shaded"][e] and meds["shaded"][e]]
    r56 = [meds["extrap-shaded"][e] / meds["shaded"][e]
           for e in (4, 5) if meds["extrap-shaded"][e] and meds["shaded"][e]]
    p4a = all(r <= 0.90 for r in r34) if r34 else False
    p4b = all(r <= 1.10 for r in r56) if r56 else False
    print(f"  P4 extrap-shaded: e3-e4 ratios "
          f"{[f'{r:.2f}' for r in r34]} (<=0.90? "
          f"{'PASS' if p4a else 'FAIL'}); e5-e6 "
          f"{[f'{r:.2f}' for r in r56]} (<=1.10? "
          f"{'PASS' if p4b else 'FAIL'})")
    print(f"  P1 wrong certifications: {total_wrong}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_chain_shaded.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_chain_shaded.txt'}")
