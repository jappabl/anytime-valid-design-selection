#!/usr/bin/env python3
"""AUDIT: reproduce and stress the "d = K + #boundary wins 3-for-3" claim.

FINDINGS.md (and commit ce440af) claim, for the code pools:

    "the referee's rule hit 3-for-3 (d = 6.50/5.56/6.76 vs predicted
     6/6/7) while our window [3,5] failed on every model
     (results_overhead_law_code.txt)"

There is NO script in the repo that produces those three numbers and no
results_adjudication.txt: scripts/fit_overhead_law.py reads
results_overhead_law.txt (the JSON grid) and hard-codes RATES for only
two models. This file reconstructs the fit under the frozen recipe and
then asks how much the "3-for-3" verdict is worth.

  1. Reproduce d for each code model with the frozen recipe
     (y = n*V_rr - log(1/alpha) regressed on log n; drop points with
     certified fraction < 0.9).
  2. Count free parameters vs points.
  3. Profile: fix d at each integer, refit c only, report max|resid| and
     RSS. Which integers survive the declared <= 0.75 nat criterion?
  4. Swap test: score the WRONG assignment (predictions permuted) and
     see whether fit quality can tell them apart.
  5. Bootstrap the fitted d over grid points.
  6. Functional-form check: refit with sqrt(log n) and log log n in
     place of log n.

Run: python3 audit/sim_fit_adjudication.py
"""

import json
import re
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

ALPHA = 0.05
LOG1A = np.log(1 / ALPHA)
STRATA = ["simple", "medium", "complex", "extreme"]

CODE_FILES = {
    "gpt-4o-mini": "llm_outcomes_diverse_code_gpt-4o-mini.jsonl",
    "gpt-4.1-nano": "llm_outcomes_diverse_code_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": "llm_outcomes_diverse_code_gpt-4.1-mini.jsonl",
}
JSON_FILES = {
    "gpt-4o-mini": "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
}


def pool_rates(fname):
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
                             ui=(int(m.group(7)), float(m.group(8))),
                             wsr=(int(m.group(9)), float(m.group(10)))))
    return rows


def fit_free(pts):
    n = np.array([p[0] for p in pts], float)
    v = np.array([p[1] for p in pts], float)
    y = n * v - LOG1A
    x = np.log(n)
    A = np.vstack([x, np.ones_like(x)]).T
    (slope, c), *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ np.array([slope, c])
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else np.nan
    return 2 * slope, c, r2, resid


def fit_fixed_d(pts, d):
    n = np.array([p[0] for p in pts], float)
    v = np.array([p[1] for p in pts], float)
    y = n * v - LOG1A - 0.5 * d * np.log(n)
    c = float(np.mean(y))
    resid = y - c
    return c, resid


def fit_basis(pts, basis):
    n = np.array([p[0] for p in pts], float)
    v = np.array([p[1] for p in pts], float)
    y = n * v - LOG1A
    x = basis(n)
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return coef, 1 - float(np.sum(resid ** 2)) / ss_tot, resid


