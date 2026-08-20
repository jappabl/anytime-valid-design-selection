#!/usr/bin/env python3
"""Compare pre-registered finite-L formulas with the exact absorption oracle."""

from __future__ import annotations

import argparse
import math
import sys

sys.path.insert(0, "/tmp")

from finite_l_oracle import exact_oracle
from finite_l_prediction import (
    inverse_time_brownian,
    ladder_curvature_constant,
    params,
    reciprocal_center,
    rho_spitzer,
    rho_spitzer_tangent,
    shared_score_prediction,
)


def constants(p: float, tau: float, d: int, h: float = 1e-4) -> dict[str, float]:
    rho = rho_spitzer(p, tau, d)
    rp = rho_spitzer_tangent(p, tau, d, p + h)
    rm = rho_spitzer_tangent(p, tau, d, p - h)
    return {
        "rho": rho,
        "rho1": (rp - rm) / (2.0 * h),
        "rho2": (rp - 2.0 * rho + rm) / (h * h),
        "curv": ladder_curvature_constant(p, tau, d)["curvature"],
    }


def asymptotic_predictions(
    L: float, p: float, tau: float, const: dict[str, float]
) -> tuple[float, float]:
    q, _, _, c, mu = params(p, tau)
    pq = p * q
    os_corr = (
        pq * c * const["rho1"]
        + 0.5 * pq * mu * const["rho2"]
        + mu * const["curv"]
    ) / L
    sel_corr = (1.0 + (q - p) * c) / (2.0 * L)
    return const["rho"] + os_corr, sel_corr


def run_grid(pairs, ds, alphas, n0: int) -> None:
    columns = [
        "p",
        "tau",
        "d",
        "alpha",
        "L",
        "rho",
        "exact_os",
        "asym_os",
        "renorm_os",
        "ig_os",
        "exact_selcov",
        "asym_selcov",
        "renorm_selcov",
        "ig_selcov",
        "mean_n",
        "mean_inv_n",
        "median_n",
        "tail",
    ]
    print(",".join(columns), flush=True)
    for p, tau in pairs:
        for d in ds:
            const = constants(p, tau, d)
            for alpha in alphas:
                L = math.log(1.0 / alpha)
                exact = exact_oracle(p, tau, L, d, n0=n0)
                asym_os, asym_sel = asymptotic_predictions(L, p, tau, const)
                renorm = shared_score_prediction(
                    L, p, tau, d, inverse_time=reciprocal_center
                )
                ig = shared_score_prediction(
                    L, p, tau, d, inverse_time=inverse_time_brownian
                )
                values = [
                    p,
                    tau,
                    d,
                    alpha,
                    L,
                    const["rho"],
                    exact.mean_overshoot,
                    asym_os,
                    renorm["overshoot"],
                    ig["overshoot"],
                    exact.selection_cov_correction,
                    asym_sel,
                    renorm["selection_cov"],
                    ig["selection_cov"],
                    exact.mean_n,
                    exact.mean_inv_n,
                    exact.median_n,
                    exact.tail_mass,
                ]
                print(",".join(str(v) for v in values), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args()
    if args.extended:
        run_grid(
            [(0.202, 0.157)],
            [4],
            [math.exp(-x) for x in [8.0, 10.0, 15.0, 20.0, 30.0, 50.0]],
            20,
        )
    else:
        run_grid(
            [(0.202, 0.157), (0.3, 0.2)],
            [1, 2, 4],
            [0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.002],
            20,
        )


if __name__ == "__main__":
    main()
