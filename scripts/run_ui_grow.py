#!/usr/bin/env python3
"""Union-intersection e-process + GROW allocation: benchmark.

Two additions over the existing arms:

1. UI product e-process (src/eval_harness/stats/stratified_ui_cs.py):
   no alpha-splitting across strata, valid at EVERY n under any
   predictable allocation (per-stratum martingales; no iid-mixture
   assumption, hence no mid-block-peeking caveat). This is the
   state-of-the-art-style construction the adversarial audit required
   as a baseline (cf. Spertus, Sridhar & Stark 2024).

2. GROW allocation (ours): sample the stratum maximizing
   KL(p_hat_k || m*_k), where m* is the least-favorable null on the
   certification boundary. By Danskin's theorem this is the first-order
   growth rate of the minimized log product e-value per sample in
   stratum k, so the rule greedily maximizes the growth of exactly the
   statistic that triggers certification. One boundary solve per step
   (already needed for the stopping check) prices the rule.

Arms:
  single-stream : betting CS on the raw round-robin stream, block-gated
                  (validity empirical -- results_advanced.txt E2)
  bonf+directed : per-stratum CSs at alpha/K, decision-directed rule
                  (the previous best; results_crossmodel.txt)
  UI+round-robin: product e-process, fixed rotation
  UI+GROW       : product e-process, KL-directed allocation (ours)
  UI+GROW-oracle: GROW fed the true pool rates instead of p_hat
                  (performance ceiling for this rule family)

Also: fixed-n width comparison (UI vs Bonferroni vs block-WSR vs
single-stream) and a validity check of the UI CS under GROW's
data-dependent allocation. Offline, deterministic. Writes
results_ui_grow.txt.
"""

import hashlib
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.fast_bounds import betting_bounds
from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.stats.wsr_block_cs import WSRBlockCS

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_MAX = 2000
N_MIN = 20
N_REPS = 300

POOLS_FILES = {
    "gpt-4o-mini": "llm_outcomes_diverse_json.jsonl",
    "gpt-4.1-nano": "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
    "gpt-4.1-mini": "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl",
}

_bet_cache = {}


def bet_bounds(f, s, alpha):
    key = (f, s, alpha)
    if key not in _bet_cache:
        _bet_cache[key] = betting_bounds(f, s, alpha)
    return _bet_cache[key]


