#!/usr/bin/env python3
"""Warm-start with JOINT contamination (design fix from the stress test).

The per-stratum contamination pays K*log(1/eps) ~ 9.2 nats worst case
(measured +9.9 vs bound +9.2 - consistent). Joint contamination bounds
the worst case at log(1/eps) ~ 2.3 nats TOTAL. PRE-STATED: joint benign
within 15%% of per-stratum benign (204/316/586); joint inverted within
~2.3 nats + noise of the COLD mixture (i.e. <= ~150 samples slower);
zero wrong certifications everywhere.

Companion to results_warmstart_joint.txt. The benign-epoch result must survive
prior misspecification to be a deployment claim. Arms (pre-stated
expectations): (a) drifted prior (extreme stratum 0.736 -> 0.55, others
doubled) — expect degradation but still >= 1.5x faster than cold, zero
wrong; (b) adversarially WRONG prior (rates inverted: high where truth
is low) — expect the eps-contamination floor: within ~log(1/eps)+O(1)
~ 3-4 nats of the COLD mixture (i.e. graceful, never catastrophic),
zero wrong certifications; (c) benign prior for reference.

The conservation result (results_frontier.txt) says the ~(d/2) log n
adaptivity tax is unavoidable for COLD-START, uniformly-powerful
anytime procedures. Real evaluations are recurring: a prior epoch of the
same model exists. A prior concentrated near the truth converts the tax
into a constant, with validity untouched (the prior is data-independent
of the new stream), and an epsilon-contaminated prior caps the
misspecification risk at log(1/eps) nats.

Construction — TransferPriorUICS: per-stratum numerator is the
predictive of the two-component mixture
    0.9 * Beta(1 + kappa*p_prior, 1 + kappa*(1-p_prior)) + 0.1 * Beta(1,1)
with p_prior taken from the ARCHIVED pre-fix pools
(data/archive_pre_multipleof_fix/ — a genuinely stale, slightly
mislabeled epoch: 58/3000 labels differ from current truth, i.e. a
realistic warm start, not an oracle). kappa = 200 (prior epoch had 250
samples/stratum). Denominator machinery identical to StratifiedUICS.

PRE-REGISTERED PREDICTIONS (before running; from overhead accounting):
  - warm-start UI overhead in [1.5, 6] nats at all three margins
    (vs 15.5-18.4 for the cold mixture);
  - median samples ~ (log(1/alpha) + overhead)/V_rr: approx 310 / 470 /
    800 at tau = 0.15 / 0.16 / 0.17 (+-35%);
  - consequently: beats the cold mixture >= 2.5x everywhere, and is
    within +-30% of WSR at tau = 0.17 (the crossover regime; at harder
    margins the rate advantage should dominate);
  - zero wrong certifications; abstention <= 5%.

REVISION 2 (post-audit 2026-08-12, audit/AUDIT_WARMSTART.md): per-rep
CRN seeding (the original shared one generator across reps, breaking
arm pairing after rep 1 — audit finding W9); predictions unchanged.
Also corrected: the prior file is the SAME 1000-prompt pool with
16/1000 labels flipped by the validator fix (aggregate 88/3000 across
three models) — effectively an ORACLE-adjacent prior; realistic
staleness is measured by the drift sweep, not this benign arm.

Offline, deterministic. Writes results_warmstart_joint.txt.
"""

import hashlib
import io
import json
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from scipy.special import betaln

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.stats.wsr_block_cs import WSRBlockCS

_ug = open(REPO / "scripts" / "run_ui_grow.py").read().split("if __name__")[0]
bench = types.ModuleType("bench")
bench.__dict__["__file__"] = str(REPO / "scripts" / "run_ui_grow.py")
exec(_ug, bench.__dict__)

BASE_SEED = 42
ALPHA = 0.05
STRATA = ["simple", "medium", "complex", "extreme"]
N_REPS = 200
N_MAX = 6000
KAPPA = 200.0
EPS = 0.10


def load(path):
    pools = {s: [] for s in STRATA}
    for line in open(path):
        r = json.loads(line)
        pools[r["stratum"]].append(0 if r["passed"] else 1)
    return {s: np.array(v, dtype=np.int8) for s, v in pools.items()}


