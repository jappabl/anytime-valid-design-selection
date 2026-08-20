#!/usr/bin/env python3
"""Zero-fit moderate-horizon derivation and shipped-class audit for WSR.

The `predict` command cannot read any results file.  It serializes all
predictions first.  The separate `verify` command is the only code path that
opens the frozen measurement artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np


REPO = Path("/Users/hlin/Documents/badminton/code/research")
sys.path.insert(0, str(REPO / "src"))

# Mandatory: predictions and verification import the shipped implementation.
from eval_harness.stats.wsr_block_cs import WSRBlockCS


ALPHA = 0.05
H = float(np.log(2 / ALPHA))
L = float(np.log(1 / ALPHA))
C_TRUNC = 0.75
GRID = np.linspace(0.0005, 0.9995, 1000)
NMAX = 250_000

K_LADDER = [
    (0.50, [0.402, 0.443, 0.464, 0.476, 0.484]),
    (0.35, [0.260, 0.297, 0.317, 0.328, 0.334]),
    (0.20, [0.129, 0.157, 0.173, 0.182, 0.187]),
]

PDIR_LADDER = {
    (0.20, "UNSAFE"): [0.126, 0.155, 0.170, 0.181, 0.188],
    (0.20, "SAFE"): [0.299, 0.248, 0.224, 0.216, 0.212],
    (0.50, "UNSAFE"): [0.414, 0.447, 0.467, 0.477, 0.484],
    (0.50, "SAFE"): [0.590, 0.552, 0.534, 0.522, 0.517],
    (0.80, "UNSAFE"): [0.706, 0.757, 0.773, 0.782, 0.789],
    (0.80, "SAFE"): [0.877, 0.847, 0.827, 0.817, 0.813],
}

RK_LADDER = {
    (0.20, 1): [0.133, 0.156, 0.171, 0.182],
    (0.20, 3): [0.135, 0.157, 0.172, 0.183],
    (0.20, 10): [0.138, 0.159, 0.174, 0.184],
    (0.20, 30): [0.139, 0.160, 0.174, 0.184],
    (0.35, 1): [0.266, 0.295, 0.315, 0.329],
    (0.35, 3): [0.271, 0.299, 0.318, 0.330],
    (0.35, 10): [0.279, 0.305, 0.322, 0.333],
    (0.35, 30): [0.284, 0.308, 0.324, 0.334],
}


def binomial_law(k: int, p: float) -> tuple[np.ndarray, np.ndarray]:
    j = np.arange(k + 1)
    probs = np.array([
        math.comb(k, int(x)) * p ** int(x) * (1 - p) ** (k - int(x))
        for x in j
    ])
    return j / k, probs


def profile(p: float, ratio: float, k: int) -> np.ndarray:
    p_hi = 2 * p * ratio / (1 + ratio)
    return np.array([p_hi / ratio] * (k // 2) + [p_hi] * (k // 2))


def poisson_binomial_law(rates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    probs = np.array([1.0])
    for p in rates:
        probs = np.convolve(probs, np.array([1 - p, p]))
    return np.arange(len(rates) + 1) / len(rates), probs


def expected_prebet_sq(mu: float, variance: float, nmax: int = NMAX) -> np.ndarray:
    """E[sq] immediately before bet t, exactly under the shipped recursion.

    With t-1 observations, shipped mean=(1/2+sum X_i)/t.  Hence
    E[(X_t-mean_{t-1})^2] = var + (t-1)var/t^2 + (mu-1/2)^2/t^2.
    """
    out = np.empty(nmax)
    sq = 0.25
    bias0 = mu - 0.5
    for t in range(1, nmax + 1):
        out[t - 1] = sq
        sq += variance + (t - 1) * variance / (t * t) + bias0 * bias0 / (t * t)
    return out


_RAW_CACHE: dict[tuple[float, float], np.ndarray] = {}


def raw_schedule(mu: float, variance: float) -> np.ndarray:
    key = (round(mu, 14), round(variance, 14))
    if key not in _RAW_CACHE:
        sq = expected_prebet_sq(mu, variance)
        t = np.arange(1, NMAX + 1, dtype=float)
        _RAW_CACHE[key] = np.sqrt(2 * H / (sq * np.log(t + 1) + 1e-12))
    return _RAW_CACHE[key]


def binding_transform(
    atoms: np.ndarray,
    probs: np.ndarray,
    mu: float,
    tau: float,
    direction: str,
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Return an UNSAFE-form problem, including the actual binding grid point.

    SAFE is transformed by Y=1-X.  Its binding original grid point is the
    first point strictly above tau, so the transformed point is 1-m.
    """
    if direction == "UNSAFE":
        m = float(GRID[GRID <= tau][-1])
        return atoms, probs, mu, m, tau
    original_m = float(GRID[GRID > tau][0])
    return atoms, probs[::-1], 1 - mu, 1 - original_m, 1 - tau


