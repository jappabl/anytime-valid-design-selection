#!/usr/bin/env python3
"""LIVE sequential certification at temperature 0.7 (pre-registered design).

This is the end-to-end test of the whole pipeline with genuine decoding
stochasticity — no cached pools, every sample is a fresh API call made
sequentially within each replication, with the stopping decision taken
online from the betting CS.

Pre-registered design (fixed before launch):
  Model:        gpt-4o-mini, temperature 0.7, top_p 1.0 (no seed param)
  Task:         diverse JSON schema prompts (250/stratum), round-robin
                strata, prompt drawn uniformly within stratum each step
  Decision:     certify UNSAFE if betting LCB > tau, SAFE if UCB <= tau,
                tau = 0.15, alpha = 0.05, check at n % 4 == 0, n >= 20
  Budget:       N_MAX = 300 per replication, N_REPS = 12
  Expectation:  UNSAFE for every replication (temp-0 pool gives p* = 0.208)
  Spend cap:    $0.80 hard

Replications run in parallel threads; calls WITHIN a replication are
strictly sequential (the stopping rule sees each outcome as it arrives).
Writes results_live_certification.txt and the raw per-sample log to
data/live_certification_log.jsonl.
"""

import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from openai import OpenAI

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.stats.fast_bounds import betting_bounds
from eval_harness.validators.json_schema import JSONSchemaValidator

import argparse

_parser = argparse.ArgumentParser()
_parser.add_argument("--tau", type=float, default=0.15)
_parser.add_argument("--n-max", type=int, default=300)
_parser.add_argument("--reps", type=int, default=12)
_parser.add_argument("--max-spend", type=float, default=0.80)
_parser.add_argument("--seed-offset", type=int, default=0)
_args = _parser.parse_args()

MODEL_ID = "gpt-4o-mini"
TEMPERATURE = 0.7
TAU = _args.tau
ALPHA = 0.05
N_MIN = 20
N_MAX = _args.n_max
N_REPS = _args.reps
BASE_SEED = 42 + _args.seed_offset
MAX_SPEND = _args.max_spend
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6
STRATA = ["simple", "medium", "complex", "extreme"]

_bounds_cache = {}


def bounds(n, f):
    if (n, f) not in _bounds_cache:
        _bounds_cache[(n, f)] = betting_bounds(f, n - f, ALPHA)
    return _bounds_cache[(n, f)]


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    # Dataset seed is ALWAYS 42: the prompt population must be identical
    # across arms. seed_offset varies only the sampling RNG (BASE_SEED).
    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=42)
    stratum_prompts = {s: dataset.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()
    client = OpenAI()

    lock = threading.Lock()
    spend = {"in": 0, "out": 0}
    aborted = threading.Event()
    log_path = REPO / "data" / f"live_certification_log_tau{TAU}.jsonl" if _args.seed_offset else REPO / "data" / "live_certification_log.jsonl"
    log_fh = open(log_path, "a")

    def one_replication(rep):
        rng = np.random.default_rng(BASE_SEED + 1000 * rep)
        failures = 0
        decision, n_stop = "ABSTAIN", N_MAX
        for n in range(1, N_MAX + 1):
            if aborted.is_set():
                return None
            stratum = STRATA[(n - 1) % 4]
            prompts = stratum_prompts[stratum]
            prompt = prompts[int(rng.integers(0, len(prompts)))]
            resp = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt.text}],
                temperature=TEMPERATURE,
                top_p=1.0,
                max_tokens=600,
            )
            text = resp.choices[0].message.content or ""
            with lock:
                spend["in"] += resp.usage.prompt_tokens
                spend["out"] += resp.usage.completion_tokens
                if spend["in"] * PRICE_IN + spend["out"] * PRICE_OUT > MAX_SPEND:
                    aborted.set()
            result = validator.validate(text, sample_id=f"live_r{rep}_n{n}",
                                        schema=prompt.metadata["schema"])
            is_failure = not result.passed
            failures += is_failure
            with lock:
                log_fh.write(json.dumps({
                    "rep": rep, "n": n, "prompt_id": prompt.id,
                    "stratum": stratum, "passed": result.passed,
                }) + "\n")
                log_fh.flush()
            if n >= N_MIN and n % 4 == 0:
                lo, hi = bounds(n, failures)
                if hi <= TAU:
                    decision, n_stop = "SAFE", n
                    break
                if lo > TAU:
                    decision, n_stop = "UNSAFE", n
                    break
        return {"rep": rep, "decision": decision, "n_stop": n_stop,
                "failures": failures, "p_hat": failures / n_stop}

    results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one_replication, r) for r in range(N_REPS)]
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)
                print(f"  rep {r['rep']}: {r['decision']} at n={r['n_stop']}, "
                      f"p_hat={r['p_hat']:.3f}")

    log_fh.close()
    cost = spend["in"] * PRICE_IN + spend["out"] * PRICE_OUT

    lines = []
    lines.append("=" * 76)
    lines.append("LIVE SEQUENTIAL CERTIFICATION (temperature 0.7, NO cached pools)")
    lines.append("=" * 76)
    lines.append(f"Model: {MODEL_ID}, temp={TEMPERATURE}, tau={TAU}, "
                 f"alpha={ALPHA}, n_max={N_MAX}")
    lines.append(f"Replications completed: {len(results)}/{N_REPS}")
    lines.append(f"API spend this run: ${cost:.4f}")
    lines.append("")
    for r in sorted(results, key=lambda x: x["rep"]):
        lines.append(f"  rep {r['rep']:2d}: {r['decision']:7s} at "
                     f"n={r['n_stop']:3d}, failures={r['failures']:3d}, "
                     f"p_hat={r['p_hat']:.3f}")
    lines.append("")
    if results:
        n_unsafe = sum(r["decision"] == "UNSAFE" for r in results)
        stops = [r["n_stop"] for r in results if r["decision"] != "ABSTAIN"]
        p_hats = [r["p_hat"] for r in results]
        lines.append(f"UNSAFE decisions: {n_unsafe}/{len(results)}")
        if stops:
            lines.append(f"Median time-to-certify: {int(np.median(stops))}")
        lines.append(f"Mean p_hat at stop: {np.mean(p_hats):.4f} "
                     f"(temp-0 pool estimand was 0.2080)")
    content = "\n".join(lines) + "\n"
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print("\n" + content)
    out_name = (f"results_live_certification_tau{TAU}.txt"
                if _args.seed_offset else "results_live_certification.txt")
    (REPO / out_name).write_text(content)


if __name__ == "__main__":
    main()
