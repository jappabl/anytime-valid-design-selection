#!/usr/bin/env python3
"""Prediction-powered certification via predictor-refined stratification.

Idea: a cheap predictor's outputs — here the CACHED outcomes of an
already-evaluated model (gpt-4o-mini, "model A") — are free side
information about which prompts are hard. Using them to REFINE the
stratification of the pool before evaluating a new model B is a
design-based form of prediction-powered inference:

  - The refined cells are fixed from A's labels alone, BEFORE any B
    sample is drawn: no leakage into B's evaluation.
  - A block = one draw per cell; the WEIGHTED cell mean (weights =
    cell sizes) is an iid bounded variable with mean exactly p*_B, so
    the WSR betting CS applies with its full guarantee — no new
    validity argument is needed.
  - If B's failures concentrate where A's did, within-cell variance
    shrinks and certification gets cheaper.

Cells: original stratum kept whole unless splitting by A's outcome
leaves both sides with >= 25 prompts (avoids empty/tiny cells).

Fairness: the baseline is our CURRENT champion (WSR on original
4-stratum blocks), not a straw man. Same CS, same alpha, same stopping;
the only change is the design. A per-SAMPLE accounting is used (refined
blocks cost more draws per block).

The variance prediction below is computed from pool quantities before
any sequential run. Offline, deterministic. Writes results_ppc.txt.
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

from eval_harness.stats.wsr_block_cs import WSRBlockCS

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
MIN_CELL = 25
N_REPS = 300
N_MAX_SAMPLES = 4000

FILES = {
    "gpt-4o-mini": "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
}


def load(fname):
    recs = {}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        recs[r["id"]] = (r["stratum"], 0 if r["passed"] else 1)
    return recs


def build_cells(a_recs, b_recs):
    """Refined cells from A's outcomes; returns list of (name, weight,
    np.array of B outcomes)."""
    cells = []
    for s in STRATA:
        ids = [i for i, (st, _) in a_recs.items() if st == s]
        a_fail = [i for i in ids if a_recs[i][1] == 1]
        a_pass = [i for i in ids if a_recs[i][1] == 0]
        if len(a_fail) >= MIN_CELL and len(a_pass) >= MIN_CELL:
            cells.append((f"{s}|A-fail", len(a_fail),
                          np.array([b_recs[i][1] for i in a_fail])))
            cells.append((f"{s}|A-pass", len(a_pass),
                          np.array([b_recs[i][1] for i in a_pass])))
        else:
            cells.append((s, len(ids),
                          np.array([b_recs[i][1] for i in ids])))
    total = sum(w for _, w, _ in cells)
    return [(n, w / total, arr) for n, w, arr in cells]


def block_var(cells):
    """Var of the weighted per-block mean = sum w_c^2 p_c q_c."""
    return float(sum(w * w * arr.mean() * (1 - arr.mean())
                     for _, w, arr in cells))


def run_wsr(cells, tau, truth, rng, n_max_samples):
    """WSR CS on weighted block means; returns (decision, n_samples)."""
    k = len(cells)
    weights = np.array([w for _, w, _ in cells])
    # Weighted block mean lies in [0, 1]; mean = p* exactly.
    cs = WSRBlockCS(alpha=ALPHA)
    n = 0
    while n + k <= n_max_samples:
        draws = np.array([float(arr[int(rng.integers(0, len(arr)))])
                          for _, _, arr in cells])
        cs.update(float(np.sum(weights * draws)))
        n += k
        if n >= 20:
            lo, hi = cs.get_bounds()
            if hi <= tau:
                return "SAFE", n
            if lo > tau:
                return "UNSAFE", n
    return "ABSTAIN", n


def widths_at(cells, n_target, rng):
    k = len(cells)
    weights = np.array([w for _, w, _ in cells])
    cs = WSRBlockCS(alpha=ALPHA)
    n = 0
    while n + k <= n_target:
        draws = np.array([float(arr[int(rng.integers(0, len(arr)))])
                          for _, _, arr in cells])
        cs.update(float(np.sum(weights * draws)))
        n += k
    lo, hi = cs.get_bounds()
    return hi - lo


def evaluate(model_b, a_recs):
    b_recs = load(FILES[model_b])
    base_cells = [(s, 0.25,
                   np.array([v[1] for i, v in b_recs.items()
                             if v[0] == s]))
                  for s in STRATA]
    ref_cells = build_cells(a_recs, b_recs)
    p_star = float(sum(w * arr.mean() for _, w, arr in base_cells))

    print(f"\n{model_b} (p* = {p_star:.4f}):")
    print("  refined cells (from gpt-4o-mini outcomes only):")
    for name, w, arr in ref_cells:
        print(f"    {name:16s} weight {w:.3f}  B-rate {arr.mean():.3f} "
              f"(n={len(arr)})")

    v_base = block_var(base_cells)
    v_ref = block_var(ref_cells)
    # Per-sample variance comparison: block of 4 vs block of len(ref_cells)
    ps_base = v_base * 4
    ps_ref = v_ref * len(ref_cells)
    print(f"  PREDICTION (pool quantities, computed before any run): "
          f"per-sample variance {ps_base:.4f} -> {ps_ref:.4f} "
          f"({'REFINEMENT HELPS' if ps_ref < ps_base else 'no gain expected'})")

    print(f"  {'design':22s} {'width@400':>10} {'width@800':>10}")
    for label, cells in [("WSR original 4-strata", base_cells),
                         ("WSR predictor-refined", ref_cells)]:
        row = f"  {label:22s}"
        for n_t in [400, 800]:
            rng = np.random.default_rng(BASE_SEED + 81)
            ws = [widths_at(cells, n_t, rng) for _ in range(150)]
            row += f"{np.median(ws):>10.4f}"
        print(row)

    for tau in [0.15, 0.11 if model_b == "gpt-4.1-nano" else 0.06]:
        truth = "SAFE" if p_star <= tau else "UNSAFE"
        print(f"  certification tau={tau} (truth {truth}, margin "
              f"{abs(p_star - tau):.3f}):")
        for label, cells in [("WSR original 4-strata", base_cells),
                             ("WSR predictor-refined", ref_cells)]:
            rng = np.random.default_rng(BASE_SEED + 82)
            outs = [run_wsr(cells, tau, truth, rng, N_MAX_SAMPLES)
                    for _ in range(N_REPS)]
            correct = [n for d, n in outs if d == truth]
            wrong = sum(1 for d, _ in outs if d not in (truth, "ABSTAIN"))
            abstain = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(correct)) if correct else None
            print(f"    {label:22s}: correct {len(correct)}/{N_REPS}, "
                  f"wrong {wrong}, abstain {abstain}, median samples {med}")


def main():
    print("=" * 76)
    print("PREDICTION-POWERED CERTIFICATION (predictor-refined stratification)")
    print("=" * 76)
    print(f"Predictor: cached gpt-4o-mini outcomes (free side information).")
    print(f"alpha={ALPHA}, {N_REPS} reps, sample budget {N_MAX_SAMPLES}, "
          f"BASE_SEED={BASE_SEED}")
    a_recs = load(FILES["gpt-4o-mini"])
    evaluate("gpt-4.1-nano", a_recs)
    evaluate("gpt-4.1-mini", a_recs)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_ppc.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_ppc.txt'}")