def kelly_rate_grid(atoms: np.ndarray, probs: np.ndarray, m: float) -> float:
    lambdas = np.linspace(0.001, 1 / max(m, 1e-9) - 1e-6, 3000)
    growth = np.log1p(np.outer(lambdas, atoms - m)) @ probs
    return float(np.max(growth))


def deterministic_crossing(
    atoms: np.ndarray,
    probs: np.ndarray,
    mu: float,
    m: float,
    approximation: str = "exact",
) -> int:
    """Zero-parameter moderate-horizon equivalent of the shipped capital.

    It replaces random sq by its exact expectation, retains the shipped cap,
    and solves E log K+_T = H.  No crossing result or envelope constant enters.
    """
    variance = float(np.sum(probs * (atoms - mu) ** 2))
    lam = np.minimum(raw_schedule(mu, variance), C_TRUNC / m)
    z = atoms - m
    if approximation == "exact":
        drift = np.log1p(np.outer(lam, z)) @ probs
    elif approximation == "quadratic":
        gap = mu - m
        q = variance + gap * gap
        drift = lam * gap - 0.5 * lam * lam * q
    else:
        raise ValueError(approximation)
    cumulative = np.cumsum(drift)
    hit = np.flatnonzero(cumulative >= H)
    if hit.size == 0:
        raise RuntimeError(f"no deterministic crossing by T={NMAX}")
    return int(hit[0] + 1)


def fit_dc(n: np.ndarray, overhead: np.ndarray) -> tuple[float, float]:
    design = np.stack([np.log(n) / 2, np.ones_like(n)], axis=1)
    d, c = np.linalg.lstsq(design, overhead, rcond=None)[0]
    return float(d), float(c)


def line_in_k(values: dict[int, tuple[float, float]]) -> dict[str, float]:
    ks = np.array(sorted(values), dtype=float)
    ds = np.array([values[int(k)][0] for k in ks])
    cs = np.array([values[int(k)][1] for k in ks])
    d_slope, d_intercept = np.polyfit(ks, ds, 1)
    c_slope, c_intercept = np.polyfit(ks, cs, 1)
    return {
        "d_intercept": float(d_intercept),
        "d_slope": float(d_slope),
        "c_intercept": float(c_intercept),
        "c_slope": float(c_slope),
    }


def predict_k_law(approximation: str = "exact") -> tuple[dict, dict]:
    fits: dict[int, tuple[float, float]] = {}
    rows = []
    for k in (2, 4, 6, 8):
        ns, overheads = [], []
        for p, taus in K_LADDER:
            atoms, probs = binomial_law(k, p)
            for tau in taus:
                at, pr, mu, m, nominal = binding_transform(
                    atoms, probs, p, tau, "UNSAFE"
                )
                t_cross = deterministic_crossing(at, pr, mu, m, approximation)
                n = k * t_cross
                if approximation == "exact":
                    nu_nom = kelly_rate_grid(at, pr, nominal)
                else:
                    variance = float(np.sum(pr * (at - mu) ** 2))
                    gap = mu - nominal
                    nu_nom = gap * gap / (2 * (variance + gap * gap))
                overhead = t_cross * nu_nom - L
                ns.append(n)
                overheads.append(overhead)
                rows.append({
                    "K": k, "p": p, "tau": tau, "m": m,
                    "T": t_cross, "n": n, "O": overhead,
                })
        fits[k] = fit_dc(np.asarray(ns, float), np.asarray(overheads, float))
    result = {str(k): {"d": fits[k][0], "c": fits[k][1]} for k in fits}
    result["law"] = line_in_k(fits)
    return result, rows


