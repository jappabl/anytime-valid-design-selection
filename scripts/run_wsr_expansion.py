#!/usr/bin/env python3
"""Does WSR have an expansion? Stock schedule vs Kelly-floored, a decade of n.

Peer structural result (gpt-5.6-sol derivation, peer-verified on our
schedule): the STOCK predictable lambda schedule admits NO fixed
(d, c) with nV = log(1/alpha) + (d/2)log n + c + o(1); instead
nV ~ A log n (loglog n)^2, so nV/log n DIVERGES and any fitted d must
drift upward with horizon — which retro-predicts Section 5.4's
d = 1.8-2.3 anomaly. The peer's constant A = 0.1469 was MEASURED
(their derivation's H/16 = 0.2306 refuted, 57% high; do not quote it).

THIS SCRIPT reproduces the structural claim on our own classes (the
real WSRBlockCS, not a reimplementation) and runs the DECISIVE new
test the result makes valuable: the same sweep on KellyFloorWSR. The
floor was committed as a pragmatic fix for the long-horizon pathology
(results_kelly_floor.txt); if it restores a non-decaying drift it may
restore a genuine expansion — the only remaining route to a full
boundary theorem on the WSR side.

SETUP (peer's, on our code): iid Bernoulli(0.5) samples, K=4 blocks,
block mean fed to the CS, certify UNSAFE at tau = 0.5 - delta,
alpha = 0.05. V = per-sample Kelly rate of the 16-atom block game
(bench v_kelly_block / 4, as everywhere else in the project). Median
crossing over reps. Margins shrink to sweep a ~30x range of n.

PRE-REGISTERED:
  P1 (reproduce divergence): stock nV/log n is monotone increasing
     across the margin ladder with last/first >= 1.5.
  P2 (reproduce the form): stock nV/(log n (loglog n)^2) flat to
     +/-10% around its mean, EXCLUDING the deepest margin (peer
     caveat: that point may carry a further effect).
  P3 (the decisive discrimination, outcome NOT pre-committed): the
     floored arm's nV/log n total drift across the same ladder —
     FLAT (< 15% drift, vs stock > 50%) means an expansion exists and
     the boundary theorem can close on the floored arm; DIVERGING
     means the envelope stays semi-empirical there too. Either way it
     is reported as measured.

Offline, deterministic. Writes results_wsr_expansion.txt.
"""

import hashlib
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402
from eval_harness.stats.wsr_kelly_floor import KellyFloorWSR  # noqa: E402

_pb = open(REPO / "scripts" / "derive_phase_boundary.py").read()
pb = types.ModuleType("pb")
pb.__dict__["__file__"] = str(REPO / "scripts" / "derive_phase_boundary.py")
exec(_pb.rsplit("if __name__", 1)[0], pb.__dict__)

ALPHA = 0.05
BASE_SEED = 42
P = 0.5
# (delta, reps, n_max) — reps taper at the deepest margins, disclosed
LADDER = [(0.035, 300, 30000), (0.025, 300, 60000),
          (0.018, 300, 120000), (0.013, 200, 250000),
          (0.009, 150, 600000)]


def median_crossing(cls, tau, reps, n_max, seed0):
    """v2: v1 computed block means with numpy BOOLEAN addition
    (logical OR — means capped at 0.25 < tau, so nothing ever
    crossed and both arms returned identical censored n_max rows;
    the first artifact was INVALID and its P3 verdict nonsense).
    v2 uses int8 + reshape, and returns the crossing fraction so
    verdicts can be validity-guarded."""
    times = []
    done = 0
    n_blocks = n_max // 4
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        cs = cls(alpha=ALPHA)
        x = (rng.random(n_blocks * 4) < P).astype(np.int8)
        means = x.reshape(-1, 4).mean(axis=1)
        crossed = None
        for j in range(n_blocks):
            cs.update(float(means[j]))
            lo, _ = cs.get_bounds()
            if lo > tau:
                crossed = 4 * (j + 1)
                break
        if crossed:
            done += 1
            times.append(crossed)
        else:
            times.append(n_max)
    return int(np.median(times)), done / reps


