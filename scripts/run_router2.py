#!/usr/bin/env python3
"""Router v2: drift-extrapolated margin routing (still no alpha-split).

Router v1 (results_router.txt) missed its <=1.05x-of-WSR target (1.101x)
for two diagnosed reasons: (a) a fast WSR epoch starves the next
epoch's prior (kappa ~ 28 after a 114-sample epoch), and (b) the prior
margin alone cannot separate an epoch drifting TOWARD the boundary
(epoch 3, prior margin 0.045, true winner WSR) from one drifting AWAY
(epoch 6, prior margin 0.044, true winner warm-UI). Both fixes use only
prior-epoch data, so the routing decision remains data-independent of
the new stream and each epoch runs ONE anytime-valid procedure chosen
predictably — no alpha-splitting, validity untouched.

V2 RULE (frozen):
  epoch 1: WSR (no prior exists).
  epoch 2: warm-UI iff LCB(margin) = |p_hat - tau| - se(p_hat) >= 0.03
           (starved priors have big se and fall back to WSR).
  epoch >= 3: one-step drift extrapolation p_pred = p_(e-1) +
           (p_(e-1) - p_(e-2)) per stratum (clipped to [0.001, 0.999]);
           warm-UI iff |mean(p_pred) - tau| - se >= 0.03, with the
           transfer prior CENTERED AT p_pred (not at the stale rates).
  Priors: decay-cumulative counts (old counts halved each epoch, new
  added), per-stratum kappa = min(counts, 200).

Two trajectories, both 2000/stratum fixed pools:
  A "boundary-heavy": the chain trajectory (epochs 3-4 within ~0.017
    of tau) — WSR's home turf.
  B "margin-rich": every epoch's design margin >= 0.05 (pooled 0.239,
    0.214, 0.099, 0.069, 0.046, 0.032 vs tau = 0.16).

PRE-REGISTERED PREDICTIONS (stated before running):
  1. Zero wrong certifications, all arms, both trajectories.
  2. Trajectory A: router-v2 total <= 1.00x pure WSR (parity or
     better on WSR's home turf; v1 was 1.101x) and <= 0.65x pure
     chain-warm; routing picks the true per-epoch winner at >= 4 of
     the 5 routed epochs.
  3. Trajectory B: router-v2 total <= 0.85x pure WSR (warm-heavy
     routing pays off when margins are honest) and abstention 0
     everywhere.

Offline, deterministic. Writes results_router2.txt.
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

_src = open(REPO / "scripts" / "run_warmstart_chain.py").read()
wc = types.ModuleType("wc")
wc.__dict__["__file__"] = str(REPO / "scripts" / "run_warmstart_chain.py")
exec(_src.rsplit('if __name__', 1)[0], wc.__dict__)

_r1 = open(REPO / "scripts" / "run_router.py").read()
r1 = types.ModuleType("r1")
r1.__dict__["__file__"] = str(REPO / "scripts" / "run_router.py")
exec(_r1.rsplit('if __name__', 1)[0], r1.__dict__)

BASE_SEED = wc.BASE_SEED
ALPHA = wc.ALPHA
TAU = wc.TAU
N_REPS = 200
N_MAX = wc.N_MAX
POOL_N = wc.POOL_N
STRATA = wc.STRATA
LCB_THRESH = 0.03
DECAY = 0.5

TRAJ_B = np.array([
    [0.004, 0.004, 0.004, 0.004, 0.004, 0.004],
    [0.000, 0.000, 0.000, 0.000, 0.000, 0.000],
    [0.100, 0.080, 0.040, 0.030, 0.020, 0.015],
    [0.850, 0.770, 0.350, 0.240, 0.160, 0.110],
])


def make_pools_from(design, rng):
    pools, rates = [], []
    for e in range(design.shape[1]):
        p = {}
        for i, s in enumerate(STRATA):
            p[s] = (rng.random(POOL_N) < design[i, e]).astype(np.int8)
        pools.append(p)
        rates.append(np.array([float(p[s].mean()) for s in STRATA]))
    return pools, rates


def margin_lcb(rates_hat, counts):
    p_pool = float(np.mean(rates_hat))
    var = float(np.sum(rates_hat * (1 - rates_hat)
                       / np.maximum(counts, 1.0))) / 16.0
    return abs(p_pool - TAU) - np.sqrt(max(var, 0.0))


def run_traj(design, label):
    pool_rng = np.random.default_rng(BASE_SEED + 271828)
    pools, emp_rates = make_pools_from(design, pool_rng)
    n_epochs = design.shape[1]
    truths = ["UNSAFE" if float(r.mean()) > TAU else "SAFE"
              for r in emp_rates]

    print(f"  trajectory {label}: pooled rates "
          f"{[round(float(r.mean()), 4) for r in emp_rates]}")

    arms = ["router-v2", "pure chain-warm", "pure WSR"]
    stats = {a: [[] for _ in range(n_epochs)] for a in arms}
    routes = [[] for _ in range(n_epochs)]

    for rep in range(N_REPS):
        rngs = {a: np.random.default_rng(BASE_SEED + 104729 + rep)
                for a in arms}
        # router-v2 state: decay-cumulative counts + last two epochs'
        # rate estimates
        cum_n = np.zeros(4)
        cum_f = np.zeros(4)
        hist = []          # per-epoch point estimates (fresh, not decayed)
        w_rates, w_kappa = None, None
        for e in range(n_epochs):
            # --- router-v2 decision ---
            if e == 0:
                choice = "WSR"
            else:
                rates_hat = (cum_f + 0.5) / (cum_n + 1.0)
                if e == 1:
                    center = rates_hat
                else:
                    center = np.clip(hist[-1] + (hist[-1] - hist[-2]),
                                     0.001, 0.999)
                lcb = margin_lcb(center, cum_n)
                choice = "warm" if lcb >= LCB_THRESH else "WSR"
            routes[e].append(choice)
            if choice == "WSR":
                d, n, nk, fk = r1.run_epoch_wsr_counted(pools[e],
                                                        rngs["router-v2"])
            else:
                pr = center
                pk = cum_n
                d, n, nk, fk = wc.run_epoch(
                    pools[e], rngs["router-v2"],
                    lambda: wc.wj.TransferPriorJointUICS(
                        pr, kappa=np.minimum(pk, 200.0)))
            stats["router-v2"][e].append((d, n))
            hist.append((fk + 0.5) / (nk + 1.0))
            cum_n = DECAY * cum_n + nk
            cum_f = DECAY * cum_f + fk
            # --- pure chain-warm ---
            if w_rates is None:
                mk = lambda: StratifiedUICS(k=4, alpha=ALPHA)
            else:
                pr2, pk2 = w_rates, w_kappa
                mk = lambda: wc.wj.TransferPriorJointUICS(
                    pr2, kappa=np.minimum(pk2, 200.0))
            d2, n2, nk2, fk2 = wc.run_epoch(pools[e],
                                            rngs["pure chain-warm"], mk)
            stats["pure chain-warm"][e].append((d2, n2))
            w_rates = (fk2 + 0.5) / (nk2 + 1.0)
            w_kappa = nk2.astype(float)
            # --- pure WSR ---
            d3, n3, _, _ = r1.run_epoch_wsr_counted(pools[e],
                                                    rngs["pure WSR"])
            stats["pure WSR"][e].append((d3, n3))

    total_wrong = 0
    meds = {a: [] for a in arms}
    for e in range(n_epochs):
        n_warm = sum(1 for c in routes[e] if c == "warm")
        print(f"    epoch {e+1} (truth {truths[e]}, pooled "
              f"{emp_rates[e].mean():.4f}; warm {n_warm}/{N_REPS}):")
        for a in arms:
            outs = stats[a][e]
            dec = [n for d, n in outs if d == truths[e]]
            wrong = sum(1 for d, _ in outs
                        if d not in (truths[e], "ABSTAIN"))
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            total_wrong += wrong
            med = int(np.median(dec)) if dec else None
            meds[a].append(med)
            print(f"      {a:16s}: correct {len(dec):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median "
                  f"{med if med else '--'}")

    def total(ms):
        return sum(m for m in ms if m is not None)

    t_r, t_w, t_s = (total(meds[a]) for a in arms)
    print(f"    totals: router-v2 {t_r}, pure warm {t_w}, pure WSR "
          f"{t_s}; v2/WSR = {t_r/t_s:.3f}, v2/warm = {t_r/t_w:.3f}")
    picks = 0
    routed = 0
    for e in range(1, n_epochs):
        w, s = meds["pure chain-warm"][e], meds["pure WSR"][e]
        if w is None or s is None:
            continue
        routed += 1
        winner = "warm" if w < s else "WSR"
        chosen = max(set(routes[e]), key=routes[e].count)
        picks += int(winner == chosen)
    print(f"    routing accuracy (majority choice vs true winner): "
          f"{picks}/{routed} routed epochs; wrong certs {total_wrong}")
    return total_wrong


def main():
    print("=" * 76)
    print("ROUTER V2: drift-extrapolated margin routing "
          "(predictions pre-registered in header)")
    print("=" * 76)
    print(f"tau={TAU}, alpha={ALPHA}, LCB_THRESH={LCB_THRESH}, "
          f"decay={DECAY}, {N_REPS} reps, n_max={N_MAX}, "
          f"pools {POOL_N}/stratum, BASE_SEED={BASE_SEED}\n")
    w1 = run_traj(wc.DESIGN, "A (boundary-heavy)")
    print()
    w2 = run_traj(TRAJ_B, "B (margin-rich)")
    print(f"\n  wrong certifications, both trajectories: {w1 + w2}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_router2.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_router2.txt'}")
