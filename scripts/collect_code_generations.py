#!/usr/bin/env python3
"""Phase 1: collect raw code generations (NO execution here).

One temperature-0 call per distinct prompt from the diverse code dataset.
Raw generations are stored for offline, sandboxed validation by
scripts/validate_code_generations.py.
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

from eval_harness.prompts.diverse_code_prompts import StratifiedDiverseCodeDataset

SEED = 42
MAX_TOKENS = 600
PRICING = {
    "gpt-4o-mini": (0.15 / 1e6, 0.60 / 1e6),
    "gpt-4.1-nano": (0.10 / 1e6, 0.40 / 1e6),
    "gpt-4.1-mini": (0.40 / 1e6, 1.60 / 1e6),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-stratum", type=int, default=80)
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        choices=list(PRICING))
    parser.add_argument("--max-spend", type=float, default=0.40)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    price_in, price_out = PRICING[args.model]
    out_path = REPO / "data" / f"code_generations_{args.model}.jsonl"
    out_path.parent.mkdir(exist_ok=True)

    done = set()
    if out_path.exists():
        with open(out_path) as fh:
            done = {json.loads(line)["id"] for line in fh}
    print(f"Already collected: {len(done)}")

    dataset = StratifiedDiverseCodeDataset(prompts_per_stratum=80, seed=SEED)
    todo = []
    for stratum in dataset.STRATA:
        prompts = dataset.get_stratum_prompts(stratum)[: args.per_stratum]
        todo.extend((stratum, p) for p in prompts if p.id not in done)
    print(f"To collect: {len(todo)} prompts (model={args.model}, temp=0)")

    client = OpenAI()
    lock = threading.Lock()
    spend = {"in": 0, "out": 0}
    aborted = threading.Event()

    def query(item):
        stratum, prompt = item
        if aborted.is_set():
            return None
        resp = client.chat.completions.create(
            model=args.model,
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
            if spend["in"] * price_in + spend["out"] * price_out > args.max_spend:
                aborted.set()
        return {"id": prompt.id, "stratum": stratum, "generation": text}

    n_ok = 0
    with open(out_path, "a") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(query, item) for item in todo]
            for fut in as_completed(futures):
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

    cost = spend["in"] * price_in + spend["out"] * price_out
    print(f"Collected {n_ok} generations. Spend: ${cost:.4f}")
    if aborted.is_set():
        print("WARNING: aborted early — spend cap reached")


if __name__ == "__main__":
    main()
