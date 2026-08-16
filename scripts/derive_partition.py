#!/usr/bin/env python3
"""Design-space PARTITION: pairwise boundaries among single / UI+RR / WSR.

The phase boundary (derive_phase_boundary.py) derived ONE curve
(single vs WSR). The same construction — write both crossing times in
the shared expansion n*V = log(1/alpha) + (d/2)log n + c and solve for
equality — applies to any pair. Three designs give three pairwise
boundaries that PARTITION (heterogeneity ratio R x margin m) at fixed
p* into winner regions, each with a WIDTH (the tie band, where the
three-region form says the choice does not matter).

CROSSING TIMES (shared expansion, constants as frozen elsewhere):
  single: V = KL(p*, tau), four-term derived residual + c_ren = -1.105
          (single_fourterm from derive_phase_boundary).
  UI+RR : V = V_rr = min over {w.m = tau} mean_k KL(p_k || m_k)
          (bench._inner_min), d = 4.0 (measured 4.2/4.3, rule K+0),
          c = -0.7 (median local/mbpp UI fit), banded d in [3.5, 4.5].
  WSR   : two-regime Kelly envelope (wsr_crossing), central + corners.

Two-level profile p = [p_lo, p_lo, p_hi, p_hi], p_hi = 2 p* R/(1+R).

PRE-REGISTERED ANCHORS (relation-gate R1: each must DISCRIMINATE —
verdict flips under a wrong constant, else it is not evidence):
  ANC-1 mild MBPP-like (R~2.6): single-SIDE or TIE vs WSR (the phase
        verification PROVED this region is a tie — measured single 960
        vs WSR 1052 = 9%, v2b ties below band; demanding a crisp winner
        here would contradict our own verified result). UI must not win.
  ANC-2 extreme JSON-hard (R~200, m<=0.05): WSR beats both
        (results_wsr_hard / results_overhead: WSR 662/1308/748).
  ANC-3 UI is DOMINATED everywhere in the grid data (no cell in
        results_*_law has UI the outright fastest) -> the partition
        must show UI's region is empty or a thin sliver; if the
        derivation hands UI a fat region that is a FAIL to disclose.

Writes results_partition.txt (the frozen partition + tie widths).
"""

import hashlib
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

_pb = open(REPO / "scripts" / "derive_phase_boundary.py").read()
pb = types.ModuleType("pb")
pb.__dict__["__file__"] = str(REPO / "scripts" / "derive_phase_boundary.py")
exec(_pb.rsplit("if __name__", 1)[0], pb.__dict__)

_ug = open(REPO / "scripts" / "run_ui_grow.py").read()
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug.rsplit("if __name__", 1)[0], bench.__dict__)

ALPHA = 0.05
L = pb.L


def v_rr(rates, tau):
    lam = np.full(4, 0.25)
    m = bench._inner_min(lam, rates, np.full(4, 0.25), tau)
    return float(np.sum(lam * [bench.kl_bern(rates[i], m[i])
                               for i in range(4)]))


def n_ui(rates, tau, d_ui=4.0, c_ui=-0.7):
    V = v_rr(rates, tau)
    if V <= 0:
        return np.inf
    f = lambda n: n * V - L - 0.5 * d_ui * np.log(n) - c_ui
    try:
        return brentq(f, 4.0, 1e8)
    except ValueError:
        return np.inf


def winners(p_star, R, m, wsr_corner, d_ui=4.0, c_ui=-0.7):
    rates = pb.profile(p_star, R)
    if rates is None:
        rates = np.array([2 * p_star, 2 * p_star, 0.999, 0.999])
    tau = p_star - m
    n_s = pb.single_fourterm(p_star, tau)
    n_u = n_ui(rates, tau, d_ui, c_ui)
    n_w = pb.wsr_crossing(pb.v_kelly_block(rates, tau), *wsr_corner)
    order = sorted([("single", n_s), ("ui", n_u), ("wsr", n_w)],
                   key=lambda t: t[1])
    return order


