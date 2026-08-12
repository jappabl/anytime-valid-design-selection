#!/usr/bin/env python3
"""AUDIT: is the crash-resume of the live capstone a LOSSLESS replay?

scripts/run_live_prediction.py crashed mid-run; scripts/resume_live_prediction.py
rebuilt each replication's e-process by replaying data/live_prediction_log.jsonl
and then continued live. THEORY.md calls this a "lossless log-replay resume".

Four independent checks:

  T1  Bit-identity. Synthetic streams with a mid-stream crash+replay must
      reproduce the uninterrupted run's log_pred to the last bit, the
      same (f, s) counts, and the same stopping time.

  T2  Stratum-index alignment across the seam. The original assigns
      STRATA[(n-1) % 4] for sample n (1-based); the resume assigns
      STRATA[n % 4] where n is the count already logged. Verify these
      agree for every crash point.

  T3  Order fragility. resume's crossing() replays by ENUMERATION ORDER
      and never reads the "n" field of the log record. Show that a
      per-rep reordering of the log (which nothing in the pipeline
      forbids) silently changes the reconstructed stopping time --
      i.e. the replay's correctness rests entirely on an unchecked
      invariant.

  T4  Real data. Replay data/live_prediction_log.jsonl and check every
      (decision, n, p_hat) printed in results_live_prediction.txt, plus
      log integrity (contiguity, ordering, duplicates, stratum rotation).

Run: python3 audit/sim_resume_replay.py
"""

import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

TAU = 0.16
ALPHA = 0.05
N_MAX = 2500
STRATA = ["simple", "medium", "complex", "extreme"]


def bits(x):
    return struct.pack("<d", float(x)).hex()


# --- the two code paths, transcribed verbatim from the scripts ----------

def uninterrupted(outcomes_passed):
    """scripts/run_live_prediction.py::rep, driven by a fixed outcome list."""
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
    failures = 0
    for n, passed in enumerate(outcomes_passed, 1):
        x = not passed
        failures += x
        cs.update(0, bool(x))
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(TAU):
                return ("UNSAFE", n, failures / n, cs)
            if cs.rejects_ge(TAU):
                return ("SAFE", n, failures / n, cs)
    return ("ABSTAIN", len(outcomes_passed),
            failures / max(len(outcomes_passed), 1), cs)


def crossing(outcomes):
    """scripts/resume_live_prediction.py::crossing, verbatim."""
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
    f = 0
    for n, passed in enumerate(outcomes, 1):
        cs.update(0, not passed)
        f += (not passed)
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(TAU):
                return ("UNSAFE", n, f / n), cs
            if cs.rejects_ge(TAU):
                return ("SAFE", n, f / n), cs
    return None, cs


def resumed(outcomes_passed, crash_at):
    """resume_live_prediction.py::finish_rep with a pre-crash prefix."""
    pre = outcomes_passed[:crash_at]
    done, cs = crossing(pre)
    if done:
        d, n, ph = done
        return (d, n, ph, cs)
    n = len(pre)
    fails = sum(1 for p in pre if not p)
    for passed in outcomes_passed[crash_at:]:
        x = not passed
        n += 1
        fails += x
        cs.update(0, bool(x))
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(TAU):
                return ("UNSAFE", n, fails / n, cs)
            if cs.rejects_ge(TAU):
                return ("SAFE", n, fails / n, cs)
    return ("ABSTAIN", n, fails / max(n, 1), cs)


# --- T1 / T2 -----------------------------------------------------------

def t1_t2():
    print("T1/T2  bit-identity of crash+replay vs uninterrupted")
    rng = np.random.default_rng(0)
    fails = 0
    checked = 0
    for trial in range(60):
        p = float(rng.uniform(0.17, 0.30))
        stream = list(rng.random(N_MAX) >= p)          # True == passed
        base = uninterrupted(stream)
        for crash_at in [1, 3, 19, 20, 21, 23, 24, 25, 40, 97, 200, 333,
                         500, 887, base[1] - 1, base[1], base[1] + 1]:
            if crash_at < 0 or crash_at > len(stream):
                continue
            res = resumed(stream, crash_at)
            checked += 1
            ok = (res[0] == base[0] and res[1] == base[1]
                  and res[2] == base[2]
                  and bits(res[3].log_pred) == bits(base[3].log_pred)
                  and int(res[3].f[0]) == int(base[3].f[0])
                  and int(res[3].s[0]) == int(base[3].s[0]))
            if not ok:
                fails += 1
                print(f"   MISMATCH trial={trial} p={p:.3f} "
                      f"crash_at={crash_at}: base={base[:3]} "
                      f"resumed={res[:3]} "
                      f"log_pred {bits(base[3].log_pred)} vs "
                      f"{bits(res[3].log_pred)}")
    print(f"   {checked} crash points checked, {fails} mismatches "
          f"-> {'PASS' if fails == 0 else 'FAIL'}")

    # T2: stratum rotation across the seam
    bad = [n for n in range(0, 4000)
           if STRATA[n % 4] != STRATA[((n + 1) - 1) % 4]]
    print(f"   stratum-rotation alignment original vs resume: "
          f"{'PASS' if not bad else 'FAIL at ' + str(bad[:5])}")


