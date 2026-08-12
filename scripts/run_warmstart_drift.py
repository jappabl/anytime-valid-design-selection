#!/usr/bin/env python3
"""Warm-start drift phase diagram: how stale can the prior be?

The warm-start results (results_warmstart*.txt) used a benign prior
(near-copy of the truth) plus two hand-picked misspecifications. The
deployment question is continuous: a model update shifts failure rates
by some drift delta between epochs — at what staleness does warm-start
stop being worth it? This script sweeps additive drift on all strata,

    p_prior_k = clip(p_k + delta, 0.001, 0.999),

for the JOINT-contamination transfer prior (the recommended production
variant; worst-case premium log(1/eps) total), at the middle margin
tau = 0.16 where the incumbents are cold UI (median 1498) and WSR
blocks (median 374).

PRE-REGISTERED PREDICTIONS (stated before running):
  1. Zero wrong certifications at EVERY delta (validity does not depend
     on the prior; only power does).
  2. Degradation is monotone in |delta| up to noise, and SATURATES: the
     eps-component floors the damage, so worst-case median <= cold
     median + log(1/eps)/V_rr ~ 1498 + 181 ~ 1700 (allow <= 2000 with
     median noise).
  3. Breakeven vs WSR (374): the prior's effective sd at kappa=200 is
     ~sqrt(0.2*0.8/200) ~ 0.028 per stratum, so warm-start still beats
     WSR at |delta| <= 0.015 and loses by |delta| >= 0.06; the
     breakeven staleness lies in |delta| in [0.015, 0.06].
  4. Asymmetry: understatement (delta < 0, prior claims the model is
     SAFER than it is) hurts UNSAFE certification more than equal
     overstatement (the prior mass sits on the null side of the
     boundary and actively supports the null).

Offline, deterministic. Writes results_warmstart_drift.txt.
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

_src = open(REPO / "scripts" / "run_warmstart_joint.py").read()
wj = types.ModuleType("wj")
wj.__dict__["__file__"] = str(REPO / "scripts" / "run_warmstart_joint.py")
exec(_src.rsplit('if __name__', 1)[0], wj.__dict__)

BASE_SEED = 42
ALPHA = 0.05
TAU = 0.16
N_REPS = 200
STRATA = wj.STRATA
DELTAS = [-0.10, -0.06, -0.03, -0.015, 0.0, 0.015, 0.03, 0.06, 0.10]


def main():
    pools = wj.load(REPO / "data" / "llm_outcomes_diverse_json.jsonl")
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    p_star = float(rates.mean())

    lam = np.full(4, 0.25)
    w = np.full(4, 0.25)
    m = wj.bench._inner_min(lam, rates, w, TAU)
    v_rr = float(np.sum(lam * [wj.bench.kl_bern(rates[i], m[i])
                               for i in range(4)]))
    log1a = np.log(1 / ALPHA)

    print("=" * 76)
    print("WARM-START DRIFT PHASE DIAGRAM (predictions pre-registered "
          "in header)")
    print("=" * 76)
    print(f"current pools p_k = {[round(float(r), 3) for r in rates]} "
          f"(p* = {p_star:.4f})")
    print(f"tau={TAU} (V_rr={v_rr:.4f}), joint contamination "
          f"kappa={wj.KAPPA:.0f} eps={wj.EPS}, alpha={ALPHA}, "
          f"{N_REPS} reps, n_max={wj.N_MAX}, BASE_SEED={BASE_SEED}")
    print(f"prior_k = clip(p_k + delta, 0.001, 0.999); incumbents: "
          f"cold UI and WSR blocks\n")

    rows = []
    for delta in DELTAS:
        prior = np.clip(rates + delta, 0.001, 0.999)
        rng = np.random.default_rng(BASE_SEED + 7919)
        outs = [wj.run_arm(pools, TAU, rng,
                           lambda: wj.TransferPriorJointUICS(prior))
                for _ in range(N_REPS)]
        ok = [n for d, n in outs if d == "UNSAFE"]
        wrong = sum(1 for d, _ in outs if d == "SAFE")
        ab = sum(1 for d, _ in outs if d == "ABSTAIN")
        med = int(np.median(ok)) if ok else None
        oh = med * v_rr - log1a if med else None
        rows.append((delta, len(ok), wrong, ab, med, oh))

    rng = np.random.default_rng(BASE_SEED + 7919)
    outs = [wj.run_arm(pools, TAU, rng,
                       lambda: StratifiedUICS(k=4, alpha=ALPHA))
            for _ in range(N_REPS)]
    ok = [n for d, n in outs if d == "UNSAFE"]
    cold_med = int(np.median(ok))
    rng = np.random.default_rng(BASE_SEED + 7919)
    outs = [wj.run_wsr(pools, TAU, rng) for _ in range(N_REPS)]
    ok = [n for d, n in outs if d == "UNSAFE"]
    wsr_med = int(np.median(ok))

    print(f"  {'delta':>7s} {'cert':>9s} {'wrong':>5s} {'abst':>4s} "
          f"{'median':>6s} {'overhead':>10s}  vs WSR({wsr_med}) / "
          f"cold({cold_med})")
    for delta, nok, wrong, ab, med, oh in rows:
        oh_s = f"{oh:+7.2f}" if oh is not None else "     --"
        med_s = str(med) if med else "--"
        rel = ("BEATS both" if med and med < wsr_med else
               "loses to WSR, beats cold" if med and med < cold_med else
               "loses to both")
        print(f"  {delta:+7.3f} {nok:4d}/{N_REPS} {wrong:5d} {ab:4d} "
              f"{med_s:>6s} {oh_s} nats  {rel}")

    below = [d for d, _, _, _, med, _ in rows if med and med < wsr_med]
    above = [d for d, _, _, _, med, _ in rows if med and med >= wsr_med]
    print(f"\n  breakeven vs WSR: last winning |delta| = "
          f"{max(abs(d) for d in below) if below else None}; first "
          f"losing |delta| = "
          f"{min(abs(d) for d in above) if above else None}")
    worst = max(med for _, _, _, _, med, _ in rows if med)
    print(f"  saturation check: worst median {worst} vs predicted "
          f"ceiling ~1700 (cold {cold_med} + log(1/eps)/V_rr "
          f"~ {int(np.log(1/wj.EPS)/v_rr)})")
    tot_wrong = sum(wrong for _, _, wrong, _, _, _ in rows)
    print(f"  wrong certifications across all deltas: {tot_wrong}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_warmstart_drift.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_warmstart_drift.txt'}")
