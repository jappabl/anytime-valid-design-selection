#!/usr/bin/env python3
"""Re-label the JSON-task outcome pools after the multipleOf validator fix.

The original validator used jsonschema's float multipleOf check, which
wrongly rejects decimal multiples (e.g. 199.95 for 0.05). 59 recorded
failures across the three model pools carried that error. Because raw
generations were not stored in the original collection, every prompt
recorded as FAILED is re-queried once (temperature 0) and re-validated
with the corrected validator; this time the raw generation is stored.
Prompts recorded as PASSED cannot become failures under the corrected
(strictly more permissive) multipleOf check and are not re-queried.

Original outcome files are archived to data/archive_pre_multipleof_fix/
before the corrected files are written under the original names.
"""

import json
import os
import shutil
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
MAX_SPEND = 0.30
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
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=SEED)
    by_id = {p.id: p for s in dataset.STRATA
             for p in dataset.get_stratum_prompts(s)}
    validator = JSONSchemaValidator()
    client = OpenAI()

    archive = REPO / "data" / "archive_pre_multipleof_fix"
    archive.mkdir(exist_ok=True)

    lock = threading.Lock()
    spend = {"usd": 0.0}

    for model, fname in FILES.items():
        path = REPO / "data" / fname
        records = [json.loads(l) for l in open(path)]
        failed = [r for r in records if not r["passed"]]
        print(f"{model}: {len(failed)} recorded failures to re-query")

        price_in, price_out = PRICING[model]
        gen_log = open(REPO / "data" / f"requery_generations_{model}.jsonl", "w")

        def requery(rec):
            prompt = by_id[rec["id"]]
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt.text}],
                temperature=0.0, top_p=1.0, max_tokens=600, seed=SEED,
            )
            text = resp.choices[0].message.content or ""
            with lock:
                spend["usd"] += (resp.usage.prompt_tokens * price_in
                                 + resp.usage.completion_tokens * price_out)
                if spend["usd"] > MAX_SPEND:
                    raise RuntimeError("spend cap reached")
            result = validator.validate(text, sample_id=rec["id"],
                                        schema=prompt.metadata["schema"])
            return rec["id"], text, result

        updates = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(requery, r) for r in failed]
            for fut in as_completed(futures):
                pid, text, result = fut.result()
                updates[pid] = result
                gen_log.write(json.dumps({"id": pid, "generation": text}) + "\n")
        gen_log.close()

        shutil.copy(path, archive / fname)
        flipped = 0
        with open(path, "w") as fh:
            for r in records:
                if r["id"] in updates:
                    res = updates[r["id"]]
                    if res.passed and not r["passed"]:
                        flipped += 1
                    r = dict(r, passed=res.passed,
                             failure_mode=res.failure_mode,
                             error=((res.details or {}).get("error")
                                    if not res.passed else None))
                fh.write(json.dumps(r) + "\n")

        new_recs = [json.loads(l) for l in open(path)]
        print(f"  flipped fail->pass: {flipped}")
        for s in dataset.STRATA:
            rs = [r for r in new_recs if r["stratum"] == s]
            fails = sum(not r["passed"] for r in rs)
            print(f"  {s:8s}: {fails}/{len(rs)} (p = {fails/len(rs):.3f})")

    print(f"\nTotal re-query spend: ${spend['usd']:.4f}")
    print(f"Originals archived in: {archive}")


if __name__ == "__main__":
    main()
