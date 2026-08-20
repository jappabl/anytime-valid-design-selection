#!/usr/bin/env python3
"""Pre-registered finite-L prediction; contains no full log-E oracle."""

from __future__ import annotations

import argparse
import math
from functools import lru_cache

import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import lambertw
from scipy.special import ndtri


def params(p: float, tau: float) -> tuple[float, float, float, float, float]:
    q = 1.0 - p
    a = math.log(p / tau)
    b = math.log(q / (1.0 - tau))
    c = a - b
    mu = p * a + q * b
    return q, a, b, c, mu


def tangent_params(
    p: float, tau: float, u: float
) -> tuple[float, float, float, float, float]:
    """Increment law under true p, locally tangent at Bernoulli parameter u."""
    q = 1.0 - p
    a = math.log(u / tau)
    b = math.log((1.0 - u) / (1.0 - tau))
    c = a - b
    mu = p * a + q * b
    return q, a, b, c, mu


def block_probs(d: int, p: float) -> np.ndarray:
    q = 1.0 - p
    return np.array(
        [math.comb(d, k) * p**k * q ** (d - k) for k in range(d + 1)],
        dtype=float,
    )


def ladder_curvature_constant(
    p: float, tau: float, d: int, tol: float = 2e-15
) -> dict[str, float]:
    """Moments of the first strict ladder height and beta-ratio curvature."""
    q, _, b, c, _ = params(p, tau)
    kernel = block_probs(d, p)
    live = np.array([1.0])
    mass = eh = eh2 = ec = ehc = 0.0
    ehw = ehw2_minus_vt = 0.0
    for j in range(1, 500_000):
        live = np.convolve(live, kernel)
        k = np.arange(live.size, dtype=float)
        r = float(j * d)
        position = r * b + c * k
        hit = position > 0.0
        if np.any(hit):
            prob = live[hit]
            hh = position[hit]
            kk = k[hit]
            cc = (
                kk * (kk + 1.0) / (2.0 * p)
                + (r - kk) * (r - kk + 1.0) / (2.0 * q)
                - r * (r + 3.0) / 2.0
            )
            ww = kk - p * r
            mass += float(prob.sum())
            eh += float(np.dot(prob, hh))
            eh2 += float(np.dot(prob, hh * hh))
            ec += float(np.dot(prob, cc))
            ehc += float(np.dot(prob, hh * cc))
            ehw += float(np.dot(prob, hh * ww))
            ehw2_minus_vt += float(
                np.dot(prob, hh * (ww * ww - p * q * r))
            )
            live[hit] = 0.0
        if float(live.sum()) < tol:
            break
    else:
        raise RuntimeError("ladder recursion failed to converge")
    rho = eh2 / (2.0 * eh)
    curvature = (ehc - rho * ec) / eh
    q_cycle = ehw2_minus_vt / (2.0 * p * q * eh)
    return {
        "mass": mass,
        "EH": eh / mass,
        "EH2": eh2 / mass,
        "EC": ec / mass,
        "EHC": ehc / mass,
        "rho": rho,
        "curvature": curvature,
        "EHW_over_EH": ehw / eh,
        "quadratic_cycle": q_cycle,
    }


def base_overshoot(x: float, p: float, tau: float, d: int, tol: float = 2e-15) -> float:
    """Exact finite-level mean overshoot of the d-draw linear skeleton."""
    if x <= 0.0:
        return -x
    _, _, b, c, _ = params(p, tau)
    kernel = block_probs(d, p)
    live = np.array([1.0])
    absorbed = 0.0
    mean_excess = 0.0
    max_blocks = 200_000
    for j in range(1, max_blocks + 1):
        live = np.convolve(live, kernel)
        f = np.arange(live.size)
        position = j * d * b + c * f
        hit = position >= x
        if np.any(hit):
            mass = live[hit]
            absorbed += float(mass.sum())
            mean_excess += float(np.dot(mass, position[hit] - x))
            live[hit] = 0.0
        if float(live.sum()) < tol:
            break
    else:
        raise RuntimeError(f"base renewal failed to converge: x={x}, live={live.sum()}")
    if abs(absorbed + float(live.sum()) - 1.0) > 2e-11:
        raise RuntimeError("base renewal lost probability mass")
    return mean_excess / absorbed


def rho_spitzer_tangent(
    p: float, tau: float, d: int, u: float, tol: float = 2e-15
) -> float:
    """Closed Spitzer expression supplied in the problem statement."""
    q, _, b, c, mu = tangent_params(p, tau, u)
    if mu <= 0.0:
        raise ValueError("tangent increment must have positive drift")
    sigma2 = c * c * p * q
    total = 0.0
    # A_n/m decays exponentially for positive drift; sum blocks m.
    from scipy.special import bdtr

    for m in range(1, 2_000_000):
        n = d * m
        k = math.ceil(-n * b / c) - 1
        # Binomial CDF conventions outside [0,n].
        Fn = 0.0 if k < 0 else (1.0 if k >= n else float(bdtr(k, n, p)))
        km1 = k - 1
        Fnm1 = 0.0 if km1 < 0 else (1.0 if km1 >= n - 1 else float(bdtr(km1, n - 1, p)))
        A = -n * b * Fn - c * n * p * Fnm1
        term = A / m
        total += term
        if m > 100 and abs(term) < tol:
            break
    else:
        raise RuntimeError("Spitzer series failed to converge")
    return sigma2 / (2.0 * mu) + d * mu / 2.0 - total