def load_pools(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        rec = json.loads(line)
        pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


def kl_bern(p, q):
    p = min(max(p, 1e-12), 1 - 1e-12)
    q = min(max(q, 1e-12), 1 - 1e-12)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


# ---------------------------------------------------------------------------
# TaSC: Track-and-Stop Certification (max-min allocation game)
# ---------------------------------------------------------------------------

def _m_of_mu(mu, lam, p_hat, w):
    """Per-stratum minimizer of lam_k*KL(p_hat_k||m) + mu*w_k*m.

    Same quadratic as StratifiedUICS._m_of_lambda with effective counts
    f = lam*p_hat, s = lam*(1-p_hat), a = mu*w. Handles lam_k = 0
    (m -> 0 for mu>0, m -> 1 for mu<0) automatically.
    """
    f = lam * p_hat
    s = lam * (1.0 - p_hat)
    a = mu * w
    with np.errstate(divide="ignore", invalid="ignore"):
        b = f + s + a
        disc = np.maximum(b * b - 4 * a * f, 0.0)
        sq = np.sqrt(disc)
        r1 = (b - sq) / (2 * a)
        r2 = (b + sq) / (2 * a)
    in1 = (r1 >= -1e-12) & (r1 <= 1 + 1e-12)
    root = np.where(in1, r1, r2)
    mle = np.where(f + s > 0, f / np.maximum(f + s, 1e-12), 0.5)
    m = np.where(np.abs(a) < 1e-14, mle, root)
    return np.clip(m, 1e-12, 1 - 1e-12)


def _inner_min(lam, p_hat, w, tau):
    """min over {sum w m = tau} of sum lam_k KL(p_hat_k || m_k); returns m*."""
    lo, hi = -1e7, 1e7
    for _ in range(70):
        mu = 0.5 * (lo + hi)
        mix = float(np.sum(w * _m_of_mu(mu, lam, p_hat, w)))
        if mix > tau:
            lo = mu
        else:
            hi = mu
    return _m_of_mu(0.5 * (lo + hi), lam, p_hat, w)


def game_allocation(p_hat, w, tau, iters=40):
    """Frank-Wolfe on the concave game  max_lam min_m sum lam_k KL_k.

    Gradient in lam at the inner minimizer is KL(p_hat_k || m*_k)
    (Danskin). Returns (lam*, game value).
    """
    k = len(p_hat)
    lam = np.full(k, 1.0 / k)
    for t in range(1, iters + 1):
        m_star = _inner_min(lam, p_hat, w, tau)
        grads = np.array([kl_bern(p_hat[i], m_star[i]) for i in range(k)])
        j = int(np.argmax(grads))
        gamma = 2.0 / (t + 2.0)
        vertex = np.zeros(k)
        vertex[j] = 1.0
        lam = (1 - gamma) * lam + gamma * vertex
    m_star = _inner_min(lam, p_hat, w, tau)
    value = float(np.sum(lam * [kl_bern(p_hat[i], m_star[i])
                                for i in range(k)]))
    return lam, value


def run_tasc(pools, tau, rng, oracle_rates=None, resolve_every=16):
    """Track-and-Stop Certification: track the max-min allocation,
    stop via the UI e-process. Forced exploration keeps every stratum
    sampled at rate >= sqrt(step)."""
    cs = StratifiedUICS(k=4, alpha=ALPHA)
    lam_star = np.full(4, 0.25)
    for step in range(1, N_MAX + 1):
        n = cs.f + cs.s
        if step <= 8:
            k = (step - 1) % 4
        elif int(np.min(n)) < np.sqrt(step):
            k = int(np.argmin(n))
        else:
            if step % resolve_every == 0 or step == 9:
                p_hat = ((cs.f + 0.5) / (n + 1.0) if oracle_rates is None
                         else np.asarray(oracle_rates))
                lam_star, _ = game_allocation(p_hat, cs.w, tau)
            # D-tracking: most under-sampled stratum relative to lam*
            k = int(np.argmax(lam_star * step - n))
        pool = pools[STRATA[k]]
        cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        if step >= N_MIN and step % 4 == 0:
            if cs.rejects_ge(tau):
                return "SAFE", step
            if cs.rejects_le(tau):
                return "UNSAFE", step
    return "ABSTAIN", N_MAX


# ---------------------------------------------------------------------------
# Certification arms
# ---------------------------------------------------------------------------

def run_single_stream(pools, tau, rng):
    f = 0
    for n in range(1, N_MAX + 1):
        pool = pools[STRATA[(n - 1) % 4]]
        f += int(pool[int(rng.integers(0, len(pool)))])
        if n >= N_MIN and n % 4 == 0:
            lo, hi = bet_bounds(f, n - f, ALPHA)
            if hi <= tau:
                return "SAFE", n
            if lo > tau:
                return "UNSAFE", n
    return "ABSTAIN", N_MAX


def run_bonf_directed(pools, tau, rng):
    state = {s: [0, 0] for s in STRATA}
    for step in range(1, N_MAX + 1):
        if step > 8:
            p_mix = sum(0.25 * (state[s][0] / state[s][1]) for s in STRATA)
            aim_safe = p_mix < tau
            best, best_gain = None, -1.0
            for s in STRATA:
                f, n = state[s]
                p_hat = (f + 1) / (n + 2)
                l0, u0 = bet_bounds(f, n - f, ALPHA / 4)
                l_f, u_f = bet_bounds(f + 1, n - f, ALPHA / 4)
                l_s, u_s = bet_bounds(f, n - f + 1, ALPHA / 4)
                if aim_safe:
                    gain = u0 - (p_hat * u_f + (1 - p_hat) * u_s)
                else:
                    gain = (p_hat * l_f + (1 - p_hat) * l_s) - l0
                if gain > best_gain:
                    best, best_gain = s, gain
            stratum = best
        else:
            stratum = STRATA[(step - 1) % 4]
        pool = pools[stratum]
        state[stratum][0] += int(pool[int(rng.integers(0, len(pool)))])
        state[stratum][1] += 1
        if step >= N_MIN and step % 4 == 0:
            lo = hi = 0.0
            for s in STRATA:
                f, n = state[s]
                l, u = bet_bounds(f, n - f, ALPHA / 4) if n else (0.0, 1.0)
                lo += 0.25 * l
                hi += 0.25 * u
            if hi <= tau:
                return "SAFE", step
            if lo > tau:
                return "UNSAFE", step
    return "ABSTAIN", N_MAX


def run_ui(pools, tau, rng, allocation, oracle_rates=None):
    """allocation in {'round-robin', 'grow'}."""
    cs = StratifiedUICS(k=4, alpha=ALPHA)
    for step in range(1, N_MAX + 1):
        n = cs.f + cs.s
        if allocation == "round-robin" or step <= 8:
            k = (step - 1) % 4
        elif int(np.min(n)) < np.sqrt(step):
            # Forced exploration (Track-and-Stop style): no stratum may
            # starve, or plug-in estimates lock in and the rule stalls.
            k = int(np.argmin(n))
        else:
            # GROW: aim by plug-in mixture, allocate argmax KL(p_hat_k, m*_k)
            p_hat = (cs.f + 0.5) / (n + 1.0)
            if oracle_rates is not None:
                p_hat = np.asarray(oracle_rates)
            mix = float(np.sum(cs.w * p_hat))
            side = "ge" if mix < tau else "le"
            lam_m = cs.least_favorable(tau, side)
            gains = [kl_bern(p_hat[i], lam_m[i]) for i in range(4)]
            k = int(np.argmax(gains))
        pool = pools[STRATA[k]]
        cs.update(k, bool(pool[int(rng.integers(0, len(pool)))]))
        if step >= N_MIN and step % 4 == 0:
            if cs.rejects_ge(tau):
                return "SAFE", step
            if cs.rejects_le(tau):
                return "UNSAFE", step
    return "ABSTAIN", N_MAX


# ---------------------------------------------------------------------------


def bench_certification(all_pools):
    print("CERTIFICATION at tau = 0.15 "
          f"({N_REPS} reps, n_max={N_MAX}, alpha={ALPHA})")
    print("-" * 76)
    arms = [
        ("single-stream", lambda p, t, r: run_single_stream(p, t, r)),
        ("bonf+directed", lambda p, t, r: run_bonf_directed(p, t, r)),
        ("UI+round-robin", lambda p, t, r: run_ui(p, t, r, "round-robin")),
        ("UI+GROW (ours)", lambda p, t, r: run_ui(p, t, r, "grow")),
    ]
    for model, fname in POOLS_FILES.items():
        pools = load_pools(fname)
        rates = [float(pools[s].mean()) for s in STRATA]
        p_star = float(np.mean(rates))
        truth = "SAFE" if p_star <= 0.15 else "UNSAFE"
        print(f"\n  {model} (p*={p_star:.4f}, truth {truth}):")
        model_arms = arms + [
            ("UI+GROW-oracle", lambda p, t, r, rt=rates:
             run_ui(p, t, r, "grow", oracle_rates=rt)),
            ("TaSC (ours v2)", lambda p, t, r: run_tasc(p, t, r)),
            ("TaSC-oracle", lambda p, t, r, rt=rates:
             run_tasc(p, t, r, oracle_rates=rt)),
        ]
        lam_o, val_o = game_allocation(np.array(rates), np.full(4, 0.25), 0.15)
        print(f"    [game value at true rates: {val_o:.4f} -> theoretical "
              f"~{np.log(1/ALPHA)/max(val_o,1e-9):.0f} samples; "
              f"lam* = {[round(float(x),2) for x in lam_o]}]")
        for name, fn in model_arms:
            rng = np.random.default_rng(BASE_SEED + 61)
            outs = [fn(pools, 0.15, rng) for _ in range(N_REPS)]
            correct = [n for d, n in outs if d == truth]
            wrong = sum(1 for d, _ in outs if d not in (truth, "ABSTAIN"))
            abstain = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(correct)) if correct else None
            q = ([int(np.percentile(correct, 25)),
                  int(np.percentile(correct, 75))] if correct else None)
            print(f"    {name:15s}: correct {len(correct)}/{N_REPS}, "
                  f"wrong {wrong}, abstain {abstain}, median {med} {q}")


