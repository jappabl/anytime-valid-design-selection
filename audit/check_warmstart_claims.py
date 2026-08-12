#!/usr/bin/env python3
"""Forensics on the warm-start performance claims (not validity).

Sections
--------
1  PRIOR FORENSICS   How "stale" is the transfer prior really? Per-stratum
                     |p_prior - p_current|, label-flip counts, the residual
                     KL the prior costs, and the prior-sd distance to truth.
2  CRN               scripts/run_warmstart*.py reset one Generator per ARM and
                     then let all N_REPS replications consume it sequentially.
                     Arms stop at different n, so the streams desynchronise
                     after replication 1. Demonstrated, and the size measured.
3  ERROR BARS        Bootstrap CIs for the median-sample differences behind
                     "beats WSR everywhere". Both the as-published (unpaired,
                     desynchronised) comparison and a correctly paired
                     re-run with per-replication common seeds.
4  PREMIUM UNITS     The eps-contamination bound is on log E (nats). The
                     artifacts translate it into stopping-time/median-sample
                     statements. Measures the pathwise nats gap (which must
                     obey the bound) against the median-sample gap (which
                     need not), for the inverted-prior arms.

Offline, deterministic. Writes nothing.
"""

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402


def _load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ws = _load_script("_c_ws", REPO / "scripts" / "run_warmstart.py")
_wj = _load_script("_c_wj", REPO / "scripts" / "run_warmstart_joint.py")
TransferPriorUICS = _ws.TransferPriorUICS
TransferPriorJointUICS = _wj.TransferPriorJointUICS
STRATA = _ws.STRATA
BASE_SEED, ALPHA, N_MAX = _ws.BASE_SEED, _ws.ALPHA, _ws.N_MAX
CUR = REPO / "data" / "llm_outcomes_diverse_json.jsonl"
ARC = REPO / "data" / "archive_pre_multipleof_fix" / "llm_outcomes_diverse_json.jsonl"


def kl_bern(p, q):
    p = min(max(p, 1e-12), 1 - 1e-12)
    q = min(max(q, 1e-12), 1 - 1e-12)
    return p * math.log(p / q) + (1 - p) * math.log((1 - p) / (1 - q))


# ---------------------------------------------------------------- section 1
def prior_forensics():
    print("=" * 88)
    print("1. PRIOR FORENSICS -- is the transfer prior 'genuinely stale'?")
    print("=" * 88)
    cur = {r["id"]: r for r in (json.loads(l) for l in open(CUR))}
    arc = {r["id"]: r for r in (json.loads(l) for l in open(ARC))}
    print(f"records: current {len(cur)}, archive {len(arc)}, "
          f"ids present in both {len(set(cur) & set(arc))}, "
          f"ids unique to one {len(set(cur) ^ set(arc))}")
    flips = {s: 0 for s in STRATA}
    for i in cur:
        if cur[i]["passed"] != arc[i]["passed"]:
            flips[cur[i]["stratum"]] += 1
    print(f"label flips between the two files: {sum(flips.values())}/{len(cur)} "
          f"= {sum(flips.values()) / len(cur):.3%}   per stratum {flips}")

    pc = _ws.load(CUR)
    pa = _ws.load(ARC)
    rc = np.array([pc[s].mean() for s in STRATA])
    ra = np.array([pa[s].mean() for s in STRATA])
    print(f"\n{'stratum':10s} {'n':>4s} {'p_current':>10s} {'p_prior':>9s} "
          f"{'|gap|':>7s} {'gap/prior_sd':>13s} {'KL(cur||prior)':>15s}")
    kap = _ws.KAPPA
    for s, a, b in zip(STRATA, rc, ra):
        A, B = 1 + kap * b, 1 + kap * (1 - b)
        sd = math.sqrt(A * B / ((A + B) ** 2 * (A + B + 1)))
        print(f"{s:10s} {len(pc[s]):4d} {a:10.4f} {b:9.4f} {abs(a-b):7.4f} "
              f"{(a - A/(A+B))/sd:13.2f} {kl_bern(a, b):15.6f}")
    print(f"\np*_current = {rc.mean():.4f}   p*_prior = {ra.mean():.4f}   "
          f"gap = {abs(rc.mean()-ra.mean()):.4f}")
    print(f"total residual KL the prior pays (sum_k KL(p_k || prior_k)) = "
          f"{sum(kl_bern(a, b) for a, b in zip(rc, ra)):.6f} nats")
    print("Reference points: log(1/eps) = 2.303 nats; the reported warm-start "
          "overhead is ~1 nat;\n  a mixture prior's own irreducible cost "
          "log(1/(1-eps)) = 0.105 nats.")
    return pc, pa, rc, ra


