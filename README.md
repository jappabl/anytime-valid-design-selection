# Anytime-Valid Design Selection for LLM Certification

**Which sequential testing design should you use to certify an LLM's failure
rate — and can you know before collecting a single sample?**

This project shows the answer is largely *derivable in advance* from three
pre-observable quantities: the **stratum heterogeneity ratio**, the **decision
direction**, and the **margin**. It builds the theory (a fourth-order expansion
of the certification crossing time, whose residual constant is exactly
computable and provably admits no scalar closed form in the natural class), a
**derived and verified two-region design map**, and a working `certify()`
library — all validated on real LLM outcome pools across 10 models, 4 task
families, and 3 vendors, with every prediction frozen before its test and
every miss scored in a public ledger.

*Author: Hao Lin.*

---

## Headline results

| # | Result | Status | Artifact |
|---|--------|--------|----------|
| 1 | **The design boundary is derivable.** Single-stream vs. WSR-block crossing times equated in a shared expansion predict which design certifies faster from (p\*, R, margin) alone. | Derived + verified (calibrated instrument: below-band 4/4 resolving + 6 genuine ties; above-band 10/10) | `results_phase_curve.txt`, `results_phase_test.txt` |
| 2 | **The design map has two regions, not four.** UI-mixture designs are provably dominated — outright fastest in 0/84 derived cells and 0/10 measured cells, including their own best case. | Derived + verified | `results_partition.txt`, `results_partition_test.txt` |
| 3 | **The expansion's constant is exactly computable — and provably not scalar-closed.** c_ren(p\*, τ, α, d, n₀) = −1.1700824 at the reference point via a finite absorption recursion, zero fitted parameters; the fourth term −½log(2πp\*q\*) is derived (Stirling) and blind-tested. A scalar closed form is **proved impossible** in the natural class (smooth renewal reductions, power series, universal thresholds, single-eigenvalue formulas): c_ren has infinitely many discrete-median jumps ≥ dV/2 > 0 for every (τ, p\*), so no limit constant exists. The check period *d* sits inside the bound, which derives the schedule-dependence rather than measuring it. Finite-L split: the selection term is closed exactly ((1+(1−2p)θ)/(2L), d-independent, 8.9% high at L=3); the overshoot's finite-L correction is **refuted** as any smooth form (quasi-lattice near-resonance — no universal L threshold exists), so the absorption recursion is the operational answer. | Exact algorithm retained; scalar closed form **proved impossible in the stated class** | `results_cren_exact.txt`, `results_overshoot.txt`, `scripts/external/finite_l/`, `paper/BOUNDARY_THEOREM.md` |
| 4 | **Ties are a finding.** Below the boundary the designs are statistically indistinguishable at realistic budgets (power analysis at 20k paired reps) — the practical rule is *measure your ratio; above the boundary use WSR blocks; below it, use whichever is convenient.* | Verified | `results_phase_test.txt` |
| 5 | **Optimal stratification is population-dependent.** With the estimand fixed as the population mean, the optimal number of strata K\* ranges over {1, 2, 4} across ten real pools (llama3.2-3b certifies 2.8× faster stratified); a universal K\*=1 claim was refuted and retracted; at genuine per-prompt resolution (temp>0 pools, split-draws signal, r ≥ 0.94) the finite-interior mechanism is confirmed: K\* = 2 and 3 on the two collected pools. | Measured; census 1:4 / 2:4 / 4:2; interior K\* confirmed at per-prompt resolution | `results_gain.txt` |
| 6 | **Stock WSR has no fixed dimension; the Kelly-floored variant is regular.** The floored arm admits d = 1 on the post-warmup idealization (derived); the shipped class is that idealization plus a warmup over-bet, predicted at d = 1.5301. A 10,000-rep journaled ladder resolves the previously UNRESOLVED adjudication in favour of the prediction: **d = 1.5824 ± 0.1016**, rejecting d = 1 at 5.7 SE (P-A misses, P-B hits). Our own first analysis of that journal scored it in the wrong rate convention (nominal τ instead of the binding grid point) and reported the **opposite** verdict — a scored miss of ours, now a ledger row. Scoped: the warmup decays as 1/log t_c, so this is an effective d over n ≈ 1.8k–38k, not a constant. | Idealization derived; shipped class resolved as a horizon-window effective d | `results_wsr_expansion.txt`, `results_floor_d.txt`, `data/floor_ladder_long.jsonl` |
| 7 | **Out-of-family: safety-domain test — a scored partial miss.** StrongREJECT refusal outcomes (8 local models, mild regime). Frozen predictions: the single-arm predictor **ports** (within ~5% on 6/6 pools), UI-domination **transfers** (0/6), validity holds (4/2700 wrong); but the K=4 WSR overhead envelope does **not** port to K=6 blocks (WSR 19–37% faster than predicted), flipping one call — P1 1/2, an unretouched ledger miss that localizes to one constant, not the boundary's structure. Grader label noise measured and disclosed (43%: pool parameters, not safety measures). Follow-up: the envelope's constants are **linear in block size K** (d = 4.14 − 0.427·K, c = 0.964·K − 8.98), and transporting the measured K=4→K=6 difference cuts the over-prediction from +19–37% to −1…+15% — most of the magnitude, none of the resolution, so the miss stands. A designed 12-cell (R, K) grid then rules **heterogeneity out** as the envelope's second argument — sweeping R = 1→30 at fixed p\* moves c by under 0.4 standard errors, and the joint envelope still matches only 1/2 of its resolving calls. A third grid crosses p\* with the **decision direction** — every envelope in this project was fitted one-sided, on p > τ — and finds both axes ~4× the refuted R axis at function level; direction- and p\*-matched constants lift the labelled diagnostic to **4/5**, recovering the missed call, so the envelope's arguments are block size, p\*, and direction (the miss still stands as scored). Row 9 later shows direction is **not** an independent argument but an exact reflection of the p\* axis — the matched-constant correction is right and is now derivable, but the "both axes" reading is superseded. | Scored — miss reported | `results_safety.txt`, `results_safety_noise.txt`, `results_wsr_k.txt`, `results_wsr_rk.txt`, `results_wsr_pdir.txt` |
| 8 | **The RLA bridge: the same mathematics, priced in hand-counted ballots.** A risk-limiting election audit is an anytime-valid one-sided test of a rate against a threshold with county strata — the same object, in a field (SHANGRLA, ALPHA, Spertus et al.'s UI-TS, already shipped here) that owns the machinery but has no pre-observable design-selection rule. On Georgia's 2020 county structure (p\* = 0.501, R = 3.22) the frozen call moves along the margin axis — SINGLE at the real 0.24% margin, TIE at 2%, WSR at 5% — and scores **P1 1/1 HIT**, UI dominated (it never certifies at all), and the **risk limit held on a truly-tied pool (1/450 = 0.0022 ≤ α)**. The single-arm predictor lands at **0.0% error** on the 2% cell; the (K, p\*, direction)-matched WSR envelope, tested prospectively for the first time, errs ±12% in **both** signs. Payoff in ballots: the design choice is worth 1.09–1.22× between live arms and ≥3× against UI, and at Georgia's real margin *every* design needs a majority of the 4.94M ballots cast — so no ballot-polling audit beats a full hand count, which is what Georgia did. Non-claim: nothing here improves SHANGRLA/BRAVO/ALPHA/UI-TS and no procedure here is proposed for a real election. Porting the certifier also exposed a root-selection defect in the shipped UI optimizer (fixed, regression-tested). | Scored — P1/P2/P3 pass | `results_rla.txt` |
| 9 | **The WSR overhead envelope law is derived — twice, independently.** The block-size law d_K = 4.1407 − 0.4267·K, c_K = 0.9638·K − 8.9801, previously an *observed regularity*, is derived **zero-fit** by two routes kept mutually blind until frozen and each re-verified in-repo against the committed grids: a finite-window projection of the stock schedule's drift, and a loglog Kelly-deficit integral whose warm-up t₀ = K/(4p(1−p)) comes from the *shipped* prior. 4 of 4 frozen constants HIT; the measured linearity is identified as a **chord** of a convex d(K) (residual signs +,−,−,+). Two exact structural results: `WSRBlockCS` is x → 1−x **equivariant** (1.1e−16; crossing times bit-identical), so decision direction is **not** an independent axis but a reflection — superseding the earlier "both axes, comparably" reading — and the p\* carrier is block skewness (1−2p)/(p(1−p)), exact, K-free, odd under that same reflection. **Open, and reported as prominently:** both routes overshoot the measured *slopes* by 4.4%/9.6% in the same direction (intercepts agree to ~1.5%); three candidate explanations were scored against a criterion frozen in advance and **all three refuted**. The bands in the boundary still use the measured envelope. | Derived (2 routes, 4/4 HIT); slope residue open, 3 candidates refuted | `results_wsr_envelope.txt`, `scripts/derive_wsr_envelope.py`, `scripts/external/` |

**Methodology contributions** (arguably the most transferable part):
- A **relation gate** (`scripts/relation_gate.py`) — nine mechanical rules
  (R1–R9) distilled from a 16-defect census whose single generator was
  *locally-correct objects with unchecked relations*: discrimination checks
  for anchors and scoring rules, artifact–claim identity, threshold identity,
  allocation balance, absorption ordering, and more. The gate caught defects
  in its own rules twice.
- The **threshold cycle** — state the claim and its measured residual; fork on
  *structured vs. noise*; derive or re-instrument accordingly; literature pass
  on stall; terminate at unstructured noise. Recorded with worked examples,
  including one where the same data flipped verdict when the fork was
  called correctly.
- A **36-row miss ledger** — every frozen prediction that failed, scored and
  kept. Failures here localized real theory (the o(1) term, the schedule
  dependence, the grid bias) rather than being noise to bury. The two newest
  rows are a scored **triple negative** (three candidate explanations for the
  envelope's slope residue, all refuted against a criterion frozen in advance)
  and a defect of ours caught during paper consolidation: a ladder measurement
  scored in a different rate convention from the prediction it was being
  scored against, which briefly inverted a verdict.
- A **two-route derivation protocol** — run a derivation twice on routes kept
  mutually blind until each is frozen, then re-verify every adopted constant
  in-repo against the committed grids. It paid off in the way that was not
  planned for: both routes to the envelope law agree with each other to 1–4%
  and miss the measurement in the *same* direction, which localizes a shared
  missing term that neither route's own error bar could have exposed.

## The one-paragraph method

Certification is a sequential hypothesis test: draw outcomes, update an
e-process, stop when the evidence crosses log(1/α). The crossing time obeys
`n·V = log(1/α) + (d/2)·log n + c` where V is an information rate, d an
effective dimension, and c a computable constant. Different designs
(single-stream mixture, stratified mixtures, betting/WSR blocks) have
different (V, d, c) — so equating crossing times yields a **boundary in the
space of pre-observable pool parameters** that predicts the winner before
collection. The paper derives the single-stream side to fourth order, measures
the WSR side's envelope, verifies the resulting map on constructed
real-outcome pools, and ships the decision rule as `certify()`.

## Quickstart

```bash
pip install -e .            # or: poetry install
python3 -m pytest tests/ -q # 112 tests
./reproduce.sh              # regenerates the offline artifacts byte-identically
```

Certify a failure rate with automatic design selection:

```python
from eval_harness.certify import Certifier, auto_select
# outcomes: iterable of booleans (True = failure), optionally stratified
design = auto_select(pilot_outcomes)           # boundary-based dispatch
cert   = Certifier(alpha=0.05, design=design)
for y in stream:
    cert.update(y)
    if cert.rejects_le(tau):   # anytime-valid: stop whenever you like
        print("certified: failure rate > tau"); break
```

## Repository layout

```
src/eval_harness/        the library (samplers, validators, stats, certify)
  stats/                 e-processes: Beta-mixture CS, stratified UI, WSR
                         blocks, Kelly-floored WSR (opt-in)
scripts/                 every experiment, derivation, and gate — one file
                         per artifact, self-scoring, deterministic
results_*.txt            committed artifacts (SHA256 footers; reproduce.sh
                         regenerates 26/26 byte-identically)
data/                    outcome pools: {prompt_hash, stratum, passed} records
                         across 4 task families x 10 models
paper/DRAFT.md           the paper (v4.3)
paper/BOUNDARY_THEOREM.md  formal statement: what is proved vs. measured
THEORY.md                the running theory thread (verdicts, corrections)
FINDINGS.md              indexed findings F1-F16
AUDIT_PREP.md            the audit trail — single source of truth for claims
ISEF_PLAN.md             resumable state / handoff document
```

## Data and scope notes

- **Pools are temp-0 snapshots** of specific model+task populations; the
  estimand is pool-scoped (see paper §2, §3.3). Per-model numbers are *pool
  parameters*, not model rankings — this applies with force to the safety
  family, which measures refusal-string outcomes on StrongREJECT and makes
  **no safety claims about any model**.
- **Safety family storage exception** (paper §9): raw completions for
  harmful prompts are never committed — records carry prompt hashes,
  category strata, and binary outcomes only. The corpus itself is public and
  re-downloadable; the statistical claims reproduce without the raw text.
- Live-API experiments (OpenAI/Gemini/Groq) need your own keys via
  environment variables; everything in `reproduce.sh` is offline.

## Status

Active research project (ISEF track). The paper draft, ledger, and this
README are updated together — if a number here disagrees with
`AUDIT_PREP.md`, the audit trail wins.

## License

MIT — see [LICENSE](LICENSE).
