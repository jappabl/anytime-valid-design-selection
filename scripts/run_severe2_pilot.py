#!/usr/bin/env python3
"""Disclosed pilot for SEVERE TEST V2 (gpt-4o-mini — the stable-rate scale).

V1 failed because 3B live rates drift day-to-day (results_severe_live.txt).
gpt-4o-mini is the scale where live-vs-pool agreement was ~0.5pp, so the
rate input is pinnable and windows centered here test the THEORY. Same
disclosure rules: pilot samples never reused in the test.

Draws 3,000 temperature-0.7 samples from gpt-4o-mini on the FRESH
population (seed 20260812), round-robin across strata, to estimate the
live failure rate before any prediction windows are frozen. Rationale: severity_sim.py showed a +/-0.008 live-vs-pool
offset moves medians more than any tight window tolerates, so windows
centered on the pool rate would test the offset, not the theory.
Centering on a pilot estimate decouples them.

Rules: this pilot is DISCLOSED in the freeze; its samples are never
reused in the test (the test uses fresh RNG streams and its own
journal); the pilot also yields the per-stratum temp-0-vs-temp-0.7
comparison for llama as a methodology datapoint.

Writes data/severe2_pilot_log.jsonl (journaled, resumable) and prints
per-stratum and pooled rates.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.validators.json_schema import JSONSchemaValidator

MODEL = "gpt-4o-mini"
POP_SEED = 20260812
N_PILOT = 3000
LOG = REPO / "data" / "severe2_pilot_log.jsonl"
STRATA = ["simple", "medium", "complex", "extreme"]

from openai import OpenAI
_client = OpenAI()


def ollama_chat(text, retries=60):
    # OpenAI transport (name kept so the rest of the script is
    # unchanged); patient on 429s because of the org's 10k RPD cap.
    for attempt in range(retries):
        try:
            resp = _client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": text}],
                temperature=0.7, top_p=1.0, max_tokens=600)
            return resp.choices[0].message.content or ""
        except Exception as e:
            wait = 90 if "429" in str(e) else min(60, 2 ** attempt)
            time.sleep(wait)
    raise RuntimeError("retries exhausted")


def main():
    ds = StratifiedDiverseJSONDataset(prompts_per_stratum=250,
                                      seed=POP_SEED)
    prompts = {s: ds.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()

    done = 0
    if LOG.exists():
        done = sum(1 for _ in open(LOG))
    print(f"pilot: {done} already journaled, {N_PILOT - done} to go",
          flush=True)
    rng = np.random.default_rng(77_000_000)
    for _ in range(done):
        rng.integers(0, 250)

    log_fh = open(LOG, "a")
    t0 = time.time()
    for n in range(done, N_PILOT):
        s = STRATA[n % 4]
        p = prompts[s][int(rng.integers(0, 250))]
        text = ollama_chat(p.text)
        res = validator.validate(text, sample_id=f"pilot_n{n+1}",
                                 schema=p.metadata["schema"])
        log_fh.write(json.dumps(
            {"n": n + 1, "stratum": s, "passed": res.passed}) + "\n")
        log_fh.flush()
        if (n + 1) % 200 == 0:
            rate = (n + 1 - done) / (time.time() - t0)
            print(f"  {n + 1}/{N_PILOT} ({rate:.2f}/s, "
                  f"~{(N_PILOT - n - 1) / rate / 60:.0f} min left)",
                  flush=True)
    log_fh.close()

    per = {s: [] for s in STRATA}
    for line in open(LOG):
        r = json.loads(line)
        per[r["stratum"]].append(0 if r["passed"] else 1)
    rates = {s: float(np.mean(v)) for s, v in per.items()}
    pooled = float(np.mean([rates[s] for s in STRATA]))
    se = float(np.sqrt(np.mean([rates[s] * (1 - rates[s])
                                / len(per[s]) for s in STRATA]) / 4))
    print("\nPILOT ESTIMATES (temperature 0.7, fresh population):")
    for s in STRATA:
        print(f"  {s:8s}: {sum(per[s])}/{len(per[s])} "
              f"(p = {rates[s]:.3f})")
    print(f"  pooled p_live = {pooled:.4f} (se ~ {se:.4f})")


if __name__ == "__main__":
    main()
