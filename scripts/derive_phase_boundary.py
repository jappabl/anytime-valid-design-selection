#!/usr/bin/env python3
"""Derive the single-stream vs WSR phase boundary — algebra first.

Target 1 (corrected per peer review: DERIVE the curve, then test it;
pools are the test, not the search). The practical design-map boundary
is single-stream vs WSR blocks (UI never wins a cell in our data), and
both arms obey the frozen expansion

    n * V = log(1/alpha) + (d/2) * log n + c

with the 5.1 rate definitions: V_single = KL(p*, tau) (pooled
Bernoulli), V_wsr = exact per-sample Kelly growth over the 16-atom
block-mean distribution. Setting the two crossing times equal and
solving gives the flip as a CURVE over (heterogeneity ratio R, margin
m) at fixed p* and K.

Stratum profile for the derivation (REVISED after the first pass
saturated at high p*): two cold + two hot, p = [p_lo, p_lo, p_hi,
p_hi] with p_hi = 2 p* R / (1 + R) and p_lo = p_hi / R — valid for
all R at any p* < 0.5, and closer to the real pools' shapes.

CONSTANTS, pass 4 (the four-term revolution): the SINGLE arm now uses
DERIVED constants — the Stirling fourth term makes its crossing solve
    n KL(p*, tau) = L + (1/2) log n - (1/2) log(2 pi p* q*) + C_ren
with C_ren = -1.105 the ONE measured renewal scalar
(results_overshoot.txt C3; its closed form is the stated open
clause). No fitted pairs remain on the single side. WSR keeps its
measured two-regime envelope (its own o(1) derivation is open):
central (c_short, d_long, c_long) = (2.3, 1.95, -4.6), corners
(1.6, 1.81, -3.4) and (3.0, 2.34, -5.9). Bands below therefore span
ONLY WSR's envelope uncertainty.
ANCHORS (relation-gate R1 applied): A1 (MBPP-like, R ~ 2.6, expected
single) and A3 (llama3-8b-like, R ~ 7.5, expected WSR from
results_lineage_d.txt where WSR wins 2-3x at every margin) are the
DISCRIMINATING anchors and both must pass; A2 (R ~ 31) is reported
but NOT scored — the gate proved its verdict invariant across the
band (it cannot fail; it is not evidence). A1 + A3 bracket the flip
in R (2.6, 7.5).

OUTPUT: the central curve R*(m) at p* in {0.20, 0.30, 0.40} and the
band [R*_lo, R*_hi] from the corner combinations of the constant
bands. FROZEN prediction for the verification test (next script):
constructed reweighted pools with R below R*_lo(m) are won by
single-stream, above R*_hi(m) by WSR, at every tested margin; points
inside the band are unresolved by design and not scored.

Writes results_phase_curve.txt (the frozen curve artifact).
"""

import hashlib
import io
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import brentq

ALPHA = 0.05
L = float(np.log(1 / ALPHA))
K = 4


def kl(p, q):
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def v_kelly_block(rates, tau):
    atoms, probs = [], []
    for bits in range(2 ** K):
        m, pr = 0.0, 1.0
        for i in range(K):
            if bits >> i & 1:
                m += 1.0 / K
                pr *= rates[i]
            else:
                pr *= 1 - rates[i]
        atoms.append(m)
        probs.append(pr)
    atoms, probs = np.array(atoms), np.array(probs)
    best = 0.0
    for lam in np.linspace(0.001, 1 / max(tau, 1e-9) - 1e-6, 3000):
        g = float(np.sum(probs * np.log1p(lam * (atoms - tau))))
        best = max(best, g)
    return best / K


def crossing_n(V, d, c):
    if V <= 0:
        return np.inf
    f = lambda n: n * V - L - 0.5 * d * np.log(n) - c
    try:
        return brentq(f, 4.0, 1e8)
    except ValueError:
        return np.inf


