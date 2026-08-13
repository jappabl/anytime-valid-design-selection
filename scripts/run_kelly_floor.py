#!/usr/bin/env python3
"""Kelly-floored lambda schedule: attacking WSR's measured pathology.

Measured basis (not intuition): the law-referee measured stock WSR's
predictable schedule lam ~ 1/sqrt(t log t) forfeiting the Kelly growth
rate (achieved/Kelly 0.73 -> 0.29 and falling), and the MBPP grids
exposed the consequence at long horizons — fitted overhead dimension
d ~ 1.8-2.3 instead of the flat tax seen at short horizons
(results_mbpp_law.txt).

DESIGN: floor the bet at a shrunk Kelly plug-in. For each grid
candidate m, after a 10-block warmup,

    lam_kelly(m) = (mu_hat - m) / (sigma_hat^2 + (mu_hat - m)^2)

clipped to [0, c/m] for the K+ process (symmetrically for K-), and

    lam_t(m) = max(lam_wsr(t), lam_kelly(m))   [same truncation]

Both terms use only past observations, so lambda stays predictable and
the capital processes remain nonnegative martingales under the true
mean: validity is UNCHANGED BY CONSTRUCTION (and re-checked by a null
Monte Carlo below anyway, per house audit culture).

PRE-REGISTERED PREDICTIONS (stated before running):
  P1 null MC at m = tau (worst null point), 2000 reps x both
     directions: false-certification rate <= alpha = 0.05 for the
     floored schedule.
  P2 MBPP qwen pools (the measured-pathology regime): floored medians
     improve >= 15% at the two hardest >=90%-certified margins, and
     the fitted d drops to <= 1.0 (from 1.81).
  P3 JSON gpt-4o-mini pools (short-horizon control): floored within
     +/-5% of stock at every margin — no regression where stock was
     already fine.
  P4 zero wrong certifications on all pool runs.

Offline, deterministic. Writes results_kelly_floor.txt.
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

from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 200
N_MAX = 6000
WARMUP = 10


class KellyFloorWSR(WSRBlockCS):
    """WSR with the bet floored at a shrunk Kelly plug-in (predictable)."""

    def update(self, x: float):
        if not 0.0 <= x <= 1.0:
            raise ValueError(f"observation {x} outside [0, 1]")
        self.t += 1
        sigma2 = self.sq / self.t
        lam = np.sqrt(2 * np.log(2 / self.alpha)
                      / (sigma2 * self.t * np.log(self.t + 1) + 1e-12))
        lam_p = np.minimum(lam, self.c / np.maximum(self.grid, 1e-6))
        lam_m = np.minimum(lam, self.c / np.maximum(1 - self.grid, 1e-6))
        if self.t > WARMUP:
            gap = self.mean - self.grid
            kelly = gap / (sigma2 + gap * gap + 1e-12)
            kp = np.clip(kelly, 0.0,
                         self.c / np.maximum(self.grid, 1e-6))
            km = np.clip(-kelly, 0.0,
                         self.c / np.maximum(1 - self.grid, 1e-6))
            lam_p = np.maximum(lam_p, kp)
            lam_m = np.maximum(lam_m, km)
        self.log_kp += np.log1p(lam_p * (x - self.grid))
        self.log_km += np.log1p(-lam_m * (x - self.grid))
        self.sq += (x - self.mean) ** 2
        self.mean += (x - self.mean) / (self.t + 1)


STRATA_BY_FILE = {
    "llm_outcomes_diverse_json.jsonl":
        ["simple", "medium", "complex", "extreme"],
    "llm_outcomes_mbpp_qwen2.5-7b.jsonl": ["q1", "q2", "q3", "q4"],
    "llm_outcomes_mbpp_llama3.2-3b.jsonl": ["q1", "q2", "q3", "q4"],
}
MARGINS = [0.022, 0.027, 0.032, 0.042, 0.052, 0.057]


def load(fname):
    strata = STRATA_BY_FILE[fname]
    pools = {s: [] for s in strata}
    for line in open(REPO / "data" / fname):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return strata, {s: np.array(v, dtype=np.int8)
                    for s, v in pools.items()}


def run(pools, strata, tau, rng, cls):
    cs = cls(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in strata]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > tau:
                return "UNSAFE", 4 * b
            if hi <= tau:
                return "SAFE", 4 * b
    return "ABSTAIN", N_MAX


def v_kelly_block(rates, tau):
    atoms, probs = [], []
    K = len(rates)
    for bits in range(2 ** K):
        m, pr = 0.0, 1.0
        for i in range(K):
            if bits >> i & 1:
                m += 1.0 / K
                pr *= rates[i]
            else:
                pr *= 1 - rates[i]
        atoms.append(m)
        probs.append(pr)
    atoms, probs = np.array(atoms), np.array(probs)
    best = 0.0
    for lam in np.linspace(0.001, 1 / max(tau, 1e-9) - 1e-6, 3000):
        g = float(np.sum(probs * np.log1p(lam * (atoms - tau))))
        best = max(best, g)
    return best / K


def fit_d(points):
    x = np.array([np.log(n) / 2 for n, _ in points])
    y = np.array([n * v - np.log(1 / ALPHA) for n, v in points])
    A = np.stack([x, np.ones_like(x)], axis=1)
    (d, c), *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(d), float(c)


def main():
    print("=" * 76)
    print("KELLY-FLOORED LAMBDA vs STOCK WSR (predictions "
          "pre-registered in header)")
    print("=" * 76)
    print(f"alpha={ALPHA}, {N_REPS} reps/point, n_max={N_MAX}, "
          f"warmup={WARMUP} blocks, BASE_SEED={BASE_SEED}\n")

    # P1: null Monte Carlo at m = tau (iid blocks at exactly the
    # boundary; any false certification is a validity violation).
    print("  P1 null MC (block mean exactly at tau, 2000 reps, "
          "n_max 2000):")
    for tau in [0.16, 0.30]:
        false_certs = 0
        for rep in range(2000):
            rng = np.random.default_rng(BASE_SEED + 555 + rep)
            cs = KellyFloorWSR(alpha=ALPHA)
            fired = False
            for b in range(1, 501):
                x = float(rng.random() < tau)
                cs.update(x)
                if 4 * b >= 20:
                    lo, hi = cs.get_bounds()
                    if lo > tau or hi <= tau:
                        fired = True
                        break
            false_certs += fired
        rate = false_certs / 2000
        print(f"    tau={tau}: false-cert rate {rate:.4f} "
              f"(<= {ALPHA}? {'PASS' if rate <= ALPHA else 'FAIL'})")
    print()

    wrong_total = 0
    for fname, label in [
            ("llm_outcomes_mbpp_qwen2.5-7b.jsonl", "MBPP qwen2.5-7b"),
            ("llm_outcomes_mbpp_llama3.2-3b.jsonl", "MBPP llama3.2-3b"),
            ("llm_outcomes_diverse_json.jsonl", "JSON gpt-4o-mini")]:
        strata, pools = load(fname)
        rates = np.array([float(pools[s].mean()) for s in strata])
        p_star = float(rates.mean())
        print(f"  {label} (p* = {p_star:.4f}):")
        print(f"  {'tau':>7} {'margin':>7} {'V_kelly':>8} "
              f"{'stock':>12} {'floored':>12} {'ratio':>6}")
        pts = {"stock": [], "floor": []}
        for i_m, margin in enumerate(MARGINS):
            tau = round(p_star - margin, 3)
            vk = v_kelly_block(rates, tau)
            row = f"  {tau:>7.3f} {margin:>7.3f} {vk:>8.4f}"
            meds = {}
            for i_f, (key, cls) in enumerate(
                    [("stock", WSRBlockCS), ("floor", KellyFloorWSR)]):
                rng_seed = BASE_SEED + 101 + 1000 * i_m + 100 * i_f
                outs = []
                for rep in range(N_REPS):
                    rng = np.random.default_rng(rng_seed + 10000 * rep)
                    outs.append(run(pools, strata, tau, rng, cls))
                ok = [n for d, n in outs if d == "UNSAFE"]
                wrong_total += sum(1 for d, _ in outs if d == "SAFE")
                frac = len(ok) / N_REPS
                med = int(np.median(ok)) if ok else None
                meds[key] = (med, frac)
                if med and frac >= 0.9:
                    pts[key].append((med, vk))
                row += f" {med if med else '--':>7}|{frac:>4.2f}"
            r = (meds["floor"][0] / meds["stock"][0]
                 if meds["floor"][0] and meds["stock"][0] else None)
            row += f" {r:>6.2f}" if r else "     --"
            print(row)
        for key in ["stock", "floor"]:
            if len(pts[key]) >= 3:
                d, c = fit_d(pts[key])
                print(f"    fit {key:6s}: d = {d:+.2f}, c = {c:+.2f} "
                      f"({len(pts[key])} pts)")
        print()

    print(f"  P4 wrong certifications across all pool runs: "
          f"{wrong_total}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_kelly_floor.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_kelly_floor.txt'}")
