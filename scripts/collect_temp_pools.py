#!/usr/bin/env python3
"""Temp>0 per-prompt rate pools: the collection that lifts F14's K<=4 limit.

The committed temp-0 pools have degenerate per-prompt rates (0/1), so
the finest honest stratification was the four designed strata. This
collects PER-PROMPT FAILURE RATES: M=24 sampled draws per prompt at
temperature 0.7, giving each prompt a rate in {0/24..24/24} — a real
difficulty signal supporting quantile stratification at K up to ~12.

DESIGN (frozen before any analysis):
- Prompts: first 50 per stratum (200 total) of the SAME seeded
  StratifiedDiverseJSONDataset(seed=SEED) used by every JSON pool —
  deterministic subset, no selection.
- Draws: M=24 per prompt, temperature 0.7, top_p 1.0, options.seed =
  draw index (reproducible sampling).
- SPLIT-DRAWS RULE for all downstream analysis: EVEN draw indices form
  the STRATIFICATION SIGNAL, ODD draw indices form the EVALUATION
  pool. Stratifying and evaluating on the same draws would self-select
  (a prompt lucky in the signal is lucky in the pool); the split makes
  the signal an independent noisy difficulty estimate, like MBPP's
  line-count. Stated here so no later analysis can quietly violate it.
- Journaled/resumable: one line per (prompt, draw) appended to
  data/llm_temp_outcomes_<model>.jsonl; reruns skip completed pairs.
- Record: {id, stratum, draw, passed} — same non-sensitive shape as
  the temp-0 pools.

Validator: the same decimal-aware JSONSchemaValidator. Models: local
Ollama only. Runtime ~2h (3B) to ~5h (7-9B) per model; run in
background, machine-sleep safe.
"""

import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.prompts.diverse_json_prompts import StratifiedDiverseJSONDataset  # noqa: E402
from eval_harness.validators.json_schema import JSONSchemaValidator  # noqa: E402

SEED = 42
PER_STRATUM = 50
M_DRAWS = 24
OLLAMA_URL = "http://localhost:11434/api/chat"


def ollama_chat(model, prompt_text, draw_seed, retries=3):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 1.0,
                    "num_predict": 700, "seed": draw_seed},
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read())["message"]["content"]
        except Exception:
            if attempt == retries - 1:
                raise
    return ""


def collect(model):
    dataset = StratifiedDiverseJSONDataset(prompts_per_stratum=250,
                                           seed=SEED)
    prompts = [(s, p) for s in dataset.STRATA
               for p in dataset.get_stratum_prompts(s)[:PER_STRATUM]]
    validator = JSONSchemaValidator()
    tag = model.replace(":", "-")
    out = REPO / "data" / f"llm_temp_outcomes_{tag}.jsonl"
    done = set()
    if out.exists():
        for line in open(out):
            r = json.loads(line)
            done.add((r["id"], r["draw"]))
    todo = [(s, p, d) for s, p in prompts for d in range(M_DRAWS)
            if (p.id, d) not in done]
    print(f"{model}: {len(todo)} calls to go "
          f"({len(done)} already journaled)", flush=True)
    with open(out, "a") as fh:
        for k, (stratum, prompt, draw) in enumerate(todo):
            text = ollama_chat(model, prompt.text, draw)
            res = validator.validate(text, prompt.id,
                                     schema=prompt.metadata["schema"])
            fh.write(json.dumps({
                "id": prompt.id, "stratum": stratum, "draw": draw,
                "passed": bool(res.passed)}) + "\n")
            fh.flush()
            if (k + 1) % 200 == 0:
                print(f"  {k + 1}/{len(todo)}", flush=True)
    print(f"{model}: complete -> {out.name}", flush=True)


if __name__ == "__main__":
    for m in (sys.argv[1:] or ["llama3.2:3b"]):
        collect(m)
