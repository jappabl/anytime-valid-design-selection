#!/usr/bin/env python3
"""Spertus-Sridhar-Stark (2024) UI-TS baseline vs WSR-on-blocks.

Implements the union-of-intersections test sequence of arXiv:2409.06680
adapted to our setting (K = 4 Bernoulli strata, sampling WITH
replacement, uniform weights), using their "arbitrary K" recipe:

  - Per-stratum betting TSMs with INVERSE bets lam_k(eta_k) = c_k/eta_k
    (their Sec. 4.2.2), where c_k = clamp(mu_hat - sigma_hat, 0.1, 0.9)
    is estimated during a 10-observation warmup (bets are ZERO during
    warmup) and frozen thereafter — predictable, hence valid, and it
    keeps the TSM single-phase:
      log TSM_k(eta) = F_k log(1 - c_k + c_k/eta) + S_k log(1 - c_k),
    log-convex and decreasing in eta.
  - The intersection-null minimum over C = {sum w eta = tau} is computed
    EXACTLY by bisection on the Lagrange multiplier with a closed-form
    per-stratum quadratic (validity does not rest on vertex evaluation,
    which is only justified for eta-oblivious log-concave TSMs — a first
    draft of this script used AGRAPA bets with vertex minimization and
    was caught INVALID by an information-bound smell test; see
    AUDIT_PREP).
  - UI-TS statistic: running max (sampled at stopping checks) of the
    minimized product; reject when >= 1/alpha (Ville).
  - Selection rules: round-robin, and their Section-6 GREEDY (sample the
    stratum with the largest expected log-growth of the currently
    smallest I-TSM, lagged estimates, forced exploration sqrt(t)).
  - SAFE direction (H0: p* >= tau) via the mirror transform X -> 1-X.

Writes results_spertus_baseline.txt. Offline, deterministic.
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

from eval_harness.stats.wsr_block_cs import WSRBlockCS

import types as _types
_ug = open(Path(__file__).parent / "run_ui_grow.py").read().split("if __name__")[0]
_bench = _types.ModuleType("bench")
_bench.__dict__["__file__"] = str(Path(__file__).parent / "run_ui_grow.py")
exec(_ug, _bench.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 300


def load(fname):
    pools = {s: [] for s in STRATA}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


class SpertusUITS:
    """Union-of-intersections TS with frozen inverse bets."""

    WARMUP = 10

    def __init__(self, tau, alpha=ALPHA):
        self.tau = tau
        self.log_thresh = np.log(1 / alpha)
        self.c = np.zeros(4)            # 0 = still in warmup (bets off)
        self.F = np.zeros(4)            # post-warmup failures
        self.S = np.zeros(4)            # post-warmup successes
        self.n = np.zeros(4)
        self.sum = np.zeros(4)
        self.sumsq = np.zeros(4)
        self.run_max = -np.inf

    def _mu_sig(self, k):
        if self.n[k] < 2:
            return 0.5, 0.5
        mu = self.sum[k] / self.n[k]
        var = max(self.sumsq[k] / self.n[k] - mu * mu, 1e-6)
        return mu, np.sqrt(var)

    def update(self, k, x):
        if self.c[k] > 0:
            if x:
                self.F[k] += 1
            else:
                self.S[k] += 1
        self.n[k] += 1
        self.sum[k] += x
        self.sumsq[k] += x * x
        if self.c[k] == 0 and self.n[k] >= self.WARMUP:
            mu, sig = self._mu_sig(k)
            self.c[k] = float(np.clip(mu - sig, 0.1, 0.9))

    def _etas_of_lam(self, lam):
        """Per-stratum minimizer of log TSM_k(eta) + lam*w*eta.

        d/deta [F log(1-c+c/eta)] = -F c / ((1-c) eta^2 + c eta).
        Stationarity: lam*w*(1-c)*eta^2 + lam*w*c*eta - F*c = 0.
        """
        w = 0.25
        etas = np.zeros(4)
        for k in range(4):
            F, c = self.F[k], self.c[k]
            if F <= 0 or c <= 0:
                # TSM flat in eta: assign 0 so the boundary budget goes
                # to failure strata, letting their eta sit as high as
                # possible (the null's best case). Pinning flat strata
                # HIGH was the bug caught by the information-bound test.
                etas[k] = 0.0
                continue
            a = lam * w * (1 - c)
            b = lam * w * c
            if a + b < 1e-12:
                etas[k] = 1.0
                continue
            disc = b * b + 4 * a * F * c
            eta = (-b + np.sqrt(disc)) / (2 * a) if a > 1e-15 else F / lam / w
            etas[k] = float(np.clip(eta, 1e-6, 1.0))
        return etas

    def min_log_tsm(self):
        """Exact min over {sum w eta = tau} (TSMs decrease in eta, so the
        min over the null region {<= tau} is on this boundary)."""
        # Slack check: if failure strata at eta=1 cannot absorb tau, the
        # constraint is inactive and every TSM sits at its unconstrained
        # minimum (<= 0): the null survives, no rejection possible.
        active = [k for k in range(4) if self.F[k] > 0 and self.c[k] > 0]
        if 0.25 * len(active) <= self.tau + 1e-12:
            total = 0.0
            for k in active:
                total += self.S[k] * np.log(1 - self.c[k])
            return min(total, 0.0), np.ones(4)
        lo, hi = 0.0, 1e9
        for _ in range(90):
            lam = 0.5 * (lo + hi)
            mix = float(np.sum(0.25 * self._etas_of_lam(lam)))
            if mix > self.tau:
                lo = lam
            else:
                hi = lam
        etas = self._etas_of_lam(0.5 * (lo + hi))
        total = 0.0
        for k in range(4):
            F, S, c = self.F[k], self.S[k], self.c[k]
            if c > 0:
                e = max(etas[k], 1e-6)
                total += F * np.log(1 - c + c / e) + S * np.log(1 - c)
        return total, etas

    def check_reject(self):
        val, _ = self.min_log_tsm()
        self.run_max = max(self.run_max, val)
        return self.run_max >= self.log_thresh

    def expected_growth(self, k):
        _, etas = self.min_log_tsm()
        c = self.c[k]
        if c <= 0:
            return 0.0
        e = max(etas[k], 1e-6)
        mu, _ = self._mu_sig(k)
        return mu * np.log(1 - c + c / e) + (1 - mu) * np.log(1 - c)


def run_spertus(pools, tau, truth, rng, n_max, selection):
    mirror = truth == "SAFE"
    uits = SpertusUITS(1 - tau if mirror else tau)
    for step in range(1, n_max + 1):
        if selection == "round-robin" or step <= 8:
            k = (step - 1) % 4
        elif int(np.min(uits.n)) < np.sqrt(step):
            k = int(np.argmin(uits.n))
        else:
            k = int(np.argmax([uits.expected_growth(j) for j in range(4)]))
        pool = pools[STRATA[k]]
        x = int(pool[int(rng.integers(0, len(pool)))])
        uits.update(k, 1 - x if mirror else x)
        if step >= 20 and step % 4 == 0 and uits.check_reject():
            return truth, step
    return "ABSTAIN", n_max


def run_wsr(pools, tau, truth, rng, n_max):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, n_max // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if hi <= tau:
                return "SAFE", 4 * b
            if lo > tau:
                return "UNSAFE", 4 * b
    return "ABSTAIN", n_max


def validity_check():
    """False-certification rate with the null TRUE, both directions."""
    print("Validity (null true; false-certification must be <= alpha; "
          "300 reps):")
    rng = np.random.default_rng(BASE_SEED + 5)
    configs = [
        ("UNSAFE claim, p* = tau", [0.05, 0.10, 0.20, 0.25], 0.15, "UNSAFE"),
        ("SAFE claim,   p* = tau", [0.05, 0.10, 0.20, 0.25], 0.15, "SAFE"),
    ]
    for label, rates, tau, direction in configs:
        for sel in ["round-robin", "greedy"]:
            false_cert = 0
            for _ in range(300):
                pools = {s: (rng.random(250) < r).astype(np.int8)
                         for s, r in zip(STRATA, rates)}
                d, _ = run_spertus(pools, tau, direction, rng, 600, sel)
                false_cert += d == direction
            print(f"  {label} / {sel:12s}: {false_cert}/300 "
                  f"= {false_cert/300:.3f}")


def main():
    print("=" * 76)
    print("SPERTUS-SRIDHAR-STARK UI-TS BASELINE (inverse bets, exact "
          "boundary min)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps, BASE_SEED={BASE_SEED}\n")
    validity_check()

    conditions = [
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.15,
         "UNSAFE", 2000),
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.17,
         "UNSAFE", 4000),
        ("gpt-4o-mini", "llm_outcomes_diverse_json.jsonl", 0.18,
         "UNSAFE", 4000),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         0.15, "SAFE", 2000),
        ("gpt-4.1-nano", "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl",
         0.11, "SAFE", 4000),
    ]
    for model, fname, tau, truth, n_max in conditions:
        pools = load(fname)
        rates = np.array([float(pools[s].mean()) for s in STRATA])
        p_star = float(rates.mean())
        # Information-bound guard: no valid method can have median
        # time-to-certify far below log(1/alpha) / game-value. This
        # smell test caught two invalid drafts of this script.
        if truth == "SAFE":
            _, gv = _bench.game_allocation(1 - rates, np.full(4, 0.25),
                                           1 - tau)
        else:
            _, gv = _bench.game_allocation(rates, np.full(4, 0.25), tau)
        bound = np.log(1 / ALPHA) / max(gv, 1e-9)
        print(f"\n  {model}, tau={tau} (p*={p_star:.4f}, truth {truth}; "
              f"info-bound ~{bound:.0f} samples):")
        arms = [
            ("WSR blocks", lambda p, r, nm=n_max, t=tau, tr=truth:
             run_wsr(p, t, tr, r, nm)),
            ("Spertus+RR", lambda p, r, nm=n_max, t=tau, tr=truth:
             run_spertus(p, t, tr, r, nm, "round-robin")),
            ("Spertus+greedy", lambda p, r, nm=n_max, t=tau, tr=truth:
             run_spertus(p, t, tr, r, nm, "greedy")),
        ]
        for name, fn in arms:
            outs = []
            for rep in range(N_REPS):
                rng = np.random.default_rng(BASE_SEED + 7919 * rep)
                outs.append(fn(pools, rng))
            correct = [n for d, n in outs if d == truth]
            wrong = sum(1 for d, _ in outs if d not in (truth, "ABSTAIN"))
            abstain = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(correct)) if correct else None
            flag = ""
            if med is not None and med < 0.5 * bound:
                flag = "  << INFO-BOUND VIOLATION: INVALID, investigate"
            print(f"    {name:15s}: correct {len(correct)}/{N_REPS}, "
                  f"wrong {wrong}, abstain {abstain}, median {med}{flag}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_spertus_baseline.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_spertus_baseline.txt'}")