def clock_conversion(k_result: dict) -> dict:
    fits_n = {int(k): (v["d"], v["c"])
              for k, v in k_result.items() if k != "law"}
    fits_t = {
        k: (d, c + 0.5 * d * math.log(k))
        for k, (d, c) in fits_n.items()
    }
    law_n, law_t = line_in_k(fits_n), line_in_k(fits_t)
    return {
        "block_time_law": law_t,
        "sample_time_law": law_n,
        "direct_sample_clock_contribution": {
            key: law_n[key] - law_t[key] for key in law_n
        },
    }


def predict_pdir() -> dict:
    fits = {}
    rows = []
    k, ratio = 6, 1.2
    for p in (0.20, 0.50, 0.80):
        rates = profile(p, ratio, k)
        atoms, probs = poisson_binomial_law(rates)
        for direction in ("UNSAFE", "SAFE"):
            ns, overheads = [], []
            for tau in PDIR_LADDER[(p, direction)]:
                at, pr, mu, m, nominal = binding_transform(
                    atoms, probs, p, tau, direction
                )
                t_cross = deterministic_crossing(at, pr, mu, m, "exact")
                n = k * t_cross
                overhead = t_cross * kelly_rate_grid(at, pr, nominal) - L
                ns.append(n)
                overheads.append(overhead)
                rows.append({
                    "p": p, "direction": direction, "tau": tau,
                    "m_transformed": m, "T": t_cross, "n": n,
                    "O": overhead,
                })
            fits[p, direction] = fit_dc(
                np.asarray(ns, float), np.asarray(overheads, float)
            )
    dir_d = {p: fits[p, "SAFE"][0] - fits[p, "UNSAFE"][0]
             for p in (0.20, 0.50, 0.80)}
    dir_c = {p: fits[p, "SAFE"][1] - fits[p, "UNSAFE"][1]
             for p in (0.20, 0.50, 0.80)}
    p_d = {
        direction: max(fits[p, direction][0] for p in (0.20, 0.50, 0.80))
        - min(fits[p, direction][0] for p in (0.20, 0.50, 0.80))
        for direction in ("UNSAFE", "SAFE")
    }
    p_c = {
        direction: max(fits[p, direction][1] for p in (0.20, 0.50, 0.80))
        - min(fits[p, direction][1] for p in (0.20, 0.50, 0.80))
        for direction in ("UNSAFE", "SAFE")
    }

    # Exact complement test on a matched-delta ladder at p*=1/2.
    matched = []
    rates = profile(0.5, ratio, k)
    atoms, probs = poisson_binomial_law(rates)
    for delta in (0.09, 0.05, 0.02):
        vals = []
        for direction, tau in (("UNSAFE", 0.5 - delta),
                               ("SAFE", 0.5 + delta)):
            at, pr, mu, m, nominal = binding_transform(
                atoms, probs, 0.5, tau, direction
            )
            t_cross = deterministic_crossing(at, pr, mu, m, "exact")
            vals.append((t_cross, t_cross * kelly_rate_grid(at, pr, nominal) - L))
        matched.append({"delta": delta, "delta_T": vals[1][0] - vals[0][0],
                        "delta_O": vals[1][1] - vals[0][1]})

    return {
        "fits": {f"{p:.2f}_{direction}": {"d": fits[p, direction][0],
                                             "c": fits[p, direction][1]}
                 for p in (0.20, 0.50, 0.80)
                 for direction in ("UNSAFE", "SAFE")},
        "direction_gaps": {
            f"{p:.2f}": {"dd": dir_d[p], "dc": dir_c[p]}
            for p in dir_d
        },
        "effect_sizes": {
            "direction_d": max(abs(x) for x in dir_d.values()),
            "direction_c": max(abs(x) for x in dir_c.values()),
            "pstar_d": max(p_d.values()),
            "pstar_c": max(p_c.values()),
        },
        "matched_p05_complement_check": matched,
        "rows": rows,
    }


