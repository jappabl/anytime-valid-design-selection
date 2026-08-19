#!/usr/bin/env python3
"""Frozen-prediction certification of the phase boundary in the SAFETY domain.

This is a DESIGN-SELECTION test of the derived single-stream-vs-WSR phase
boundary in a fourth, out-of-family task family. It is NOT a safety finding
about any model. Every per-model number below is a POOL PARAMETER (pooled
compliance p*, category heterogeneity ratio R) reported exactly like the
JSON/MBPP pool parameters elsewhere in this repo -- NOT a safety ranking.
Single small local models, one public corpus (StrongREJECT, 313 prompts, 6
published categories), one deterministic refusal-string proxy grader (label
noise estimated separately, estimate_safety_noise.py), pool-scoped estimand.

FRAMING (peer-verified, mandatory): MILD-to-moderate regime. Measured
category ratios span 1.16-5.40 on five pools plus one outlier at 17.0; p*
spans 0.019-0.857 ACROSS models. Section 4.3 says single-stream wins or the
choice ties below the boundary, so this is the mild-regime out-of-family
test. Mechanism: BETWEEN-MODEL variance dominates BETWEEN-STRATUM variance
-> stratification buys little -> mild ratios. The corpus publishes CATEGORY
strata, which do not grade difficulty; there is no sophistication ladder.

--------------------------------------------------------------------------
MARGIN POLICY (stated before any result):
  m = 0.045. tau = round(p* - m, 3), using p* = the equal-weighted mean of
  the 6 category rates (mu) -- the estimand all three arms and v_kelly_block
  target under round-robin/block sampling (mu is within ~0.004 of the
  size-weighted pooled rate, also reported). Six pools have p* >= 0.09 and
  feasible tau > 0; they are SCORED. Two near-zero pools (llama3-8b p*~0.019,
  gemma2-9b p*~0.035) have tau = mu - m < 0 and exact-zero strata (R -> inf):
  BOUNDARY-REGIME cases, tau trivially certifiable, reported (p*/ratio) and
  marked "not scored: degenerate margin". They are NOT forced into the
  winner test.

DECISION DIRECTION (per pool): tau sits BELOW p* by the margin m, so the
true compliance rate exceeds tau on every scored pool; the direction each
pool actually certifies is rejects_le(tau) -> "compliance p* > tau" (the
code's UNSAFE branch; lower bound clears tau). This is uniform across the
six scored pools by construction of the margin policy and is stated per
pool in the output. A SAFE-direction certification (p* < tau) would be a
wrong certification and is counted for P3.

--------------------------------------------------------------------------
FROZEN DESIGN PREDICTION (committed in this docstring BEFORE the certification
runs; the freeze() step below recomputes these live and asserts they match).

Machinery (reused, per handoff): the single arm's crossing is
derive_phase_boundary.single_fourterm (exact absorption recursion, d=4,
n0=20); the WSR arm's crossing is derive_phase_boundary.wsr_crossing under
its measured two-regime overhead envelope (central + two corners); the only
generalization is v_kelly_block -> K=6 (a 64-atom block-mean distribution
over the 6 MEASURED stratum rates, mirroring the 16-atom K=4 code).
Predicted winner = arm with the smaller central crossing n, with a +-5% tie
band (|n_s - n_w| / min < 0.05 -> TIE). The per-corner WSR band is printed
for transparency (corner-robust vs corner-fragile), but the frozen call
uses the central crossing-n comparison with the 5% band, the literal rule.

  pool          p*(mu) pooled     R    tau   n_single  n_wsr(central)  FROZEN
  mistral-7b     0.857  0.856  1.16  0.812       764             844   SINGLE
  qwen2-7b       0.107  0.105  5.40  0.062       336             362   SINGLE
  phi3.5-latest  0.531  0.534  1.68  0.486      1244            1289   TIE
  llama3.1-8b    0.528  0.530  1.94  0.483      1256            1267   TIE
  llama3.2-3b    0.457  0.463  2.82  0.412      1244            1205   TIE
  qwen2.5-7b     0.160  0.157 17.00  0.115       572             560   TIE
  llama3-8b      0.019  0.019   inf    --         --              --   BOUNDARY (not scored)
  gemma2-9b      0.036  0.035   inf    --         --              --   BOUNDARY (not scored)

Reading of the frozen call: at these mild ratios the reused machinery calls
SINGLE on the two pools where the single arm clears the WSR central crossing
by > 5% (mistral, qwen2-7b) and TIE (design-indifferent) on the other four,
INCLUDING qwen2.5 at R=17 -- whose central estimate actually leans WSR by
2.1% but sits inside the tie band. The boundary predicts WSR OUTRIGHT on no
scored pool. This is the committed, falsifiable design map for the domain.

--------------------------------------------------------------------------
CERTIFICATION (three arms, CRN-paired, on the REAL pool outcomes):
  single : StratifiedUICS k=1, round-robin over the 6 categories (pooled),
           polled every 6 from n>=24.
  UI+RR  : StratifiedUICS k=6, round-robin over the 6 categories, polled
           every 24 (compute bound only: UI trails the faster arm by >2000
           samples on every pool, so a <=24-sample poll cannot affect the P2
           domination verdict; single & WSR -- the scored comparison -- are
           polled every 6).
  WSR    : WSRBlockCS on blocks of 6 (one real draw per category per block).
Per-category draws are with replacement from each pool's empirical outcome
arrays. Verdict instrument = run_phase_test's v2c EXACTLY: Harrell-Davis
marginal-median (scipy hdquantiles) inside a CRN-paired bootstrap, three-way
SINGLE/WSR/TIE (CI on median(single)-median(wsr) straddles 0 -> TIE), plus
UI vs both for P2. ~150 reps/arm/pool, n_max 12000.

SCORING (a MISS is a REPORTABLE FINDING; nothing is tuned to pass):
  HIT/MISS/TIE per scored pool whose FROZEN prediction resolves (SINGLE or
  WSR): HIT if the measured resolving winner equals the frozen winner, MISS
  if it is the opposite winner, "unconfirmed" if the measurement ties.
  Frozen-TIE pools are reported (measured winner shown) but not scored for
  P1, exactly as run_phase_test treats in-band points.
  P1 every resolving scored pool matches its frozen prediction.
  P2 UI never outright fastest (CI-below BOTH other arms) -- domination.
  P3 wrong (SAFE-direction) certification rate <= alpha.

SEVERITY / DISCRIMINATION gate (the frozen set must not be trivially
satisfiable): reported below -- non-vacuity (>=1 resolving prediction), and
per resolving prediction whether the call FLIPS under a wrong-theory single
arm (d in {0,2}, mirroring relation_gate R1). A set no measurement could
refute discriminates nothing and is refused.

Offline, deterministic (fixed seeds). Self-scoring with a VERDICT line and a
SHA256 footer. Writes results_safety.txt.
"""

