"""Validate BernoulliCSBetting: correctness, time-uniform coverage, width vs intersection.

Key questions:
1. Does the fast closed-form e-value match the repo's loop implementation? (sanity)
2. Is time-uniform coverage >= 95% (checked at ALL n, not just final)?
3. How much tighter is betting CS than the Hoeffding/Bernstein intersection?
4. Would the real-LLM experiment (p~0.25, width target 0.35, n_max=100) have stopped early?
"""

import sys
from pathlib import Path

import numpy as np
from scipy.special import betaln

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.bernoulli_cs_betting import BernoulliCSBetting
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


# ---------------------------------------------------------------------------
# Fast closed-form equivalent of the repo's betting CS
# log E(p0) = log[Beta(a+f, b+s)/Beta(a,b)] - [f log p0 + s log(1-p0)]
# (the sequential product of Beta predictive ratios telescopes to this)
# ---------------------------------------------------------------------------

def log_e_value(f: int, s: int, p0: float, a: float = 1.0, b: float = 1.0) -> float:
    p0 = min(max(p0, 1e-10), 1 - 1e-10)
    log_marginal = betaln(a + f, b + s) - betaln(a, b)
    log_null = f * np.log(p0) + s * np.log(1 - p0)
    return log_marginal - log_null


def betting_bounds(f: int, s: int, alpha: float = 0.05) -> tuple:
    """Confidence set {p0 : log E(p0) < log(1/alpha)}; return its inf/sup."""
    n = f + s
    if n == 0:
        return 0.0, 1.0
    thresh = np.log(1.0 / alpha)
    p_hat = f / n

    # E(p0) is increasing in p0 on [p_hat, 1]; rejected region is [ucb, 1].
    # Invariant: E(lo) < thresh, E(hi) >= thresh; converge to the crossing.
    if log_e_value(f, s, 1 - 1e-9) < thresh:
        ucb = 1.0
    else:
        lo, hi = p_hat, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if log_e_value(f, s, mid) >= thresh:
                hi = mid
            else:
                lo = mid
        ucb = hi

    # E(p0) is decreasing in p0 on [0, p_hat]; rejected region is [0, lcb].
    if log_e_value(f, s, 1e-9) < thresh:
        lcb = 0.0
    else:
        lo, hi = 0.0, p_hat
        for _ in range(60):
            mid = (lo + hi) / 2
            if log_e_value(f, s, mid) >= thresh:
                lo = mid
            else:
                hi = mid
        lcb = lo

    return lcb, ucb


# ---------------------------------------------------------------------------
# 1. Sanity: closed form matches repo implementation
# ---------------------------------------------------------------------------

def check_matches_repo():
    print("1. CLOSED FORM vs REPO IMPLEMENTATION")
    rng = np.random.default_rng(0)
    max_err = 0.0
    for _ in range(20):
        n = int(rng.integers(1, 60))
        f = int(rng.integers(0, n + 1))
        cs = BernoulliCSBetting(alpha=0.05)
        for i in range(n):
            cs.update(i < f)
        for p0 in [0.05, 0.2, 0.5, 0.8]:
            repo_val = cs._log_e_value_upper(p0)
            fast_val = log_e_value(f, n - f, p0)
            max_err = max(max_err, abs(repo_val - fast_val))
    print(f"   max |repo - closed_form| over 80 cases: {max_err:.2e}")
    assert max_err < 1e-6, "MISMATCH — closed form is not equivalent"
    print("   MATCH: repo loop == Beta-Bernoulli marginal likelihood ratio\n")


# ---------------------------------------------------------------------------
# 2. Time-uniform coverage (the property that actually matters)
# ---------------------------------------------------------------------------

def check_coverage(n_reps: int = 400, n_max: int = 200, alpha: float = 0.05):
    print(f"2. TIME-UNIFORM COVERAGE ({n_reps} reps, n_max={n_max}, alpha={alpha})")
    print("   miss = true p outside [LCB, UCB] at ANY n in 1..n_max")
    for p_true in [0.02, 0.05, 0.1375, 0.25, 0.5]:
        rng = np.random.default_rng(42)
        misses = 0
        for rep in range(n_reps):
            x = rng.random(n_max) < p_true
            f = 0
            missed = False
            for n in range(1, n_max + 1):
                f += int(x[n - 1])
                lcb, ucb = betting_bounds(f, n - f, alpha)
                if not (lcb <= p_true <= ucb):
                    missed = True
                    break
            misses += missed
        cov = 1 - misses / n_reps
        status = "PASS" if cov >= 1 - alpha - 0.02 else "FAIL"
        print(f"   p={p_true:.4f}: coverage {n_reps - misses}/{n_reps} = {cov:.3f}  [{status}]")
    print()


# ---------------------------------------------------------------------------
# 3. Width comparison + real-LLM stopping rescue
# ---------------------------------------------------------------------------

def width_comparison():
    print("3. WIDTH: betting vs intersection (deterministic failures = round(p*n))")
    print(f"   {'p':>6} {'n':>5} {'intersect':>10} {'betting':>9} {'ratio':>6}")
    for p in [0.05, 0.1375, 0.25]:
        for n in [50, 100, 200]:
            f = round(p * n)
            cs_i = BernoulliCSIntersection(alpha=0.05, n_max=1000)
            for i in range(n):
                cs_i.update(i < f)
            lo_i, hi_i = cs_i.get_bounds()
            w_i = hi_i - lo_i
            lo_b, hi_b = betting_bounds(f, n - f)
            w_b = hi_b - lo_b
            print(f"   {p:>6.4f} {n:>5} {w_i:>10.4f} {w_b:>9.4f} {w_b / w_i:>6.2f}")
    print()

    print("4. REAL-LLM RESCUE: p=0.25, precision target width<=0.35, min n=20")
    for label, width_fn in [
        ("intersection", lambda f, s: (lambda b: b[1] - b[0])(_intersection_bounds(f, s))),
        ("betting", lambda f, s: (lambda b: b[1] - b[0])(betting_bounds(f, s))),
    ]:
        n_stop = None
        for n in range(20, 1001):
            f = round(0.25 * n)
            if width_fn(f, n - f) <= 0.35:
                n_stop = n
                break
        print(f"   {label:>12}: first n with width<=0.35 is {n_stop}")

    print()
    print("5. CERTIFICATION RESCUE: true p=0.05, certify UCB <= 0.15")
    for label, ucb_fn in [
        ("intersection", lambda f, s: _intersection_bounds(f, s)[1]),
        ("betting", lambda f, s: betting_bounds(f, s)[1]),
    ]:
        n_cert = None
        for n in range(20, 2001):
            f = round(0.05 * n)
            if ucb_fn(f, n - f) <= 0.15:
                n_cert = n
                break
        print(f"   {label:>12}: first n with UCB<=0.15 is {n_cert}")


def _intersection_bounds(f: int, s: int) -> tuple:
    n = f + s
    cs = BernoulliCSIntersection(alpha=0.05, n_max=2000)
    for i in range(n):
        cs.update(i < f)
    return cs.get_bounds()


if __name__ == "__main__":
    import hashlib
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        print("=" * 80)
        print("BETTING CS VALIDATION (post binary-search inversion fix)")
        print("=" * 80)
        print()
        check_matches_repo()
        check_coverage()
        width_comparison()

    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 80 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 80 + "\n"

    print(content, end="")
    out_path = REPO / "results_betting_cs.txt"
    out_path.write_text(content)
    print(f"\nResults written to: {out_path}")
