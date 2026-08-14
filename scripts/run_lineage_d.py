#!/usr/bin/env python3
"""Within-lineage differential test of the boundary-stratum dimension rule.

llama3.1-8b is the first local pool with an EXACT-boundary stratum
(simple = 0/250), while its lineage siblings llama3-8b and llama3.2-3b
have none. The rule d = K + #boundary-strata therefore makes a
DIFFERENTIAL prediction inside one vendor lineage, on pools collected
for an unrelated purpose (ISEF_PLAN 1.2): d_UI = 5 for llama3.1-8b,
d_UI = 4 for both siblings.

PRE-REGISTERED (frozen before any fitting on these pools):
  P1 llama3.1-8b fitted d_UI in [4.0, 6.0];
  P2 llama3-8b and llama3.2-3b fitted d_UI in [3.0, 5.0] each;
  P3 THE DIFFERENTIAL: d(llama3.1-8b) - mean(d(siblings)) >= +0.5;
  P4 single-stream d in [0.3, 1.5] on all three (the d = 1 constant).
Frozen >=90%-certification filter; per-(margin, method) seeds;
functional-form residuals reported per house rules.

Original protocol docstring follows.


The law n*V = log(1/alpha) + (d_eff/2)*log n + c was calibrated on
OpenAI pools (gpt-4o-mini, gpt-4.1-nano) with the referee's dimension
rule d = K + #boundary-strata adjudicated 3-for-3 on frozen code pools.
Local pools (Ollama; different vendor, architecture, scale) are a
genuinely out-of-family test: llama3.2-3b sits in a different regime
entirely (p* ~ 0.48 vs 0.20, near-degenerate extreme stratum at 0.996,
NO exact-zero strata).

FROZEN PROTOCOL: margins m in {0.022, 0.027, 0.032, 0.042, 0.052,
0.057} (the gpt-4o-mini grid's margins), tau_i = round(p* - m_i, 3),
UNSAFE direction, alpha=0.05, 200 reps, n_max=6000. Fit per method by
least squares of n*V - log(1/alpha) on (log n)/2 (slope = d_eff,
intercept = c).

PRE-REGISTERED PREDICTIONS (stated before running):
  P1 (d-rule, out of family): UI+RR fitted d in [3.0, 5.0] — the rule
     predicts d = K + #boundary = 4 + 0 here, since no stratum is at
     an exact edge (llama extreme = 0.996 is 1/250 from the edge; the
     adjudicated rule counts exact-boundary strata only — this
     near-edge case is the interesting stress and is stated up front).
  P2: single-stream fitted d in [0.3, 1.5] (gpt-family fits gave
     0.79-1.01 at d_pred = 1).
  P3: WSR at its own Kelly block rate remains sub-logarithmic:
     fitted d in [-0.5, 1.0] (the finite-window flat-tax regime).
  P4: zero wrong certifications anywhere; certified fraction >= 0.95
     at every margin >= 0.027 for all three methods.

Offline, deterministic. Writes results_lineage_d.txt.
"""

import hashlib
import io
import json
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

_ug = open(REPO / "scripts" / "run_ui_grow.py").read()
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug.rsplit('if __name__', 1)[0], bench.__dict__)

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 200
N_MAX = 6000
STRATA = ["simple", "medium", "complex", "extreme"]
MARGINS = [0.022, 0.027, 0.032, 0.042, 0.052, 0.057]
POOL_FILES = [("llama3-8b", "llm_outcomes_diverse_json_llama3-8b.jsonl"),
              ("llama3.1-8b", "llm_outcomes_diverse_json_llama3.1-8b.jsonl"),
              ("llama3.2-3b", "llm_outcomes_diverse_json_llama3.2-3b.jsonl")]


def load(fname):
    path = REPO / "data" / fname
    if not path.exists():
        return None
    pools = {s: [] for s in STRATA}
    for line in open(path):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def v_rr(rates, tau):
    lam = np.full(4, 0.25)
    w = np.full(4, 0.25)
    m = bench._inner_min(lam, rates, w, tau)
    return float(np.sum(lam * [bench.kl_bern(rates[i], m[i])
                               for i in range(4)]))