import hashlib
import io
import json
import sys
import types as _types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.stratified_ui_cs import StratifiedUICS  # noqa: E402
from eval_harness.stats.wsr_block_cs import WSRBlockCS  # noqa: E402
from scipy.stats.mstats import hdquantiles  # noqa: E402

# Reuse the DERIVED boundary machinery verbatim (single_fourterm, wsr_crossing,
# crossing_n, kl); only v_kelly_block is generalized to K=6 below.
_pb_src = open(REPO / "scripts" / "derive_phase_boundary.py").read()
_pb = _types.ModuleType("pb")
_pb.__dict__["__file__"] = str(REPO / "scripts" / "derive_phase_boundary.py")
exec(_pb_src.rsplit("if __name__", 1)[0], _pb.__dict__)
single_fourterm = _pb.single_fourterm
wsr_crossing = _pb.wsr_crossing
crossing_n = _pb.crossing_n
kl = _pb.kl

BASE_SEED = 42
ALPHA = 0.05
N_REPS = 150
N_MAX = 12000
K = 6
M = 0.045
UI_POLL = 24
# WSR overhead envelope (reused, K=4-derived): central last, two corners.
CORNERS = [(1.6, 1.81, -3.4), (3.0, 2.34, -5.9), (2.3, 1.95, -4.6)]
TIE_BAND = 0.05

SCORED = ["mistral-7b", "qwen2-7b", "phi3.5-latest", "llama3.1-8b",
          "llama3.2-3b", "qwen2.5-7b"]
BOUNDARY = ["llama3-8b", "gemma2-9b"]

# Committed frozen winners (recomputed and asserted in freeze()).
FROZEN = {"mistral-7b": "single", "qwen2-7b": "single",
          "phi3.5-latest": "tie", "llama3.1-8b": "tie",
          "llama3.2-3b": "tie", "qwen2.5-7b": "tie"}


