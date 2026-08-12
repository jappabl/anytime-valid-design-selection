#!/usr/bin/env python3
"""AUDIT: score the law's headline accuracy claims and the frontier's
conservation window against the committed numbers.

Claims under test
  C1 THEORY.md "What survives": zero-free-parameter predictions reproduce
     the definitive grid medians "single-stream within -3%...+7%,
     UI within -5%...+4%".
  C2 THEORY.md frontier section: "The UI mixture's measured overhead
     matched (d/2)*log n with d = K + #boundary within ~1 nat at all
     three margins."
  C3 THEORY.md frontier section header: "conservation hypothesis:
     SUPPORTED", against the pre-registered window
     "epoch-split overhead within [0.7, 1.5]x of the UI mixture at each
     tau" (scripts/run_frontier.py docstring).
  C4 run_frontier.py's other pre-registration: the one-shot freeze
     variant should show "fast medians, elevated abstention".

Everything here is arithmetic on committed artifacts -- no new sampling.

Run: python3 audit/sim_law_accounting.py
"""

import json
import re
import sys
import types
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

ALPHA = 0.05
LOG1A = np.log(1 / ALPHA)
STRATA = ["simple", "medium", "complex", "extreme"]


def rates_of(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return np.array([float(np.mean(pools[s])) for s in STRATA])


def v_rr(rates, tau, safe):
    r = 1 - rates if safe else rates
    t = 1 - tau if safe else tau
    lam = w = np.full(4, 0.25)
    m = bench._inner_min(lam, r, w, t)
    return float(np.sum(lam * [bench.kl_bern(r[i], m[i]) for i in range(4)]))


def solve(V, d, c):
    f = lambda n: n * V - LOG1A - 0.5 * d * np.log(n) - c
    try:
        return brentq(f, 21.0, 1e8)
    except ValueError:
        return float("nan")


def parse(path):
    txt = open(REPO / path).read()
    rows, model, truth = [], None, None
    for line in txt.splitlines():
        m = re.match(r"\s+(gpt-[\w.-]+) \(p\* = ([\d.]+), truth (\w+)\):", line)
        if m:
            model, truth = m.group(1), m.group(3)
            continue
        m = re.match(r"\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
                     r"\s+(-?\d+)\|\s*([\d.]+)\s+(-?\d+)\|\s*([\d.]+)"
                     r"\s+(-?\d+)\|\s*([\d.]+)", line)
        if m and model:
            rows.append(dict(model=model, truth=truth, tau=float(m.group(1)),
                             v_pool=float(m.group(4)),
                             single=(int(m.group(5)), float(m.group(6))),
                             ui=(int(m.group(7)), float(m.group(8)))))
    return rows


def c1():
    print("\nC1  zero-free-parameter closed form vs the definitive grid")
    print("    single-stream: d = 1 (referee: EXACT), "
          "c = -0.5*log(2*pi*p*q*) - rho/2  [THEORY.md referee note,")
    print("    dropping its extra +0.5*log n term, which would double-count "
          "the (d/2)log n already in the law]")
    files = {"gpt-4o-mini": "llm_outcomes_diverse_json.jsonl",
             "gpt-4.1-nano": "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl"}
    rows = parse("results_overhead_law.txt")
    errs_s, errs_u = [], []
    for model, fname in files.items():
        r = rates_of(fname)
        pstar = float(r.mean())
        rho = float(np.mean(r * (1 - r)) / (pstar * (1 - pstar)))
        nb = int(np.sum((r <= 1e-12) | (r >= 1 - 1e-12)))
        c_single = -0.5 * np.log(2 * np.pi * pstar * (1 - pstar)) - rho / 2
        print(f"\n    {model}: p*={pstar:.4f} rho={rho:.4f} "
              f"c_single={c_single:+.4f}  d_UI(rule)={4 + nb}")
        print(f"      {'tau':>6} {'frac':>5} {'grid med':>9} "
              f"{'pred(single)':>13} {'err%':>7} | {'grid UI':>8} "
              f"{'pred(UI,c=0)':>13} {'err%':>7}")
        for row in rows:
            if row["model"] != model:
                continue
            safe = row["truth"] == "SAFE"
            med_s, frac_s = row["single"]
            med_u, frac_u = row["ui"]
            n_s = solve(row["v_pool"], 1.0, c_single)
            n_u = solve(v_rr(r, row["tau"], safe), 4 + nb, 0.0)
            e_s = 100 * (n_s / med_s - 1) if frac_s >= 0.9 else np.nan
            e_u = 100 * (n_u / med_u - 1) if frac_u >= 0.9 else np.nan
            if frac_s >= 0.9:
                errs_s.append(e_s)
            if frac_u >= 0.9:
                errs_u.append(e_u)
            print(f"      {row['tau']:>6.3f} {frac_s:>5.2f} {med_s:>9d} "
                  f"{n_s:>13.0f} {e_s:>7.1f} | {med_u:>8d} "
                  f"{n_u:>13.0f} {e_u:>7.1f}")
    print(f"\n    single-stream prediction error range: "
          f"[{min(errs_s):+.1f}%, {max(errs_s):+.1f}%]   "
          f"(claimed -3%..+7%)")
    print(f"    UI prediction error range (c=0, d=K+boundary): "
          f"[{min(errs_u):+.1f}%, {max(errs_u):+.1f}%]   "
          f"(claimed -5%..+4%)")
    print("    NOTE: the UI arm has no theory value for c anywhere in the "
          "repo; with c=0 the rule is far off, so the published UI "
          "numbers must have used a c estimated from data.")


def c2_c3_c4():
    print("\nC2  'UI overhead matched (d/2) log n with d=K+#boundary "
          "within ~1 nat'")
    r = rates_of("llm_outcomes_diverse_json.jsonl")
    nb = int(np.sum((r <= 1e-12) | (r >= 1 - 1e-12)))
    d = 4 + nb
    data = {0.15: (960, 15.47), 0.16: (1498, 16.00), 0.17: (2872, 18.42)}
    print(f"    d = 4 + {nb} = {d}")
    print(f"    {'tau':>6} {'median':>7} {'measured oh':>12} "
          f"{'(d/2)log n':>11} {'gap':>7}")
    gaps = []
    for tau, (med, oh) in data.items():
        pred = 0.5 * d * np.log(med)
        gaps.append(oh - pred)
        print(f"    {tau:>6.2f} {med:>7d} {oh:>12.2f} {pred:>11.2f} "
              f"{oh - pred:>+7.2f}")
    print(f"    gaps: {[round(g, 2) for g in gaps]}  -> "
          f"max |gap| = {max(abs(g) for g in gaps):.2f} nats "
          f"({'within' if max(abs(g) for g in gaps) <= 1.0 else 'NOT within'}"
          f" ~1 nat as literally claimed)")
    print(f"    with a free constant c = {np.mean(gaps):+.2f}, residuals "
          f"{[round(g - np.mean(gaps), 2) for g in gaps]} -- fine, but "
          f"then c is a fitted parameter.")

    print("\nC3  conservation window scoring (never computed in the "
          "artifact itself)")
    fr = {0.15: (15.47, 25.90), 0.16: (16.00, 27.46), 0.17: (18.42, 27.33)}
    print(f"    {'tau':>6} {'UI oh':>7} {'epoch oh':>9} {'ratio':>7} "
          f"{'in [0.7,1.5]?':>14}")
    hits = 0
    for tau, (ui, es) in fr.items():
        rr = es / ui
        ok = 0.7 <= rr <= 1.5
        hits += ok
        print(f"    {tau:>6.2f} {ui:>7.2f} {es:>9.2f} {rr:>7.3f} "
              f"{str(ok):>14}")
    print(f"    pre-registered window hit at {hits}/3 margins.  "
          f"THEORY.md heading: 'conservation hypothesis: SUPPORTED'.")
    print("    results_frontier.txt states the window in its Reading note "
          "but never computes the ratio or scores PASS/MISS.")

    print("\nC4  one-shot freeze arm vs its pre-registration "
          "('fast medians, elevated abstention')")
    os_ = {0.15: (5264, 47), 0.16: (None, 0), 0.17: (None, 0)}
    ui_ = {0.15: 960, 0.16: 1498, 0.17: 2872}
    for tau, (med, cert) in os_.items():
        print(f"    tau={tau}: one-shot median {med}, certified {cert}/200 "
              f"| UI median {ui_[tau]}")
    print("    elevated abstention: YES.  fast medians: NO -- the only "
          "measurable median (5264) is 5.5x SLOWER than the UI mixture,")
    print("    and it is a median over the 47 fastest of 200 paths "
          "(76% censored), so the true median is larger still.")
    print("    THEORY.md reports this as 'collapsed into the PREDICTED "
          "variance-risk corner', which drops the failed half.")


if __name__ == "__main__":
    print("=" * 78)
    print("AUDIT: law accounting and frontier scoring")
    print("=" * 78)
    c1()
    c2_c3_c4()