class TransferPriorJointUICS(StratifiedUICS):
    """Joint eps-contamination: ONE global two-component mixture
    (all-strata-concentrated vs all-strata-uniform), so the worst-case
    premium is log(1/eps) TOTAL rather than K*log(1/eps)."""

    def __init__(self, prior_rates, k=4, alpha=ALPHA,
                 kappa=KAPPA, eps=EPS):
        super().__init__(k=k, alpha=alpha)
        pr = np.asarray(prior_rates)
        self._a = np.stack([1.0 + kappa * pr, np.ones(k)])
        self._b = np.stack([1.0 + kappa * (1 - pr), np.ones(k)])
        self._logw = np.log(np.array([1 - eps, eps]))
        self._cf = np.zeros((2, k))
        self._cs = np.zeros((2, k))
        self._logm_total = np.zeros(2)   # GLOBAL per-component marginal

    def update(self, stratum, is_failure):
        i = stratum
        a = self._a[:, i] + self._cf[:, i]
        b = self._b[:, i] + self._cs[:, i]
        pred_fail = a / (a + b)
        p_obs = pred_fail if is_failure else 1 - pred_fail
        lw = self._logw + self._logm_total
        lw = lw - np.logaddexp.reduce(lw)
        mix_pred = float(np.exp(np.logaddexp.reduce(lw + np.log(p_obs))))
        self.log_pred += float(np.log(max(mix_pred, 1e-300)))
        self._logm_total += np.log(p_obs)
        if is_failure:
            self._cf[:, i] += 1
            self.f[i] += 1
        else:
            self._cs[:, i] += 1
            self.s[i] += 1


class TransferPriorUICS(StratifiedUICS):
    """UI e-process with an epsilon-contaminated transfer prior."""

    def __init__(self, prior_rates, k=4, alpha=ALPHA,
                 kappa=KAPPA, eps=EPS):
        super().__init__(k=k, alpha=alpha)
        # Two Beta components per stratum: concentrated + uniform.
        self._a = np.stack([1.0 + kappa * np.asarray(prior_rates),
                            np.ones(k)])           # [component, stratum]
        self._b = np.stack([1.0 + kappa * (1 - np.asarray(prior_rates)),
                            np.ones(k)])
        self._logw = np.log(np.array([1 - eps, eps]))  # mixture weights
        # per-stratum, per-component posterior counts
        self._cf = np.zeros((2, k))
        self._cs = np.zeros((2, k))
        # per-stratum log marginal per component (for posterior weights)
        self._logm = np.zeros((2, k))

    def update(self, stratum, is_failure):
        i = stratum
        a = self._a[:, i] + self._cf[:, i]
        b = self._b[:, i] + self._cs[:, i]
        pred_fail = a / (a + b)                    # per component
        p_obs = pred_fail if is_failure else 1 - pred_fail
        # mixture predictive with current posterior weights
        lw = self._logw + self._logm[:, i]
        lw = lw - np.logaddexp.reduce(lw)
        mix_pred = float(np.exp(np.logaddexp.reduce(lw + np.log(p_obs))))
        self.log_pred += float(np.log(max(mix_pred, 1e-300)))
        # update component marginals and counts
        self._logm[:, i] += np.log(p_obs)
        if is_failure:
            self._cf[:, i] += 1
            self.f[i] += 1
        else:
            self._cs[:, i] += 1
            self.s[i] += 1


def run_arm(pools, tau, rng, make_cs):
    cs = make_cs()
    for n in range(1, N_MAX + 1):
        k = (n - 1) % 4
        pool = pools[STRATA[k]]
        cs.update(k if cs.k == 4 else 0,
                  bool(pool[int(rng.integers(0, len(pool)))]))
        if n >= 20 and n % 4 == 0:
            if cs.rejects_le(tau):
                return "UNSAFE", n
            if cs.rejects_ge(tau):
                return "SAFE", n
    return "ABSTAIN", N_MAX