def rho_spitzer(p: float, tau: float, d: int, tol: float = 2e-15) -> float:
    return rho_spitzer_tangent(p, tau, d, p, tol)


def rho_tangent_derivatives_formal(
    p: float, tau: float, d: int, tol: float = 2e-14
) -> tuple[float, float]:
    """Termwise derivatives at u=p, holding each Spitzer ceiling index fixed."""
    from scipy.special import bdtr

    q, _, b, c, mu = params(p, tau)
    v = p * q
    bp = -1.0 / q
    bpp = -1.0 / (q * q)
    cp = 1.0 / v
    cpp = (2.0 * p - 1.0) / (v * v)
    mup = 0.0
    mupp = -1.0 / v
    sum1 = 0.0
    sum2 = 0.0
    for m in range(1, 2_000_000):
        n = d * m
        k = math.ceil(-n * b / c) - 1
        Fn = 0.0 if k < 0 else (1.0 if k >= n else float(bdtr(k, n, p)))
        km1 = k - 1
        Fnm1 = 0.0 if km1 < 0 else (1.0 if km1 >= n - 1 else float(bdtr(km1, n - 1, p)))
        A1 = -n * bp * Fn - cp * n * p * Fnm1
        A2 = -n * bpp * Fn - cpp * n * p * Fnm1
        t1 = A1 / m
        t2 = A2 / m
        sum1 += t1
        sum2 += t2
        if m > 100 and max(abs(t1), abs(t2)) < tol:
            break
    else:
        raise RuntimeError("formal derivative series failed to converge")
    rho1 = v * c * cp / mu - sum1
    rho2 = (
        v * ((cp * cp + c * cpp) / mu - c * c * mupp / (2.0 * mu * mu))
        + d * mupp / 2.0
        - sum2
    )
    return rho1, rho2


def center_time(L: float, p: float, tau: float, rho: float) -> float:
    """KW self-consistent center using E[Q]=1/2."""
    q, _, _, _, mu = params(p, tau)
    kappa = 0.5 * math.log(2.0 * math.pi * p * q)
    rhs = L + rho - kappa - 0.5
    arg = -2.0 * mu * math.exp(-2.0 * rhs)
    return float(-lambertw(arg, -1).real / (2.0 * mu))


@lru_cache(maxsize=None)
def cached_base_overshoot(x_rounded: float, p: float, tau: float, d: int) -> float:
    return base_overshoot(x_rounded, p, tau, d)


def frozen_quadratic_prediction(
    L: float, p: float, tau: float, d: int, quadrature_order: int = 32
) -> tuple[float, float, float]:
    """rho + E[r_d(A_L-Q)-rho], Q~chi-square_1/2."""
    rho = rho_spitzer(p, tau, d)
    nbar = center_time(L, p, tau, rho)
    q = 1.0 - p
    kappa = 0.5 * math.log(2.0 * math.pi * p * q)
    A = L + 0.5 * math.log(nbar) - kappa
    nodes, weights = hermgauss(quadrature_order)
    # For Z~N(0,1), Q=Z^2/2=x^2 under Hermite weight exp(-x^2).
    vals = np.array([base_overshoot(A - x * x, p, tau, d) for x in nodes])
    pred = float(np.dot(weights, vals) / math.sqrt(math.pi))
    return pred, rho, nbar


def frozen_quadratic_quantile_prediction(
    L: float, p: float, tau: float, d: int, points: int = 512
) -> tuple[float, float, float]:
    """Mid-quantile integration, robust to jumps in the renewal remainder."""
    rho = rho_spitzer(p, tau, d)
    nbar = center_time(L, p, tau, rho)
    q = 1.0 - p
    kappa = 0.5 * math.log(2.0 * math.pi * p * q)
    A = L + 0.5 * math.log(nbar) - kappa
    half = points // 2
    u = (np.arange(half, dtype=float) + 0.5) / points
    qvals = 0.5 * ndtri(u) ** 2
    vals = np.array([base_overshoot(A - value, p, tau, d) for value in qvals])
    return float(vals.mean()), rho, nbar


def selection_leading(L: float, p: float, tau: float) -> float:
    """Exact-score leading correction from E(1/N)=D(p||tau)/L+o(L^-1)."""
    q, _, _, c, _ = params(p, tau)
    return (1.0 + (q - p) * c) / (2.0 * L)


