#!/usr/bin/env python3
"""Uncertainty quantification for the certification scoreboard.

The scoreboard (fig6, FINDINGS F9) declares winners by comparing medians
whose IQRs overlap. This experiment adds the missing rigor (audit F8):

  - Common random numbers: for each replication r, BOTH arms are run
    with an identically-seeded generator, so between-arm differences are
    not confounded with draw luck (coupling is partial — arms consume
    randomness differently — but shared initial streams remove the
    first-order confound).
  - Paired bootstrap (10,000 resamples over replications) on the
    DIFFERENCE of median stopping times, with abstentions treated as
    censored at n_max (conservative; stated convention).
  - Each scoreboard win is reclassified: SIGNIFICANT if the 95%
    bootstrap CI on the median difference excludes 0, otherwise TIE.

Winner vs runner-up on all six scoreboard conditions, 300 reps/arm.
Offline, deterministic. Writes results_uncertainty.txt.
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

from eval_harness.stats.wsr_block_cs import WSRBlockCS

_src = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
mod = types.ModuleType("bench")
mod.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_src, mod.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = mod.STRATA
N_REPS = 300
N_BOOT = 10000


def run_wsr(pools, tau, rng, n_max):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, n_max // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if hi <= tau:
                return "SAFE", 4 * b
            if lo > tau:
                return "UNSAFE", 4 * b
    return "ABSTAIN", n_max


def run_single(pools, tau, rng, n_max):
    mod.N_MAX = n_max
    return mod.run_single_stream(pools, tau, rng)


def run_directed(pools, tau, rng, n_max):
    mod.N_MAX = n_max
    return mod.run_bonf_directed(pools, tau, rng)


ARMS = {"WSR": run_wsr, "directed": run_directed, "single": run_single}

CONDITIONS = [
    # (model file, tau, truth, n_max, winner, runner_up)
    ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.15, "UNSAFE",
     2000, "directed", "WSR"),
    ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl", 0.15,
     "SAFE", 2000, "single", "WSR"),
    ("gpt-4.1-mini", "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl", 0.15,
     "SAFE", 2000, "single", "WSR"),
    ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.17, "UNSAFE",
     4000, "WSR", "directed"),
    ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.18, "UNSAFE",
     4000, "WSR", "directed"),
    ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl", 0.11,
     "SAFE", 4000, "WSR", "single"),
]


def collect_times(arm, pools, tau, truth, n_max):
    """Per-rep stopping times under CRN seeding; abstain/wrong censored
    at n_max (wrong decisions also counted separately)."""
    times = np.empty(N_REPS)
    wrong = 0
    for r in range(N_REPS):
        rng = np.random.default_rng(BASE_SEED + 7919 * r)
        d, n = ARMS[arm](pools, tau, rng, n_max)
        if d == truth:
            times[r] = n
        else:
            times[r] = n_max
            if d != "ABSTAIN":
                wrong += 1
    return times, wrong


def main():
    print("=" * 76)
    print("SCOREBOARD UNCERTAINTY: CRN + PAIRED BOOTSTRAP ON MEDIAN "
          "DIFFERENCES")
    print("=" * 76)
    print(f"{N_REPS} reps/arm, {N_BOOT} bootstrap resamples, "
          f"abstentions censored at n_max, BASE_SEED={BASE_SEED}\n")

    boot_rng = np.random.default_rng(BASE_SEED + 12345)
    for model, fname, tau, truth, n_max, win, run_up in CONDITIONS:
        pools = mod.load_pools(fname)
        t_win, wrong_w = collect_times(win, pools, tau, truth, n_max)
        t_run, wrong_r = collect_times(run_up, pools, tau, truth, n_max)
        med_diff = np.median(t_run) - np.median(t_win)

        idx = boot_rng.integers(0, N_REPS, size=(N_BOOT, N_REPS))
        diffs = (np.median(t_run[idx], axis=1)
                 - np.median(t_win[idx], axis=1))
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        verdict = "SIGNIFICANT" if lo > 0 else (
            "REVERSED?" if hi < 0 else "TIE")
        print(f"  {model} tau={tau} ({truth}): {win} vs {run_up}")
        print(f"    medians {np.median(t_win):.0f} vs {np.median(t_run):.0f}"
              f"  |  median diff {med_diff:+.0f}, 95% CI "
              f"[{lo:+.0f}, {hi:+.0f}]  ->  {verdict}"
              f"{'' if wrong_w + wrong_r == 0 else f'  (wrong: {wrong_w}/{wrong_r})'}")
    print("""
Convention: positive difference = scoreboard winner faster. TIE means
the 95% CI on the median difference includes 0 and the scoreboard box
should be read as a statistical tie, not a win.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_uncertainty.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_uncertainty.txt'}")
