#!/usr/bin/env python3
"""Auto-select validation: does the shipped dispatch match the oracle?

ISEF_PLAN 2.2. Certifier.auto_select dispatches between the two
designs the library ships ("single" k=1 mixture vs "wsr" blocks) from
a 120-sample pilot's shrunk heterogeneity ratio. This experiment
measures, across all eight pools and both decision directions, how
often that automatic choice matches the oracle-best design and what a
miss costs. The pilot tax (120 samples) is charged to the auto arm
explicitly.

Cells: 8 pools x 2 directions; tau = p* -/+ 0.045 (UNSAFE/SAFE),
clipped to [0.02, 0.9]; 200 reps/cell/design; n_max 6000. Oracle =
lower median among designs certifying >= 90% (ineligible designs
excluded; if none eligible the cell is reported UNRESOLVED and not
scored). Auto arm: per rep, a fresh 120-sample round-robin pilot
chooses the design, then a fresh stream runs it; auto total = 120 +
certification n.

PRE-REGISTERED PREDICTIONS:
  P1 auto matches the oracle design in >= 12 of the scoreable cells.
  P2 mean auto regret (auto_median / (oracle_median + 120) - 1,
     pilot-tax-adjusted on both sides) <= 0.15; worst cell <= 0.60.
  P3 wrong certifications <= alpha per cell (no zero-claims).

Offline, deterministic. Writes results_auto_select.txt.
"""

import hashlib
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.certify import Certifier  # noqa: E402

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 200
N_MAX = 6000
PILOT_N = 120
POOLS = [
    ("gpt4omini-json", "llm_outcomes_diverse_json.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt41nano-json", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt41mini-json", "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("gpt4omini-code", "llm_outcomes_diverse_code_gpt-4o-mini.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("llama32-json", "llm_outcomes_diverse_json_llama3.2-3b.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("qwen25-json", "llm_outcomes_diverse_json_qwen2.5-7b.jsonl",
     ["simple", "medium", "complex", "extreme"]),
    ("llama32-mbpp", "llm_outcomes_mbpp_llama3.2-3b.jsonl",
     ["q1", "q2", "q3", "q4"]),
    ("qwen25-mbpp", "llm_outcomes_mbpp_qwen2.5-7b.jsonl",
     ["q1", "q2", "q3", "q4"]),
]


def load(fname, strata):
    pools = {s: [] for s in strata}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def run_design(pools, strata, tau, truth, rng, kind):
    k = len(strata) if kind == "wsr" else 1
    c = Certifier(tau=tau, alpha=ALPHA, k=k, method=(
        "wsr" if kind == "wsr" else "mixture"))
    for n in range(1, N_MAX + 1):
        i = (n - 1) % len(strata)
        y = bool(pools[strata[i]][int(
            rng.integers(0, len(pools[strata[i]])))])
        v = c.update(y, stratum=i if kind == "wsr" else 0)
        if v != "CONTINUE":
            return v, n
    return "ABSTAIN", N_MAX


def main():
    print("=" * 76)
    print("AUTO-SELECT VALIDATION (predictions pre-registered in header)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/cell/design, pilot {PILOT_N}, "
          f"n_max={N_MAX}, BASE_SEED={BASE_SEED}\n")

    matches, regrets, unresolved, wrong_flags = 0, [], 0, 0
    scoreable = 0
    for pi, (label, fname, strata) in enumerate(POOLS):
        pools = load(fname, strata)
        p_star = float(np.mean([pools[s].mean() for s in strata]))
        for di, (direction, tau) in enumerate([
                ("UNSAFE", round(min(0.9, max(0.02, p_star - 0.045)), 3)),
                ("SAFE", round(min(0.9, max(0.02, p_star + 0.045)), 3))]):
            truth = "UNSAFE" if p_star > tau else "SAFE"
            meds, ok_fracs, wrongs = {}, {}, {}
            for kind in ("single", "wsr"):
                rng = np.random.default_rng(
                    BASE_SEED + 10_000 * pi + 1000 * di
                    + (0 if kind == "single" else 500))
                outs = [run_design(pools, strata, tau, truth, rng, kind)
                        for _ in range(N_REPS)]
                dec = [n for d, n in outs if d == truth]
                wrongs[kind] = sum(1 for d, _ in outs
                                   if d not in (truth, "ABSTAIN"))
                ok_fracs[kind] = len(dec) / N_REPS
                meds[kind] = int(np.median(dec)) if dec else None
            eligible = {k: m for k, m in meds.items()
                        if m and ok_fracs[k] >= 0.9}
            if not eligible:
                unresolved += 1
                print(f"  {label:15s} {direction}: UNRESOLVED "
                      f"(no design certifies >= 90%)")
                continue
            oracle = min(eligible, key=eligible.get)
            # auto arm: per-rep pilot choice + fresh certification
            rng = np.random.default_rng(
                BASE_SEED + 10_000 * pi + 1000 * di + 777)
            auto_ns, auto_choices, auto_wrong = [], [], 0
            for rep in range(N_REPS):
                pilot = []
                for n in range(PILOT_N):
                    i = n % len(strata)
                    y = bool(pools[strata[i]][int(
                        rng.integers(0, len(pools[strata[i]])))])
                    pilot.append((i, y))
                kind, _ = Certifier.auto_select(pilot)
                auto_choices.append(kind)
                d, n = run_design(pools, strata, tau, truth, rng, kind)
                if d == truth:
                    auto_ns.append(PILOT_N + n)
                elif d != "ABSTAIN":
                    auto_wrong += 1
            maj = max(set(auto_choices), key=auto_choices.count)
            auto_med = int(np.median(auto_ns)) if auto_ns else None
            scoreable += 1
            match = maj == oracle
            matches += match
            reg = (auto_med / (eligible[oracle] + PILOT_N) - 1
                   if auto_med else None)
            if reg is not None:
                regrets.append(reg)
            wrong_flags += (wrongs["single"] > ALPHA * N_REPS) \
                + (wrongs["wsr"] > ALPHA * N_REPS) \
                + (auto_wrong > ALPHA * N_REPS)
            print(f"  {label:15s} {direction}: oracle {oracle:6s} "
                  f"(meds {meds}), auto chose {maj} "
                  f"({auto_choices.count(maj)}/{N_REPS}), "
                  f"auto med {auto_med} -> "
                  f"{'MATCH' if match else 'MISS'}, regret "
                  f"{reg:+.2f}" if reg is not None else "n/a")

    print(f"\n  P1 oracle match: {matches}/{scoreable} scoreable cells "
          f"(need >= 12): {'PASS' if matches >= 12 else 'FAIL'}")
    mr = float(np.mean(regrets)) if regrets else float("nan")
    wr = float(np.max(regrets)) if regrets else float("nan")
    print(f"  P2 regret: mean {mr:+.3f} (<= 0.15: "
          f"{'PASS' if mr <= 0.15 else 'FAIL'}), worst {wr:+.2f} "
          f"(<= 0.60: {'PASS' if wr <= 0.60 else 'FAIL'})")
    print(f"  P3 cells exceeding the alpha wrong-cert budget: "
          f"{wrong_flags} (0 required): "
          f"{'PASS' if wrong_flags == 0 else 'FAIL'}")
    print(f"  unresolved cells (excluded): {unresolved}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_auto_select.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_auto_select.txt'}")