def analyze(title, grid_path, files, taus_safe, predicted):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    rows = parse(grid_path)
    for model, fname in files.items():
        rates = pool_rates(fname)
        nb = int(np.sum((rates <= 1e-12) | (rates >= 1 - 1e-12)))
        pred = 4 + nb
        pts, dropped = [], []
        for r in rows:
            if r["model"] != model:
                continue
            med, frac = r["ui"]
            if frac < 0.9 or med <= 0:
                dropped.append((r["tau"], med, frac))
                continue
            pts.append((med, v_rr(rates, r["tau"], taus_safe)))
        d, c, r2, resid = fit_free(pts)
        print(f"\n{model}: rates {np.round(rates, 5).tolist()}  "
              f"boundary={nb}  K+boundary={pred}  "
              f"(claimed elsewhere: {predicted.get(model, '?')})")
        print(f"  usable points {len(pts)} (dropped {len(dropped)}), "
              f"free parameters 2  ->  residual dof = {len(pts) - 2}")
        print(f"  FREE FIT: d = {d:.2f}, c = {c:+.2f}, R^2 = {r2:.4f}, "
              f"max|resid| = {np.max(np.abs(resid)):.2f} nats")

        print(f"  profile over fixed d (c refit):")
        print(f"    {'d':>5} {'c':>8} {'max|resid|':>11} {'RSS':>9}  pass<=0.75?")
        rows_ok = []
        for dd in range(0, 13):
            cc, rr = fit_fixed_d(pts, dd)
            mx = float(np.max(np.abs(rr)))
            ok = mx <= 0.75
            rows_ok.append((dd, mx, ok))
            print(f"    {dd:>5d} {cc:>8.2f} {mx:>11.2f} "
                  f"{float(np.sum(rr ** 2)):>9.2f}  {'YES' if ok else 'no'}")
        passing = [dd for dd, mx, ok in rows_ok if ok]
        print(f"    integers passing the declared <=0.75 nat criterion: "
              f"{passing if passing else 'none'}")

        # bootstrap over points
        rng = np.random.default_rng(4)
        ds = []
        for _ in range(4000):
            idx = rng.integers(0, len(pts), len(pts))
            try:
                ds.append(fit_free([pts[i] for i in idx])[0])
            except Exception:
                pass
        ds = np.array([x for x in ds if np.isfinite(x)])
        print(f"  bootstrap over grid points: d 95% CI "
              f"[{np.percentile(ds, 2.5):.2f}, {np.percentile(ds, 97.5):.2f}]")

        for name, b in [("sqrt(log n)", lambda n: np.sqrt(np.log(n))),
                        ("log log n", lambda n: np.log(np.log(n))),
                        ("n^0 (no term)", lambda n: np.zeros_like(n))]:
            coef, r2b, rb = fit_basis(pts, b)
            print(f"  alternative basis {name:>14}: R^2 = {r2b:.4f}, "
                  f"max|resid| = {np.max(np.abs(rb)):.2f} nats")


def swap_test():
    print("\n" + "=" * 78)
    print("SWAP TEST: can the fit tell the right prediction vector from a "
          "permuted one?")
    print("=" * 78)
    rows = parse("results_overhead_law_code.txt")
    fitted = {}
    for model, fname in CODE_FILES.items():
        rates = pool_rates(fname)
        pts = [(r["ui"][0], v_rr(rates, r["tau"], True)) for r in rows
               if r["model"] == model and r["ui"][1] >= 0.9 and r["ui"][0] > 0]
        fitted[model] = fit_free(pts)[0]
    truth = {"gpt-4o-mini": 6, "gpt-4.1-nano": 6, "gpt-4.1-mini": 7}
    perms = [
        ("K+boundary (claimed)", {"gpt-4o-mini": 6, "gpt-4.1-nano": 6,
                                  "gpt-4.1-mini": 7}),
        ("swap the 6 and the 7", {"gpt-4o-mini": 7, "gpt-4.1-nano": 6,
                                  "gpt-4.1-mini": 6}),
        ("all 6", {m: 6 for m in truth}),
        ("all 7", {m: 7 for m in truth}),
        ("all 5", {m: 5 for m in truth}),
        ("K only (all 4)", {m: 4 for m in truth}),
        ("author's frozen window mid (all 4)", {m: 4 for m in truth}),
    ]
    print(f"  fitted d: " + ", ".join(f"{m}={fitted[m]:.2f}"
                                      for m in CODE_FILES))
    print(f"\n  {'hypothesis':>36} {'sum |d_fit - d_pred|':>22} "
          f"{'max |err|':>10}")
    for name, pv in perms:
        errs = [abs(fitted[m] - pv[m]) for m in CODE_FILES]
        print(f"  {name:>36} {sum(errs):>22.2f} {max(errs):>10.2f}")
    print("\n  Reading: 'K + #boundary' and 'all 6' are nearly "
          "indistinguishable;\n  the entire discriminating content is "
          "'d is around 6, not around 4'.")


def main():
    analyze("CODE-POOL ADJUDICATION (the 3-for-3 claim)",
            "results_overhead_law_code.txt", CODE_FILES, True,
            {"gpt-4o-mini": "6.50 vs 6", "gpt-4.1-nano": "5.56 vs 6",
             "gpt-4.1-mini": "6.76 vs 7"})
    analyze("JSON GRID (for reference; fit_overhead_law.py's own target)",
            "results_overhead_law.txt", JSON_FILES, False, {})
    swap_test()


if __name__ == "__main__":
    main()