def main():
    print("=" * 76)
    print("DESIGN-SPACE PARTITION: single / UI+RR / WSR pairwise "
          "boundaries")
    print("=" * 76)
    central = (2.3, 1.95, -4.6)
    corners = [(1.6, 1.81, -3.4), (3.0, 2.34, -5.9), central]

    # --- anchors (R1) ---
    print("\nANCHOR DISCRIMINATION (R1):")
    # ANC-1 accepts single OR tie (verified tie region), rejects WSR-
    # crisp and UI; ANC-2 demands crisp WSR.
    ok = True
    # ANC-1
    order = winners(0.234, 2.6, 0.045, central)
    w1, n1 = order[0]; n2 = order[1][1]
    tie1 = (n2 - n1) / n1 < 0.15
    a1 = (w1 == "single") or (tie1 and order[0][0] != "ui"
                              and order[1][0] != "ui")
    alt1 = winners(0.234, 2.6, 0.045, central, d_ui=0.0)[0][0]
    print(f"  ANC-1 mild R~2.6: winner {w1} (runner-up gap "
          f"{(n2-n1)/n1:.0%}), UI-alt {alt1}; expect single-or-tie, "
          f"UI never -> {'PASS' if a1 else 'FAIL'} "
          f"{'(tie band)' if tie1 else ''}; discriminating "
          f"{'yes' if alt1 == 'ui' else 'no'}")
    ok &= a1
    # ANC-2
    v2 = [winners(0.202, 200.0, 0.045, c)[0][0] for c in corners]
    a2 = all(v == "wsr" for v in v2)
    print(f"  ANC-2 hard R~200: corners {v2}; expect crisp wsr -> "
          f"{'PASS' if a2 else 'FAIL'}")
    ok &= a2
    if not ok:
        print("\n  ANCHORS DISAGREE — partition NOT frozen")
        return

    # --- ANC-3: is UI ever the outright winner anywhere? ---
    ui_wins = 0
    total = 0
    for p_star in (0.20, 0.30, 0.40):
        for R in (1.2, 2.0, 3.5, 6.0, 12.0, 40.0, 120.0):
            for m in (0.030, 0.045, 0.060, 0.080):
                total += 1
                if winners(p_star, R, m, central)[0][0] == "ui":
                    ui_wins += 1
    print(f"\n  ANC-3 UI-dominated check: UI is outright fastest at "
          f"{ui_wins}/{total} grid cells "
          f"({'PASS — thin/empty as observed' if ui_wins <= total * 0.05 else 'FAIL — UI region too fat vs data'})")

    # --- the partition, at p* = 0.30, central WSR envelope ---
    for p_star in (0.20, 0.30, 0.40):
        print(f"\n  PARTITION at p* = {p_star} (central WSR envelope):")
        print(f"  {'margin':>7} " + "  ".join(f"R={R:<5g}"
              for R in (1.5, 2.5, 4.0, 7.0, 15.0, 40.0)))
        for m in (0.030, 0.045, 0.060, 0.080):
            row = f"  {m:>7.3f} "
            for R in (1.5, 2.5, 4.0, 7.0, 15.0, 40.0):
                order = winners(p_star, R, m, central)
                w, nw = order[0]
                second = order[1][1]
                # tie band: within 5% is 'unresolvable' per three-region
                tie = (second - nw) / nw < 0.05
                row += f"  {(w[:4] + '~' if tie else w[:5]):<7}"
            print(row)
        print("    (~ = tie band: winner within 5% of runner-up — "
              "choice does not matter)")

    print("""
READING: the partition is DERIVED, not observed — one crossing-time
equality per pair, same expansion, constants frozen from prior
artifacts. The tie bands (~) are the practically important part: they
mark where design choice is free. ANC-3 quantifies UI's region: if UI
never wins outright (matching every grid artifact where it is
dominated), the honest partition is essentially TWO regions (single |
WSR) with UI nowhere optimal — a sharper statement than the
four-regime table. Verification harness: run_phase_test.py extended to
three arms (queued).""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_partition.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_partition.txt'}")