# ---------------------------------------------------------------- section 2
def crn_check(pools, prior_rates):
    print("\n" + "=" * 88)
    print("2. CRN -- do the arms actually share a random-number stream?")
    print("=" * 88)
    print("scripts/run_warmstart.py: `rng = default_rng(BASE_SEED+7919)` is "
          "reset per ARM, then\n  `[run_arm(pools, tau, rng, mk) for _ in "
          "range(N_REPS)]` shares ONE Generator across reps.")
    tau = 0.16
    draws = {}
    for name, mk in [("cold", lambda: StratifiedUICS(k=4, alpha=ALPHA)),
                     ("warm", lambda: TransferPriorUICS(prior_rates))]:
        rng = np.random.default_rng(BASE_SEED + 7919)
        stops, starts = [], []
        for _ in range(5):
            before = rng.bit_generator.state["state"]["state"]
            _d, n = _ws.run_arm(pools, tau, rng, mk)
            stops.append(n)
            starts.append(before)
        draws[name] = (stops, starts)
        print(f"  {name:5s} first 5 stopping times {stops}  "
              f"-> cumulative draws consumed {np.cumsum(stops).tolist()}")
    a, b = draws["cold"][1], draws["warm"][1]
    same = [x == y for x, y in zip(a, b)]
    print(f"  PRNG state identical at the START of reps 1..5? {same}")
    print("  => only replication 1 is a common-random-number pair; from "
          "replication 2 on the\n     arms read disjoint segments of the "
          "stream. Any PAIRED statistic across arms\n     (paired bootstrap, "
          "paired difference) is unjustified as published; unpaired\n"
          "     Monte-Carlo comparison remains valid.")


# ---------------------------------------------------------------- section 3
def run_arm_seeded(pools, tau, seed, make_cs):
    return _ws.run_arm(pools, tau, np.random.default_rng(seed), make_cs)


def run_wsr_seeded(pools, tau, seed):
    return _ws.run_wsr(pools, tau, np.random.default_rng(seed))


def boot_median_diff(x, y, reps=20000, paired=False, seed=7):
    """Bootstrap CI for median(x) - median(y)."""
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    out = np.empty(reps)
    n = len(x)
    for r in range(reps):
        if paired:
            idx = rng.integers(0, n, n)
            out[r] = np.median(x[idx]) - np.median(y[idx])
        else:
            out[r] = (np.median(x[rng.integers(0, len(x), len(x))])
                      - np.median(y[rng.integers(0, len(y), len(y))]))
    return float(np.median(out)), tuple(np.percentile(out, [2.5, 97.5]))


