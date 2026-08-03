"""Closed-form confidence bounds used by the offline experiment scripts.

The betting bounds here are the closed form of BernoulliCSBetting (the
sequential Beta-predictive e-value telescopes to a marginal likelihood
ratio); equivalence and time-uniform coverage are validated in
scripts/validate_betting_cs.py and tests/test_betting_cs.py.

Wald and Wilson intervals are FIXED-n intervals with no time-uniform
guarantee; they are included only to demonstrate miscoverage under peeking.
"""

import numpy as np
from scipy.special import betaln
from scipy.stats import norm


def log_e_value(f: int, s: int, p0: float, a: float = 1.0, b: float = 1.0) -> float:
    """Log e-value for point null p = p0 under a Beta(a,b) mixture."""
    p0 = min(max(p0, 1e-12), 1 - 1e-12)
    log_marginal = betaln(a + f, b + s) - betaln(a, b)
    log_null = f * np.log(p0) + s * np.log(1 - p0)
    return log_marginal - log_null


def betting_bounds(f: int, s: int, alpha: float = 0.05) -> tuple:
    """Anytime-valid confidence interval {p0 : e(p0) < 1/alpha}."""
    n = f + s
    if n == 0:
        return 0.0, 1.0
    thresh = np.log(1.0 / alpha)
    p_hat = f / n

    if log_e_value(f, s, 1 - 1e-9) < thresh:
        ucb = 1.0
    else:
        lo, hi = p_hat, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if log_e_value(f, s, mid) >= thresh:
                hi = mid
            else:
                lo = mid
        ucb = hi

    if log_e_value(f, s, 1e-9) < thresh:
        lcb = 0.0
    else:
        lo, hi = 0.0, p_hat
        for _ in range(50):
            mid = (lo + hi) / 2
            if log_e_value(f, s, mid) >= thresh:
                lo = mid
            else:
                hi = mid
        lcb = lo

    return lcb, ucb


def intersection_bounds(f: int, s: int, alpha: float = 0.05) -> tuple:
    """Stitched Hoeffding ∩ empirical-Bernstein CS (alpha/2 each)."""
    n = f + s
    if n == 0:
        return 0.0, 1.0
    p_hat = f / n
    delta_n = (alpha / 2) / (n * (n + 1))
    log_term = np.log(2.0 / delta_n)

    eps_h = np.sqrt(log_term / (2 * n))
    if n > 1:
        var_hat = p_hat * (1 - p_hat)
        eps_b = np.sqrt(2 * var_hat * log_term / n) + (7 / 3) * log_term / (n - 1)
    else:
        eps_b = 1.0

    lower = max(0.0, p_hat - eps_h, p_hat - eps_b)
    upper = min(1.0, p_hat + eps_h, p_hat + eps_b)
    return lower, upper


def wald_interval(f: int, s: int, alpha: float = 0.05) -> tuple:
    """Fixed-n Wald interval. NOT valid under peeking (demo only)."""
    n = f + s
    if n == 0:
        return 0.0, 1.0
    p_hat = f / n
    z = norm.ppf(1 - alpha / 2)
    eps = z * np.sqrt(max(p_hat * (1 - p_hat), 1e-12) / n)
    return max(0.0, p_hat - eps), min(1.0, p_hat + eps)


def wilson_interval(f: int, s: int, alpha: float = 0.05) -> tuple:
    """Fixed-n Wilson score interval. NOT valid under peeking (demo only)."""
    n = f + s
    if n == 0:
        return 0.0, 1.0
    p_hat = f / n
    z = norm.ppf(1 - alpha / 2)
    z2 = z * z
    denom = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    half = z * np.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)
