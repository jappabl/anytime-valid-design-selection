#!/usr/bin/env python3
"""Deterministic summary of the severe live test from its journal.

Replays data/severe_live_log.jsonl through the exact frozen procedure
(k=1 mixture CS, checks every 4th sample from n >= 20) and scores the
four pre-registered criteria from scripts/run_severe_live.py (frozen
at commit fe01a4c). The live run printed its verdict but did not write
a checksummed artifact; this script produces one reproducibly from the
committed journal.

Writes results_severe_live.txt.
"""

import hashlib
import io
import json
import sys
from collections import defaultdict
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS

TAU = {"tau1": 0.49, "tau2": 0.45}
WIN_C1 = (396, 632)
WIN_C2 = (148, 240)
WIN_C3 = (0.258, 0.561)
SEVERITY = "0.59 central; 0.31/0.45 at +/-0.006 pilot-error band"
ALPHA = 0.05


def main():
    logged = defaultdict(list)
    for line in open(REPO / "data" / "severe_live_log.jsonl"):
        r = json.loads(line)
        logged[(r["arm"], r["rep"])].append(r["passed"])

    print("=" * 76)
    print("SEVERE LIVE TEST — SUMMARY FROM JOURNAL "
          "(pre-registration frozen at commit fe01a4c)")
    print("=" * 76)
    print("llama3.2:3b live temp 0.7, fresh population (seed 20260812),"
          " 20 reps/arm,\npilot-centered windows; disclosed severity "
          f"P(all|theory) = {SEVERITY}\n")

    results = {}
    for (arm, rep), outcomes in sorted(logged.items()):
        cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
        decision, n_stop = "ABSTAIN", len(outcomes)
        f = 0
        for n, passed in enumerate(outcomes, 1):
            cs.update(0, not passed)
            f += (not passed)
            if n >= 20 and n % 4 == 0:
                if cs.rejects_le(TAU[arm]):
                    decision, n_stop = "UNSAFE", n
                    break
                if cs.rejects_ge(TAU[arm]):
                    decision, n_stop = "SAFE", n
                    break
        results[(arm, rep)] = (decision, n_stop, f / max(n_stop, 1))
        print(f"  {arm} rep {rep:2d}: {decision:7s} n={n_stop:5d} "
              f"p_hat={f / max(n_stop, 1):.3f}")

    m = {}
    for arm in ("tau1", "tau2"):
        ts = [n for (a, _), (d, n, _) in results.items()
              if a == arm and d == "UNSAFE"]
        m[arm] = int(np.median(ts))
    n_safe = sum(1 for (d, _, _) in results.values() if d == "SAFE")
    ratio = m["tau2"] / m["tau1"]
    c1 = WIN_C1[0] <= m["tau1"] <= WIN_C1[1]
    c2 = WIN_C2[0] <= m["tau2"] <= WIN_C2[1]
    c3 = WIN_C3[0] <= ratio <= WIN_C3[1]
    c4 = n_safe == 0

    print(f"\nC1 median(tau1=0.49) = {m['tau1']} in {WIN_C1}: "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"C2 median(tau2=0.45) = {m['tau2']} in {WIN_C2}: "
          f"{'PASS' if c2 else 'FAIL'}")
    print(f"C3 ratio = {ratio:.4f} in {WIN_C3}: "
          f"{'PASS' if c3 else 'FAIL'}")
    print(f"C4 zero SAFE: {n_safe} SAFE across 40 reps: "
          f"{'PASS' if c4 else 'FAIL'}")
    print(f"\nSEVERE TEST VERDICT (frozen rule): "
          f"{'ALL CRITERIA PASS' if c1 and c2 and c3 and c4 else 'FAILED'}")
    print("""
Frozen interpretation rule (from the pre-registration): a C3 failure
indicts the log-n overhead structure itself. The verdict stands as
FAILED under that rule.

POST-HOC DIAGNOSIS (labeled as such; not part of the frozen scoring):
both arms inflated (tau1 1.95x, tau2 1.31x vs the simulator's central
medians), the pattern of a live rate ~0.538-0.545 rather than the
pilot's 0.558 (2.5-4 pilot standard errors, or genuine day-to-day
drift of small-model sampled decoding — reinforcing finding F12's
scale boundary a second way: at 3B scale even a 4,000-sample
same-population pilot does not pin the live rate for the next day).
Under that rate correction the predicted ratio moves to ~0.29 and the
observed 0.257 sits within 20-rep median noise of it — but the frozen
window edge was 0.258 and the observed ratio is 0.2566: the test
fails by 0.0014, and pre-registration means exactly that it is not
re-scored after the fact. Validity was perfect throughout: 40/40
correct UNSAFE certifications, zero SAFE, zero wrong.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_severe_live.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_severe_live.txt'}")