def error_bars(pools, prior_rates, n_reps, taus):
    print("\n" + "=" * 88)
    print("3. ERROR BARS on 'warm-start beats WSR at all margins tested'")
    print("=" * 88)
    print(f"{n_reps} replications per arm; per-replication independent seeds "
          f"(correct pairing),\nplus the as-published shared-Generator "
          f"reproduction for cross-checking the medians.\n")
    for tau in taus:
        # (a) as-published structure, to confirm we reproduce the artifact
        pub = {}
        for name, mk in [
                ("warm", lambda: TransferPriorUICS(prior_rates)),
                ("joint", lambda: TransferPriorJointUICS(prior_rates))]:
            rng = np.random.default_rng(BASE_SEED + 7919)
            pub[name] = [_ws.run_arm(pools, tau, rng, mk)[1]
                         for _ in range(n_reps)]
        rng = np.random.default_rng(BASE_SEED + 7919)
        pub["wsr"] = [_ws.run_wsr(pools, tau, rng)[1] for _ in range(n_reps)]

        # (b) correctly paired: identical seed per replication across arms
        seeds = np.random.SeedSequence(20260812 + int(tau * 1000)).spawn(n_reps)
        par = {
            "warm": [run_arm_seeded(pools, tau, s,
                                    lambda: TransferPriorUICS(prior_rates))[1]
                     for s in seeds],
            "joint": [run_arm_seeded(pools, tau, s,
                                     lambda: TransferPriorJointUICS(prior_rates))[1]
                      for s in seeds],
            "wsr": [run_wsr_seeded(pools, tau, s)[1] for s in seeds],
        }
        print(f"  tau={tau}")
        print(f"    as-published medians   warm {int(np.median(pub['warm'])):5d}"
              f"   joint {int(np.median(pub['joint'])):5d}"
              f"   WSR {int(np.median(pub['wsr'])):5d}")
        print(f"    re-seeded medians      warm {int(np.median(par['warm'])):5d}"
              f"   joint {int(np.median(par['joint'])):5d}"
              f"   WSR {int(np.median(par['wsr'])):5d}")
        for arm in ("warm", "joint"):
            d, ci = boot_median_diff(pub["wsr"], pub[arm])
            dp, cip = boot_median_diff(par["wsr"], par[arm], paired=True)
            sig = "SIGNIFICANT" if cip[0] > 0 else "NOT significant"
            print(f"    median(WSR) - median({arm}):  unpaired "
                  f"{d:+7.1f} [{ci[0]:+.1f}, {ci[1]:+.1f}]   "
                  f"paired {dp:+7.1f} [{cip[0]:+.1f}, {cip[1]:+.1f}]  "
                  f"-> {sig}")
        print()


# ---------------------------------------------------------------- section 4
def premium_units(pools, n_reps):
    print("=" * 88)
    print("4. PREMIUM UNITS -- nats bound vs the sample-count claim")
    print("=" * 88)
    print("Pathwise guarantee (verified exactly in audit/check_mixture_recursion.py):")
    print("   log E_warm(n) >= log E_cold(n) - c   with c = log(1/eps) (joint) "
          "or K log(1/eps) (per-stratum),")
    print("   uniformly in n AND after the min over the null boundary.")
    print("The artifacts additionally assert sample-count consequences "
          "('<= ~150 samples slower',")
    print("'measured +9.9 vs bound +9.2 - consistent', 'worst median <= cold "
          "+ log(1/eps)/V_rr').")
    print("Those are NOT implied: a nats cap on log E does not cap the median "
          "of a first-crossing time.\n")
    inverted = np.array([0.70, 0.60, 0.30, 0.05])
    for tau in (0.15, 0.16, 0.17):
        lam = np.full(4, 0.25)
        rates = np.array([pools[s].mean() for s in STRATA])
        m = _ws.bench._inner_min(lam, rates, lam, tau)
        v_rr = float(np.sum(lam * [_ws.bench.kl_bern(rates[i], m[i])
                                   for i in range(4)]))
        seeds = np.random.SeedSequence(555 + int(tau * 1000)).spawn(n_reps)
        res = {}
        for name, mk in [("cold", lambda: StratifiedUICS(k=4, alpha=ALPHA)),
                         ("joint-inv", lambda: TransferPriorJointUICS(inverted)),
                         ("perstrat-inv", lambda: TransferPriorUICS(inverted))]:
            res[name] = [run_arm_seeded(pools, tau, s, mk)[1] for s in seeds]
        mc = np.median(res["cold"])
        for name, cap in (("joint-inv", math.log(1 / _ws.EPS)),
                          ("perstrat-inv", 4 * math.log(1 / _ws.EPS))):
            extra_n = np.median(res[name]) - mc
            print(f"  tau={tau} V_rr={v_rr:.4f}  {name:13s} "
                  f"median {int(np.median(res[name])):5d} vs cold {int(mc):5d}"
                  f"  -> extra {extra_n:+7.1f} samples = "
                  f"{extra_n * v_rr:+6.2f} nats in the artifacts' overhead "
                  f"metric;  nats cap = {cap:.2f} "
                  f"({'WITHIN' if extra_n * v_rr <= cap else 'EXCEEDS'})")
    print("\n  A median-sample gap exceeding the nats cap is NOT a validity "
          "failure -- the cap\n  bounds log E, not the median crossing time -- "
          "but the artifacts present the two as\n  the same quantity.")


