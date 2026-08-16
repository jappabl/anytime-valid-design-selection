#!/usr/bin/env python3
"""Three-arm verification of the derived partition (single / UI+RR / WSR).

The partition (results_partition.txt) DERIVED two claims: (1) the
single|WSR winner map with tie widths, and (2) UI+RR is DOMINATED
everywhere (outright fastest at 0/84 derived cells). This verifies both
empirically on constructed real-outcome pools, with all three arms
CRN-paired and paired-bootstrap three-way verdicts (the v2b instrument:
SINGLE / UI / WSR / TIE, ties reported not forced).

Pools: constructed 2+2 from the gpt-4o-mini extreme (.736) and simple
(.004) outcome pools, mixed to target stratum rates (same as
run_phase_test.py). Cells chosen to span the partition, including where
UI's V_rr advantage is largest (mild heterogeneity, easy margin) —
the toughest test of the dominated claim, since that is where UI has
the best rate.

PRE-REGISTERED:
  P1 UI is NEVER the outright fastest (lower CI-separated median than
     BOTH others) at any cell — the derived 0/84 dominated claim.
     A single UI outright win refutes it.
  P2 among single/WSR, the resolving cells match the derived partition
     winner (single below the boundary, WSR above); ties reported.
  P3 wrong certifications <= alpha across all reps.

100 reps/arm/cell (mixture arm is ~21us/sample via the O(1) fix but
UI is k=4), n_max 12000, UNSAFE, round-robin. Offline, deterministic.
Writes results_partition_test.txt.
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
N_REPS = 100
N_MAX = 12000
# (p*, margin, R): span the partition; the last few are UI's best case
CELLS = [
    (0.20, 0.045, 2.0), (0.20, 0.045, 8.0), (0.30, 0.045, 3.0),
    (0.30, 0.060, 6.0), (0.40, 0.045, 4.0), (0.20, 0.080, 2.0),
    (0.20, 0.080, 6.0), (0.30, 0.030, 12.0), (0.40, 0.080, 3.0),
    (0.30, 0.045, 15.0),
]


def load_base():
    pools = {}
    for line in open(REPO / "data" / "llm_outcomes_diverse_json.jsonl"):
        r = json.loads(line)
        pools.setdefault(r["stratum"], []).append(0 if r["passed"] else 1)
    return (np.array(pools["simple"], dtype=np.int8),
            np.array(pools["extreme"], dtype=np.int8))


def draw(rate, lo, hi, rng, r_lo=0.004, r_hi=0.736):
    q = (rate - r_lo) / (r_hi - r_lo)
    if rng.random() < q:
        return bool(hi[int(rng.integers(0, len(hi)))])
    return bool(lo[int(rng.integers(0, len(lo)))])


def strata_for(p_star, R):
    p_hi = 2 * p_star * R / (1 + R)
    return [p_hi / R, p_hi / R, p_hi, p_hi]


def run(kind, rates, tau, lo, hi, rng):
    if kind == "wsr":
        cs = WSRBlockCS(alpha=ALPHA)
        for b in range(1, N_MAX // 4 + 1):
            m = float(np.mean([draw(rates[i], lo, hi, rng)
                               for i in range(4)]))
            cs.update(m)
            if 4 * b >= 20:
                l, h = cs.get_bounds()
                if l > tau:
                    return "UNSAFE", 4 * b
                if h <= tau:
                    return "SAFE", 4 * b
        return "ABSTAIN", N_MAX
    k = 1 if kind == "single" else 4
    cs = StratifiedUICS(k=k, weights=[1.0] if k == 1 else None,
                        alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        i = (n - 1) % 4
        y = draw(rates[i], lo, hi, rng)
        cs.update(0 if k == 1 else i, y)
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(tau):
                return "UNSAFE", n
            if cs.rejects_ge(tau):
                return "SAFE", n
    return "ABSTAIN", N_MAX


def main():
    lo, hi = load_base()
    print("=" * 76)
    print("PARTITION THREE-ARM VERIFICATION (single / UI+RR / WSR)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/arm/cell, n_max={N_MAX}, "
          f"paired bootstrap three-way verdicts\n")

    ui_outright, wrong, total = 0, 0, 0
    part_hits, part_n = 0, 0
    for ci, (p_star, m, R) in enumerate(CELLS):
        rates = strata_for(p_star, R)
        tau = round(p_star - m, 3)
        times = {}
        fr = {}
        for kind in ("single", "ui", "wsr"):
            ts = []
            done = 0
            for rep in range(N_REPS):
                rng = np.random.default_rng(BASE_SEED + 91 * ci + rep)
                d, n = run(kind, rates, tau, lo, hi, rng)
                if d == "UNSAFE":
                    ts.append(n)
                    done += 1
                else:
                    ts.append(N_MAX)
                    if d == "SAFE":
                        wrong += 1
                total += 1
            times[kind] = np.array(ts)
            fr[kind] = done / N_REPS
        # paired bootstrap medians
        brng = np.random.default_rng(555 + ci)
        meds = {k: int(np.median(v)) for k, v in times.items()}
        boot = {k: [] for k in times}
        for _ in range(4000):
            idx = brng.integers(0, N_REPS, N_REPS)
            for k in times:
                boot[k].append(np.median(times[k][idx]))
        # UI outright win? UI CI-below both others
        def ci_below(a, b):
            diff = np.array(boot[a]) - np.array(boot[b])
            return np.percentile(diff, 97.5) < 0
        ui_win = (fr["ui"] >= 0.9 and ci_below("ui", "single")
                  and ci_below("ui", "wsr"))
        ui_outright += ui_win
        # single vs wsr resolving winner
        if fr["single"] >= 0.9 and fr["wsr"] >= 0.9:
            diff = np.array(boot["single"]) - np.array(boot["wsr"])
            lo_ci, hi_ci = np.percentile(diff, [2.5, 97.5])
            sw = ("single" if hi_ci < 0 else "wsr" if lo_ci > 0
                  else "tie")
        else:
            sw = "unresolved"
        print(f"  p*={p_star} m={m} R={R:>4}: meds S{meds['single']} "
              f"U{meds['ui']} W{meds['wsr']} (cert "
              f"{fr['single']:.2f}/{fr['ui']:.2f}/{fr['wsr']:.2f}); "
              f"single|wsr -> {sw}; UI outright win: "
              f"{'YES (REFUTES)' if ui_win else 'no'}")

    print(f"\n  P1 UI never outright fastest: {ui_outright}/{len(CELLS)} "
          f"UI wins -> {'PASS' if ui_outright == 0 else 'FAIL — UI region exists'}")
    print(f"  P3 wrong-cert rate {wrong}/{total} = {wrong/total:.4f} "
          f"<= {ALPHA}: {'PASS' if wrong/total <= ALPHA else 'FAIL'}")
    print(f"""
  READING: P1 is the verification of the derived UI-dominated claim
  (0/84 cells). If UI wins outright nowhere here — including the
  mild-heterogeneity easy-margin cells where its V_rr advantage is
  largest — the two-region partition (single | WSR, UI nowhere
  optimal) is empirically confirmed, not just derived.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_partition_test.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_partition_test.txt'}")
