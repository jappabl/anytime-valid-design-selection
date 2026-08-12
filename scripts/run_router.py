#!/usr/bin/env python3
"""Prior-routed portfolio: margin routing with no alpha-splitting.

The chain experiment (results_warmstart_chain.txt) showed a structural
split: warm-UI dominates clear-margin epochs, WSR dominates the
razor-margin flip epochs where every UI variant abstains. The router
synthesizes them: each epoch runs warm-UI when the PRIOR epoch's
estimated pooled margin |p_hat_prior - tau| >= THRESH, else WSR blocks.
The routing decision uses only prior-epoch data, so it is
data-independent of the new stream: each epoch runs ONE anytime-valid
procedure chosen predictably — validity holds with no alpha-split.
Epoch 1 (no prior) defaults to WSR (pre-registered choice).

Same 6-epoch improving-model trajectory as run_warmstart_chain.py
(pools 2000/stratum, epoch-2 anchored to real gpt-4o-mini rates).

PRE-REGISTERED PREDICTIONS (THRESH = 0.05 frozen from the chain's
epoch-level readout; stated before running):
  1. Zero wrong certifications; at the flip epochs 3-4 the router
     recovers WSR's deciding power: correct >= 140/200 per epoch
     (vs <= 60 for every pure UI variant in the chain run).
  2. Chain total (sum over epochs of median samples among correct
     reps): router <= 1.05x pure WSR and <= 0.75x pure chain-warm,
     and within 15% of the hindsight-best per-epoch portfolio
     (min of the two pure arms' medians, summed).
  3. Routing accuracy: the router's margin rule picks the per-epoch
     winner (by pure-arm medians in THIS run) in >= 4 of 6 epochs.

Offline, deterministic. Writes results_router.txt.
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

_src = open(REPO / "scripts" / "run_warmstart_chain.py").read()
wc = types.ModuleType("wc")
wc.__dict__["__file__"] = str(REPO / "scripts" / "run_warmstart_chain.py")
exec(_src.rsplit('if __name__', 1)[0], wc.__dict__)

BASE_SEED = wc.BASE_SEED
ALPHA = wc.ALPHA
TAU = wc.TAU
N_REPS = wc.N_REPS
N_MAX = wc.N_MAX
POOL_N = wc.POOL_N
STRATA = wc.STRATA
N_EPOCHS = wc.N_EPOCHS
THRESH = 0.05


def run_epoch_wsr_counted(pools_e, rng):
    """WSR blocks, also returning per-stratum (n_k, f_k)."""
    cs = WSRBlockCS(alpha=ALPHA)
    nk = np.zeros(4, dtype=int)
    fk = np.zeros(4, dtype=int)
    for b in range(1, N_MAX // 4 + 1):
        ys = [int(pools_e[s][int(rng.integers(0, POOL_N))])
              for s in STRATA]
        nk += 1
        fk += np.array(ys)
        cs.update(float(np.mean(ys)))
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > TAU:
                return "UNSAFE", 4 * b, nk, fk
            if hi <= TAU:
                return "SAFE", 4 * b, nk, fk
    return "ABSTAIN", N_MAX, nk, fk


def main():
    pool_rng = np.random.default_rng(BASE_SEED + 271828)
    pools, emp_rates = wc.make_pools(pool_rng)
    truths = ["UNSAFE" if float(r.mean()) > TAU else "SAFE"
              for r in emp_rates]

    print("=" * 76)
    print("PRIOR-ROUTED PORTFOLIO (predictions pre-registered in header)")
    print("=" * 76)
    print(f"tau={TAU}, alpha={ALPHA}, THRESH={THRESH}, {N_REPS} reps, "
          f"n_max={N_MAX}, pools {POOL_N}/stratum, BASE_SEED={BASE_SEED}")
    for e in range(N_EPOCHS):
        print(f"  epoch {e+1}: pooled {emp_rates[e].mean():.4f} "
              f"(truth {truths[e]})")
    print()

    arms = ["router", "pure chain-warm", "pure WSR"]
    stats = {a: [[] for _ in range(N_EPOCHS)] for a in arms}
    routes = [[] for _ in range(N_EPOCHS)]

    for rep in range(N_REPS):
        rngs = {a: np.random.default_rng(BASE_SEED + 104729 + rep)
                for a in arms}
        # router chain state
        r_rates, r_kappa = None, None
        # pure chain-warm state
        w_rates, w_kappa = None, None
        for e in range(N_EPOCHS):
            # --- router ---
            if r_rates is None:
                choice = "WSR"
            else:
                margin = abs(float(np.mean(r_rates)) - TAU)
                choice = "warm" if margin >= THRESH else "WSR"
            routes[e].append(choice)
            if choice == "WSR":
                d, n, nk, fk = run_epoch_wsr_counted(pools[e],
                                                     rngs["router"])
            else:
                pr, pk = r_rates, r_kappa
                d, n, nk, fk = wc.run_epoch(
                    pools[e], rngs["router"],
                    lambda: wc.wj.TransferPriorJointUICS(
                        pr, kappa=np.minimum(pk, 200.0)))
            stats["router"][e].append((d, n))
            r_rates = (fk + 0.5) / (nk + 1.0)
            r_kappa = nk.astype(float)
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
            d3, n3, _, _ = run_epoch_wsr_counted(pools[e],
                                                 rngs["pure WSR"])
            stats["pure WSR"][e].append((d3, n3))

    total_wrong = 0
    meds = {a: [] for a in arms}
    for e in range(N_EPOCHS):
        n_warm = sum(1 for c in routes[e] if c == "warm")
        print(f"  epoch {e+1} (truth {truths[e]}, pooled "
              f"{emp_rates[e].mean():.4f}; router chose warm "
              f"{n_warm}/{N_REPS}):")
        for a in arms:
            outs = stats[a][e]
            dec = [n for d, n in outs if d == truths[e]]
            wrong = sum(1 for d, _ in outs
                        if d not in (truths[e], "ABSTAIN"))
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            total_wrong += wrong
            med = int(np.median(dec)) if dec else None
            meds[a].append(med)
            print(f"    {a:16s}: correct {len(dec):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median "
                  f"{med if med else '--'}")
        print()

    def total(ms):
        return sum(m for m in ms if m is not None)

    hindsight = [min(w, s) for w, s in
                 zip(meds["pure chain-warm"], meds["pure WSR"])
                 if w is not None and s is not None]
    t_router = total(meds["router"])
    t_warm = total(meds["pure chain-warm"])
    t_wsr = total(meds["pure WSR"])
    t_hind = sum(hindsight)
    print(f"  chain totals (sum of per-epoch medians among correct):")
    print(f"    router          : {t_router}")
    print(f"    pure chain-warm : {t_warm}")
    print(f"    pure WSR        : {t_wsr}")
    print(f"    hindsight-best  : {t_hind}")
    print(f"    router/WSR = {t_router/t_wsr:.3f}, router/warm = "
          f"{t_router/t_warm:.3f}, router/hindsight = "
          f"{t_router/t_hind:.3f}")
    picks = 0
    for e in range(N_EPOCHS):
        w, s = meds["pure chain-warm"][e], meds["pure WSR"][e]
        if w is None or s is None:
            continue
        winner = "warm" if w < s else "WSR"
        chosen = max(set(routes[e]), key=routes[e].count)
        picks += int(winner == chosen)
    print(f"  routing accuracy: picked per-epoch winner {picks}/"
          f"{N_EPOCHS} epochs")
    print(f"  wrong certifications, all arms x epochs: {total_wrong}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_router.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_router.txt'}")