# ---------------------------------------------------------------- section 5
def oracle_equivalence(pools, prior_rates, n_epochs, n_reps, tau=0.16):
    """Is the archive prior interchangeable with a REAL 250-sample epoch?

    The docstrings sell the archive as "a prior epoch ... kappa = 200 (prior
    epoch had 250 samples/stratum)". If that were the provenance, the prior
    rates would carry the sampling noise of 250 draws per stratum. This draws
    many genuine 250-per-stratum epochs from the same pools and reports the
    distribution of warm-start median samples, against (a) the archive prior
    and (b) an exact-truth oracle prior.
    """
    print("\n" + "=" * 88)
    print("5. IS THE ARCHIVE PRIOR A REAL 'PRIOR EPOCH'? "
          f"(joint contamination, tau={tau})")
    print("=" * 88)
    truth = np.array([pools[s].mean() for s in STRATA])
    ep_rng = np.random.default_rng(31337)

    def median_for(pr, seed0):
        seeds = np.random.SeedSequence(seed0).spawn(n_reps)
        return float(np.median([
            run_arm_seeded(pools, tau, s,
                           lambda: TransferPriorJointUICS(pr))[1]
            for s in seeds]))

    med_arc = median_for(prior_rates, 991)
    med_orc = median_for(truth, 991)
    meds, gaps = [], []
    for e in range(n_epochs):
        pr = np.array([float(np.mean(pools[s][ep_rng.integers(0, len(pools[s]),
                                                              len(pools[s]))]))
                       for s in STRATA])
        gaps.append(float(np.max(np.abs(pr - truth))))
        meds.append(median_for(pr, 991))
    meds = np.array(meds)
    arc_gap = float(np.max(np.abs(prior_rates - truth)))
    print(f"    truth p_k                 = {[round(float(x),4) for x in truth]}")
    print(f"    archive prior p_k         = "
          f"{[round(float(x),4) for x in prior_rates]}   "
          f"max|gap| = {arc_gap:.4f}")
    print(f"    {n_epochs} genuine 250/stratum epochs: max|gap| "
          f"median {np.median(gaps):.4f}, "
          f"p10 {np.percentile(gaps,10):.4f}, p90 {np.percentile(gaps,90):.4f}")
    print(f"    archive prior is at percentile "
          f"{100*np.mean(np.array(gaps) <= arc_gap):.0f} of epoch accuracy "
          f"(0 = most accurate possible)\n")
    print(f"    median samples, exact-truth ORACLE prior : {med_orc:.0f}")
    print(f"    median samples, ARCHIVE prior            : {med_arc:.0f}"
          f"   ({100*(med_arc/med_orc-1):+.1f}% vs oracle)")
    print(f"    median samples, genuine epochs           : "
          f"median {np.median(meds):.0f}, p10 {np.percentile(meds,10):.0f}, "
          f"p90 {np.percentile(meds,90):.0f}, max {meds.max():.0f}")
    print(f"    archive prior is at percentile "
          f"{100*np.mean(meds >= med_arc):.0f} of epoch PERFORMANCE "
          f"(100 = best)")
    print("\n    If the archive prior sits far better than a typical genuine "
          "epoch, the reported\n    warm-start medians are a best-case "
          "realisation, not the expected deployment value.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--epoch-reps", type=int, default=60)
    ap.add_argument("--taus", type=float, nargs="*",
                    default=[0.15, 0.16, 0.17])
    ap.add_argument("--skip", type=str, default="",
                    help="comma-separated section numbers to skip")
    args = ap.parse_args()
    skip = set(args.skip.split(",")) if args.skip else set()

    pools, prior_pools, rc, ra = prior_forensics()
    if "2" not in skip:
        crn_check(pools, ra)
    if "3" not in skip:
        error_bars(pools, ra, args.reps, args.taus)
    if "4" not in skip:
        premium_units(pools, args.reps)
    if "5" not in skip:
        oracle_equivalence(pools, ra, args.epochs, args.epoch_reps)


if __name__ == "__main__":
    main()