def main():
    print("=" * 76)
    print("WSR EXPANSION TEST: stock schedule vs Kelly-floored, "
          "shrinking margins")
    print("=" * 76)
    print(f"p = {P}, K = 4 blocks, alpha = {ALPHA}; V = per-sample "
          f"block Kelly rate\n")

    rates = np.array([P, P, P, P])
    rows = {"stock": [], "floor": []}
    print(f"  {'delta':>6} {'arm':>6} {'n_med':>8} {'nV':>8} "
          f"{'nV/logn':>8} {'nV/(logn llog^2)':>16}")
    for i, (delta, reps, n_max) in enumerate(LADDER):
        tau = P - delta
        V = pb.v_kelly_block(rates, tau)
        for arm, cls in [("stock", WSRBlockCS), ("floor", KellyFloorWSR)]:
            n, frac = median_crossing(cls, tau, reps, n_max,
                                      BASE_SEED + 1000 * i
                                      + (0 if arm == "stock" else 500))
            nv = n * V
            r1 = nv / np.log(n)
            r2 = nv / (np.log(n) * np.log(np.log(n)) ** 2)
            rows[arm].append((delta, n, nv, r1, r2, frac))
            print(f"  {delta:>6.3f} {arm:>6} {n:>8} {nv:>8.3f} "
                  f"{r1:>8.3f} {r2:>16.4f}  cert {frac:.2f}")

    s = rows["stock"]
    f = rows["floor"]
    # VALIDITY GUARD (v2; generator instance six — a verdict computed
    # from censored data): every scored rung must have >= 90% of reps
    # actually crossing, else the artifact declares itself INVALID.
    if min(r[5] for r in s + f) < 0.9:
        print("\n  INVALID: a rung has < 90% crossings — instrument "
              "failure, no verdicts scored.")
        return
    p1 = (all(s[i + 1][3] > s[i][3] for i in range(len(s) - 1))
          and s[-1][3] / s[0][3] >= 1.5)
    core = [r[4] for r in s[:-1]]
    # criterion stated precisely (R1b nit): MAX DEVIATION FROM MEAN
    # <= 10% (equivalently total spread <= 20%); both printed.
    maxdev = max(abs(c - np.mean(core)) for c in core) / np.mean(core)
    p2 = maxdev <= 0.10
    drift_f = abs(f[-1][3] - f[0][3]) / f[0][3]
    drift_s = abs(s[-1][3] - s[0][3]) / s[0][3]
    print(f"\n  P1 stock nV/log n diverges (monotone, >=1.5x): "
          f"{s[-1][3] / s[0][3]:.2f}x "
          f"{'PASS' if p1 else 'FAIL'}")
    print(f"  P2 stock form nV/(log n (loglog n)^2) flat +/-10% "
          f"(excl. deepest): max dev from mean {maxdev:.1%}, total "
          f"spread {(max(core) - min(core)) / np.mean(core):.1%} "
          f"{'PASS' if p2 else 'FAIL'}; mean A = {np.mean(core):.4f} "
          f"(peer 0.1469; H/16=0.2306 refuted)")
    print(f"  P3 floored-arm discrimination: nV/log n drift "
          f"{drift_f:.1%} (stock {drift_s:.1%}) -> "
          f"{'FLAT: an expansion EXISTS on the floored arm — the boundary theorem can close there' if drift_f < 0.15 else 'DIVERGES: the envelope stays semi-empirical on both arms'}")
    if drift_f < 0.15:
        # local d estimate from the flat regime: nV = L + (d/2)log n + c
        x = np.array([np.log(r[1]) / 2 for r in f])
        y = np.array([r[2] - np.log(1 / ALPHA) for r in f])
        A = np.stack([x, np.ones_like(x)], axis=1)
        (d_est, c_est), *_ = np.linalg.lstsq(A, y, rcond=None)
        print(f"     floored-arm fit: d = {d_est:+.2f}, c = {c_est:+.2f} "
              f"(report as measured; derive before claiming)")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_wsr_expansion.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_wsr_expansion.txt'}")
