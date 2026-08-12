#!/usr/bin/env python3
"""Collect MBPP (sanitized) outcome pools from local models via Ollama.

External-validity arc: replaces our synthetic task families with a
standard public benchmark. Source: the canonical sanitized MBPP split
(427 problems with test asserts) from the google-research repository;
the file is fetched once to data/mbpp/sanitized-mbpp.json and its
SHA256 is printed and stored alongside for the audit trail.

Protocol (frozen before collection):
- Strata: quartiles of the REFERENCE solution's non-empty line count —
  a structural difficulty proxy computable before any model runs
  (strata named q1..q4, ~107 problems each; ties broken by task_id).
- Prompt (deterministic template, one user message):
    "You are an expert Python programmer. Write a Python function for
     this task: {prompt}\n\nYour code must pass these tests:\n{tests}\n
     Output ONLY the Python code, no explanation."
- Decoding: temperature 0, top_p 1, 600 tokens (matches all pools).
- Validation: generated code (first ``` fence, else raw text) is
  exec'd in an isolated `python3 -I` subprocess with a 10s timeout,
  then the benchmark's assert statements run in the same namespace;
  pass = all asserts hold. Mirrors validate_code_generations.py.
- Resumable via data/.partial_mbpp_<tag>.jsonl.

Outputs per model:
  data/llm_outcomes_mbpp_<tag>.jsonl   (id, stratum, passed, failure_mode)
  data/mbpp_generations_<tag>.jsonl    (raw generations)
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent.parent

SEED = 42
MAX_TOKENS = 600
TIMEOUT_S = 10
OLLAMA_URL = "http://localhost:11434/api/chat"
MBPP_URL = ("https://raw.githubusercontent.com/google-research/"
            "google-research/master/mbpp/sanitized-mbpp.json")
MODELS = {
    "llama3.2:3b": "llama3.2-3b",
    "qwen2.5:7b": "qwen2.5-7b",
}

RUNNER = r"""
import json, sys
payload = json.load(open(sys.argv[1]))
ns = {}
try:
    exec(payload["code"], ns)
except Exception as e:
    print(json.dumps({"status": "exec_error", "error": str(e)[:200]}))
    sys.exit(0)
for t in payload["tests"]:
    try:
        exec(t, ns)
    except AssertionError:
        print(json.dumps({"status": "assert_fail", "test": t[:200]}))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"status": "runtime_error", "error": str(e)[:200]}))
        sys.exit(0)
print(json.dumps({"status": "ok"}))
"""


def fetch_mbpp():
    path = REPO / "data" / "mbpp" / "sanitized-mbpp.json"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        req = urllib.request.Request(MBPP_URL,
                                     headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            path.write_bytes(resp.read())
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"sanitized-mbpp.json SHA256: {sha}", flush=True)
    (path.parent / "SHA256.txt").write_text(sha + "\n")
    return json.loads(path.read_text())


def stratify(problems):
    """Quartiles of reference-solution non-empty line count."""
    def keyfn(p):
        lines = [l for l in p["code"].splitlines() if l.strip()]
        return (len(lines), p["task_id"])
    ordered = sorted(problems, key=keyfn)
    n = len(ordered)
    strata = {}
    for i, p in enumerate(ordered):
        q = min(3, i * 4 // n)
        strata[p["task_id"]] = f"q{q + 1}"
    return strata


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
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def extract_code(generation):
    m = re.findall(r"```(?:python)?\s*(.*?)```", generation, re.DOTALL)
    return m[0].strip() if m else generation.strip()


def run_tests(code, tests):
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as pf:
        json.dump({"code": code, "tests": tests}, pf)
        pf.flush()
        payload_path = pf.name
    with tempfile.NamedTemporaryFile("w", suffix=".py",
                                     delete=False) as rf:
        rf.write(RUNNER)
        rf.flush()
        runner_path = rf.name
    try:
        out = subprocess.run(
            [sys.executable, "-I", runner_path, payload_path],
            capture_output=True, text=True, timeout=TIMEOUT_S)
        line = out.stdout.strip().splitlines()
        return json.loads(line[-1]) if line else {"status": "no_output"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "harness_error", "error": str(e)[:200]}
    finally:
        Path(payload_path).unlink(missing_ok=True)
        Path(runner_path).unlink(missing_ok=True)


def main():
    problems = fetch_mbpp()
    strata = stratify(problems)
    print(f"{len(problems)} problems, strata sizes: "
          f"{[sum(1 for s in strata.values() if s == q) for q in ['q1', 'q2', 'q3', 'q4']]}",
          flush=True)

    for model, tag in MODELS.items():
        out_path = REPO / "data" / f"llm_outcomes_mbpp_{tag}.jsonl"
        gen_path = REPO / "data" / f"mbpp_generations_{tag}.jsonl"
        part_path = REPO / "data" / f".partial_mbpp_{tag}.jsonl"

        done = {}
        if part_path.exists():
            for line in open(part_path):
                rec = json.loads(line)
                done[rec["id"]] = rec
        print(f"[{model}] {len(done)} done, "
              f"{len(problems) - len(done)} to go", flush=True)

        part_fh = open(part_path, "a")
        gen_fh = open(gen_path, "a")
        t0, n_new = time.time(), 0
        for p in sorted(problems, key=lambda x: x["task_id"]):
            pid = f"mbpp_{p['task_id']}"
            if pid in done:
                continue
            tests = "\n".join(p["test_list"])
            prompt = ("You are an expert Python programmer. Write a "
                      f"Python function for this task: {p['prompt']}\n\n"
                      f"Your code must pass these tests:\n{tests}\n"
                      "Output ONLY the Python code, no explanation.")
            text = ollama_chat(model, prompt)
            code = extract_code(text)
            res = run_tests(code, list(p.get("test_imports", []))
                            + list(p["test_list"]))
            rec = {"id": pid, "stratum": strata[p["task_id"]],
                   "passed": res["status"] == "ok",
                   "failure_mode": (None if res["status"] == "ok"
                                    else res["status"])}
            done[pid] = rec
            part_fh.write(json.dumps(rec) + "\n")
            part_fh.flush()
            gen_fh.write(json.dumps({"id": pid, "generation": text}) + "\n")
            gen_fh.flush()
            n_new += 1
            if n_new % 25 == 0:
                rate = n_new / (time.time() - t0)
                left = (len(problems) - len(done)) / max(rate, 1e-9)
                print(f"[{model}] {len(done)}/{len(problems)} "
                      f"({rate:.2f}/s, ~{left / 60:.0f} min left)",
                      flush=True)
        part_fh.close()
        gen_fh.close()

        with open(out_path, "w") as fh:
            for p in sorted(problems, key=lambda x: x["task_id"]):
                fh.write(json.dumps(done[f"mbpp_{p['task_id']}"]) + "\n")

        print(f"[{model}] complete -> {out_path.name}", flush=True)
        for q in ["q1", "q2", "q3", "q4"]:
            rs = [r for r in done.values() if r["stratum"] == q]
            fails = sum(not r["passed"] for r in rs)
            print(f"  {q}: {fails}/{len(rs)} (p = {fails / len(rs):.3f})",
                  flush=True)


if __name__ == "__main__":
    main()