def run_wsr(pools, tau, rng):
    cs = WSRBlockCS(alpha=ALPHA)
    for b in range(1, N_MAX // 4 + 1):
        m = float(np.mean([pools[s][int(rng.integers(0, len(pools[s])))]
                           for s in STRATA]))
        cs.update(m)
        if 4 * b >= 20:
            lo, hi = cs.get_bounds()
            if lo > tau:
                return "UNSAFE", 4 * b
            if hi <= tau:
                return "SAFE", 4 * b
    return "ABSTAIN", N_MAX


def main():
    pools = load(REPO / "data" / "llm_outcomes_diverse_json.jsonl")
    prior = load(REPO / "data" / "archive_pre_multipleof_fix"
                 / "llm_outcomes_diverse_json.jsonl")
    rates = np.array([float(pools[s].mean()) for s in STRATA])
    prior_rates = np.array([float(prior[s].mean()) for s in STRATA])
    p_star = float(rates.mean())

    print("=" * 76)
    print("WARM-START CERTIFICATION (predictions pre-registered in header)")
    print("=" * 76)
    print(f"current pools p_k = {[round(float(r),3) for r in rates]} "
          f"(p* = {p_star:.4f})")
    print(f"PRIOR epoch p_k  = {[round(float(r),3) for r in prior_rates]} "
          f"(stale + mislabeled epoch; kappa={KAPPA:.0f}, eps={EPS})")
    print(f"alpha={ALPHA}, {N_REPS} reps, n_max={N_MAX}, "
          f"BASE_SEED={BASE_SEED}\n")

    log1a = np.log(1 / ALPHA)
    records = {}
    for tau in [0.15, 0.16, 0.17]:
        lam = np.full(4, 0.25)
        w = np.full(4, 0.25)
        m = bench._inner_min(lam, rates, w, tau)
        v_rr = float(np.sum(lam * [bench.kl_bern(rates[i], m[i])
                                   for i in range(4)]))
        print(f"  tau={tau} (V_rr={v_rr:.4f}):")
        drifted = np.clip(np.array([0.01, 0.01, 0.14, 0.55]), 0, 1)
        inverted = np.clip(np.array([0.70, 0.60, 0.30, 0.05]), 0, 1)
        arms = [
            ("cold UI mixture", lambda: StratifiedUICS(k=4, alpha=ALPHA)),
            ("joint (benign)", lambda: TransferPriorJointUICS(prior_rates)),
            ("joint (drifted)", lambda: TransferPriorJointUICS(drifted)),
            ("joint (inverted)", lambda: TransferPriorJointUICS(inverted)),
            ("perstrat (inverted)", lambda: TransferPriorUICS(inverted)),
        ]
        for name, mk in arms:
            outs = [run_arm(pools, tau,
                            np.random.default_rng(
                                BASE_SEED + 7919 + 1000 * rep), mk)
                    for rep in range(N_REPS)]
            ok = [n for d, n in outs if d == "UNSAFE"]
            wrong = sum(1 for d, _ in outs if d == "SAFE")
            ab = sum(1 for d, _ in outs if d == "ABSTAIN")
            med = int(np.median(ok)) if ok else None
            oh = med * v_rr - log1a if med else None
            oh_s = f"{oh:+7.2f} nats" if oh is not None else "     --"
            records[(tau, name)] = (med, oh)
            print(f"    {name:16s}: certified {len(ok):3d}/{N_REPS}, "
                  f"wrong {wrong}, abstain {ab:3d}, median {med}, "
                  f"overhead {oh_s}")
        outs = [run_wsr(pools, tau,
                        np.random.default_rng(
                            BASE_SEED + 7919 + 1000 * rep))
                for rep in range(N_REPS)]
        ok = [n for d, n in outs if d == "UNSAFE"]
        med = int(np.median(ok)) if ok else None
        records[(tau, "WSR")] = (med, None)
        print(f"    {'WSR (ref)':16s}: certified {len(ok):3d}/{N_REPS}, "
              f"median {med}")
        print()

    print("PRE-REGISTERED SCORING (verdicts printed per audit round 2; "
          "ALL\nthree inverted-arm premiums shown — no selection):")
    prem = []
    for tau in [0.15, 0.16, 0.17]:
        i_oh = records[(tau, "joint (inverted)")][1]
        c_oh = records[(tau, "cold UI mixture")][1]
        prem.append(i_oh - c_oh)
        b_med = records[(tau, "joint (benign)")][0]
        c_med = records[(tau, "cold UI mixture")][0]
        print(f"  tau={tau}: inverted-minus-cold overhead "
              f"{i_oh - c_oh:+.2f} nats; benign vs cold "
              f"{c_med/b_med:.1f}x")
    cap = float(np.log(1 / EPS))
    print(f"  inverted premiums: "
          f"{', '.join(f'{p:+.2f}' for p in prem)} nats vs cap "
          f"log(1/eps) = {cap:.2f}. NOTE (audit round 2): the cap bounds"
          f"\n  the LOG E-VALUE premium PATHWISE (verified exact); these"
          f" median-\n  overhead gaps are a downstream statistic and may"
          f" exceed it by\n  stopping-time noise — values above the cap "
          f"are DISCLOSED, not\n  'consistent with' it.")
    print("""
Validity note (corrected per audit round 2): the prior file is the SAME
prompt pool relabeled by a validator fix (16/1000 labels differ), i.e.
an ORACLE-adjacent prior — realistic staleness lives in
results_warmstart_drift.txt. Validity holds because the prior is fixed
w.r.t. the resampling stream (conditional on the pools), not because
it "predates" the current pools.""")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_warmstart_joint.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_warmstart_joint.txt'}")
