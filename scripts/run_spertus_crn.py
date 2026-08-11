#!/usr/bin/env python3
"""CRN censored-median comparison: Spertus+greedy vs incumbent winners.

The full-scale baseline run showed Spertus+greedy with FASTER medians
when it certifies but nonzero abstention. Under the scoreboard's
censoring convention (abstain = n_max), boxes could flip on three
conditions. Same CRN + paired-bootstrap protocol as
results_uncertainty.txt. Writes results_spertus_crn.txt.
"""
import hashlib, io, sys, types
from contextlib import redirect_stdout
from pathlib import Path
import numpy as np

REPO = Path("/Users/hlin/Documents/badminton/code/research")
sys.path.insert(0, str(REPO / "src"))
sp_src = open(REPO / "scripts" / "run_spertus_baseline.py").read().rsplit("if __name__", 1)[0]
sp = types.ModuleType("sp"); sp.__dict__["__file__"] = str(REPO / "scripts" / "run_spertus_baseline.py")
exec(sp_src, sp.__dict__)
ug_src = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
ug = types.ModuleType("ug"); ug.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(ug_src, ug.__dict__)

N_REPS, N_BOOT = 300, 10000

def times_for(arm, pools, tau, truth, n_max):
    out = np.empty(N_REPS)
    for r in range(N_REPS):
        rng = np.random.default_rng(42 + 7919 * r)
        if arm == "spertus":
            d, n = sp.run_spertus(pools, tau, truth, rng, n_max, "greedy")
        elif arm == "wsr":
            d, n = sp.run_wsr(pools, tau, truth, rng, n_max)
        elif arm == "directed":
            ug.N_MAX = n_max
            d, n = ug.run_bonf_directed(pools, tau, rng)
        else:
            ug.N_MAX = n_max
            d, n = ug.run_single_stream(pools, tau, rng)
        out[r] = n if d == truth else n_max
    return out

def main():
    print("=" * 72)
    print("CRN CENSORED-MEDIAN: Spertus+greedy vs incumbent box-holders")
    print("=" * 72)
    print(f"{N_REPS} reps, {N_BOOT} bootstrap resamples, abstain censored "
          "at n_max\n")
    conds = [
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.15, "UNSAFE",
         2000, "directed"),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         0.15, "SAFE", 2000, "single"),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         0.11, "SAFE", 4000, "wsr"),
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.17, "UNSAFE",
         4000, "wsr"),
    ]
    brng = np.random.default_rng(4242)
    for model, fname, tau, truth, n_max, incumbent in conds:
        pools = sp.load(fname)
        t_sp = times_for("spertus", pools, tau, truth, n_max)
        t_in = times_for(incumbent, pools, tau, truth, n_max)
        diff = np.median(t_in) - np.median(t_sp)
        idx = brng.integers(0, N_REPS, size=(N_BOOT, N_REPS))
        d = np.median(t_in[idx], axis=1) - np.median(t_sp[idx], axis=1)
        lo, hi = np.percentile(d, [2.5, 97.5])
        if lo > 0:
            verdict = "SPERTUS TAKES THE BOX"
        elif hi < 0:
            verdict = "incumbent holds"
        else:
            verdict = "TIE"
        print(f"  {model} tau={tau} ({truth}) vs {incumbent}:")
        print(f"    censored medians: spertus {np.median(t_sp):.0f} vs "
              f"{incumbent} {np.median(t_in):.0f}; diff {diff:+.0f}, "
              f"95% CI [{lo:+.0f},{hi:+.0f}] -> {verdict}")

if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 72 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 72 + "\n"
    print(content, end="")
    (REPO / "results_spertus_crn.txt").write_text(content)
