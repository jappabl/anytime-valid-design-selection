#!/usr/bin/env python3
"""CAPSTONE: zero-free-parameter live prediction test (pre-registered).

Classical theory (Pollak & Siegmund 1975 / Woodroofe 1982 expansion,
constants per the adversarial referee's closed form), with NO fitted
parameters, predicts the live temperature-0.7 median time-to-certify
for the single-stream mixture CS at a FRESH threshold never used in any
live run.

PRE-REGISTERED (before launch):
  Condition: gpt-4o-mini, diverse JSON prompts, round-robin strata,
    temperature 0.7, tau = 0.16, UNSAFE direction, alpha = 0.05,
    single-stream Beta-mixture CS (StratifiedUICS k=1), checks at
    n % 4 == 0, n >= 20, n_max = 2500, N_REPS = 16, spend cap $6.
  Theory: n*KL(p,0.16) = log 20 + 0.5*log n + c, c ~ 0 +/- 0.3
    (referee's closed form for this stream). At the pool rate
    p = 0.202 this gives n ~ 1045; propagating live-rate uncertainty
    p in [0.195, 0.209] (all prior live runs matched pools within
    ~1.5pp) gives the PREDICTION WINDOW:
      ** live median in [800, 1450]; >= 14/16 UNSAFE; zero SAFE. **
  Offline replay at tau=0.16 (median 1024) is consistent with the
  theory value 1045 but is NOT the prediction source.

Writes results_live_prediction.txt and data/live_prediction_log.jsonl.
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
from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.validators.json_schema import JSONSchemaValidator

MODEL_ID = "gpt-4o-mini"
TAU = 0.16
N_MAX = 2500
N_REPS = 16
MAX_SPEND = 6.00
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6
STRATA = ["simple", "medium", "complex", "extreme"]
PRED_LO, PRED_HI = 800, 1450


def main():
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")
    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=42)
    prompts = {s: dataset.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()
    client = OpenAI()
    lock = threading.Lock()
    spend = {"in": 0, "out": 0}
    aborted = threading.Event()
    log_fh = open(REPO / "data" / "live_prediction_log.jsonl", "a")

    def rep(r):
        rng = np.random.default_rng(42 + 3000 * r)
        cs = StratifiedUICS(k=1, weights=[1.0], alpha=0.05)
        failures = 0
        for n in range(1, N_MAX + 1):
            if aborted.is_set():
                return None
            s = STRATA[(n - 1) % 4]
            p = prompts[s][int(rng.integers(0, len(prompts[s])))]
            resp = client.chat.completions.create(
                model=MODEL_ID, messages=[{"role": "user", "content": p.text}],
                temperature=0.7, top_p=1.0, max_tokens=600)
            text = resp.choices[0].message.content or ""
            with lock:
                spend["in"] += resp.usage.prompt_tokens
                spend["out"] += resp.usage.completion_tokens
                if spend["in"] * PRICE_IN + spend["out"] * PRICE_OUT > MAX_SPEND:
                    aborted.set()
            res = validator.validate(text, sample_id=f"pred_r{r}_n{n}",
                                     schema=p.metadata["schema"])
            x = not res.passed
            failures += x
            cs.update(0, bool(x))
            with lock:
                log_fh.write(json.dumps({"rep": r, "n": n, "stratum": s,
                                         "passed": res.passed}) + "\n")
                log_fh.flush()
            if n >= 20 and n % 4 == 0:
                if cs.rejects_le(TAU):
                    return {"rep": r, "decision": "UNSAFE", "n": n,
                            "p_hat": failures / n}
                if cs.rejects_ge(TAU):
                    return {"rep": r, "decision": "SAFE", "n": n,
                            "p_hat": failures / n}
        return {"rep": r, "decision": "ABSTAIN", "n": N_MAX,
                "p_hat": failures / N_MAX}

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(rep, r) for r in range(N_REPS)]
        for f in as_completed(futs):
            out = f.result()
            if out:
                results.append(out)
                print(f"  rep {out['rep']}: {out['decision']} at "
                      f"n={out['n']}, p_hat={out['p_hat']:.3f}")
    log_fh.close()
    cost = spend["in"] * PRICE_IN + spend["out"] * PRICE_OUT

    lines = ["=" * 76,
             "ZERO-FIT LIVE PREDICTION TEST (pre-registered; see docstring)",
             "=" * 76,
             f"tau={TAU}, reps {len(results)}/{N_REPS}, spend ${cost:.4f}",
             f"PREDICTION: median in [{PRED_LO}, {PRED_HI}] "
             "(theory-central 1045); >= 14/16 UNSAFE; zero SAFE.", ""]
    for r in sorted(results, key=lambda x: x["rep"]):
        lines.append(f"  rep {r['rep']:2d}: {r['decision']:7s} "
                     f"n={r['n']:4d} p_hat={r['p_hat']:.3f}")
    unsafe = [r["n"] for r in results if r["decision"] == "UNSAFE"]
    n_safe = sum(1 for r in results if r["decision"] == "SAFE")
    if results:
        med = int(np.median(unsafe)) if unsafe else None
        ok = (len(unsafe) >= 14 and n_safe == 0 and med is not None
              and PRED_LO <= med <= PRED_HI)
        lines += ["", f"UNSAFE {len(unsafe)}/{len(results)}, SAFE {n_safe}, "
                  f"median {med}",
                  f"PREDICTION: {'CONFIRMED' if ok else 'FAILED'}"]
    content = "\n".join(lines) + "\n"
    ck = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "=" * 76 + f"\nChecksum (SHA256): {ck}\n" + "=" * 76 + "\n"
    print("\n" + content)
    (REPO / "results_live_prediction.txt").write_text(content)


if __name__ == "__main__":
    main()
