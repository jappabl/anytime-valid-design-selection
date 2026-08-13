#!/usr/bin/env python3
"""Second-order refinements of the asymmetric-prior win.

results_asym_prior.txt banked the win: flat shade-down 0.015 halves
the worst-case staleness cost. The MECHANISM behind it is per-stratum
(zero-rate strata absorb downward error via clipping; a flat shade is
0.48 prior-sd on the hot stratum but oversized relative to tiny
strata's scales), so two refinements are designed from that mechanism
— NOT iterated against results:

  arm "prop-shade": shade_k = min(0.5 * p_k, sqrt(p_k (1-p_k)/kappa))
      — one prior standard deviation per stratum, capped at half the
      rate (deeper shade exactly where the prior has room to be wrong).
  arm "kappa-ladder": 0.6 at flat-shaded kappa=200, 0.3 at the
      UNSHADED prior with kappa=20, 0.1 uniform — the drift table's
      saturation shape says damage comes from being CONFIDENTLY wrong,
      so a medium-resolution component gives a soft landing between
      kappa=200 and kappa=1.
  controls: baseline joint (no shade) and flat-shade 0.015 (the
      banked win).

Same protocol as run_asym_prior.py: gpt-4o-mini pools, tau=0.16,
true-drift grid {-0.03,-0.015,0,+0.015,+0.03} on all strata, per-rep
CRN, 200 reps, n_max 6000.

PRE-REGISTERED PREDICTIONS (from mechanism arithmetic, stated before
running; the flat-shade win is already banked — losses here are
logged and flat-shade stands):
  P1 zero wrong certifications everywhere.
  P2 prop-shade: <= 0.95x flat-shade at delta=+0.03; within [0.97,
     1.05]x flat-shade at benign; <= 1.10x flat-shade at -0.03.
  P3 kappa-ladder: best worst-case over the grid of ALL arms,
     <= 0.90x flat-shade's worst case, at <= 1.10x baseline benign.
  P4 sanity: flat-shade control reproduces the banked pattern
     (worst case <= 0.55x baseline).

Offline, deterministic. Writes results_shade_refine.txt.
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

_src = open(REPO / "scripts" / "run_asym_prior.py").read()
ap = types.ModuleType("ap")
ap.__dict__["__file__"] = str(REPO / "scripts" / "run_asym_prior.py")
exec(_src.rsplit('if __name__', 1)[0], ap.__dict__)

wj = ap.wj
MultiCenterJointUICS = ap.MultiCenterJointUICS
BASE_SEED = ap.BASE_SEED
ALPHA = ap.ALPHA
TAU = ap.TAU
N_REPS = 200
KAPPA = ap.KAPPA
STRATA = ap.STRATA
DELTAS = ap.DELTAS


def main():
    pools = wj.load(REPO / "data" / "llm_outcomes_diverse_json.jsonl")
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    lam = np.full(4, 0.25)
    w4 = np.full(4, 0.25)
    m = wj.bench._inner_min(lam, rates, w4, TAU)
    v_rr = float(np.sum(lam * [wj.bench.kl_bern(rates[i], m[i])
                               for i in range(4)]))
    log1a = np.log(1 / ALPHA)

    print("=" * 76)
    print("SHADE REFINEMENTS (predictions pre-registered in header)")
    print("=" * 76)
    print(f"tau={TAU} (V_rr={v_rr:.4f}), kappa={KAPPA:.0f}, "
          f"alpha={ALPHA}, {N_REPS} reps, n_max={wj.N_MAX}, "
          f"BASE_SEED={BASE_SEED}\n")

    def flat(pr):
        return np.clip(np.asarray(pr) - 0.015, 1e-3, 1 - 1e-3)

    def prop(pr):
        pr = np.asarray(pr)
        sd = np.sqrt(pr * (1 - pr) / KAPPA)
        return np.clip(pr - np.minimum(0.5 * pr, sd), 1e-3, 1 - 1e-3)

    meds = {}
    for delta in DELTAS:
        prior = np.clip(rates + delta, 1e-3, 1 - 1e-3)
        arms = [
            ("baseline joint", [(0.9, prior), (0.1, None)], KAPPA),
            ("flat-shade", [(0.9, flat(prior)), (0.1, None)], KAPPA),
            ("prop-shade", [(0.9, prop(prior)), (0.1, None)], KAPPA),
            ("kappa-ladder", None, None),   # built below (mixed kappas)
        ]
        print(f"  true-drift delta={delta:+.3f}:")
        for name, comps, kap in arms:
            if name == "kappa-ladder":
                mk = lambda: _ladder(prior)
            else:
                mk = lambda c=comps, k=kap: MultiCenterJointUICS(
                    c, kappa=k)
            outs = [wj.run_arm(pools, TAU,
                               np.random.default_rng(
                                   BASE_SEED + 7919 + 1000 * rep), mk)
                    for rep in range(N_REPS)]
            ok = [n for d, n in outs if d == "UNSAFE"]
            wrong = sum(1 for d, _ in outs if d == "SAFE")
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(ok)) if ok else None
            meds[(delta, name)] = med
            oh = f"{med * v_rr - log1a:+.2f}" if med else "--"
            print(f"    {name:14s}: certified {len(ok):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median {med}, "
                  f"overhead {oh} nats")
        print()

    def _worst(name):
        return max(meds[(d, name)] for d in DELTAS)

    print("PRE-REGISTERED SCORING:")
    b_flat = meds[(0.0, "flat-shade")]
    r_up = meds[(0.03, "prop-shade")] / meds[(0.03, "flat-shade")]
    r_be = meds[(0.0, "prop-shade")] / b_flat
    r_dn = meds[(-0.03, "prop-shade")] / meds[(-0.03, "flat-shade")]
    print(f"  P2 prop-shade: +0.03 {r_up:.2f}x flat (<=0.95? "
          f"{'PASS' if r_up <= 0.95 else 'FAIL'}); benign {r_be:.2f}x "
          f"(in [0.97,1.05]? "
          f"{'PASS' if 0.97 <= r_be <= 1.05 else 'FAIL'}); "
          f"-0.03 {r_dn:.2f}x (<=1.10? "
          f"{'PASS' if r_dn <= 1.10 else 'FAIL'})")
    wl = _worst("kappa-ladder")
    wf = _worst("flat-shade")
    lb = meds[(0.0, "kappa-ladder")] / meds[(0.0, "baseline joint")]
    all_worsts = {a: _worst(a) for a in
                  ["baseline joint", "flat-shade", "prop-shade",
                   "kappa-ladder"]}
    best = min(all_worsts, key=all_worsts.get)
    print(f"  P3 kappa-ladder: worst {wl} vs flat {wf} "
          f"({wl / wf:.2f}x, <=0.90? "
          f"{'PASS' if wl <= 0.9 * wf else 'FAIL'}); benign "
          f"{lb:.2f}x baseline (<=1.10? "
          f"{'PASS' if lb <= 1.10 else 'FAIL'}); best worst-case arm = "
          f"{best}")
    wb = _worst("baseline joint")
    print(f"  P4 sanity: flat-shade worst {wf} vs baseline {wb} "
          f"({wf / wb:.2f}x, <=0.55? "
          f"{'PASS' if wf <= 0.55 * wb else 'FAIL'})")
    print(f"  worst-case by arm: {all_worsts}")


def _ladder(prior):
    pr = np.asarray(prior)
    shaded = np.clip(pr - 0.015, 1e-3, 1 - 1e-3)
    cs = MultiCenterJointUICS.__new__(MultiCenterJointUICS)
    # three components with DIFFERENT kappas: build arrays directly
    from eval_harness.stats.stratified_ui_cs import StratifiedUICS
    StratifiedUICS.__init__(cs, k=4, alpha=ALPHA)
    a_list = [1.0 + 200.0 * shaded, 1.0 + 20.0 * np.clip(pr, 1e-3, 1 - 1e-3),
              np.ones(4)]
    b_list = [1.0 + 200.0 * (1 - shaded),
              1.0 + 20.0 * (1 - np.clip(pr, 1e-3, 1 - 1e-3)),
              np.ones(4)]
    cs._a = np.stack(a_list)
    cs._b = np.stack(b_list)
    cs._logw = np.log(np.array([0.6, 0.3, 0.1]))
    cs._cf = np.zeros((3, 4))
    cs._cs = np.zeros((3, 4))
    cs._logm_total = np.zeros(3)
    return cs


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_shade_refine.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_shade_refine.txt'}")
