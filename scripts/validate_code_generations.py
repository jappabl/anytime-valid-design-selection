#!/usr/bin/env python3
"""Phase 2: validate cached code generations OFFLINE.

Each generation is executed in an isolated python subprocess (`python3 -I`)
with a timeout; the candidate `solve` function is called on the instance's
test inputs and outputs are compared (JSON-normalized, so tuples == lists)
against the reference outputs stored with the prompt.

Writes data/llm_outcomes_diverse_code_<model>.jsonl in the same format as
the JSON-task outcome pools ({id, stratum, passed, failure_mode}).
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.prompts.diverse_code_prompts import StratifiedDiverseCodeDataset

SEED = 42
TIMEOUT_S = 10

RUNNER = r"""
import json, sys
payload = json.load(open(sys.argv[1]))
ns = {}
try:
    exec(payload["code"], ns)
except Exception as e:
    print(json.dumps({"status": "exec_error", "error": str(e)[:200]}))
    sys.exit(0)
fn = ns.get("solve")
if not callable(fn):
    print(json.dumps({"status": "no_function"}))
    sys.exit(0)
outputs = []
for args in payload["tests"]:
    try:
        outputs.append(fn(*args))
    except Exception as e:
        print(json.dumps({"status": "runtime_error", "error": str(e)[:200]}))
        sys.exit(0)
try:
    print(json.dumps({"status": "ok", "outputs": outputs}))
except TypeError:
    print(json.dumps({"status": "unserializable_output"}))
"""


def extract_code(generation: str) -> str:
    text = generation.strip()
    m = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m[0].strip()
    return text


def normalize(value):
    return json.loads(json.dumps(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    args = parser.parse_args()

    gen_path = REPO / "data" / f"code_generations_{args.model}.jsonl"
    out_path = REPO / "data" / f"llm_outcomes_diverse_code_{args.model}.jsonl"

    dataset = StratifiedDiverseCodeDataset(prompts_per_stratum=80, seed=SEED)
    by_id = {p.id: p for p in dataset.get_all_prompts()}

    generations = [json.loads(line) for line in open(gen_path)]
    print(f"Validating {len(generations)} generations for {args.model}...")

    runner_path = Path(tempfile.mkdtemp()) / "runner.py"
    runner_path.write_text(RUNNER)

    results = []
    for rec in generations:
        prompt = by_id[rec["id"]]
        code = extract_code(rec["generation"])
        payload_path = runner_path.parent / "payload.json"
        payload_path.write_text(json.dumps({
            "code": code,
            "tests": prompt.metadata["tests"],
        }))
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(runner_path), str(payload_path)],
                capture_output=True, text=True, timeout=TIMEOUT_S,
            )
            out = json.loads(proc.stdout.strip()) if proc.stdout.strip() else \
                {"status": "no_output"}
        except subprocess.TimeoutExpired:
            out = {"status": "timeout"}
        except json.JSONDecodeError:
            out = {"status": "bad_runner_output"}

        if out["status"] == "ok":
            passed = normalize(out["outputs"]) == normalize(
                prompt.metadata["expected"])
            failure_mode = None if passed else "wrong_output"
        else:
            passed = False
            failure_mode = out["status"]

        results.append({
            "id": rec["id"],
            "stratum": rec["stratum"],
            "passed": passed,
            "failure_mode": failure_mode,
        })

    with open(out_path, "w") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")

    print(f"\nPer-stratum failure rates ({args.model}, code task):")
    for stratum in dataset.STRATA:
        recs = [r for r in results if r["stratum"] == stratum]
        fails = sum(not r["passed"] for r in recs)
        print(f"  {stratum:8s}: {fails}/{len(recs)} failed "
              f"(p = {fails/len(recs):.3f})")

    from collections import Counter
    modes = Counter(r["failure_mode"] for r in results if not r["passed"])
    print(f"\nFailure modes: {dict(modes)}")
    print(f"Outcomes written to: {out_path}")


if __name__ == "__main__":
    main()
