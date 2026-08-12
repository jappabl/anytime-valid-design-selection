#!/usr/bin/env python3
"""Resume the crashed capstone run (pre-registration unchanged).

The original process died on an unhandled transient API error. All
samples were logged; completed replications' stopping times are
deterministic replays of the log. This script resumes the six
mid-flight replications (replaying logged outcomes into the CS, then
continuing live) and runs the two never-started ones, with per-call
retry/backoff. Appends to the same log; writes the final
results_live_prediction.txt over the 16-rep set. The prediction window
[800, 1450], >= 14/16 UNSAFE, zero SAFE is UNCHANGED from the original
pre-registration.
"""

import hashlib, json, os, sys, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from openai import OpenAI
from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.validators.json_schema import JSONSchemaValidator

TAU, N_MAX, MAX_SPEND = 0.16, 2500, 6.00
PRICE_IN, PRICE_OUT = 0.15/1e6, 0.60/1e6
STRATA = ["simple", "medium", "complex", "extreme"]
PRED_LO, PRED_HI = 800, 1450
LOG = REPO / "data" / "live_prediction_log.jsonl"

def main():
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("no key")
    ds = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=42)
    prompts = {s: ds.get_stratum_prompts(s) for s in STRATA}
    validator = JSONSchemaValidator()
    client = OpenAI()
    lock = threading.Lock()
    spend = {"usd": 2.05}  # estimated pre-crash spend counted toward cap
    log_fh = open(LOG, "a")

    logged = defaultdict(list)
    logged_n = defaultdict(list)
    for line in open(LOG):
        r = json.loads(line)
        logged[r["rep"]].append(r["passed"])
        logged_n[r["rep"]].append(r["n"])
    # Replay invariant (audit round 2, fix #12): a permuted or gapped
    # log would silently change crossing(); fail loudly instead.
    for rep, ns in logged_n.items():
        if ns != list(range(1, len(ns) + 1)):
            raise RuntimeError(
                f"replay log for rep {rep} is not the contiguous "
                f"sequence 1..{len(ns)}; refusing to replay")

    def crossing(outcomes):
        cs = StratifiedUICS(k=1, weights=[1.0], alpha=0.05)
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

    def call_with_retry(text):
        # The org is against its 10k requests-per-day rolling cap;
        # requests free up slowly, so waits must be long and patient.
        for attempt in range(60):
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": text}],
                    temperature=0.7, top_p=1.0, max_tokens=600)
                return resp
            except Exception as e:
                wait = 90 if "429" in str(e) else min(60, 2 ** attempt)
                time.sleep(wait)
        raise RuntimeError("retries exhausted after ~90 min")

    def finish_rep(rep):
        outcomes = list(logged.get(rep, []))
        done, cs = crossing(outcomes)
        if done:
            d, n, ph = done
            return {"rep": rep, "decision": d, "n": n, "p_hat": ph}
        n = len(outcomes)
        fails = sum(1 for p in outcomes if not p)
        rng = np.random.default_rng(9000 + 31 * rep)
        while n < N_MAX:
            with lock:
                if spend["usd"] > MAX_SPEND:
                    break
            s = STRATA[n % 4]
            p = prompts[s][int(rng.integers(0, len(prompts[s])))]
            resp = call_with_retry(p.text)
            text = resp.choices[0].message.content or ""
            with lock:
                spend["usd"] += (resp.usage.prompt_tokens * PRICE_IN
                                 + resp.usage.completion_tokens * PRICE_OUT)
            res = validator.validate(text, sample_id=f"res_r{rep}_n{n+1}",
                                     schema=p.metadata["schema"])
            x = not res.passed
            n += 1
            fails += x
            cs.update(0, bool(x))
            with lock:
                log_fh.write(json.dumps({"rep": rep, "n": n, "stratum": s,
                                         "passed": res.passed}) + "\n")
                log_fh.flush()
            if n >= 20 and n % 4 == 0:
                if cs.rejects_le(TAU):
                    return {"rep": rep, "decision": "UNSAFE", "n": n,
                            "p_hat": fails / n}
                if cs.rejects_ge(TAU):
                    return {"rep": rep, "decision": "SAFE", "n": n,
                            "p_hat": fails / n}
        # Label WHY we abstained (audit round 2, fix #13): the spend cap
        # is a stopping rule and must not be silent.
        why = "budget" if spend["usd"] > MAX_SPEND else "n_max"
        return {"rep": rep, "decision": f"ABSTAIN({why})", "n": n,
                "p_hat": fails / max(n, 1)}

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(finish_rep, r) for r in range(16)]
        for f in as_completed(futs):
            out = f.result()
            results.append(out)
            print(f"  rep {out['rep']:2d}: {out['decision']} n={out['n']} "
                  f"p_hat={out['p_hat']:.3f}")
    log_fh.close()

    lines = ["=" * 76,
             "ZERO-FIT LIVE PREDICTION TEST (pre-registered; resumed after "
             "crash — see scripts/resume_live_prediction.py)",
             "=" * 76,
             f"tau={TAU}, 16 reps, est. total spend ${spend['usd']:.2f}",
             f"PREDICTION (unchanged): median in [{PRED_LO}, {PRED_HI}] "
             "(theory-central 1045); >= 14/16 UNSAFE; zero SAFE.", ""]
    for r in sorted(results, key=lambda x: x["rep"]):
        lines.append(f"  rep {r['rep']:2d}: {r['decision']:7s} "
                     f"n={r['n']:4d} p_hat={r['p_hat']:.3f}")
    unsafe = [r["n"] for r in results if r["decision"] == "UNSAFE"]
    n_safe = sum(1 for r in results if r["decision"] == "SAFE")
    med = int(np.median(unsafe)) if unsafe else None
    ok = (len(unsafe) >= 14 and n_safe == 0 and med is not None
          and PRED_LO <= med <= PRED_HI)
    lines += ["", f"UNSAFE {len(unsafe)}/16, SAFE {n_safe}, median {med}",
              f"PREDICTION: {'CONFIRMED' if ok else 'FAILED'}"]
    content = "\n".join(lines) + "\n"
    ck = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "=" * 76 + f"\nChecksum (SHA256): {ck}\n" + "=" * 76 + "\n"
    print("\n" + content)
    (REPO / "results_live_prediction.txt").write_text(content)

if __name__ == "__main__":
    main()
