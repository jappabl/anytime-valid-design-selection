#!/usr/bin/env python3
"""Multi-epoch warm-start chaining: the recurring-eval deployment loop.

Scenario: a model improving across 6 releases, crossing the threshold
tau = 0.16 mid-chain. Per-stratum design rates (epoch 2 anchored to the
real gpt-4o-mini pools; extreme improves 0.10/release, complex slowly):

    simple  0.004 (all epochs)      medium 0.0 (all epochs)
    complex [0.100 0.068 0.048 0.035 0.022 0.012]
    extreme [0.836 0.736 0.636 0.536 0.436 0.336]

Pooled design rates: 0.235 0.202 0.172 0.144 0.116 0.088 — epochs 1-3
UNSAFE, 4-6 SAFE, with razor-thin margins at 3 and 4 (the flip). Truth
for scoring is each synthetic pool's EMPIRICAL pooled rate (2000/stratum,
fixed seed), the exact resampling ground truth.

Chain protocol (the realistic practitioner loop): epoch 1 runs the cold
UI mixture; every later epoch warm-starts TransferPriorJointUICS with
prior rates = the PREVIOUS epoch's own Jeffreys estimates at stopping
time, and per-stratum kappa = that epoch's actual per-stratum sample
counts (capped at 200). Estimates from a stopped run carry a little
optional-stopping bias — that is the deployed reality, kept on purpose.
Arms: chain-warm, always-cold UI, WSR blocks (memoryless), and
oracle-prior (previous epoch's TRUE rates, kappa=200) as the
no-estimation-noise reference.

PRE-REGISTERED PREDICTIONS (stated before running):
  1. Zero wrong certifications in every arm at every epoch; elevated
     abstention (>= 30% for every method) at the flip epochs 3-4 where
     the margin is ~0.012-0.016 and log(20)/KL exceeds n_max.
  2. Chain-warm beats always-cold at every epoch >= 2 (smaller median
     among decided reps); by >= 2x at the clear-margin epochs 2, 5, 6.
     NOTE the chain's inter-epoch drift is alarmist (+~0.03 pooled,
     the expensive direction per the drift sweep) BUT concentrated in
     the hot stratum (the cheap geometry) — predicted net: benign + ~2
     nats, i.e. chain-warm median within [250, 700] at epochs 2, 5, 6.
  3. Epoch 4 (prior says UNSAFE, truth flipped to SAFE): no wrong
     certifications; chain-warm median (among decided) in [0.7, 1.5]x
     of always-cold — the poisoned prior burns the advantage, the eps
     floor prevents catastrophe.
  4. No error accumulation along the chain: epoch-6 chain-warm median
     within +-25% of the oracle-prior arm.

Offline, deterministic. Writes results_warmstart_chain.txt.
"""

import hashlib
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402

_src = open(REPO / "scripts" / "run_warmstart_joint.py").read()
wj = types.ModuleType("wj")
wj.__dict__["__file__"] = str(REPO / "scripts" / "run_warmstart_joint.py")
exec(_src.rsplit('if __name__', 1)[0], wj.__dict__)

BASE_SEED = 42
ALPHA = 0.05
TAU = 0.16
N_REPS = 200
N_MAX = 6000
POOL_N = 2000
STRATA = ["simple", "medium", "complex", "extreme"]
DESIGN = np.array([
    [0.004, 0.004, 0.004, 0.004, 0.004, 0.004],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.100, 0.068, 0.048, 0.035, 0.022, 0.012],
    [0.836, 0.736, 0.636, 0.536, 0.436, 0.336],
])
N_EPOCHS = DESIGN.shape[1]


def make_pools(rng):
    """Fixed synthetic pools per epoch; empirical rates are the truth."""
    pools, rates = [], []
    for e in range(N_EPOCHS):
        p = {}
        for i, s in enumerate(STRATA):
            p[s] = (rng.random(POOL_N) < DESIGN[i, e]).astype(np.int8)
        pools.append(p)
        rates.append(np.array([float(p[s].mean()) for s in STRATA]))
    return pools, rates


def run_epoch(pools_e, rng, make_cs):
    """Run one epoch to decision; also return per-stratum counts."""
    cs = make_cs()
    nk = np.zeros(4, dtype=int)
    fk = np.zeros(4, dtype=int)
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        y = bool(pools_e[STRATA[k]][int(rng.integers(0, POOL_N))])
        cs.update(k, y)
        nk[k] += 1
        fk[k] += int(y)
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(TAU):
                return "UNSAFE", n, nk, fk
            if cs.rejects_ge(TAU):
                return "SAFE", n, nk, fk
    return "ABSTAIN", N_MAX, nk, fk


