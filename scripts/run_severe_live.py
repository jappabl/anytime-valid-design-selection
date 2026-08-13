#!/usr/bin/env python3
"""SEVERE live test: fresh population, fresh vendor, tight frozen windows.

Designed to fix every severity defect audit round 2 found in the first
capstone (audit/AUDIT_LAW_CAPSTONE.md):
- FRESH POPULATION: dataset seed 20260812, verified 0/1000 prompt
  overlap with the seed-42 calibration population.
- FRESH VENDOR: llama3.2:3b via local Ollama (no OpenAI artifact ever
  touched this lineage live); temperature 0.7.
- TIGHT WINDOWS chosen by scripts/severity_sim.py so the test can
  actually fail: the pre-launch pass probability under
  theory + pool rates (+/-0.008 live-offset band) is COMPUTED AND
  DISCLOSED below, not discovered by auditors afterwards.
- RATIO CRITERION: C3 predicts median(tau2)/median(tau1), which
  cancels the live-vs-pool rate offset to first order and tests the
  log-n overhead structure itself.
- Crash-safe from the start: every outcome journaled to
  data/severe_live_log.jsonl before use; replay-order assertion; no
  silent stopping rules (abstains labeled; no spend cap — local
  inference is free).

FROZEN PARAMETERS (this commit is the pre-registration; the disclosed
4000-sample pilot measured p_live = 0.5580 (se 0.0053) and its samples
are never reused below). Windows from scripts/severity_sim.py at
p_live = 0.558, offsets +/-0.006, 20 reps/tau: the test passes only if
ALL of C1-C4 hold, and the pre-computed pass probability GIVEN the
theory is 0.59 (central) — this test is designed to be able to fail.
Interpretation rule, frozen now: C3 (ratio) is first-order immune to a
wrong live-rate estimate, so [C1/C2 fail, C3 pass] indicts the rate
estimate; [C3 fail] indicts the log-n overhead structure itself.
PILOT FINDING, disclosed: the temp-0 pool rate (0.485) is 7.3pp below
the live temp-0.7 rate at this model scale — temp-0 replay pools do
NOT transfer to sampled decoding for 3B models (they did at 4o-mini
scale, ~0.5pp); windows are therefore pilot-centered, not
pool-centered.
"""

import json
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.validators.json_schema import JSONSchemaValidator

# ----- FROZEN (values set at freeze commit; runner refuses PLACEHOLDER)
MODEL = "llama3.2:3b"
POP_SEED = 20260812
TAU1 = 0.49                   # harder margin (pilot p_live - 0.068)
TAU2 = 0.45                   # easier margin (pilot p_live - 0.108)
REPS_PER_TAU = 20
WIN_C1 = (396, 632)           # median window at TAU1
WIN_C2 = (148, 240)           # median window at TAU2
WIN_C3 = (0.258, 0.561)       # ratio median(TAU2)/median(TAU1)
SEVERITY = "0.59 central; 0.31/0.45 at +/-0.006 pilot-error band"
# C4: zero SAFE certifications across all reps (both taus are on the
# UNSAFE side of the pool rate by construction).
# ----------------------------------------------------------------------

ALPHA = 0.05
N_MAX = 4000
LOG = REPO / "data" / "severe_live_log.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"
STRATA = ["simple", "medium", "complex", "extreme"]


def ollama_chat(text, retries=5):
    payload = json.dumps({
        "model": MODEL, "stream": False,
        "options": {"temperature": 0.7, "top_p": 1.0, "num_predict": 600},
        "messages": [{"role": "user", "content": text}],
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())["message"]["content"] or ""
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def main():
    frozen = [TAU1, TAU2, REPS_PER_TAU, WIN_C1, WIN_C2, WIN_C3, SEVERITY]
    if any(v == "PLACEHOLDER" for v in frozen):
        sys.exit("refusing to run: frozen parameters not set")

    ds = StratifiedDiverseJSONDataset(prompts_per_stratum=250,
                                      seed=POP_SEED)
    prompts = {s: ds.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()

    logged = defaultdict(list)
    if LOG.exists():
        for line in open(LOG):
            r = json.loads(line)
            logged[(r["arm"], r["rep"])].append(r)
        for key, rows in logged.items():
            ns = [r["n"] for r in rows]
            if ns != list(range(1, len(ns) + 1)):
                raise RuntimeError(f"journal for {key} not contiguous")
    log_fh = open(LOG, "a")

    def run_rep(arm, tau, rep):
        cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
        n = 0
        fails = 0
        for r in logged.get((arm, rep), []):
            n += 1
            fails += int(not r["passed"])
            cs.update(0, not r["passed"])
        rng = np.random.default_rng(31_000_000 + 1009 * rep
                                    + (0 if arm == "tau1" else 500))
        # fast-forward the prompt rng over replayed samples
        for _ in range(n):
            rng.integers(0, 250)
        while n < N_MAX:
            s = STRATA[n % 4]
            p = prompts[s][int(rng.integers(0, 250))]
            text = ollama_chat(p.text)
            res = validator.validate(text, sample_id=f"{arm}_r{rep}_n{n+1}",
                                     schema=p.metadata["schema"])
            n += 1
            fails += int(not res.passed)
            cs.update(0, not res.passed)
            log_fh.write(json.dumps(
                {"arm": arm, "rep": rep, "n": n, "stratum": s,
                 "passed": res.passed}) + "\n")
            log_fh.flush()
            if n >= 20 and n % 4 == 0:
                if cs.rejects_le(tau):
                    return "UNSAFE", n, fails / n
                if cs.rejects_ge(tau):
                    return "SAFE", n, fails / n
        return "ABSTAIN(n_max)", n, fails / max(n, 1)

    results = {"tau1": [], "tau2": []}
    for arm, tau in [("tau1", TAU1), ("tau2", TAU2)]:
        for rep in range(REPS_PER_TAU):
            d, n, ph = run_rep(arm, tau, rep)
            results[arm].append((d, n, ph))
            print(f"  {arm} rep {rep:2d}: {d:14s} n={n:5d} "
                  f"p_hat={ph:.3f}", flush=True)

    m1 = int(np.median([n for d, n, _ in results["tau1"]
                        if d == "UNSAFE"]))
    m2 = int(np.median([n for d, n, _ in results["tau2"]
                        if d == "UNSAFE"]))
    n_safe = sum(1 for arm in results for d, _, _ in results[arm]
                 if d == "SAFE")
    ratio = m2 / m1
    c1 = WIN_C1[0] <= m1 <= WIN_C1[1]
    c2 = WIN_C2[0] <= m2 <= WIN_C2[1]
    c3 = WIN_C3[0] <= ratio <= WIN_C3[1]
    c4 = n_safe == 0
    print(f"\nC1 median(tau1={TAU1}) = {m1} in {WIN_C1}: "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"C2 median(tau2={TAU2}) = {m2} in {WIN_C2}: "
          f"{'PASS' if c2 else 'FAIL'}")
    print(f"C3 ratio = {ratio:.3f} in {WIN_C3}: "
          f"{'PASS' if c3 else 'FAIL'}")
    print(f"C4 zero SAFE: {n_safe} SAFE: {'PASS' if c4 else 'FAIL'}")
    print(f"pre-disclosed severity P(all|theory+band) = {SEVERITY}")
    print(f"\nSEVERE TEST VERDICT: "
          f"{'ALL CRITERIA PASS' if c1 and c2 and c3 and c4 else 'FAILED'}")


if __name__ == "__main__":
    main()