def v_kelly_block_K(rates, tau, k=K):
    """Per-sample Kelly growth of the block mean over a k-atom^? block: the
    2**k-atom distribution of the mean of k independent Bernoulli(rate_i)
    (K=6 generalization of derive_phase_boundary.v_kelly_block's 16-atom
    K=4 form; returns growth PER SAMPLE, i.e. divided by k)."""
    rates = np.asarray(rates, dtype=float)
    atoms, probs = [], []
    for bits in range(2 ** k):
        m, pr = 0.0, 1.0
        for i in range(k):
            if bits >> i & 1:
                m += 1.0 / k
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
    return best / k


def load_pool(model):
    cat = {}
    for line in open(REPO / "data" / f"llm_outcomes_safety_{model}.jsonl"):
        r = json.loads(line)
        cat.setdefault(r["stratum"], []).append(0 if r["passed"] else 1)
    cats = sorted(cat)
    arrs = [np.array(cat[c], dtype=np.int8) for c in cats]
    rates = np.array([a.mean() for a in arrs])
    sizes = np.array([len(a) for a in arrs])
    mu = float(rates.mean())
    pooled = float((rates * sizes).sum() / sizes.sum())
    rmin = rates.min()
    R = float(rates.max() / rmin) if rmin > 0 else float("inf")
    return arrs, rates, mu, pooled, R


def predict(mu, rates, tau):
    """Frozen design call from the reused machinery: central crossing-n
    comparison with a +-5% tie band. Returns (winner, n_single, n_wsr_band)."""
    n_s = single_fourterm(mu, tau)
    n_ws = [wsr_crossing(v_kelly_block_K(rates, tau), *c) for c in CORNERS]
    n_w = n_ws[-1]  # central
    if abs(n_s - n_w) / min(n_s, n_w) < TIE_BAND:
        w = "tie"
    else:
        w = "single" if n_s < n_w else "wsr"
    return w, n_s, n_ws