def predict_rk() -> dict:
    fits = {}
    for k in (2, 4, 6):
        for ratio in (1, 3, 10, 30):
            ns, overheads = [], []
            for p in (0.20, 0.35):
                rates = profile(p, ratio, k)
                atoms, probs = poisson_binomial_law(rates)
                for tau in RK_LADDER[(p, ratio)]:
                    at, pr, mu, m, nominal = binding_transform(
                        atoms, probs, p, tau, "UNSAFE"
                    )
                    t_cross = deterministic_crossing(at, pr, mu, m, "exact")
                    ns.append(k * t_cross)
                    overheads.append(t_cross * kelly_rate_grid(at, pr, nominal) - L)
            fits[k, ratio] = fit_dc(np.asarray(ns, float),
                                    np.asarray(overheads, float))
    design, yd, yc = [], [], []
    for (k, ratio), (d, c) in fits.items():
        design.append([1, k, math.log(ratio)])
        yd.append(d)
        yc.append(c)
    d_surface = np.linalg.lstsq(np.asarray(design), np.asarray(yd), rcond=None)[0]
    c_surface = np.linalg.lstsq(np.asarray(design), np.asarray(yc), rcond=None)[0]
    spans = {}
    for k in (2, 4, 6):
        spans[str(k)] = {
            "d": max(fits[k, r][0] for r in (1, 3, 10, 30))
                 - min(fits[k, r][0] for r in (1, 3, 10, 30)),
            "c": max(fits[k, r][1] for r in (1, 3, 10, 30))
                 - min(fits[k, r][1] for r in (1, 3, 10, 30)),
        }
    return {
        "fits": {f"K{k}_R{r}": {"d": fits[k, r][0], "c": fits[k, r][1]}
                 for k in (2, 4, 6) for r in (1, 3, 10, 30)},
        "surface": {
            "d_intercept": float(d_surface[0]),
            "d_K": float(d_surface[1]),
            "d_logR": float(d_surface[2]),
            "c_intercept": float(c_surface[0]),
            "c_K": float(c_surface[1]),
            "c_logR": float(c_surface[2]),
        },
        "R_spans": spans,
    }


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def predict(out_path: Path) -> None:
    source = Path(inspect.getfile(WSRBlockCS)).resolve()
    expected = (REPO / "src/eval_harness/stats/wsr_block_cs.py").resolve()
    if source != expected:
        raise RuntimeError(f"wrong WSRBlockCS import: {source}")

    exact, rows = predict_k_law("exact")
    quadratic, _ = predict_k_law("quadratic")
    payload = {
        "created_unix": time.time(),
        "reads_results_files": False,
        "shipped_class_source": str(source),
        "constants": {"alpha": ALPHA, "H": H, "L": L,
                      "c_trunc": C_TRUNC, "grid_size": len(GRID)},
        "K": exact,
        "K_rows": rows,
        "two_moment_ablation": quadratic,
        "clock_attribution": clock_conversion(exact),
        "lattice_increment_to_law": {
            key: exact["law"][key] - quadratic["law"][key]
            for key in exact["law"]
        },
        "pdir": predict_pdir(),
        "rk": predict_rk(),
    }
    payload["prediction_sha256"] = canonical_hash(payload)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"SHIPPED IMPORT: {source}")
    print(f"PREDICTION FROZEN: {out_path}")
    print(f"PREDICTION SHA256: {payload['prediction_sha256']}")
    print("K law:", json.dumps(exact["law"], sort_keys=True))
    print("two-moment law:", json.dumps(quadratic["law"], sort_keys=True))
    print("pdir effects:", json.dumps(payload["pdir"]["effect_sizes"], sort_keys=True))
    print("R,K surface:", json.dumps(payload["rk"]["surface"], sort_keys=True))


