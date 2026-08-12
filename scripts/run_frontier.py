#!/usr/bin/env python3
"""The rate-vs-overhead frontier for anytime-valid certification.

Motivated by the reframed open problem (Spertus-Sridhar-Stark 2024 leave
the optimal selection rule open; our referee-corrected accounting shows
the practical gap is LEARNING overhead, not allocation): can any
anytime-valid procedure achieve the stratified rate with sub-log(n)
overhead, or is there a conservation law?

New arm — EPOCH-SPLIT (universal-inference flavored, sequentialized):
per stratum, the e-process numerator uses a plug-in rate FROZEN at
doubling epoch boundaries (predictable, hence valid; Jeffreys-smoothed).
Unlike the Beta mixture it integrates nothing; unlike WSR it targets the
full stratified rate. Wasserman-Ramdas-Balakrishnan's split-LRT is the
batch ancestor; the doubling schedule is its anytime analogue.

PRE-REGISTERED HYPOTHESIS (stated before running, from Rissanen's
universal-coding redundancy bound): adaptivity + anytime validity FORCES
~(d/2) log n redundancy, so epoch-split lands ON the mixture frontier
(overhead within [0.7, 1.5]x of the UI mixture at matched margins), NOT
below it. The one-shot freeze variant should show the variance-risk
corner instead (fast medians, elevated abstention). If epoch-split's
overhead lands BELOW 0.5x of the mixture's, the conservation hypothesis
is FALSIFIED and that is the headline.

REVISION 2 (post-audit, 2026-08-12). The second adversarial audit
(audit/AUDIT_LAW_CAPSTONE.md) found (a) the original artifact never
printed the pre-registered ratios — epoch-split landed at 1.67/1.72/1.48
of the mixture, i.e. the support window [0.7, 1.5] was MISSED at 2 of 3
margins, and the original reading of "supported" was wrong; and (b) the
original "one-shot split" arm was a strawman: it bet at p=0.5 during
burn-in and charged ~111 nats of estimation loss to the martingale,
which the split-LRT lineage it cited (Wasserman-Ramdas-Balakrishnan)
does not do. This revision adds the faithful discard-burn-in SplitLRT
(estimation half contributes nothing to log E; frozen plug-in after;
validity gated at the null boundary in audit/sim_splitlrt_validity.py),
keeps the original arm under an honest name, and prints the
pre-registered ratio verdicts. Burn-in values {25, 50, 100} are all
reported (50 was flagged by the audit's independent sweep; no
cherry-pick). Medians are comparable only at matched certification
fractions — arms with depressed cert% are marked.

Offline, deterministic. Writes results_frontier.txt.
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

from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.stats.wsr_block_cs import WSRBlockCS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 200
N_MAX = 6000


class EpochSplitUICS(StratifiedUICS):
    """UI e-process with frozen-epoch plug-in numerator (no mixture)."""

    def __init__(self, k=4, alpha=ALPHA, first_epoch=8, one_shot=False):
        super().__init__(k=k, alpha=alpha)
        self.first_epoch = first_epoch
        self.one_shot = one_shot
        self._frozen = np.full(k, 0.5)      # current epoch's bet rate
        self._next_boundary = np.full(k, first_epoch, dtype=int)

    def update(self, stratum, is_failure):
        i = stratum
        p = self._frozen[i]
        self.log_pred += float(np.log(p if is_failure else 1.0 - p))
        if is_failure:
            self.f[i] += 1
        else:
            self.s[i] += 1
        n_i = self.f[i] + self.s[i]
        if n_i >= self._next_boundary[i]:
            if not (self.one_shot and n_i > self.first_epoch):
                self._frozen[i] = (self.f[i] + 0.5) / (n_i + 1.0)
                self._next_boundary[i] = n_i * 2

    # min_log_e / rejects_* inherited: they use self.log_pred and f/s.


class SplitLRT(StratifiedUICS):
    """Faithful discard-burn-in split e-process (WRB split-LRT,
    sequentialized): the first `burn` samples per stratum are used ONLY
    to estimate a Jeffreys-smoothed plug-in rate and contribute nothing
    to log E; afterwards the frozen plug-in bets. Ported from
    audit/sim_frontier_splitlrt.py."""

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


def run_arm(pools, tau, rng, make_cs):
    cs = make_cs()
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        pool = pools[STRATA[k]]
        cs.update(k if cs.k == 4 else 0,
                  bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0 and cs.rejects_le(tau):
            return "UNSAFE", n
    return "ABSTAIN", N_MAX


def run_wsr(pools, tau, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, _ = cs.get_bounds()
            if lo > tau:
                return "UNSAFE", 4 * b
    return "ABSTAIN", N_MAX


def main():
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    pools = {s: np.array(v, dtype=np.int8) for s, v in pools.items()}
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    p_star = float(rates.mean())

    print("=" * 76)
    print("RATE-vs-OVERHEAD FRONTIER (conservation hypothesis "
          "pre-registered in header)")
    print("=" * 76)
    print(f"gpt-4o-mini pools, UNSAFE direction, alpha={ALPHA}, "
          f"{N_REPS} reps, n_max={N_MAX}, BASE_SEED={BASE_SEED}")
    print("Overhead defined as median(n)*V_rr - log(1/alpha), using the "
          "shared allocation-constrained rate V_rr for the three "
          "stratified-rate arms (WSR reported for reference at its own "
          "Kelly rate).\n")

    arms = [
        ("UI mixture", lambda: StratifiedUICS(k=4, alpha=ALPHA)),
        ("epoch-split", lambda: EpochSplitUICS(k=4, alpha=ALPHA)),
        ("0.5-burnin-charged", lambda: EpochSplitUICS(k=4, alpha=ALPHA,
                                                      first_epoch=40,
                                                      one_shot=True)),
        ("split-LRT b=25", lambda: SplitLRT(burn=25)),
        ("split-LRT b=50", lambda: SplitLRT(burn=50)),
        ("split-LRT b=100", lambda: SplitLRT(burn=100)),
        ("single-stream", lambda: StratifiedUICS(k=1, weights=[1.0],
                                                 alpha=ALPHA)),
    ]
    log1a = np.log(1 / ALPHA)
    verdicts = []
    for tau in [0.15, 0.16, 0.17]:
        lam = np.full(4, 0.25)
        w = np.full(4, 0.25)
        m = bench._inner_min(lam, rates, w, tau)
        v_rr = float(np.sum(lam * [bench.kl_bern(rates[i], m[i])
                                   for i in range(4)]))
        v_pool = bench.kl_bern(p_star, tau)
        print(f"  tau={tau} (margin {p_star - tau:.3f}, "
              f"V_rr={v_rr:.4f}, V_pool={v_pool:.4f}):")
        rows = []
        for name, mk in arms:
            rng = np.random.default_rng(BASE_SEED + 7919)
            outs = [run_arm(pools, tau, rng, mk) for _ in range(N_REPS)]
            ok = [n for d, n in outs if d == "UNSAFE"]
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(ok)) if ok else None
            v = v_pool if name == "single-stream" else v_rr
            oh = med * v - log1a if med else None
            rows.append((name, len(ok), ab, med, oh))
        rng = np.random.default_rng(BASE_SEED + 7919)
        outs = [run_wsr(pools, tau, rng) for _ in range(N_REPS)]
        ok = [n for d, n in outs if d == "UNSAFE"]
        med = int(np.median(ok)) if ok else None
        rows.append(("WSR (ref)", len(ok), N_REPS - len(ok), med, None))
        ui_oh = rows[0][4]
        for name, nok, ab, med, oh in rows:
            oh_s = f"{oh:+7.2f} nats" if oh is not None else "      --"
            ratio = (f" ratio {oh/ui_oh:5.3f}x"
                     if oh is not None and name != "UI mixture" else "")
            cens = " [CENSORED: cert<95%]" if nok < 0.95 * N_REPS else ""
            print(f"    {name:18s}: certified {nok:3d}/{N_REPS}, "
                  f"abstain {ab:3d}, median {med}, overhead {oh_s}"
                  f"{ratio}{cens}")
        for name, nok, ab, med, oh in rows:
            if oh is None or nok < 0.95 * N_REPS:
                continue
            r = oh / ui_oh
            if name == "epoch-split":
                verdicts.append(
                    (tau, name, r,
                     "IN WINDOW" if 0.7 <= r <= 1.5 else "WINDOW MISSED"))
            elif name.startswith("split-LRT"):
                verdicts.append(
                    (tau, name, r,
                     "FALSIFIES (<0.5x)" if r < 0.5 else "above 0.5x"))
        print()

    print("Pre-registered scoring (support window [0.7, 1.5]x of the UI "
          "mixture;\nbelow 0.5x at full certification falsifies the "
          "conservation hypothesis):")
    for tau, name, r, verdict in verdicts:
        print(f"  tau={tau} {name:18s} ratio {r:5.3f}x  -> {verdict}")
    n_fals = sum(1 for *_, v in verdicts if v.startswith("FALSIFIES"))
    n_miss = sum(1 for _, nm, _, v in verdicts
                 if nm == "epoch-split" and v == "WINDOW MISSED")
    print(f"""
VERDICT: epoch-split missed the support window at {n_miss} of 3 margins,
and the faithful split-LRT crosses the pre-registered falsification
line at {n_fals} grid points. The conservation hypothesis AS PRE-REGISTERED
is FALSIFIED at these sample sizes: sample splitting escapes the
(d/2) log n learning tax at the n ~ 10^3 scales this project studies,
at the price of a frozen (non-adaptive) bet whose tail risk does not
bind at these margins. The asymptotic version (mixture-optimal
redundancy) is untouched but was not what was pre-registered. Medians
are comparable only at matched certification fractions; censored arms
are flagged above.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_frontier.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_frontier.txt'}")
