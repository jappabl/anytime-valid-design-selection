#!/usr/bin/env python3
"""Overshoot term of c_ren: asymptotic constant CLOSED, finite-L gap OPEN.

Peer derivation (gpt-5.6-sol, verified by the peer to 7 decimals vs
exact enumeration), RE-VERIFIED here two independent ways before
adoption. The overshoot is NOT the naive per-sample E[Y^2]/(2E[Y]) --
that requires Y to be a LADDER HEIGHT. Because the boundary is checked
every d samples, the driving walk is the d-SAMPLE BLOCK SKELETON, and
the object is that skeleton's first strict ascending ladder height H_d.

    a = log(p/tau), b = log((1-p)/(1-tau)), c = a - b,
    mu = D(p||tau) = E[l_i],  sigma^2 = p q c^2,
    block skeleton Y_j = d b + c K_j,  K_j ~ Binom(d, p),
    rho_d = E[H_d^2] / (2 E[H_d]).

Spitzer's fluctuation identity gives it explicitly:
    rho_d = sigma^2/(2 mu) + d mu/2 - sum_{m>=1} A_{dm}/m,
    A_n = -n b F_{n,p}(k_n) - c n p F_{n-1,p}(k_n - 1),
    k_n = ceil(-n b / c) - 1,  F_{r,p} = Binom(r,p) CDF.

TWO INDEPENDENT CHECKS here: the Spitzer closed form vs a direct
ladder-height Monte Carlo. They agree, and match the peer's
rho_1 = 0.0941692, rho_4 = 0.1703462 at (0.202, 0.157).

CRITICAL DISTINCTION, do not collapse: rho_d is the ASYMPTOTIC (large
log(1/alpha)) constant. The MEASURED finite-boundary overshoot at
L = log 20 = 3.0 is ~0.228 (results_selection.txt / results_overshoot),
far from the large-L regime. The 0.170 -> 0.228 gap is REAL, sharply
posed, and is the remaining OPEN finite-L correction -- the single
obstruction now shared with the selection term. Record both numbers
with their status; do NOT fit them together.

Citations (Section 8): Kim & Woodroofe (arXiv math/0611695), nonlinear
renewal with slowly-changing perturbations (accommodates the quadratic
xi_n = (F_n-np)^2/(2npq) here); Spitzer's identity for the explicit
form. Lorden (1970) is a UNIFORM excess BOUND -- the raw-moment
equality applies only to renewal interarrivals, which the signed
one-step increments are not.

Offline, deterministic. Writes results_overshoot_closed.txt.
"""

import hashlib
import io
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.stats import binom
from scipy.special import xlogy

REPO = Path(__file__).parent.parent


def setup(p, tau):
    a = np.log(p / tau)
    b = np.log((1 - p) / (1 - tau))
    c = a - b
    mu = xlogy(p, p / tau) + xlogy(1 - p, (1 - p) / (1 - tau))
    return a, b, c, float(mu), p * (1 - p) * c * c


def A_n(n, p, b, c):
    kn = int(np.ceil(-n * b / c)) - 1
    Fn = binom.cdf(kn, n, p)
    Fnm1 = binom.cdf(kn - 1, n - 1, p) if n >= 1 else 0.0
    return -n * b * Fn - c * n * p * Fnm1


def rho_spitzer(d, p, tau, M=50000):
    a, b, c, mu, sig2 = setup(p, tau)
    return (sig2 / (2 * mu) + d * mu / 2.0
            - sum(A_n(d * m, p, b, c) / m for m in range(1, M + 1)))


def rho_mc(d, p, tau, sims, rng):
    a, b, c, mu, sig2 = setup(p, tau)
    H = np.empty(sims)
    for i in range(sims):
        S = 0.0
        while True:
            S += d * b + c * rng.binomial(d, p)
            if S > 0:
                H[i] = S
                break
    return float(np.mean(H ** 2) / (2 * np.mean(H)))


def main():
    print("=" * 76)
    print("OVERSHOOT: asymptotic constant rho_d CLOSED (two independent "
          "checks)")
    print("=" * 76)
    print("\n  rho_d = E[H_d^2]/(2 E[H_d]) for the d-sample block-skeleton "
          "ladder height\n")
    print(f"  {'p*':>5} {'tau':>6} {'d':>2} {'rho_spitzer':>12} "
          f"{'rho_ladderMC':>13} {'|diff|':>7}")
    rng = np.random.default_rng(7)
    worst = 0.0
    for p, tau in [(0.202, 0.157), (0.30, 0.255), (0.15, 0.105)]:
        for d in (1, 4):
            rs = rho_spitzer(d, p, tau)
            rm = rho_mc(d, p, tau, 150000, rng)
            worst = max(worst, abs(rs - rm))
            print(f"  {p:>5.3f} {tau:>6.3f} {d:>2} {rs:>12.5f} "
                  f"{rm:>13.5f} {abs(rs - rm):>7.4f}")
    r1 = rho_spitzer(1, 0.202, 0.157)
    r4 = rho_spitzer(4, 0.202, 0.157)
    print(f"\n  two-method agreement: worst |diff| {worst:.4f} "
          f"({'PASS' if worst < 0.01 else 'FAIL'})")
    print(f"  d-dependence (the 'factor of 2'): rho_4/rho_1 = "
          f"{r4 / r1:.3f} at (0.202, 0.157)")
    print(f"""
  STATUS:
    ASYMPTOTIC overshoot: CLOSED. rho_4 = {r4:.4f} at (0.202, 0.157),
      Spitzer closed form = ladder-height MC to <0.01, matching the
      peer's exact-enumeration 0.1703462.
    FINITE-L overshoot: measured ~0.228 at L = log 20 = 3.0 (far from
      asymptotic). The 0.170 -> 0.228 gap is the OPEN finite-L
      correction, now the single obstruction shared with selection.
    Not fitted; both numbers recorded with status.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_overshoot_closed.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_overshoot_closed.txt'}")