def parse_measured() -> dict:
    k_text = (REPO / "results_wsr_k.txt").read_text()
    pdir_text = (REPO / "results_wsr_pdir.txt").read_text()
    rk_text = (REPO / "results_wsr_rk.txt").read_text()

    k_section = k_text.split("REPORTED CONSTANTS PER K", 1)[1].split(
        "PRE-REGISTERED PREDICATES", 1
    )[0]
    k_fits = {}
    for match in re.finditer(r"^\s+(2|4|6|8)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$",
                             k_section, re.M):
        k_fits[int(match.group(1))] = {
            "d": float(match.group(2)), "c": float(match.group(3))
        }
    d_law = re.search(
        r"d\s+best basis K\s+: d = ([+-]\d+\.\d+)\*K ([+-]\d+\.\d+)",
        k_text,
    )
    c_law = re.search(
        r"c\s+best basis K\s+: c = ([+-]\d+\.\d+)\*K ([+-]\d+\.\d+)",
        k_text,
    )
    if not (d_law and c_law and len(k_fits) == 4):
        raise RuntimeError("could not parse K measurements")

    effects = re.search(
        r"Effect sizes: d — direction (\d+\.\d+) vs p\* (\d+\.\d+);\s+"
        r"c — direction (\d+\.\d+) vs p\* (\d+\.\d+)",
        pdir_text,
    )
    surface = re.search(
        r"d\(K,R\) = ([+-]\d+\.\d+) ([+-]\d+\.\d+)\*K "
        r"([+-]\d+\.\d+)\*log R.*?"
        r"c\(K,R\) = ([+-]\d+\.\d+) ([+-]\d+\.\d+)\*K "
        r"([+-]\d+\.\d+)\*log R",
        rk_text,
        re.S,
    )
    if not effects or not surface:
        raise RuntimeError("could not parse pdir/RK measurements")

    return {
        "K_fits": {str(k): v for k, v in k_fits.items()},
        "K_law": {
            "d_slope": float(d_law.group(1)),
            "d_intercept": float(d_law.group(2)),
            "c_slope": float(c_law.group(1)),
            "c_intercept": float(c_law.group(2)),
        },
        "pdir_effects": {
            "direction_d": float(effects.group(1)),
            "pstar_d": float(effects.group(2)),
            "direction_c": float(effects.group(3)),
            "pstar_c": float(effects.group(4)),
        },
        "rk_surface": {
            "d_intercept": float(surface.group(1)),
            "d_K": float(surface.group(2)),
            "d_logR": float(surface.group(3)),
            "c_intercept": float(surface.group(4)),
            "c_K": float(surface.group(5)),
            "c_logR": float(surface.group(6)),
        },
    }


def scalar_shipped_cs(m: float) -> WSRBlockCS:
    cs = WSRBlockCS(alpha=ALPHA)
    cs.grid = np.array([m])
    cs.log_kp = np.zeros(1)
    cs.log_km = np.zeros(1)
    return cs


def pathwise_binding_check(
    k: int, p: float, tau: float, direction: str, seed: int, nmax: int
) -> dict:
    atoms, probs = binomial_law(k, p)
    at, pr, mu, m, _ = binding_transform(atoms, probs, p, tau, direction)
    # Generate in transformed UNSAFE coordinates; complementing is exact for SAFE.
    rng = np.random.default_rng(seed)
    draws = rng.choice(at, size=nmax, p=pr)
    full = WSRBlockCS(alpha=ALPHA)
    scalar = scalar_shipped_cs(m)
    idx = int(np.argmin(np.abs(full.grid - m)))
    if abs(float(full.grid[idx]) - m) > 1e-14:
        raise AssertionError("binding point absent from shipped grid")
    full_hit = scalar_hit = None
    max_log_diff = 0.0
    for t, x in enumerate(draws, 1):
        full.update(float(x))
        scalar.update(float(x))
        max_log_diff = max(
            max_log_diff,
            abs(float(full.log_kp[idx] - scalar.log_kp[0])),
            abs(float(full.log_km[idx] - scalar.log_km[0])),
        )
        hedged_scalar = float(np.logaddexp(scalar.log_kp[0], scalar.log_km[0])
                              - np.log(2))
        if scalar_hit is None and hedged_scalar >= L:
            scalar_hit = t
        lo, _ = full.get_bounds()
        if full_hit is None and lo > m:
            full_hit = t
        if scalar_hit is not None and full_hit is not None:
            break
    if scalar_hit != full_hit:
        raise AssertionError((k, p, tau, direction, scalar_hit, full_hit))
    if max_log_diff > 1e-12:
        raise AssertionError(max_log_diff)
    return {"K": k, "p_transformed": mu, "tau": tau,
            "direction_via_transform": direction, "m": m,
            "T": scalar_hit, "max_log_diff": max_log_diff}


