#!/usr/bin/env python3
"""The Bonferroni design portfolio: don't choose — run all three.

DERIVATION (Target 2; algebra against constants already measured).
Routing between designs failed twice (results_router*.txt: 1.090x /
1.259x the best arm) because choosing from prior-epoch data is hard.
The portfolio removes the choice: run single-stream, UI+RR, and WSR
blocks IN PARALLEL on the SAME stream, each at alpha/3, and stop when
any one certifies. Validity is immediate (union bound; every arm is
anytime-valid at alpha/3; no data-dependent switching — all arms
always run to the stop).

Cost of not choosing, from the expansion n*V = log(1/alpha) +
(d/2) log n + c: moving an arm from alpha to alpha/3 raises its
crossing level by log 3 ~ 1.10 nats, so the portfolio stops at
approximately the ORACLE-BEST arm's time plus log(3)/V_best — a
relative premium of

    R_cell ~ 1 + log 3 / (log(1/alpha) + OH_best)

where OH_best is the best arm's measured overhead in nats. At this
project's horizons OH_best ranges ~1-16 nats, giving predicted premiums
between ~6% and ~27%. Against the measured alternatives: routing error
9-26% (and it failed its own targets twice), and any FIXED single
design pays its wrong-regime multiple (2.6-5x on at least two cells of
the 16-cell grid). The derivation therefore predicts the portfolio
beats every fixed design on grid TOTAL while paying a bounded premium
over the per-cell oracle.

PRE-REGISTERED CLAUSES (scored in-artifact; gating disclosed per
severity_sim rev-3 rule (d) — these are replay comparisons scored
directly, with the derived bound supplying the windows; the analytic
power gate does not apply to WSR's grid process and that exemption is
stated here rather than hidden):
  P1 validity: wrong certifications <= alpha of all portfolio reps
     (union-bound guarantee; no zero-claim).
  P2 per-cell premium: portfolio_median <= 1.30 x oracle_median in
     >= 13 of 16 cells (1.30 = derived worst-case premium 1.27 at the
     smallest measured overhead, plus rounding).
  P3 HEADLINE: portfolio grid TOTAL (sum of per-cell medians among
     correct) is <= the grid total of EVERY fixed design at full
     alpha. If any fixed design beats the portfolio in total, that is
     a LOSS and is reported as such.
  P4 the portfolio's stopping arm distribution matches the design map
     (WSR carries extreme-heterogeneity cells, single carries mild
     ones) — descriptive, ungated.

Cells: the 8 pools x 2 directions of results_auto_select.txt, same
taus, 100 reps/cell, n_max 6000. Offline, deterministic. Writes
results_portfolio.txt.
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

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 100
N_MAX = 6000
POOLS = [
    ("gpt4omini-json", "llm_outcomes_diverse_json.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt41nano-json", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt41mini-json", "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt4omini-code", "llm_outcomes_diverse_code_gpt-4o-mini.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("llama32-json", "llm_outcomes_diverse_json_llama3.2-3b.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("qwen25-json", "llm_outcomes_diverse_json_qwen2.5-7b.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("llama32-mbpp", "llm_outcomes_mbpp_llama3.2-3b.jsonl",
     ["q1", "q2", "q3", "q4"]),
    ("qwen25-mbpp", "llm_outcomes_mbpp_qwen2.5-7b.jsonl",
     ["q1", "q2", "q3", "q4"]),
]


def load(fname, strata):
    pools = {s: [] for s in strata}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


class _Arm:
    def __init__(self, kind, k, alpha):
        self.kind = kind
        self.k = k
        if kind == "wsr":
            self.cs = WSRBlockCS(alpha=alpha)
            self.buf = []
        else:
            self.cs = StratifiedUICS(
                k=k, weights=[1.0] if k == 1 else None, alpha=alpha)

    def update(self, i, y):
        if self.kind == "wsr":
            self.buf.append(int(y))
            if len(self.buf) == self.k:
                self.cs.update(float(np.mean(self.buf)))
                self.buf = []
        else:
            self.cs.update(0 if self.k == 1 else i, bool(y))

    def verdict(self, tau, n):
        if n < 20 or n % 4:
            return None
        if self.kind == "wsr":
            lo, hi = self.cs.get_bounds()
            if lo > tau:
                return "UNSAFE"
            if hi <= tau:
                return "SAFE"
            return None
        if self.cs.rejects_le(tau):
            return "UNSAFE"
        if self.cs.rejects_ge(tau):
            return "SAFE"
        return None


def run_portfolio(pools, strata, tau, rng):
    arms = [("single", _Arm("mix", 1, ALPHA / 3)),
            ("ui", _Arm("mix", len(strata), ALPHA / 3)),
            ("wsr", _Arm("wsr", len(strata), ALPHA / 3))]
    for n in range(1, N_MAX + 1):
        i = (n - 1) % len(strata)
        y = bool(pools[strata[i]][int(
            rng.integers(0, len(pools[strata[i]])))])
        for _, a in arms:
            a.update(i, y)
        for name, a in arms:
            v = a.verdict(tau, n)
            if v:
                return v, n, name
    return "ABSTAIN", N_MAX, None


def run_fixed(pools, strata, tau, rng, kind):
    a = _Arm("wsr" if kind == "wsr" else "mix",
             1 if kind == "single" else len(strata), ALPHA)
    for n in range(1, N_MAX + 1):
        i = (n - 1) % len(strata)
        y = bool(pools[strata[i]][int(
            rng.integers(0, len(pools[strata[i]])))])
        a.update(i, y)
        v = a.verdict(tau, n)
        if v:
            return v, n
    return "ABSTAIN", N_MAX


def main():
    print("=" * 76)
    print("BONFERRONI DESIGN PORTFOLIO (derivation + predictions "
          "pre-registered in header)")
    print("=" * 76)
    print(f"alpha={ALPHA} (alpha/3 per portfolio arm), "
          f"{N_REPS} reps/cell, n_max={N_MAX}, BASE_SEED={BASE_SEED}\n")

    totals = {"portfolio": 0, "single": 0, "ui": 0, "wsr": 0}
    complete = {"portfolio": True, "single": True, "ui": True,
                "wsr": True}
    wrong_port, all_port = 0, 0
    prem_ok, scoreable = 0, 0
    stop_counts = {}
    for pi, (label, fname, strata) in enumerate(POOLS):
        pools = load(fname, strata)
        p_star = float(np.mean([pools[s].mean() for s in strata]))
        for di, (direction, tau) in enumerate([
                ("UNSAFE", round(min(0.9, max(0.02, p_star - 0.045)), 3)),
                ("SAFE", round(min(0.9, max(0.02, p_star + 0.045)), 3))]):
            truth = "UNSAFE" if p_star > tau else "SAFE"
            meds = {}
            for kind in ("single", "ui", "wsr"):
                rng = np.random.default_rng(
                    BASE_SEED + 20_000 * pi + 2000 * di
                    + {"single": 0, "ui": 1, "wsr": 2}[kind] * 100)
                outs = [run_fixed(pools, strata, tau, rng, kind)
                        for _ in range(N_REPS)]
                dec = [n for d, n in outs if d == truth]
                meds[kind] = (int(np.median(dec)) if len(dec) >=
                              0.9 * N_REPS else None)
            rng = np.random.default_rng(
                BASE_SEED + 20_000 * pi + 2000 * di + 555)
            pouts = [run_portfolio(pools, strata, tau, rng)
                     for _ in range(N_REPS)]
            pdec = [n for d, n, _ in pouts if d == truth]
            wrong_port += sum(1 for d, _, _ in pouts
                              if d not in (truth, "ABSTAIN"))
            all_port += N_REPS
            for _, _, arm in pouts:
                if arm:
                    stop_counts[arm] = stop_counts.get(arm, 0) + 1
            pmed = (int(np.median(pdec)) if len(pdec) >= 0.9 * N_REPS
                    else None)
            eligible = {k: m for k, m in meds.items() if m}
            oracle = (min(eligible, key=eligible.get)
                      if eligible else None)
            for k, m in meds.items():
                if m is None:
                    complete[k] = False
                else:
                    totals[k] += m
            if pmed is None:
                complete["portfolio"] = False
            else:
                totals["portfolio"] += pmed
            if pmed and oracle:
                scoreable += 1
                ratio = pmed / eligible[oracle]
                prem_ok += ratio <= 1.30
                print(f"  {label:15s} {direction}: oracle "
                      f"{oracle:6s} {eligible[oracle]:5d}, portfolio "
                      f"{pmed:5d} ({ratio:.2f}x) "
                      f"{'OK' if ratio <= 1.30 else 'OVER'}; meds "
                      f"{meds}")
            else:
                print(f"  {label:15s} {direction}: "
                      f"portfolio {pmed}, meds {meds} (cell "
                      f"unresolved for premium scoring)")

    print(f"\n  P1 validity: {wrong_port}/{all_port} wrong "
          f"({wrong_port / all_port:.4f} <= {ALPHA}): "
          f"{'PASS' if wrong_port / all_port <= ALPHA else 'FAIL'}")
    print(f"  P2 premium <= 1.30x oracle: {prem_ok}/{scoreable} "
          f"(need >= 13): {'PASS' if prem_ok >= 13 else 'FAIL'}")
    beats = [k for k in ("single", "ui", "wsr")
             if complete[k] and complete["portfolio"]
             and totals["portfolio"] <= totals[k]]
    incomparable = [k for k in ("single", "ui", "wsr")
                    if not complete[k]]
    print(f"  P3 HEADLINE totals (cells where the design certified "
          f">= 90%; incomplete designs listed): {totals}")
    print(f"     portfolio <= every complete fixed design? "
          f"{'PASS' if len(beats) == sum(1 for k in ('single', 'ui', 'wsr') if complete[k]) and complete['portfolio'] else 'FAIL'}"
          f" (incomplete: {incomparable or 'none'})")
    print(f"  P4 stop-arm distribution (descriptive): {stop_counts}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_portfolio.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_portfolio.txt'}")
