#!/usr/bin/env python3
"""Collect one temperature-0 outcome per distinct prompt from the diverse
JSON schema dataset, with token-usage accounting and a hard spend cap.

Because decoding is deterministic at temperature=0, one call per distinct
prompt fully characterizes the model's behavior on the prompt pool. The
cached outcomes then support unlimited offline sequential-evaluation
replications at zero additional API cost.

Usage:
    python3 scripts/collect_llm_outcomes.py --per-stratum 40   # pilot
    python3 scripts/collect_llm_outcomes.py --per-stratum 250  # full

Outcomes are appended to data/llm_outcomes_diverse_json.jsonl (idempotent:
already-collected prompt ids are skipped).
"""

import argparse
import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from openai import OpenAI

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.validators.json_schema import JSONSchemaValidator

SEED = 42
MAX_TOKENS = 600
# Pricing (USD per token), by model
PRICING = {
    "gpt-4o-mini": (0.15 / 1e6, 0.60 / 1e6),
    "gpt-4.1-nano": (0.10 / 1e6, 0.40 / 1e6),
    "gpt-4.1-mini": (0.40 / 1e6, 1.60 / 1e6),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-stratum", type=int, default=40)
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        choices=list(PRICING))
    parser.add_argument("--max-spend", type=float, default=1.00,
                        help="Hard cap in USD for this run")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    model_id = args.model
    price_in, price_out = PRICING[model_id]
    if model_id == "gpt-4o-mini":
        out_path = REPO / "data" / "llm_outcomes_diverse_json.jsonl"
    else:
        out_path = REPO / "data" / f"llm_outcomes_diverse_json_{model_id}.jsonl"
    out_path.parent.mkdir(exist_ok=True)

    # Load existing outcomes (idempotent restart)
    done = {}
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                rec = json.loads(line)
                done[rec["id"]] = rec
    print(f"Already collected: {len(done)} outcomes")

    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=SEED)
    todo = []
    for stratum in dataset.STRATA:
        prompts = dataset.get_stratum_prompts(stratum)[: args.per_stratum]
        todo.extend((stratum, p) for p in prompts if p.id not in done)
    print(f"To collect: {len(todo)} prompts (model={model_id}, temp=0)")

    client = OpenAI()
    validator = JSONSchemaValidator()

    lock = threading.Lock()
    spend = {"in": 0, "out": 0}
    aborted = threading.Event()

    def query(item):
        stratum, prompt = item
        if aborted.is_set():
            return None
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt.text}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=MAX_TOKENS,
            seed=SEED,
        )
        text = resp.choices[0].message.content or ""
        with lock:
            spend["in"] += resp.usage.prompt_tokens
            spend["out"] += resp.usage.completion_tokens
            cost = spend["in"] * price_in + spend["out"] * price_out
            if cost > args.max_spend:
                aborted.set()
        result = validator.validate(text, sample_id=prompt.id,
                                    schema=prompt.metadata["schema"])
        return {
            "id": prompt.id,
            "stratum": stratum,
            "text_sha": hashlib.sha256(prompt.text.encode()).hexdigest()[:16],
            "passed": result.passed,
            "failure_mode": result.failure_mode,
            "error": (result.details or {}).get("error") if not result.passed else None,
        }

    n_ok = 0
    with open(out_path, "a") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(query, item) for item in todo]
            for i, fut in enumerate(as_completed(futures)):
                try:
                    rec = fut.result()
                except Exception as e:
                    print(f"  call failed: {e}")
                    continue
                if rec is None:
                    continue
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                n_ok += 1
                if (i + 1) % 100 == 0:
                    cost = spend["in"] * price_in + spend["out"] * price_out
                    print(f"  {i+1}/{len(todo)} done, spend=${cost:.4f}")

    cost = spend["in"] * price_in + spend["out"] * price_out
    print(f"\nCollected {n_ok} new outcomes. "
          f"Tokens: {spend['in']} in / {spend['out']} out. Spend: ${cost:.4f}")
    if aborted.is_set():
        print("WARNING: aborted early — spend cap reached")

    # Per-stratum summary over EVERYTHING collected so far
    all_recs = list(done.values())
    with open(out_path) as fh:
        all_recs = [json.loads(line) for line in fh]
    print("\nPer-stratum failure rates (all collected):")
    for stratum in dataset.STRATA:
        recs = [r for r in all_recs if r["stratum"] == stratum]
        if recs:
            fails = sum(not r["passed"] for r in recs)
            print(f"  {stratum:8s}: {fails}/{len(recs)} failed "
                  f"(p = {fails/len(recs):.3f})")


if __name__ == "__main__":
    main()
