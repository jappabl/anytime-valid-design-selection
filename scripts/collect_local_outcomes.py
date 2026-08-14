#!/usr/bin/env python3
"""Collect JSON-task outcome pools from LOCAL models via Ollama.

Cross-vendor generalization testbed: identical protocol to
recollect_json_full.py (same StratifiedDiverseJSONDataset(250, seed=42),
same decimal-aware JSONSchemaValidator, temperature 0, one user message,
600-token cap), pointed at local models so there is no API cost and no
rate cap. Resumable: already-collected ids are skipped on restart.

Outputs per model:
  data/llm_outcomes_diverse_json_<tag>.jsonl   (canonical prompt order)
  data/json_generations_<tag>.jsonl            (raw generations)
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset
from eval_harness.validators.json_schema import JSONSchemaValidator

SEED = 42
MAX_TOKENS = 600
OLLAMA_URL = "http://localhost:11434/api/chat"
MODELS = {
    "llama3.2:3b": "llama3.2-3b",
    "qwen2.5:7b": "qwen2.5-7b",
    "llama3.1:8b": "llama3.1-8b",
    "llama3:8b": "llama3-8b",
    "qwen2:7b": "qwen2-7b",
}


def ollama_chat(model, prompt_text, retries=3):
    payload = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 1.0,
                    "num_predict": MAX_TOKENS, "seed": SEED},
        "messages": [{"role": "user", "content": prompt_text}],
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())["message"]["content"] or ""
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    args = parser.parse_args()

    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250, seed=SEED)
    all_prompts = [(s, p) for s in dataset.STRATA
                   for p in dataset.get_stratum_prompts(s)]
    validator = JSONSchemaValidator()

    for model in args.models:
        tag = MODELS[model]
        out_path = REPO / "data" / f"llm_outcomes_diverse_json_{tag}.jsonl"
        gen_path = REPO / "data" / f"json_generations_{tag}.jsonl"
        part_path = REPO / "data" / f".partial_{tag}.jsonl"

        done = {}
        if part_path.exists():
            for line in open(part_path):
                rec = json.loads(line)
                done[rec["id"]] = rec
        print(f"[{model}] {len(done)} already collected, "
              f"{len(all_prompts) - len(done)} to go", flush=True)

        part_fh = open(part_path, "a")
        gen_fh = open(gen_path, "a")
        t0 = time.time()
        n_new = 0
        for stratum, prompt in all_prompts:
            if prompt.id in done:
                continue
            text = ollama_chat(model, prompt.text)
            result = validator.validate(text, sample_id=prompt.id,
                                        schema=prompt.metadata["schema"])
            rec = {
                "id": prompt.id, "stratum": stratum,
                "passed": result.passed,
                "failure_mode": result.failure_mode,
                "error": ((result.details or {}).get("error")
                          if not result.passed else None),
            }
            done[prompt.id] = rec
            part_fh.write(json.dumps(rec) + "\n")
            part_fh.flush()
            gen_fh.write(json.dumps(
                {"id": prompt.id, "generation": text}) + "\n")
            gen_fh.flush()
            n_new += 1
            if n_new % 50 == 0:
                rate = n_new / (time.time() - t0)
                left = (len(all_prompts) - len(done)) / max(rate, 1e-9)
                print(f"[{model}] {len(done)}/{len(all_prompts)} "
                      f"({rate:.2f}/s, ~{left/60:.0f} min left)",
                      flush=True)
        part_fh.close()
        gen_fh.close()

        with open(out_path, "w") as fh:
            for stratum, prompt in all_prompts:
                fh.write(json.dumps(done[prompt.id]) + "\n")

        print(f"[{model}] complete -> {out_path.name}", flush=True)
        for s in dataset.STRATA:
            rs = [done[p.id] for st, p in all_prompts if st == s]
            fails = sum(not r["passed"] for r in rs)
            print(f"  {s:8s}: {fails}/{len(rs)} (p = {fails/len(rs):.3f})",
                  flush=True)


if __name__ == "__main__":
    main()
