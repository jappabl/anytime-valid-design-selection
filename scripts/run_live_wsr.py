#!/usr/bin/env python3
"""LIVE validation of the champion: WSR-on-blocks certification at
temperature 0.7 (pre-registered).

Every prior live run used the single-stream betting CS; the method the
scoreboard crowns (stratify -> block -> bet) has never touched a live
stream. This run closes that gap.

PRE-REGISTERED DESIGN AND PREDICTION (fixed before launch):
  Model gpt-4o-mini, temperature 0.7, top_p 1.0, no API seed param.
  Task: diverse JSON prompts (dataset seed 42), one prompt per stratum
  per block, drawn uniformly within stratum; WSR CS on the block means;
  certify UNSAFE if LCB > tau = 0.15, SAFE if UCB <= tau; alpha = 0.05;
  check every block after n >= 20; budget 600 calls per replication;
  8 replications; spend cap $0.60 hard.
  PREDICTION from offline replay (results_block_reduction.txt, live-rate
  agreement in results_live_certification.txt): UNSAFE in >= 7 of 8
  replications with median time-to-certify in [150, 450]; zero SAFE
  decisions.

Writes results_live_wsr.txt and data/live_wsr_log.jsonl.
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
from eval_harness.stats.wsr_block_cs import WSRBlockCS
from eval_harness.validators.json_schema import JSONSchemaValidator

MODEL_ID = "gpt-4o-mini"
TEMPERATURE = 0.7
TAU = 0.15
ALPHA = 0.05
N_MAX = 600
N_REPS = 8
BASE_SEED = 42
MAX_SPEND = 0.60
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6
STRATA = ["simple", "medium", "complex", "extreme"]


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=42)
    stratum_prompts = {s: dataset.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()
    client = OpenAI()

    lock = threading.Lock()
    spend = {"in": 0, "out": 0}
    aborted = threading.Event()
    log_fh = open(REPO / "data" / "live_wsr_log.jsonl", "a")

    def one_replication(rep):
        rng = np.random.default_rng(BASE_SEED + 2000 * rep)
        cs = WSRBlockCS(alpha=ALPHA)
        decision, n_stop, failures = "ABSTAIN", N_MAX, 0
        n = 0
        while n + 4 <= N_MAX:
            if aborted.is_set():
                return None
            block = []
            for s in STRATA:
                prompts = stratum_prompts[s]
                prompt = prompts[int(rng.integers(0, len(prompts)))]
                resp = client.chat.completions.create(
                    model=MODEL_ID,
                    messages=[{"role": "user", "content": prompt.text}],
                    temperature=TEMPERATURE, top_p=1.0, max_tokens=600,
                )
                text = resp.choices[0].message.content or ""
                with lock:
                    spend["in"] += resp.usage.prompt_tokens
                    spend["out"] += resp.usage.completion_tokens
                    if (spend["in"] * PRICE_IN
                            + spend["out"] * PRICE_OUT) > MAX_SPEND:
                        aborted.set()
                result = validator.validate(
                    text, sample_id=f"livewsr_r{rep}_n{n}",
                    schema=prompt.metadata["schema"])
                x = 0 if result.passed else 1
                failures += x
                block.append(x)
                n += 1
                with lock:
                    log_fh.write(json.dumps({
                        "rep": rep, "n": n, "stratum": s,
                        "prompt_id": prompt.id, "passed": result.passed,
                    }) + "\n")
                    log_fh.flush()
            cs.update(sum(block) / 4)
            if n >= 20:
                lo, hi = cs.get_bounds()
                if hi <= TAU:
                    decision, n_stop = "SAFE", n
                    break
                if lo > TAU:
                    decision, n_stop = "UNSAFE", n
                    break
        return {"rep": rep, "decision": decision, "n_stop": n_stop,
                "failures": failures, "p_hat": failures / max(n_stop, 1)}

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(one_replication, r) for r in range(N_REPS)]
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)
                print(f"  rep {r['rep']}: {r['decision']} at n={r['n_stop']}, "
                      f"p_hat={r['p_hat']:.3f}")
    log_fh.close()
    cost = spend["in"] * PRICE_IN + spend["out"] * PRICE_OUT

    lines = ["=" * 76,
             "LIVE WSR-ON-BLOCKS CERTIFICATION (temperature 0.7, "
             "pre-registered)",
             "=" * 76,
             f"Model {MODEL_ID}, tau={TAU}, alpha={ALPHA}, n_max={N_MAX}, "
             f"reps {len(results)}/{N_REPS}, spend ${cost:.4f}",
             "Pre-registered prediction: UNSAFE >= 7/8, median in "
             "[150, 450], zero SAFE.", ""]
    for r in sorted(results, key=lambda x: x["rep"]):
        lines.append(f"  rep {r['rep']}: {r['decision']:7s} at "
                     f"n={r['n_stop']:3d}, p_hat={r['p_hat']:.3f}")
    if results:
        unsafe = [r["n_stop"] for r in results if r["decision"] == "UNSAFE"]
        lines.append("")
        lines.append(f"UNSAFE: {len(unsafe)}/{len(results)}; median "
                     f"time-to-certify "
                     f"{int(np.median(unsafe)) if unsafe else None}")
        pred_ok = (len(unsafe) >= 7
                   and (not unsafe or 150 <= np.median(unsafe) <= 450)
                   and not any(r["decision"] == "SAFE" for r in results))
        lines.append(f"Pre-registered prediction: "
                     f"{'CONFIRMED' if pred_ok else 'FAILED'}")
    content = "\n".join(lines) + "\n"
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print("\n" + content)
    (REPO / "results_live_wsr.txt").write_text(content)


if __name__ == "__main__":
    main()
