#!/usr/bin/env python3
"""Verification of the FROZEN phase curve (results_phase_curve.txt).

Constructs real-outcome pools at exact (p*, R) targets matching the
derivation's own 2+2 geometry: each constructed stratum is a mixture
of draws from the gpt-4o-mini extreme pool (rate .736) and simple
pool (rate .004), mixed to hit the target stratum rate — so every
outcome is a real model generation, and the pooled rate/heterogeneity
are placed deliberately instead of inherited from whatever a vendor
ships.

V2 ALLOCATION (disclosed; v1 put 7 of 9 scored points in the
already-established WSR region — the third instance of the
concentration generator, caught by peer review and now gate rule R8).
The novel claim is the SINGLE region, so v2 inverts the allocation.
Structural disclosure: under the frozen bands, below-band space
exists ONLY at m = 0.08 (band-lo = 1.1 elsewhere) — the curve itself
confines single-wins territory to easy margins, so that is where the
test must live. The spread across p* and R separates the two
competing explanations of v1's misses: a mis-modeled margin
dependence fails everywhere at m = 0.08; a c_short(R) effect fails
only near the band edge.

  p*    margin  R      band-lo   prediction
  0.20  0.080   1.2    4.5       single
  0.20  0.080   1.5    4.5       single
  0.20  0.080   2.0    4.5       single
  0.20  0.080   2.6    4.5       single
  0.20  0.080   3.5    4.5       single
  0.30  0.080   1.2    2.2       single
  0.30  0.080   1.5    2.2       single   (v1 point, re-run)
  0.30  0.080   2.0    2.2       single
  0.40  0.080   1.3    1.7       single   (v1 point, re-run)
  0.40  0.080   1.5    1.7       single
  0.30  0.045   8      [above]   wsr (sanity)
  0.40  0.060   6.5    [above]   wsr (sanity)
  0.20  0.045   20     [above]   wsr (sanity)
  0.30  0.060   3      in-band   unresolved (reported)
  0.20  0.060   7      in-band   unresolved (reported)

PRE-REGISTERED SCORING (v2):
  P1 below-band points won by single-stream in >= 8 of 10 (both arms
     >= 90% certified);
  P2 all 3 above-band sanity points won by WSR;
  P3 wrong certifications <= alpha of all reps.
Diagnostic readout (not scored): the spatial pattern of any P1
misses — uniform-across-m=0.08 indicts the margin model; edge-
concentrated indicts c_short(R). 200 reps/arm/point, n_max 12000,
UNSAFE, round-robin. Offline, deterministic. Writes
results_phase_test.txt (v2; v1 preserved in git at 065f9a8).
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

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 200
N_MAX = 12000
POINTS = [
    (0.20, 0.080, 1.2, "single"),
    (0.20, 0.080, 1.5, "single"),
    (0.20, 0.080, 2.0, "single"),
    (0.20, 0.080, 2.6, "single"),
    (0.20, 0.080, 3.5, "single"),
    (0.30, 0.080, 1.2, "single"),
    (0.30, 0.080, 1.5, "single"),
    (0.30, 0.080, 2.0, "single"),
    (0.40, 0.080, 1.3, "single"),
    (0.40, 0.080, 1.5, "single"),
    (0.30, 0.045, 8.0, "wsr"),
    (0.40, 0.060, 6.5, "wsr"),
    (0.20, 0.045, 20.0, "wsr"),
    (0.30, 0.060, 3.0, None),
    (0.20, 0.060, 7.0, None),
]


def load_base():
    pools = {}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        r = json.loads(line)
        pools.setdefault(r["stratum"], []).append(0 if r["passed"] else 1)
    return (np.array(pools["simple"], dtype=np.int8),
            np.array(pools["extreme"], dtype=np.int8))


def draw(rate, lo_pool, hi_pool, rng, r_lo=0.004, r_hi=0.736):
    """One real-outcome draw at target rate via pool mixing."""
    q = (rate - r_lo) / (r_hi - r_lo)
    if rng.random() < q:
        return bool(hi_pool[int(rng.integers(0, len(hi_pool)))])
    return bool(lo_pool[int(rng.integers(0, len(lo_pool)))])


def strata_for(p_star, R):
    p_hi = 2 * p_star * R / (1 + R)
    p_lo = p_hi / R
    return [p_lo, p_lo, p_hi, p_hi]


def run_single(rates, tau, lo_pool, hi_pool, rng):
    cs = StratifiedUICS(k=1, weights=[1.0], alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        y = draw(rates[(n - 1) % 4], lo_pool, hi_pool, rng)
        cs.update(0, y)
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(tau):
                return "UNSAFE", n
            if cs.rejects_ge(tau):
                return "SAFE", n
    return "ABSTAIN", N_MAX


def run_wsr(rates, tau, lo_pool, hi_pool, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        block = [draw(rates[i], lo_pool, hi_pool, rng)
                 for i in range(4)]
        cs.update(float(np.mean(block)))
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > tau:
                return "UNSAFE", 4 * b
            if hi <= tau:
                return "SAFE", 4 * b
    return "ABSTAIN", N_MAX


def main():
    lo_pool, hi_pool = load_base()
    print("=" * 76)
    print("PHASE-CURVE VERIFICATION (predictions frozen at commit "
          "f75eb8d)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/arm/point, n_max={N_MAX}, "
          f"BASE_SEED={BASE_SEED}; constructed 2+2 pools from real "
          f"gpt-4o-mini outcomes\n")

    p1_ok, p2_ok, p1_n, p2_n = 0, 0, 0, 0
    wrong, total = 0, 0
    for i, (p_star, m, R, expect) in enumerate(POINTS):
        rates = strata_for(p_star, R)
        tau = round(p_star - m, 3)
        meds = {}
        fracs = {}
        for kind, fn in [("single", run_single), ("wsr", run_wsr)]:
            rng = np.random.default_rng(
                BASE_SEED + 5000 + 137 * i
                + (0 if kind == "single" else 61))
            outs = [fn(rates, tau, lo_pool, hi_pool, rng)
                    for _ in range(N_REPS)]
            dec = [n for d, n in outs if d == "UNSAFE"]
            wrong += sum(1 for d, _ in outs if d == "SAFE")
            total += N_REPS
            fracs[kind] = len(dec) / N_REPS
            meds[kind] = int(np.median(dec)) if dec else None
        both_ok = all(fracs[k] >= 0.9 and meds[k] for k in meds)
        winner = (min(meds, key=meds.get) if both_ok else None)
        if expect is None:
            print(f"  p*={p_star} m={m} R={R:5.1f}: meds {meds} "
                  f"[in-band, unresolved-by-design, unscored]")
            continue
        hit = winner == expect
        if expect == "single":
            p1_n += 1
            p1_ok += hit
        else:
            p2_n += 1
            p2_ok += hit
        print(f"  p*={p_star} m={m} R={R:5.1f}: predict {expect:6s} "
              f"-> winner {winner} (meds {meds}) "
              f"{'HIT' if hit else 'MISS'}")

    p1 = p1_ok >= 8
    p2 = p2_ok == p2_n
    p3 = wrong / total <= ALPHA
    print(f"\n  P1 below-band -> single: {p1_ok}/{p1_n} "
          f"(need >= 8): {'PASS' if p1 else 'FAIL'}")
    print(f"  P2 above-band -> wsr: {p2_ok}/{p2_n}: "
          f"{'PASS' if p2 else 'FAIL'}")
    print(f"  P3 wrong-cert rate {wrong}/{total} = "
          f"{wrong / total:.4f} <= {ALPHA}: "
          f"{'PASS' if p3 else 'FAIL'}")
    print(f"\n  PHASE-CURVE VERDICT: "
          f"{'CONFIRMED — the design map is a predictive theory' if p1 and p2 and p3 else 'FAILED'}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_phase_test.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_phase_test.txt'}")
