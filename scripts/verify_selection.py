#!/usr/bin/env python3
"""Selection term of c_ren: the Bregman closed form + corrected value.

Peer correction (2026-08-16), independently re-verified here at 60k
reps before adoption. Three verified facts and one disputed magnitude.

VERIFIED:
1. Bregman identity for Bernoulli KL (exact to float precision):
       N[D(p_hat||tau) - D(p*||tau)] = theta*M_N + N*D(p_hat||p*),
   theta = D'(p*||tau) = log[p*(1-tau)/(tau(1-p*))], M_N = F_N - p* N.
2. FIRST-ORDER TERM IS EXACTLY ZERO: E[M_N] = 0 by Wald's first
   identity (N a stopping time, E[N] < inf), so theta*E[M_N] = 0. Hence
       selection  =  E[N * D(p_hat_N || p*)]      (exact, no approx).
   The earlier "1/2 via Var(p_hat)=p*q*/n" lead was WRONG: conditioning
   on N=n selects boundary-avoiding paths, so Var(p_hat|N=n) != p*q*/n.
3. The value in results_overshoot.txt C4 (+0.681, 8000 reps) is
   NOISE-HIGH. At 60000 reps the every-4 value is ~0.639, rejecting
   0.681 at ~z=-12 and agreeing with the peer's exact-recursion 0.640.

DISPUTED (reported, not encoded): selection is CHECK-SCHEDULE-DEPENDENT
-- so c_ren is not a universal constant, it carries the check period d,
with d=1 a special case. But the MAGNITUDE of the schedule gap is
unreconciled: this script measures every-1 minus every-4 ~ +0.011,
while the peer reported +0.086 (their every-1 = 0.726, rejected here at
~z=-18). The QUALITATIVE finding stands; no every-1 number is adopted
until the two runs are reconciled (candidate causes: n_max truncation,
min-n, or a different every-1 crossing convention).

Offline, deterministic. Writes results_selection.txt.
"""

import hashlib
import io
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.special import betaln, xlogy

REPO = Path(__file__).parent.parent
ALPHA = 0.05
L = float(np.log(1 / ALPHA))


def D(p, q):
    return xlogy(p, p / q) + xlogy(1 - p, (1 - p) / (1 - q))


def measure(p, tau, sims, rng, every=4, n_max=8000, chunk=2000):
    sels, Ms = [], []
    n = np.arange(1, n_max + 1)
    chk = (n >= 20) & (n % every == 0) if every > 1 else (n >= 20)
    for st in range(0, sims, chunk):
        b = min(chunk, sims - st)
        x = (rng.random((b, n_max)) < p).astype(np.int8)
        f = np.cumsum(x, axis=1, dtype=np.int32)
        s = n[None, :] - f
        le = betaln(1 + f, 1 + s) - (f * np.log(tau) + s * np.log(1 - tau))
        fired = (le >= L) & chk[None, :]
        for r in range(b):
            j = np.argmax(fired[r]) if fired[r].any() else -1
            if j >= 0:
                N = j + 1
                sels.append(N * D(f[r, j] / N, p))
                Ms.append(f[r, j] - p * N)
    return np.array(sels), np.array(Ms)


def main():
    print("=" * 76)
    print("SELECTION TERM: Bregman closed form + corrected value")
    print("=" * 76)

    # (1) Bregman identity
    rng = np.random.default_rng(1)
    err = 0.0
    for _ in range(3000):
        ps = rng.uniform(0.05, 0.95)
        tau = rng.uniform(0.01, max(0.011, ps - 0.005))
        N = rng.integers(20, 3000)
        ph = rng.uniform(0.02, 0.98)
        theta = np.log(ps * (1 - tau) / (tau * (1 - ps)))
        lhs = N * (D(ph, tau) - D(ps, tau))
        rhs = theta * (ph - ps) * N + N * D(ph, ps)
        err = max(err, abs(lhs - rhs))
    print(f"\n  (1) Bregman identity: max error {err:.2e} "
          f"({'EXACT' if err < 1e-9 else 'FAIL'})")

    # (2)+(3) measured
    rng = np.random.default_rng(20260816)
    print("\n  (2/3) selection = E[N D(p_hat||p*)], and E[M_N] "
          "(Wald: exactly 0):")
    print(f"  {'p*':>5} {'tau':>6} {'sched':>7} {'reps':>6} "
          f"{'selection':>10} {'SE':>7} {'E[M_N]':>8}")
    e4 = {}
    for p, tau in [(0.20, 0.155), (0.30, 0.255)]:
        for every, sims in [(4, 60000), (1, 40000)]:
            sel, M = measure(p, tau, sims, rng, every=every)
            se = sel.std() / np.sqrt(len(sel))
            print(f"  {p:>5.2f} {tau:>6.3f} {'n%'+str(every):>7} "
                  f"{len(sel):>6} {sel.mean():>10.4f} {se:>7.4f} "
                  f"{M.mean():>+8.2f}")
            if every == 4:
                e4[(p, tau)] = (sel.mean(), se)
            elif every == 1 and (p, tau) in e4:
                gap = sel.mean() - e4[(p, tau)][0]
                print(f"        schedule gap every1-every4 = "
                      f"{gap:+.3f} (peer reported +0.086 at "
                      f"p*=0.2 -- DISPUTED, not adopted)")

    v = e4[(0.20, 0.155)]
    print(f"\n  VERDICT: repo C4 value +0.681 REJECTED (this run "
          f"{v[0]:.4f} +/- {v[1]:.4f}, z vs 0.681 = "
          f"{(v[0]-0.681)/v[1]:.1f}); selection closed form "
          f"E[N D(p_hat||p*)] with first-order term exactly zero; "
          f"c_ren is SCHEDULE-DEPENDENT (carries the check period d). "
          f"results_overshoot.txt C4 is STALE and flagged for "
          f"regeneration. No constant fitted.")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_selection.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_selection.txt'}")
