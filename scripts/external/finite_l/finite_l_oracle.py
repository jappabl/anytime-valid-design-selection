#!/usr/bin/env python3
"""Exact absorption recursion for beta(1,1)-mixture Bernoulli e-values."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln


@dataclass(frozen=True)
class OracleResult:
    p: float
    tau: float
    L: float
    d: int
    n0: int
    mass: float
    tail_mass: float
    steps: int
    mean_n: float
    mean_inv_n: float
    mean_overshoot: float
    mean_selection_kl: float
    mean_quadratic: float
    selection_cov_correction: float
    martingale_mean: float
    mean_m_over_n: float
    mean_m2_over_n2: float
    score_h1: float
    score_h2: float
    median_n: int


def log_e_values(n: int, tau: float) -> np.ndarray:
    f = np.arange(n + 1, dtype=float)
    s = n - f
    return (
        gammaln(f + 1.0)
        + gammaln(s + 1.0)
        - gammaln(n + 2.0)
        - f * math.log(tau)
        - s * math.log1p(-tau)
    )


def binomial_probs(n: int, p: float) -> np.ndarray:
    f = np.arange(n + 1, dtype=float)
    logs = (
        gammaln(n + 1.0)
        - gammaln(f + 1.0)
        - gammaln(n - f + 1.0)
        + f * math.log(p)
        + (n - f) * math.log1p(-p)
    )
    out = np.exp(logs)
    return out / out.sum()


def block_kernel(d: int, p: float) -> np.ndarray:
    return binomial_probs(d, p)


def kl_bernoulli(u: np.ndarray, p: float) -> np.ndarray:
    ans = np.zeros_like(u)
    interior = (u > 0.0) & (u < 1.0)
    ui = u[interior]
    ans[interior] = ui * np.log(ui / p) + (1.0 - ui) * np.log(
        (1.0 - ui) / (1.0 - p)
    )
    ans[u == 0.0] = -math.log1p(-p)
    ans[u == 1.0] = -math.log(p)
    return ans


def exact_oracle(
    p: float,
    tau: float,
    L: float,
    d: int,
    n0: int = 20,
    tol: float = 2e-15,
    max_n: int = 1_000_000,
) -> OracleResult:
    if not (0.0 < tau < p < 1.0):
        raise ValueError("require 0 < tau < p < 1")
    t0 = d * math.ceil(n0 / d)
    live = binomial_probs(t0, p)
    kernel = block_kernel(d, p)
    absorbed_mass = 0.0
    sum_n = sum_inv_n = sum_over = sum_sel = sum_quad = sum_mart = 0.0
    sum_m_over_n = sum_m2_over_n2 = 0.0
    cdf = 0.0
    median_n = -1

    def absorb(n: int, state: np.ndarray) -> None:
        nonlocal absorbed_mass, sum_n, sum_inv_n, sum_over, sum_sel
        nonlocal sum_quad, sum_mart, sum_m_over_n, sum_m2_over_n2
        nonlocal cdf, median_n
        ell = log_e_values(n, tau)
        hit = ell >= L
        if not np.any(hit):
            return
        probs = state[hit]
        ff = np.arange(n + 1, dtype=float)[hit]
        mm = ff - p * n
        mass = float(probs.sum())
        absorbed_mass += mass
        sum_n += mass * n
        sum_inv_n += mass / n
        sum_over += float(np.dot(probs, ell[hit] - L))
        u = ff / n
        sum_sel += float(np.dot(probs, n * kl_bernoulli(u, p)))
        quad = mm * mm / (2.0 * p * (1.0 - p) * n)
        sum_quad += float(np.dot(probs, quad))
        mart = mm * mm - p * (1.0 - p) * n
        sum_mart += float(np.dot(probs, mart))
        sum_m_over_n += float(np.dot(probs, mm / n))
        sum_m2_over_n2 += float(np.dot(probs, mm * mm / (n * n)))
        cdf += mass
        if median_n < 0 and cdf >= 0.5:
            median_n = n
        state[hit] = 0.0

    n = t0
    absorb(n, live)
    steps = 0
    while float(live.sum()) >= tol:
        n += d
        steps += 1
        if n > max_n:
            raise RuntimeError(f"oracle failed to converge by n={max_n}")
        live = np.convolve(live, kernel)
        absorb(n, live)

    tail = float(live.sum())
    if abs(absorbed_mass + tail - 1.0) > 5e-12:
        raise RuntimeError(
            f"probability mass mismatch: absorbed={absorbed_mass}, tail={tail}"
        )
    # Tail is below tolerance; normalize by absorbed mass to remove truncation bias.
    z = absorbed_mass
    mean_quad = sum_quad / z
    mean_m_over_n = sum_m_over_n / z
    mean_m2_over_n2 = sum_m2_over_n2 / z
    pq = p * (1.0 - p)
    score_h1 = mean_m_over_n / pq
    selection_cov = mean_quad - 0.5
    score_h2 = (2.0 * selection_cov + (2.0 * p - 1.0) * score_h1) / pq
    return OracleResult(
        p=p,
        tau=tau,
        L=L,
        d=d,
        n0=n0,
        mass=z,
        tail_mass=tail,
        steps=steps,
        mean_n=sum_n / z,
        mean_inv_n=sum_inv_n / z,
        mean_overshoot=sum_over / z,
        mean_selection_kl=sum_sel / z,
        mean_quadratic=mean_quad,
        selection_cov_correction=selection_cov,
        martingale_mean=sum_mart / z,
        mean_m_over_n=mean_m_over_n,
        mean_m2_over_n2=mean_m2_over_n2,
        score_h1=score_h1,
        score_h2=score_h2,
        median_n=median_n,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=float, required=True)
    parser.add_argument("--tau", type=float, required=True)
    parser.add_argument("--d", type=int, required=True)
    parser.add_argument("--L", type=float, required=True)
    parser.add_argument("--n0", type=int, default=20)
    args = parser.parse_args()
    out = exact_oracle(args.p, args.tau, args.L, args.d, args.n0)
    for key, value in out.__dict__.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