def bench_width(all_pools):
    print("\nFIXED-n MEDIAN CI WIDTH for p* (gpt-4o-mini pools, 200 reps)")
    print("-" * 76)
    pools = load_pools(POOLS_FILES["gpt-4o-mini"])
    print(f"  {'n':>6} {'single':>9} {'Bonferroni':>11} {'UI':>8} "
          f"{'WSR-blocks':>11}")
    for n_tot in [200, 400, 800]:
        rows = {k: [] for k in ["single", "bonf", "ui", "wsr"]}
        rng = np.random.default_rng(BASE_SEED + 62)
        for _ in range(200):
            cs_ui = StratifiedUICS(k=4, alpha=ALPHA)
            wsr = WSRBlockCS(alpha=ALPHA)
            f_tot = 0
            fk = [0, 0, 0, 0]
            nk = [0, 0, 0, 0]
            block = []
            for step in range(1, n_tot + 1):
                k = (step - 1) % 4
                x = int(pools[STRATA[k]][int(rng.integers(0, 250))])
                f_tot += x
                fk[k] += x
                nk[k] += 1
                cs_ui.update(k, bool(x))
                block.append(x)
                if len(block) == 4:
                    wsr.update(sum(block) / 4)
                    block = []
            lo, hi = bet_bounds(f_tot, n_tot - f_tot, ALPHA)
            rows["single"].append(hi - lo)
            lo = sum(0.25 * bet_bounds(fk[k], nk[k] - fk[k], ALPHA / 4)[0]
                     for k in range(4))
            hi = sum(0.25 * bet_bounds(fk[k], nk[k] - fk[k], ALPHA / 4)[1]
                     for k in range(4))
            rows["bonf"].append(hi - lo)
            lo, hi = cs_ui.get_bounds()
            rows["ui"].append(hi - lo)
            lo, hi = wsr.get_bounds()
            rows["wsr"].append(hi - lo)
        print(f"  {n_tot:>6}" + "".join(
            f"{np.median(rows[k]):>{w}.4f}" for k, w in
            [("single", 9), ("bonf", 11), ("ui", 8), ("wsr", 11)]))
    print("  (single-stream: empirical validity only; the other three are"
          "\n   provably anytime-valid under stratified sampling)")


