#!/usr/bin/env python3
"""Asymmetric contamination priors: a DESIGNED fix for a measured effect.

The drift phase diagram (results_warmstart_drift.txt rev 2) measured a
strong asymmetry: understating the prior failure rates is nearly free
(delta = -0.015 costs +4% median) while overstating is catastrophic
(+0.015 costs +67%, +0.03 costs +236%). This experiment tests two
priors built to exploit that asymmetry — designed BEFORE running from
the drift table alone, not iterated against results:

  arm A "shift-down": concentrated component centered at
        clip(prior - 0.015, 0.001, 0.999); eps = 0.1 uniform.
  arm B "two-center": 0.45 at prior, 0.45 at clip(prior - 0.03, ...),
        0.10 uniform (the mixture picks the better center itself,
        paying ~log(2) dilution).
  baseline: rev-2 joint contamination (0.9 at prior, 0.1 uniform).

Grid: true-drift delta in {-0.03, -0.015, 0, +0.015, +0.03} applied to
all strata (prior_input = clip(truth + delta, ...)), tau = 0.16,
gpt-4o-mini pools, per-rep CRN seeds, 200 reps, n_max = 6000.

PRE-REGISTERED PREDICTIONS (from the drift table; stated before
running):
  P1 zero wrong certifications, all arms, all deltas.
  P2 benign cost: at delta = 0, arm A median <= 1.08x baseline;
     arm B <= 1.15x baseline.
  P3 upward protection: at delta = +0.015, A <= 0.70x baseline;
     at +0.03, A <= 0.60x baseline (B: <= 0.75x / <= 0.65x).
  P4 downward robustness: at delta = -0.03, A <= 1.35x baseline;
     B <= 1.15x baseline.
  P5 WIN CRITERION: an arm wins if it improves the worst-case median
     over the delta grid by >= 25% vs baseline while costing <= 15%
     at benign. Otherwise it is another characterized negative.

Offline, deterministic. Writes results_asym_prior.txt.
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
KAPPA = 200.0
STRATA = wj.STRATA
DELTAS = [-0.03, -0.015, 0.0, 0.015, 0.03]


class MultiCenterJointUICS(StratifiedUICS):
    """Joint contamination with arbitrary (weight, center) components;
    generalizes TransferPriorJointUICS (which is the 2-component case)."""

    def __init__(self, comps, k=4, alpha=ALPHA, kappa=KAPPA):
        # comps: list of (weight, rates-vector-or-None); None = uniform
        super().__init__(k=k, alpha=alpha)
        ws, As, Bs = [], [], []
        for w, rates in comps:
            ws.append(w)
            if rates is None:
                As.append(np.ones(k))
                Bs.append(np.ones(k))
            else:
                r = np.clip(np.asarray(rates, dtype=float), 1e-3, 1 - 1e-3)
                As.append(1.0 + kappa * r)
                Bs.append(1.0 + kappa * (1 - r))
        self._a = np.stack(As)
        self._b = np.stack(Bs)
        self._logw = np.log(np.asarray(ws, dtype=float))
        m = len(comps)
        self._cf = np.zeros((m, k))
        self._cs = np.zeros((m, k))
        self._logm_total = np.zeros(m)

    def update(self, stratum, is_failure):
        i = stratum
        a = self._a[:, i] + self._cf[:, i]
        b = self._b[:, i] + self._cs[:, i]
        pred_fail = a / (a + b)
        p_obs = pred_fail if is_failure else 1 - pred_fail
        lw = self._logw + self._logm_total
        lw = lw - np.logaddexp.reduce(lw)
        mix_pred = float(np.exp(np.logaddexp.reduce(lw + np.log(p_obs))))
        self.log_pred += float(np.log(max(mix_pred, 1e-300)))
        self._logm_total += np.log(p_obs)
        if is_failure:
            self._cf[:, i] += 1
            self.f[i] += 1
        else:
            self._cs[:, i] += 1
            self.s[i] += 1


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
    print("ASYMMETRIC CONTAMINATION PRIORS (predictions pre-registered "
          "in header)")
    print("=" * 76)
    print(f"tau={TAU} (V_rr={v_rr:.4f}), kappa={KAPPA:.0f}, "
          f"alpha={ALPHA}, {N_REPS} reps, n_max={wj.N_MAX}, "
          f"BASE_SEED={BASE_SEED}\n")

    def down(pr, s):
        return np.clip(np.asarray(pr) - s, 1e-3, 1 - 1e-3)

    meds = {}
    for delta in DELTAS:
        prior = np.clip(rates + delta, 1e-3, 1 - 1e-3)
        arms = [
            ("baseline joint", MultiCenterJointUICS,
             [(0.9, prior), (0.1, None)]),
            ("A shift-down", MultiCenterJointUICS,
             [(0.9, down(prior, 0.015)), (0.1, None)]),
            ("B two-center", MultiCenterJointUICS,
             [(0.45, prior), (0.45, down(prior, 0.03)), (0.1, None)]),
        ]
        print(f"  true-drift delta={delta:+.3f}:")
        for name, cls, comps in arms:
            outs = [wj.run_arm(pools, TAU,
                               np.random.default_rng(
                                   BASE_SEED + 7919 + 1000 * rep),
                               lambda: cls(comps))
                    for rep in range(N_REPS)]
            ok = [n for d, n in outs if d == "UNSAFE"]
            wrong = sum(1 for d, _ in outs if d == "SAFE")
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(ok)) if ok else None
            meds[(delta, name)] = med
            oh = med * v_rr - log1a if med else None
            print(f"    {name:14s}: certified {len(ok):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median {med}, "
                  f"overhead {oh:+.2f} nats" if med else
                  f"    {name:14s}: certified 0, abstain {ab}")
        print()

    print("PRE-REGISTERED SCORING:")
    b0 = meds[(0.0, "baseline joint")]
    for arm, benign_lim, up15, up30, down30 in [
            ("A shift-down", 1.08, 0.70, 0.60, 1.35),
            ("B two-center", 1.15, 0.75, 0.65, 1.15)]:
        rb = meds[(0.0, arm)] / b0
        r15 = meds[(0.015, arm)] / meds[(0.015, "baseline joint")]
        r30 = meds[(0.03, arm)] / meds[(0.03, "baseline joint")]
        rd30 = meds[(-0.03, arm)] / meds[(-0.03, "baseline joint")]
        worst_arm = max(meds[(d, arm)] for d in DELTAS)
        worst_base = max(meds[(d, "baseline joint")] for d in DELTAS)
        win = (worst_arm <= 0.75 * worst_base) and (rb <= 1.15)
        print(f"  {arm}: benign {rb:.2f}x (<= {benign_lim}? "
              f"{'PASS' if rb <= benign_lim else 'FAIL'}); "
              f"+0.015 {r15:.2f}x (<= {up15}? "
              f"{'PASS' if r15 <= up15 else 'FAIL'}); "
              f"+0.03 {r30:.2f}x (<= {up30}? "
              f"{'PASS' if r30 <= up30 else 'FAIL'}); "
              f"-0.03 {rd30:.2f}x (<= {down30}? "
              f"{'PASS' if rd30 <= down30 else 'FAIL'})")
        print(f"    worst-case {worst_arm} vs baseline {worst_base} "
              f"({worst_arm / worst_base:.2f}x) -> "
              f"{'WIN' if win else 'NOT A WIN'} per P5")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_asym_prior.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_asym_prior.txt'}")