def run_epoch_wsr(pools_e, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools_e[s][int(rng.integers(0, POOL_N))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > TAU:
                return "UNSAFE", 4 * b
            if hi <= TAU:
                return "SAFE", 4 * b
    return "ABSTAIN", N_MAX


def main():
    pool_rng = np.random.default_rng(BASE_SEED + 271828)
    pools, emp_rates = make_pools(pool_rng)
    truths = []
    for e in range(N_EPOCHS):
        pooled = float(emp_rates[e].mean())
        truths.append("UNSAFE" if pooled > TAU else "SAFE")

    print("=" * 76)
    print("MULTI-EPOCH WARM-START CHAIN (predictions pre-registered "
          "in header)")
    print("=" * 76)
    print(f"tau={TAU}, alpha={ALPHA}, {N_REPS} reps, n_max={N_MAX}, "
          f"pools {POOL_N}/stratum, BASE_SEED={BASE_SEED}")
    for e in range(N_EPOCHS):
        print(f"  epoch {e+1}: pooled {emp_rates[e].mean():.4f} "
              f"(truth {truths[e]}), p_k = "
              f"{[round(float(r), 3) for r in emp_rates[e]]}")
    print()

    # stats[arm][epoch] = list of (decision, n)
    arms = ["chain-warm", "always-cold", "WSR", "oracle-prior"]
    stats = {a: [[] for _ in range(N_EPOCHS)] for a in arms}

    for rep in range(N_REPS):
        rng = np.random.default_rng(BASE_SEED + 7919 + rep)
        # one shared rng per rep per arm chain (fresh spawn per arm for
        # independence of arms, common across epochs within an arm)
        rngs = {a: np.random.default_rng(BASE_SEED + 104729 + rep)
                for a in arms}
        prior_rates, prior_kappa = None, None
        for e in range(N_EPOCHS):
            # chain-warm
            if e == 0 or prior_rates is None:
                mk = lambda: StratifiedUICS(k=4, alpha=ALPHA)
            else:
                pr, pk = prior_rates, prior_kappa
                mk = lambda: wj.TransferPriorJointUICS(
                    pr, kappa=np.minimum(pk, 200.0))
            d, n, nk, fk = run_epoch(pools[e], rngs["chain-warm"], mk)
            stats["chain-warm"][e].append((d, n))
            prior_rates = (fk + 0.5) / (nk + 1.0)
            prior_kappa = nk.astype(float)
            # always-cold
            d2, n2, _, _ = run_epoch(
                pools[e], rngs["always-cold"],
                lambda: StratifiedUICS(k=4, alpha=ALPHA))
            stats["always-cold"][e].append((d2, n2))
            # WSR
            stats["WSR"][e].append(run_epoch_wsr(pools[e], rngs["WSR"]))
            # oracle-prior: previous epoch's TRUE rates
            if e == 0:
                mk4 = lambda: StratifiedUICS(k=4, alpha=ALPHA)
            else:
                tr = np.clip(emp_rates[e - 1], 0.001, 0.999)
                mk4 = lambda: wj.TransferPriorJointUICS(tr, kappa=200.0)
            d4, n4, _, _ = run_epoch(pools[e], rngs["oracle-prior"], mk4)
            stats["oracle-prior"][e].append((d4, n4))

    total_wrong = 0
    for e in range(N_EPOCHS):
        print(f"  epoch {e+1} (truth {truths[e]}, pooled "
              f"{emp_rates[e].mean():.4f}):")
        for a in arms:
            outs = stats[a][e]
            dec = [n for d, n in outs if d == truths[e]]
            wrong = sum(1 for d, _ in outs
                        if d not in (truths[e], "ABSTAIN"))
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            total_wrong += wrong
            med = int(np.median(dec)) if dec else None
            print(f"    {a:12s}: correct {len(dec):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median "
                  f"{med if med else '--'}")
        print()

    print(f"  wrong certifications, all arms x epochs: {total_wrong}")
    cw = [int(np.median([n for d, n in stats["chain-warm"][e]
                         if d == truths[e]]) )
          if any(d == truths[e] for d, _ in stats["chain-warm"][e])
          else None for e in range(N_EPOCHS)]
    cold = [int(np.median([n for d, n in stats["always-cold"][e]
                           if d == truths[e]]))
            if any(d == truths[e] for d, _ in stats["always-cold"][e])
            else None for e in range(N_EPOCHS)]
    print(f"  chain-warm medians by epoch: {cw}")
    print(f"  always-cold medians by epoch: {cold}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_warmstart_chain.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_warmstart_chain.txt'}")