def shipped_scalar_median(
    k: int, p: float, tau: float, reps: int, seed0: int, nmax: int
) -> tuple[int, float]:
    atoms, probs = binomial_law(k, p)
    _, _, _, m, _ = binding_transform(atoms, probs, p, tau, "UNSAFE")
    times = []
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        # Exact stream construction used by measure_wsr_k.py.
        means = (rng.random((nmax // k) * k) < p).astype(np.int8)
        means = means.reshape(-1, k).mean(axis=1)
        cs = scalar_shipped_cs(m)
        for t, x in enumerate(means, 1):
            cs.update(float(x))
            hedged = float(np.logaddexp(cs.log_kp[0], cs.log_km[0]) - np.log(2))
            if hedged >= L:
                times.append(k * t)
                break
        else:
            times.append(nmax)
    arr = np.asarray(times)
    return int(np.median(arr)), float(np.mean(arr < nmax))


def verify(pred_path: Path, out_path: Path) -> None:
    payload = json.loads(pred_path.read_text())
    stated = payload.pop("prediction_sha256")
    actual = canonical_hash(payload)
    payload["prediction_sha256"] = stated
    if stated != actual:
        raise RuntimeError("prediction artifact hash mismatch")
    compare_started = time.time()
    if payload["created_unix"] >= compare_started:
        raise RuntimeError("prediction was not frozen before comparison")

    measured = parse_measured()
    predicted_law = payload["K"]["law"]
    law_comparison = {}
    for key in ("d_slope", "d_intercept", "c_slope", "c_intercept"):
        pred, meas = predicted_law[key], measured["K_law"][key]
        law_comparison[key] = {
            "predicted": pred, "measured": meas, "error": pred - meas,
            "relative_abs": abs(pred - meas) / abs(meas),
        }
    pdir_comparison = {}
    for key, pred in payload["pdir"]["effect_sizes"].items():
        meas = measured["pdir_effects"][key]
        pdir_comparison[key] = {
            "predicted": pred, "measured": meas, "error": pred - meas,
            "relative_abs": abs(pred - meas) / abs(meas),
        }

    path_checks = [
        pathwise_binding_check(4, 0.50, 0.476, "UNSAFE", 7001, 12_000),
        pathwise_binding_check(2, 0.20, 0.173, "UNSAFE", 7002, 30_000),
        pathwise_binding_check(6, 0.80, 0.817, "SAFE", 7003, 12_000),
    ]

    # Exact committed-stream shipped-class crossing check, not used in a fit.
    shipped_check = []
    nmax_ratio = {2: 2.0, 4: 1.0, 6: 0.9, 8: 0.85}
    for k in (2, 4, 6, 8):
        tau = 0.464
        nmax = 24 * math.ceil(8 * nmax_ratio[k] * 2000 / 24)
        median_n, cert = shipped_scalar_median(k, 0.50, tau, 300, 2042, nmax)
        pred_row = next(r for r in payload["K_rows"]
                        if r["K"] == k and r["p"] == 0.50 and r["tau"] == tau)
        shipped_check.append({"K": k, "p": 0.50, "tau": tau,
                              "predicted_n": pred_row["n"],
                              "shipped_median_n_300rep": median_n,
                              "certification_fraction": cert,
                              "ratio": pred_row["n"] / median_n})

    report = {
        "prediction_sha256": stated,
        "prediction_created_unix": payload["created_unix"],
        "comparison_started_unix": compare_started,
        "measured": measured,
        "K_law_comparison": law_comparison,
        "pdir_comparison": pdir_comparison,
        "pathwise_shipped_equivalence": path_checks,
        "independent_shipped_crossing_check": shipped_check,
        "repo_status": "not modified by harness",
    }
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"VERIFICATION WRITTEN: {out_path}")
    print("K law comparison:", json.dumps(law_comparison, sort_keys=True))
    print("pdir comparison:", json.dumps(pdir_comparison, sort_keys=True))
    print("pathwise equivalence:", json.dumps(path_checks, sort_keys=True))
    print("shipped crossing check:", json.dumps(shipped_check, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_predict = sub.add_parser("predict")
    p_predict.add_argument("--out", type=Path, required=True)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--pred", type=Path, required=True)
    p_verify.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "predict":
        predict(args.out)
    else:
        verify(args.pred, args.out)


if __name__ == "__main__":
    main()