# --- T3 ----------------------------------------------------------------

def t3():
    print("\nT3     order fragility of crossing() "
          "(it ignores the record's 'n' field)")
    rng = np.random.default_rng(11)
    changed = 0
    worse = []
    for trial in range(200):
        p = float(rng.uniform(0.19, 0.26))
        stream = list(rng.random(1400) >= p)
        d0, n0, _ = crossing(stream)[0] or ("ABSTAIN", len(stream), 0)
        perm = list(stream)
        rng.shuffle(perm)
        r = crossing(perm)[0]
        d1, n1, _ = r if r else ("ABSTAIN", len(perm), 0)
        if (d0, n0) != (d1, n1):
            changed += 1
            worse.append(n1 - n0)
    print(f"   permuting a rep's logged outcomes changed the "
          f"reconstructed stopping time in {changed}/200 trials "
          f"(median shift {int(np.median(worse)) if worse else 0} samples)")
    print("   => replay correctness depends on an UNVERIFIED invariant: "
          "the log must be in per-rep sample order. The resume script "
          "never asserts it.")


# --- T4 ----------------------------------------------------------------

def t4():
    print("\nT4     replay of the real capstone log")
    log = REPO / "data" / "live_prediction_log.jsonl"
    recs = [json.loads(l) for l in open(log)]
    by = defaultdict(list)
    for r in recs:
        by[r["rep"]].append(r)

    reported = {}
    for line in open(REPO / "results_live_prediction.txt"):
        s = line.strip()
        if s.startswith("rep "):
            parts = s.replace("=", " ").split()
            reported[int(parts[1].rstrip(":"))] = (
                parts[2], int(parts[4]), float(parts[6]))

    print(f"   {'rep':>4} {'logged':>7} {'reported n':>11} {'decision':>9} "
          f"{'replay n':>9} {'replay dec':>11} {'p_hat ok':>9} {'integrity':>10}")
    allok = True
    for rep in sorted(by):
        rs = by[rep]
        ns = [r["n"] for r in rs]
        integrity = (sorted(ns) == list(range(1, len(ns) + 1))
                     and ns == sorted(ns)
                     and all(r["stratum"] == STRATA[(r["n"] - 1) % 4]
                             for r in rs))
        outcomes = [r["passed"] for r in rs]
        got = crossing(outcomes)[0]
        d, n, ph = got if got else ("NO-CROSS", len(outcomes), 0.0)
        rd, rn, rph = reported[rep]
        ok = (d == rd and n == rn and abs(ph - rph) < 5e-4)
        allok &= ok and integrity
        print(f"   {rep:>4} {len(rs):>7} {rn:>11} {rd:>9} {n:>9} {d:>11} "
              f"{str(abs(ph - rph) < 5e-4):>9} {str(integrity):>10}")
    unsafe = sorted(reported[r][1] for r in reported
                    if reported[r][0] == "UNSAFE")
    print(f"\n   reported medians reproduce: {allok}")
    print(f"   UNSAFE stopping times {unsafe}")
    print(f"   median = {np.median(unsafe)}  "
          f"(window [800,1450]; theory-central 1045)")
    # sensitivity of the median to single reps
    print(f"   median if the single longest rep were dropped: "
          f"{np.median(unsafe[:-1])}")
    print(f"   median if the single shortest rep were dropped: "
          f"{np.median(unsafe[1:])}")
    boot = np.random.default_rng(3).choice(unsafe, size=(20000, len(unsafe)))
    meds = np.median(boot, axis=1)
    print(f"   bootstrap 95% CI for the median: "
          f"[{np.percentile(meds, 2.5):.0f}, {np.percentile(meds, 97.5):.0f}]")
    print(f"   P(bootstrap median inside [800,1450]) = "
          f"{float(np.mean((meds >= 800) & (meds <= 1450))):.3f}")


if __name__ == "__main__":
    print("=" * 78)
    print("AUDIT: capstone crash-resume replay equivalence")
    print("=" * 78)
    t1_t2()
    t3()
    t4()