def validity_check():
    print("\nVALIDITY OF THE UI CS UNDER GROW ALLOCATION")
    print("-" * 76)
    configs = {
        "real-pool rates": [0.004, 0.0, 0.068, 0.736],
        "adversarial (0.258,0.2577,0,0)": [0.258, 0.2577, 0.0, 0.0],
        "near-threshold (0.13,0.14,0.16,0.17)": [0.13, 0.14, 0.16, 0.17],
    }
    for name, rates in configs.items():
        p_star = float(np.mean(rates))
        rng = np.random.default_rng(BASE_SEED + 63)
        misses = 0
        for rep in range(300):
            cs = StratifiedUICS(k=4, alpha=ALPHA)
            missed = False
            for step in range(1, 301):
                if step <= 8:
                    k = (step - 1) % 4
                else:
                    n = cs.f + cs.s
                    p_hat = (cs.f + 0.5) / (n + 1.0)
                    mix = float(np.sum(cs.w * p_hat))
                    side = "ge" if mix < 0.15 else "le"
                    lam_m = cs.least_favorable(0.15, side)
                    k = int(np.argmax(
                        [kl_bern(p_hat[i], lam_m[i]) for i in range(4)]))
                cs.update(k, bool(rng.random() < rates[k]))
                # miss = true p* rejected in either direction, ANY step
                if (cs.min_log_e(p_star, "le") >= cs.log_thresh
                        or cs.min_log_e(p_star, "ge") >= cs.log_thresh):
                    missed = True
                    break
            misses += missed
        cov = 1 - misses / 300
        status = "PASS" if cov >= 1 - ALPHA - 0.02 else "FAIL"
        print(f"  {name:38s} (p*={p_star:.3f}): uniform coverage "
              f"{cov:.3f} [{status}]")


def main():
    print("=" * 76)
    print("UNION-INTERSECTION E-PROCESS + GROW ALLOCATION")
    print("=" * 76)
    print(f"BASE_SEED={BASE_SEED}, alpha={ALPHA}\n")
    bench_certification(POOLS_FILES)
    bench_width(POOLS_FILES)
    validity_check()


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_ui_grow.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_ui_grow.txt'}")
