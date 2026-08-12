#!/usr/bin/env python3
"""AUDIT: is the frontier's "one-shot split" arm a strawman?

scripts/run_frontier.py implements the one-shot freeze as
EpochSplitUICS(first_epoch=40, one_shot=True): the e-process BETS AT
p = 0.5 for the first 40 samples of every stratum and only then freezes
a plug-in rate. For a stratum whose true rate is ~0 that costs
40*log(2) = 27.7 nats, i.e. ~111 nats across K = 4 strata, against a
crossing threshold of log(1/alpha) = 3.0. The arm cannot win; its
"predicted variance-risk corner" is an accounting artifact, not a
property of sample splitting.

Wasserman-Ramdas-Balakrishnan's split-LRT -- the batch ancestor the
docstring cites -- DISCARDS the estimation half; it does not charge it
to the test martingale. This script implements that faithfully:

    burn-in: b samples per stratum, used ONLY to form p_hat
             (Jeffreys-smoothed), contributing nothing to log E
    then:    a frozen plug-in e-process on the remaining stream

and asks whether a properly-implemented split lands BELOW 0.5x of the UI
mixture's overhead -- the pre-registered falsification line.

Run: python3 audit/sim_frontier_splitlrt.py
"""

import json
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

ALPHA = 0.05
LOG1A = float(np.log(1 / ALPHA))
STRATA = ["simple", "medium", "complex", "extreme"]
N_MAX = 6000
N_REPS = 100
BASE = 42 + 7919


class SplitLRT(StratifiedUICS):
    """Discard-burn-in split e-process: burn-in samples are NOT charged."""

    def __init__(self, burn=50, k=4, alpha=ALPHA):
        super().__init__(k=k, alpha=alpha)
        self.burn = burn
        self._bf = np.zeros(k, dtype=int)
        self._bn = np.zeros(k, dtype=int)
        self._p = np.full(k, np.nan)

    def update(self, stratum, is_failure):
        i = stratum
        if self._bn[i] < self.burn:                # estimation half
            self._bn[i] += 1
            self._bf[i] += bool(is_failure)
            if self._bn[i] == self.burn:
                self._p[i] = (self._bf[i] + 0.5) / (self.burn + 1.0)
            return
        p = self._p[i]
        self.log_pred += float(np.log(p if is_failure else 1.0 - p))
        if is_failure:
            self.f[i] += 1
        else:
            self.s[i] += 1


def load():
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def run(pools, tau, rng, make_cs):
    cs = make_cs()
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        pool = pools[STRATA[k]]
        cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0 and cs.rejects_le(tau):
            return n
    return None


def main():
    pools = load()
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    lam = w = np.full(4, 0.25)

    print("=" * 78)
    print("AUDIT: faithful split-LRT arm vs the frontier's 'one-shot split'")
    print(f"gpt-4o-mini JSON pools, UNSAFE, alpha={ALPHA}, {N_REPS} reps, "
          f"n_max={N_MAX}")
    print("=" * 78)
    ui_ref = {0.15: (960, 15.47), 0.16: (1498, 16.00), 0.17: (2872, 18.42)}
    oneshot_ref = {0.15: (5264, 47), 0.16: (None, 0), 0.17: (None, 0)}

    for tau in [0.15, 0.16, 0.17]:
        m = bench._inner_min(lam, rates, w, tau)
        v = float(np.sum(lam * [bench.kl_bern(rates[i], m[i])
                                for i in range(4)]))
        ui_med, ui_oh = ui_ref[tau]
        print(f"\n  tau={tau}  V_rr={v:.4f}   UI mixture: median {ui_med}, "
              f"overhead {ui_oh:+.2f} nats")
        print(f"  shipped one-shot arm: median {oneshot_ref[tau][0]}, "
              f"certified {oneshot_ref[tau][1]}/200")
        print(f"    {'burn b':>7} {'cert':>7} {'median':>7} "
              f"{'overhead':>9} {'ratio to UI':>12} {'<0.5x?':>7}")
        for burn in [10, 25, 50, 100]:
            rng = np.random.default_rng(BASE)
            outs = [run(pools, tau, rng, lambda b=burn: SplitLRT(burn=b))
                    for _ in range(N_REPS)]
            ok = [n for n in outs if n is not None]
            med = int(np.median(ok)) if ok else None
            oh = med * v - LOG1A if med else None
            r = oh / ui_oh if oh else float("nan")
            print(f"    {burn:>7d} {len(ok):>4d}/{N_REPS} "
                  f"{str(med):>7} "
                  f"{(f'{oh:+9.2f}' if oh else '       --')} "
                  f"{r:>12.3f} {str(bool(r < 0.5)) if oh else '--':>7}")


if __name__ == "__main__":
    main()