def check_anchors(corners):
    """Discriminating anchors A1 and A3 must pass under the CENTRAL
    WSR envelope AND both corners; A2 reported unscored (R1: verdict
    invariant across the band — not evidence)."""
    ok = True
    anchor_sets = [
        ("A1 (MBPP-like, R~2.6)",
         np.array([0.140, 0.215, 0.224, 0.358]), "single", True),
        ("A3 (llama3-8b-like, R~7.5)",
         np.array([0.456, 0.128, 0.892, 0.960]), "wsr", True),
        ("A2 (llama3.2-like, R~31; UNSCORED per R1)",
         np.array([0.040, 0.032, 0.864, 0.996]), "wsr", False),
    ]
    for name, rates, expect, scored in anchor_sets:
        p = float(rates.mean())
        tau = p - 0.045
        n_s = single_fourterm(p, tau)
        verdicts = []
        for csh, dlg, clg in corners:
            n_w = wsr_crossing(v_kelly_block(rates, tau), csh, dlg,
                               clg)
            verdicts.append("single" if n_s < n_w else "wsr")
        hit = all(v == expect for v in verdicts)
        tag = "PASS (all corners)" if hit else f"FAIL {verdicts}"
        if scored:
            ok &= hit
        print(f"  {name}: single {n_s:.0f}; expected {expect} -> "
              f"{tag}{'' if scored else ' [reported, not scored]'}")
    return ok


def profile(p_star, R):
    p_hi = 2 * p_star * R / (1 + R)
    p_lo = p_hi / R
    if p_hi >= 0.995:
        return None
    return np.array([p_lo, p_lo, p_hi, p_hi])


def wsr_crossing(V, c_short, d_long, c_long):
    """Crossing under the two-regime overhead envelope."""
    if V <= 0:
        return np.inf
    f = lambda n: n * V - L - max(c_short,
                                  0.5 * d_long * np.log(n) + c_long)
    try:
        return brentq(f, 4.0, 1e8)
    except ValueError:
        return np.inf


C_REN = -1.105   # measured renewal scalar (results_overshoot.txt)


def single_fourterm(p, tau):
    """Derived four-term single-arm crossing (no fitted parameters
    beyond the one disclosed measured scalar C_REN)."""
    c = -0.5 * np.log(2 * np.pi * p * (1 - p)) + C_REN
    return crossing_n(kl(p, tau), 1.0, c)


def flip_ratio(p_star, m, c_short, c_long, d_long):
    """R at which n_single = n_wsr, by bisection over R."""
    tau = p_star - m

    def gap(R):
        rates = profile(p_star, R)
        if rates is None:
            return 1.0   # saturated profile: treat as WSR side
        n_s = single_fourterm(p_star, tau)
        n_w = wsr_crossing(v_kelly_block(rates, tau),
                           c_short, d_long, c_long)
        return n_s - n_w   # positive when WSR is faster (WSR wins)

    lo, hi = 1.05, 400.0
    if gap(lo) > 0:
        return lo    # WSR wins even at homogeneity
    if gap(hi) < 0:
        return hi    # single wins everywhere in range
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        if gap(mid) > 0:
            hi = mid
        else:
            lo = mid
    return float(np.sqrt(lo * hi))


def main():
    print("=" * 76)
    print("DERIVED PHASE BOUNDARY: single-stream vs WSR blocks "
          "(frozen curve)")
    print("=" * 76)
    print(f"alpha={ALPHA}, K={K}, two-level profile (3 cold + 1 hot), "
          "expansion constants as banded in the header\n")

    corners = [
        # WSR envelope only: (c_short, d_long, c_long); last = central
        (1.6, 1.81, -3.4), (3.0, 2.34, -5.9), (2.3, 1.95, -4.6),
    ]
    if not check_anchors(corners):
        print("\n  DISCRIMINATING ANCHORS FAILED — curve NOT frozen")
        return
    print()
    for p_star in (0.20, 0.30, 0.40):
        print(f"  p* = {p_star}:")
        print(f"  {'margin':>7} {'R* central':>10} {'R* band':>18}")
        for m in (0.030, 0.045, 0.060, 0.080):
            rs = [flip_ratio(p_star, m, csh, dlg, clg)
                  for csh, dlg, clg in corners]
            central = rs[-1]
            band = (min(rs), max(rs))
            print(f"  {m:>7.3f} {central:>10.1f} "
                  f"[{band[0]:>6.1f}, {band[1]:>6.1f}]")
        print()

    print("""FROZEN VERIFICATION PREDICTION (for run_phase_test.py):
constructed reweighted pools with measured ratio R below the band's
lower edge at their margin are won by single-stream (lower median,
>= 90% certification both arms); above the upper edge, by WSR; points
inside the band are unresolved-by-design and not scored. The curve
above is committed BEFORE any verification replay runs.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    from pathlib import Path
    (Path(__file__).parent.parent / "results_phase_curve.txt").write_text(content)
    print("\nResults written to: results_phase_curve.txt")