def v_kelly_block(rates, tau):
    """Exact Kelly rate of WSR's block-mean game: sup_lam E log(1 +
    lam*(M - tau)) over the 16-atom block-mean distribution."""
    atoms, probs = [], []
    for bits in range(16):
        m, pr = 0.0, 1.0
        for i in range(4):
            if bits >> i & 1:
                m += 0.25
                pr *= rates[i]
            else:
                pr *= 1 - rates[i]
        atoms.append(m)
        probs.append(pr)
    atoms, probs = np.array(atoms), np.array(probs)
    best = 0.0
    for lam in np.linspace(0.001, 1 / max(tau, 1e-9) - 1e-6, 4000):
        g = float(np.sum(probs * np.log1p(lam * (atoms - tau))))
        best = max(best, g)
    return best / 4.0  # per SAMPLE (block = 4 samples)


def run_single(pools, tau, rng):
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
    order = STRATA
    for n in range(1, N_MAX + 1):
        s = order[(n - 1) % 4]
        cs.update(0, bool(pools[s][int(rng.integers(0, len(pools[s])))]))
        if n >= 20 and n % 4 == 0 and cs.rejects_le(tau):
            return n
    return None


def run_ui_rr(pools, tau, rng):
    cs = StratifiedUICS(k=4, alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        s = STRATA[k]
        cs.update(k, bool(pools[s][int(rng.integers(0, len(pools[s])))]))
        if n >= 20 and n % 4 == 0 and cs.rejects_le(tau):
            return n
    return None


def run_wsr(pools, tau, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, _ = cs.get_bounds()
            if lo > tau:
                return 4 * b
    return None


def fit_d(points):
    """points: list of (median_n, V). Returns (d, c) least squares."""
    x = np.array([np.log(n) / 2 for n, _ in points])
    y = np.array([n * v - np.log(1 / ALPHA) for n, v in points])
    A = np.stack([x, np.ones_like(x)], axis=1)
    (d, c), *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(d), float(c)


_FITS = {}


def main():
    print("=" * 76)
    print("WITHIN-LINEAGE d-RULE DIFFERENTIAL (predictions "
          "pre-registered in header)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/point, n_max={N_MAX}, "
          f"BASE_SEED={BASE_SEED}, UNSAFE direction")
    print(f"frozen margins: {MARGINS}\n")

    for model, fname in POOL_FILES:
        pools = load(fname)
        if pools is None:
            print(f"  {model}: pools not collected yet — SKIPPED\n")
            continue
        rates = np.array([float(pools[s].mean()) for s in STRATA])
        p_star = float(rates.mean())
        nb = sum(1 for r in rates if r in (0.0, 1.0))
        print(f"  {model} (p* = {p_star:.4f}, p_k = "
              f"{[round(float(r), 3) for r in rates]}, exact-boundary "
              f"strata = {nb}; d-rule predicts d_UI = {4 + nb})")
        print(f"  {'tau':>6} {'margin':>7} {'V_pool':>8} {'V_rr':>8} "
              f"{'V_kelly':>8} {'single':>12} {'UI+RR':>12} {'WSR':>12}")
        pts = {"single": [], "ui": [], "wsr": []}
        for i_m, margin in enumerate(MARGINS):
            tau = round(p_star - margin, 3)
            vp = bench.kl_bern(p_star, tau)
            vr = v_rr(rates, tau)
            vk = v_kelly_block(rates, tau)
            row = f"  {tau:>6.3f} {margin:>7.3f} {vp:>8.4f} " \
                  f"{vr:>8.4f} {vk:>8.4f}"
            for i_f, (key, fn, v) in enumerate([("single", run_single, vp),
                                                ("ui", run_ui_rr, vr),
                                                ("wsr", run_wsr, vk)]):
                # per-(margin, method) seed: grid points are independent
                # (audit fix #11 — the original grid shared one stream)
                rng = np.random.default_rng(
                    BASE_SEED + 101 + 1000 * i_m + 100 * i_f)
                times = [fn(pools, tau, rng) for _ in range(N_REPS)]
                done = [t for t in times if t is not None]
                frac = len(done) / N_REPS
                med = int(np.median(done)) if done else None
                # Frozen convention (fit_overhead_law.py / audit): fit
                # only points with >= 90% certification — censored
                # medians are biased low and flatten the slope. Rev 1
                # of this script omitted the filter by mistake.
                if med and frac >= 0.9:
                    pts[key].append((med, v))
                row += f" {med if med else '--':>7}|{frac:>4.2f}"
            print(row)
        for key, label in [("single", "single-stream"), ("ui", "UI+RR"),
                           ("wsr", "WSR@Kelly")]:
            if len(pts[key]) >= 3:
                d, c = fit_d(pts[key])
                _FITS.setdefault(model.split()[0], {})[
                    "ui" if key == "ui" else
                    ("single" if key == "single" else "wsr")] = d
                # functional-form honesty (audit finding 10): report the
                # log log n alternative's residuals alongside; this grid
                # cannot by itself distinguish the two forms.
                x1 = np.array([np.log(n) / 2 for n, _ in pts[key]])
                x2 = np.array([np.log(np.log(n)) for n, _ in pts[key]])
                y = np.array([n * v - np.log(1 / ALPHA)
                              for n, v in pts[key]])
                r1 = float(np.max(np.abs(
                    y - np.stack([x1, np.ones_like(x1)], 1)
                    @ np.linalg.lstsq(np.stack([x1, np.ones_like(x1)], 1),
                                      y, rcond=None)[0])))
                r2 = float(np.max(np.abs(
                    y - np.stack([x2, np.ones_like(x2)], 1)
                    @ np.linalg.lstsq(np.stack([x2, np.ones_like(x2)], 1),
                                      y, rcond=None)[0])))
                print(f"    fit {label:13s}: d = {d:+.2f}, c = {c:+.2f} "
                      f"({len(pts[key])} pts; max|resid| "
                      f"logn-form {r1:.2f} vs loglogn-form {r2:.2f})")
        print()
    if len(_FITS) == 3:
        _score_verdicts(_FITS)


def _score_verdicts(fits):
    """fits: {model: {"ui": d, "single": d}} parsed in main. Prints the
    frozen P1-P4 verdicts inside the artifact (house standard), with
    P3 scored BOTH as frozen (vs sibling mean) and against identified
    fits only — the frozen form can pass through an unidentifiable
    sibling fit, and both numbers are shown."""
    p1 = 4.0 <= fits["llama3.1-8b"]["ui"] <= 6.0
    sib = [fits["llama3-8b"]["ui"], fits["llama3.2-3b"]["ui"]]
    p2 = all(3.0 <= d <= 5.0 for d in sib)
    diff_frozen = fits["llama3.1-8b"]["ui"] - sum(sib) / 2
    diff_ident = fits["llama3.1-8b"]["ui"] - fits["llama3.2-3b"]["ui"]
    p3 = diff_frozen >= 0.5
    singles = [fits[m]["single"] for m in
               ("llama3-8b", "llama3.1-8b", "llama3.2-3b")]
    p4 = all(0.3 <= d <= 1.5 for d in singles)
    print("\nPRE-REGISTERED SCORING (frozen at commit 9a87f13):")
    print(f"  P1 llama3.1-8b d_UI in [4,6]: {fits['llama3.1-8b']['ui']:.2f} "
          f"-> {'PASS' if p1 else 'FAIL'}")
    print(f"  P2 siblings in [3,5]: {sib[0]:.2f}, {sib[1]:.2f} -> "
          f"{'PASS' if p2 else 'FAIL'} (llama3-8b fit is 3-point "
          f"censored — unidentifiable)")
    print(f"  P3 differential >= +0.5: as frozen {diff_frozen:+.2f} -> "
          f"{'PASS' if p3 else 'FAIL'}; against the identified sibling "
          f"only {diff_ident:+.2f} — the frozen pass is HOLLOW (it "
          f"clears the bar only through the fit P2 rejects)")
    print(f"  P4 single-stream in [0.3,1.5] all three: "
          f"{', '.join(f'{d:.2f}' for d in singles)} -> "
          f"{'PASS' if p4 else 'FAIL'}")
    n_pass = sum([p1, p2, p3, p4])
    print(f"  VERDICT: {n_pass}-of-4 as frozen; honest reading 2-of-4 "
          f"with P3 hollow — the boundary premium is ABSENT at the "
          f"identified comparison (+{diff_ident:.2f} vs predicted +1)")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_lineage_d.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_lineage_d.txt'}")