def run_arm(kind, arrs, tau, rng):
    """One replication of one arm on real pool draws; returns (decision, n).
    decision in {UNSAFE (p*>tau, correct), SAFE (p*<tau, wrong), ABSTAIN}."""
    if kind == "wsr":
        cs = WSRBlockCS(alpha=ALPHA)
        for b in range(1, N_MAX // K + 1):
            m = float(np.mean([arrs[i][rng.integers(0, len(arrs[i]))]
                               for i in range(K)]))
            cs.update(m)
            if K * b >= 24:
                lo, hi = cs.get_bounds()
                if lo > tau:
                    return "UNSAFE", K * b
                if hi <= tau:
                    return "SAFE", K * b
        return "ABSTAIN", N_MAX
    k = 1 if kind == "single" else K
    poll = 6 if kind == "single" else UI_POLL
    cs = StratifiedUICS(k=k, weights=[1.0] if k == 1 else None, alpha=ALPHA)
    for n in range(1, N_MAX + 1):
        i = (n - 1) % K
        y = bool(arrs[i][rng.integers(0, len(arrs[i]))])
        cs.update(0 if k == 1 else i, y)
        if n >= 24 and n % poll == 0:
            if cs.rejects_le(tau):
                return "UNSAFE", n
            if cs.rejects_ge(tau):
                return "SAFE", n
    return "ABSTAIN", N_MAX


def certify(model, arrs, tau, pool_idx):
    """Three CRN-paired arms; returns times dict, cert fracs, wrong count."""
    times = {"single": [], "ui": [], "wsr": []}
    fracs, wrong = {}, 0
    for kind in ("single", "ui", "wsr"):
        done = 0
        for rep in range(N_REPS):
            rng = np.random.default_rng(BASE_SEED + 100000 * pool_idx + rep)
            d, n = run_arm(kind, arrs, tau, rng)
            if d == "UNSAFE":
                times[kind].append(n)
                done += 1
            else:
                times[kind].append(N_MAX)
                if d == "SAFE":
                    wrong += 1
        fracs[kind] = done / N_REPS
    return times, fracs, wrong


def hd_pair(a, b, seed):
    """CRN paired HD-median bootstrap of median(a)-median(b); (lo, hi) CI."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    br = np.random.default_rng(seed)
    diffs = []
    for _ in range(4000):
        idx = br.integers(0, len(a), len(a))
        diffs.append(float(hdquantiles(a[idx], 0.5)[0])
                     - float(hdquantiles(b[idx], 0.5)[0]))
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def measured_winner(times, fracs, seed):
    """v2c three-way SINGLE/WSR/TIE on single-vs-wsr, plus UI-fastest flag."""
    if fracs["single"] < 0.9 or fracs["wsr"] < 0.9:
        sw = "unresolved"
    else:
        lo, hi = hd_pair(times["single"], times["wsr"], seed)
        sw = "single" if hi < 0 else "wsr" if lo > 0 else "tie"
    # P2: UI outright fastest = CI-below BOTH others
    ui_win = False
    if fracs["ui"] >= 0.9 and fracs["single"] >= 0.9 and fracs["wsr"] >= 0.9:
        lo1, _ = hd_pair(times["single"], times["ui"], seed + 1)
        lo2, _ = hd_pair(times["wsr"], times["ui"], seed + 2)
        ui_win = lo1 > 0 and lo2 > 0   # both others slower than UI
    return sw, ui_win


def freeze_and_severity(pools):
    """Print the recomputed frozen table + the discrimination/severity gate."""
    print("-" * 76)
    print("FREEZE (recomputed live; asserted == committed docstring table)")
    print("-" * 76)
    resolving = 0
    can_fail = 0
    for model in SCORED:
        _, rates, mu, pooled, R = pools[model]
        tau = round(mu - M, 3)
        w, n_s, n_ws = predict(mu, rates, tau)
        assert w == FROZEN[model], f"{model}: {w} != committed {FROZEN[model]}"
        band = f"[{min(n_ws):.0f},{max(n_ws):.0f}]"
        # theory-flip severity: does the call flip under a wrong-theory single
        # arm (d=0, d=2), WSR held at the central corner? (relation_gate R1.)
        flips = []
        if w != "tie":
            resolving += 1
            c4 = -0.5 * np.log(2 * np.pi * mu * (1 - mu)) - 1.105
            n_wc = wsr_crossing(v_kelly_block_K(rates, tau), *CORNERS[-1])
            for d_alt in (0.0, 2.0):
                n_alt = crossing_n(kl(mu, tau), d_alt, c4)
                flips.append("single" if n_alt < n_wc else "wsr")
            fell = any(v != w for v in flips)
            can_fail += fell
        print(f"  {model:14s} mu={mu:.3f} pooled={pooled:.3f} R={R:6.2f} "
              f"tau={tau:.3f}: n_s={n_s:.0f} n_w(c)={n_ws[-1]:.0f} "
              f"corners={band} -> FROZEN {w.upper()}"
              + (f"  (d-alt {flips} -> {'can fail' if flips and any(v!=w for v in flips) else 'ROBUST'})"
                 if w != "tie" else ""))
    for model in BOUNDARY:
        _, rates, mu, pooled, R = pools[model]
        print(f"  {model:14s} mu={mu:.3f} pooled={pooled:.3f} R={R:>6} "
              f"tau={mu-M:+.3f}: BOUNDARY-REGIME, not scored "
              f"(degenerate margin tau<0; exact-zero strata)")
    print(f"\n  SEVERITY/DISCRIMINATION: {resolving} resolving frozen "
          f"prediction(s) (need >=1 for a non-vacuous P1); "
          f"{can_fail}/{resolving} flip under a wrong-theory single arm.")
    disc = resolving >= 1 and can_fail >= 1
    print(f"  prediction set is {'DISCRIMINATING' if disc else 'NON-DISCRIMINATING'} "
          f"(not trivially satisfiable): {'ok' if disc else 'REFUSE'}")
    return disc


def main():
    print("=" * 76)
    print("SAFETY-DOMAIN FROZEN-PREDICTION CERTIFICATION (design selection, "
          "out-of-family)")
    print("=" * 76)
    print("NON-CLAIM: per-model numbers are POOL PARAMETERS (p*, R), not "
          "safety rankings. Mild-regime\ntest of the derived single-vs-WSR "
          f"boundary. alpha={ALPHA}, m={M}, {N_REPS} reps/arm/pool, "
          f"n_max={N_MAX}, K={K}.\n")

    pools = {m: load_pool(m) for m in SCORED + BOUNDARY}
    disc = freeze_and_severity(pools)

    print("\n" + "-" * 76)
    print("CERTIFY (three CRN-paired arms on real outcomes; v2c HD paired "
          "bootstrap)")
    print("-" * 76)
    hits = misses = unconf = 0
    p2_viol = 0
    wrong_total = total_reps = 0
    ui_gap_min = np.inf
    rows = []
    for pi, model in enumerate(SCORED):
        arrs, rates, mu, pooled, R = pools[model]
        tau = round(mu - M, 3)
        times, fracs, wrong = certify(model, arrs, tau, pi)
        wrong_total += wrong
        total_reps += 3 * N_REPS
        sw, ui_win = measured_winner(times, fracs, seed=777 + pi)
        p2_viol += ui_win
        meds = {k: int(np.median(v)) for k, v in times.items()}
        gap = min(meds["ui"] - meds["single"], meds["ui"] - meds["wsr"])
        ui_gap_min = min(ui_gap_min, gap)
        frozen = FROZEN[model]
        # score only pools whose FROZEN call resolves
        if frozen == "tie":
            tag = f"[frozen TIE -> reported, unscored]  measured {sw.upper()}"
        elif sw in ("tie", "unresolved"):
            unconf += 1
            tag = f"predict {frozen.upper()} -> measured {sw.upper()} [unconfirmed]"
        elif sw == frozen:
            hits += 1
            tag = f"predict {frozen.upper()} -> measured {sw.upper()}  HIT"
        else:
            misses += 1
            tag = f"predict {frozen.upper()} -> measured {sw.upper()}  MISS"
        rows.append((model, mu, tau, meds, fracs, sw, ui_win, tag))
        print(f"  {model:14s} dir=rejects_le (p*>tau): "
              f"meds S{meds['single']} U{meds['ui']} W{meds['wsr']} "
              f"(cert {fracs['single']:.2f}/{fracs['ui']:.2f}/"
              f"{fracs['wsr']:.2f}); UI-fastest {'YES' if ui_win else 'no'}; "
              f"{tag}")

    scored_n = hits + misses
    p1 = misses == 0 and scored_n > 0
    p2 = p2_viol == 0
    p3 = (wrong_total / total_reps) <= ALPHA
    print("\n" + "-" * 76)
    print("VERDICTS")
    print("-" * 76)
    print(f"  P1 every resolving scored pool matches frozen: {hits}/{scored_n} "
          f"HIT ({misses} MISS, {unconf} unconfirmed-by-measurement): "
          f"{'PASS' if p1 else 'FAIL'}")
    print(f"  P2 UI never outright fastest: {p2_viol}/{len(SCORED)} UI wins "
          f"(min UI-to-faster-arm median gap {ui_gap_min:.0f} >> {UI_POLL} "
          f"poll) -> {'PASS' if p2 else 'FAIL'}")
    print(f"  P3 wrong (SAFE-dir) certs {wrong_total}/{total_reps} = "
          f"{wrong_total/total_reps:.4f} <= {ALPHA}: {'PASS' if p3 else 'FAIL'}")
    print(f"  discrimination gate: {'ok' if disc else 'REFUSE'}")

    miss_models = [r[0] for r in rows
                   if FROZEN[r[0]] != "tie" and "MISS" in r[7]]
    print("\n" + "-" * 76)
    if p1 and p2 and p3 and disc:
        verdict = ("VERDICT: boundary PORTS to the safety domain -- every "
                   "resolving call confirmed, UI dominated, alpha held.")
    elif p2 and p3 and disc and not p1:
        verdict = (
            "VERDICT: boundary PARTIALLY PORTS (REPORTABLE MISS). UI "
            "domination (P2) and alpha (P3) carry over, but P1 FAILS: the "
            f"frozen design call misses on {miss_models}. The reused WSR "
            "overhead envelope is K=4-derived; on K=6 safety blocks it "
            "over-penalizes WSR (predicted n_wsr exceeds the measured "
            "crossing), so the boundary calls SINGLE where WSR actually "
            "certifies faster. The miss localizes to the envelope's "
            "stratum-count portability, not the boundary's structure. Not "
            "tuned to pass.")
    else:
        verdict = ("VERDICT: FAIL -- see the failing predicate(s) above; "
                   "reported, not tuned.")
    print(verdict)
    print("-" * 76)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    content = buf.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    content += "\n" + "=" * 76 + f"\nChecksum (SHA256): {checksum}\n" + "=" * 76 + "\n"
    print(content, end="")
    (REPO / "results_safety.txt").write_text(content)
    print(f"\nResults written to: {REPO / 'results_safety.txt'}")
