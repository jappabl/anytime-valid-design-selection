#!/usr/bin/env python3
"""Threshold cycle, first run: close the median-vs-mean piece of c_ren.

c_ren = -1.105 nats decomposes (results_overshoot.txt C4) as
selection -0.68 + overshoot +0.23 + median-vs-mean -0.65. The peer
flagged median-vs-mean as ORDER STATISTICS, not renewal theory — it
should close in closed form given the crossing-time moments.

DERIVATION. The residual is evaluated at the MEDIAN crossing time,
while the expansion is natural at the MEAN. Their gap is
(med N - E N) * V. A sequential first-passage time is asymptotically
normal with a positive-skew correction; Cornish-Fisher gives

    med N - E N  ~  -(gamma1 / 6) * sd(N),

so the median-vs-mean contribution is

    Delta_mvm(p*)  =  -(gamma1 / 6) * sd(N) * V,   V = KL(p*, tau).   (*)

Everything on the right is a crossing-time moment, measurable exactly
from the Bernoulli e-value simulator with NO fitted parameters. This
script measures (gamma1, sd, med, mean) across several (p*, tau) and
checks (*) against the directly-measured (med N - E N) * V.

PRE-REGISTERED (cycle step c): (*) reproduces the measured
median-vs-mean contribution within 0.10 nats at every tested point,
zero fitted parameters. If it does, this piece of c_ren is CLOSED and
the residual shrinks to selection + overshoot; overshoot then gets the
literature pass (Woodroofe / Lai-Siegmund).

Offline, deterministic. Writes results_cren.txt.
"""

import hashlib
import io
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.special import betaln
from scipy.stats import skew

REPO = Path(__file__).parent.parent
ALPHA = 0.05
L = float(np.log(1 / ALPHA))


def kl(p, q):
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def crossing_times(p, tau, sims, rng, n_max=8000, chunk=3000):
    out = []
    n = np.arange(1, n_max + 1)
    check = (n >= 20) & (n % 4 == 0)
    logtau, log1mtau = np.log(tau), np.log(1 - tau)
    for start in range(0, sims, chunk):
        b = min(chunk, sims - start)
        x = (rng.random((b, n_max)) < p).astype(np.int8)
        f = np.cumsum(x, axis=1, dtype=np.int32)
        s = n[None, :] - f
        log_e = betaln(1 + f, 1 + s) - (f * logtau + s * log1mtau)
        fired = (log_e >= L) & check[None, :]
        idx = np.where(fired.any(axis=1), fired.argmax(axis=1) + 1, 0)
        out.append(idx[idx > 0])
    return np.concatenate(out)


def main():
    print("=" * 76)
    print("THRESHOLD CYCLE — closing the median-vs-mean piece of c_ren")
    print("=" * 76)
    print(f"alpha={ALPHA}, prediction (*) Delta_mvm = "
          f"-(gamma1/6)*sd(N)*V, ZERO fitted\n")
    print(f"  {'p*':>5} {'tau':>6} {'medN':>7} {'meanN':>8} "
          f"{'sd':>7} {'skew':>6} {'measured':>9} {'formula(*)':>10} "
          f"{'|err|':>6}")

    rng = np.random.default_rng(20260816)
    errs = []
    for p, m in [(0.15, 0.045), (0.20, 0.045), (0.30, 0.045),
                 (0.20, 0.030), (0.20, 0.060), (0.40, 0.045)]:
        tau = round(p - m, 3)
        N = crossing_times(p, tau, 30000, rng)
        V = kl(p, tau)
        medN, meanN, sd = np.median(N), N.mean(), N.std()
        g1 = float(skew(N))
        measured = (medN - meanN) * V
        formula = -(g1 / 6.0) * sd * V
        err = abs(measured - formula)
        errs.append(err)
        print(f"  {p:>5.2f} {tau:>6.3f} {medN:>7.0f} {meanN:>8.1f} "
              f"{sd:>7.1f} {g1:>6.2f} {measured:>9.3f} "
              f"{formula:>10.3f} {err:>6.3f}")

    worst = max(errs)
    print(f"\n  worst |measured - formula(*)| = {worst:.3f} nats "
          f"(<= 0.10: {'PASS' if worst <= 0.10 else 'FAIL'})")
    print(f"""
READING: if PASS, the median-vs-mean piece of c_ren is CLOSED in terms
of the crossing-time skewness and sd — order statistics, exactly as the
fork predicted. c_ren then reduces to selection + overshoot; the
overshoot term takes the literature pass (Woodroofe nonlinear renewal
ladder heights; Lai-Siegmund; Siegmund's renewal overshoot), which is
recall-gap territory, not a new derivation. The selection term
(E[N(KL(p_hat)-KL(p*))]) is a variance-of-the-rate effect, moderate.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_cren.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_cren.txt'}")
