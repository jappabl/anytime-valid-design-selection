#!/usr/bin/env python3
"""SYMMETRIC full re-collection of the JSON-task outcome pools.

Why: the earlier repair (scripts/requery_json_failures.py) re-queried only
prompts recorded as FAILED. Temperature-0 decoding turned out to be only
near-deterministic (12/208 gpt-4o-mini failures flipped to pass under an
unchanged validator), so a failure-only re-query is regression-to-the-mean
selection bias — passes never got the symmetric chance to flip.

This script re-queries ALL 1000 prompts per model with the corrected
(decimal-multipleOf) validator, stores the RAW generation for every call,
and reports the two-sided flip matrix against the archived pre-fix pools,
turning decoding nondeterminism from a hidden bias into a measured
quantity. The resulting pools are a coherent single-epoch snapshot.

Outputs (per model):
  data/llm_outcomes_diverse_json*.jsonl        (overwritten, corrected)
  data/json_generations_<model>.jsonl          (raw generations, NEW)
Prior pools are already archived in data/archive_pre_multipleof_fix/.
"""

import argparse
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
PRICING = {
    "gpt-4o-mini": (0.15 / 1e6, 0.60 / 1e6),
    "gpt-4.1-nano": (0.10 / 1e6, 0.40 / 1e6),
    "gpt-4.1-mini": (0.40 / 1e6, 1.60 / 1e6),
}
FILES = {
    "gpt-4o-mini": "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-spend", type=float, default=0.80)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=SEED)
    all_prompts = [(s, p) for s in dataset.STRATA
                   for p in dataset.get_stratum_prompts(s)]
    validator = JSONSchemaValidator()
    client = OpenAI()

    archive = REPO / "data" / "archive_pre_multipleof_fix"
    lock = threading.Lock()
    spend = {"usd": 0.0}
    aborted = threading.Event()

    for model, fname in FILES.items():
        price_in, price_out = PRICING[model]
        old = {json.loads(l)["id"]: json.loads(l)["passed"]
               for l in open(archive / fname)}

        gen_path = REPO / "data" / f"json_generations_{model}.jsonl"
        gen_fh = open(gen_path, "w")

        def query(item):
            stratum, prompt = item
            if aborted.is_set():
                return None
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt.text}],
                temperature=0.0, top_p=1.0, max_tokens=MAX_TOKENS, seed=SEED,
            )
            text = resp.choices[0].message.content or ""
            with lock:
                spend["usd"] += (resp.usage.prompt_tokens * price_in
                                 + resp.usage.completion_tokens * price_out)
                if spend["usd"] > args.max_spend:
                    aborted.set()
            result = validator.validate(text, sample_id=prompt.id,
                                        schema=prompt.metadata["schema"])
            return {
                "id": prompt.id, "stratum": stratum,
                "passed": result.passed,
                "failure_mode": result.failure_mode,
                "error": ((result.details or {}).get("error")
                          if not result.passed else None),
            }, text

        records = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(query, item) for item in all_prompts]
            for fut in as_completed(futures):
                out = fut.result()
                if out is None:
                    continue
                rec, text = out
                records[rec["id"]] = rec
                gen_fh.write(json.dumps(
                    {"id": rec["id"], "generation": text}) + "\n")
        gen_fh.close()

        if aborted.is_set():
            print(f"{model}: ABORTED at spend cap — pools NOT rewritten")
            break

        # Write in canonical prompt order
        with open(REPO / "data" / fname, "w") as fh:
            for stratum, prompt in all_prompts:
                fh.write(json.dumps(records[prompt.id]) + "\n")

        # Two-sided flip matrix vs archived pre-fix pool
        pp = pf = fp = ff = 0
        for pid, rec in records.items():
            was, now = old[pid], rec["passed"]
            if was and now:
                pp += 1
            elif was and not now:
                pf += 1
            elif not was and now:
                fp += 1
            else:
                ff += 1
        print(f"{model}: flip matrix vs pre-fix pool "
              f"(pass->pass {pp}, pass->FAIL {pf}, fail->PASS {fp}, "
              f"fail->fail {ff})")
        for s in dataset.STRATA:
            rs = [r for r in records.values() if r["stratum"] == s]
            fails = sum(not r["passed"] for r in rs)
            print(f"  {s:8s}: {fails}/{len(rs)} (p = {fails/len(rs):.3f})")

    print(f"\nTotal spend this run: ${spend['usd']:.4f}")


if __name__ == "__main__":
    main()