def tangent_second_order_prediction(
    L: float, p: float, tau: float, d: int, derivative_step: float = 1e-4
) -> tuple[float, float, float, float]:
    """Local tangent correction pq*rho''(p)/(2*nbar), with no fitted inputs."""
    rho = rho_spitzer(p, tau, d)
    nbar = center_time(L, p, tau, rho)
    h = derivative_step
    rp = rho_spitzer_tangent(p, tau, d, p + h)
    rm = rho_spitzer_tangent(p, tau, d, p - h)
    rho2 = (rp - 2.0 * rho + rm) / (h * h)
    correction = p * (1.0 - p) * rho2 / (2.0 * nbar)
    return rho + correction, rho, nbar, rho2


def reciprocal_center(L: float, p: float, tau: float, d: int) -> float:
    rho = rho_spitzer(p, tau, d)
    return 1.0 / center_time(L, p, tau, rho)


def inverse_time_brownian(L: float, p: float, tau: float, d: int) -> float:
    """Inverse-Gaussian E(1/T), centered by nonlinear-renewal mean time."""
    q, _, _, c, mu = params(p, tau)
    rho = rho_spitzer(p, tau, d)
    nbar = center_time(L, p, tau, rho)
    sigma2 = c * c * p * q
    return 1.0 / nbar + sigma2 / (mu * mu * nbar * nbar)


def shared_score_prediction(
    L: float,
    p: float,
    tau: float,
    d: int,
    derivative_step: float = 1e-4,
    inverse_time=inverse_time_brownian,
) -> dict[str, float]:
    """Tangent/score correction driven by h_L(p)=E(1/N)~=1/nbar."""
    hstep = derivative_step
    rho = rho_spitzer(p, tau, d)
    h0 = inverse_time(L, p, tau, d)
    hpv = inverse_time(L, p + hstep, tau, d)
    hmv = inverse_time(L, p - hstep, tau, d)
    h1 = (hpv - hmv) / (2.0 * hstep)
    h2 = (hpv - 2.0 * h0 + hmv) / (hstep * hstep)

    rup = rho_spitzer_tangent(p, tau, d, p + hstep)
    rum = rho_spitzer_tangent(p, tau, d, p - hstep)
    r1 = (rup - rum) / (2.0 * hstep)
    r2 = (rup - 2.0 * rho + rum) / (hstep * hstep)
    pq = p * (1.0 - p)
    ladder = ladder_curvature_constant(p, tau, d)
    os_score_corr = pq * r1 * h1 + 0.5 * pq * r2 * h0
    os_curvature_corr = ladder["curvature"] * h0
    os_corr = os_score_corr + os_curvature_corr
    sel_corr = 0.5 * pq * h2 - 0.5 * (2.0 * p - 1.0) * h1
    return {
        "h": h0,
        "h1": h1,
        "h2": h2,
        "rho1_tangent": r1,
        "rho2_tangent": r2,
        "ladder_curvature": ladder["curvature"],
        "overshoot_score_correction": os_score_corr,
        "overshoot_curvature_correction": os_curvature_corr,
        "overshoot_correction": os_corr,
        "overshoot": rho + os_corr,
        "selection_cov": sel_corr,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=float, required=True)
    parser.add_argument("--tau", type=float, required=True)
    parser.add_argument("--d", type=int, required=True)
    parser.add_argument("--L", type=float, required=True)
    parser.add_argument("--quadrature", type=int, default=32)
    args = parser.parse_args()
    pred, rho, nbar = frozen_quadratic_prediction(
        args.L, args.p, args.tau, args.d, args.quadrature
    )
    print(f"PREDICTION p={args.p:.12g} tau={args.tau:.12g} d={args.d} L={args.L:.12g}")
    print(f"rho={rho:.12f}")
    print(f"nbar={nbar:.9f}")
    print(f"overshoot_pred={pred:.12f}")
    print(f"overshoot_correction={pred-rho:+.12f}")
    print(f"selection_cov_pred={selection_leading(args.L,args.p,args.tau):+.12f}")
    tan_pred, _, _, rho2 = tangent_second_order_prediction(
        args.L, args.p, args.tau, args.d
    )
    print(f"tangent_rho_second_derivative={rho2:+.12f}")
    print(f"tangent_overshoot_pred={tan_pred:.12f}")
    print(f"tangent_overshoot_correction={tan_pred-rho:+.12f}")
    shared = shared_score_prediction(args.L, args.p, args.tau, args.d)
    for key, value in shared.items():
        print(f"shared_{key}={value:+.12f}")
    reciprocal = shared_score_prediction(
        args.L, args.p, args.tau, args.d, inverse_time=reciprocal_center
    )
    print(f"reciprocal_center_overshoot={reciprocal['overshoot']:+.12f}")
    print(f"reciprocal_center_selection_cov={reciprocal['selection_cov']:+.12f}")


if __name__ == "__main__":
    main()
