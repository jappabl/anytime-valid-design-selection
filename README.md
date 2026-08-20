# Anytime-Valid Design Selection for LLM Certification

**Which sequential testing design should you use to certify an LLM's failure
rate — and can you know before collecting a single sample?**

This project shows the answer is largely *derivable in advance* from three
pre-observable quantities: the **stratum heterogeneity ratio**, the **decision
direction**, and the **margin**. It builds the theory (a fourth-order expansion
of the certification crossing time, with an exactly computable constant), a
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
| 3 | **The expansion's constant is exactly computable.** c_ren(p\*, τ, α, d, n₀) = −1.1700824 at the reference point via a finite absorption recursion, zero fitted parameters; the fourth term −½log(2πp\*q\*) is derived (Stirling) and blind-tested. | Exact algorithm; scalar closed form open (obstruction named) | `results_cren_exact.txt`, `results_overshoot.txt`, `paper/BOUNDARY_THEOREM.md` |
| 4 | **Ties are a finding.** Below the boundary the designs are statistically indistinguishable at realistic budgets (power analysis at 20k paired reps) — the practical rule is *measure your ratio; above the boundary use WSR blocks; below it, use whichever is convenient.* | Verified | `results_phase_test.txt` |
| 5 | **Optimal stratification is population-dependent.** With the estimand fixed as the population mean, the optimal number of strata K\* ranges over {1, 2, 4} across ten real pools (llama3.2-3b certifies 2.8× faster stratified); a universal K\*=1 claim was refuted and retracted. | Measured; census 1:4 / 2:4 / 4:2 | `results_gain.txt` |
| 6 | **Stock WSR has no fixed dimension; the Kelly-floored variant is regular.** The floored arm admits d = 1 on the post-warmup idealization (derived), with the shipped class carrying a small quantified warmup drift. | Derived on idealization; measurement-limited on the literal class | `results_wsr_expansion.txt`, `results_floor_d.txt` |
| 7 | **Out-of-family: safety-domain test — a scored partial miss.** StrongREJECT refusal outcomes (8 local models, mild regime). Frozen predictions: the single-arm predictor **ports** (within ~5% on 6/6 pools), UI-domination **transfers** (0/6), validity holds (4/2700 wrong); but the K=4 WSR overhead envelope does **not** port to K=6 blocks (WSR 19–37% faster than predicted), flipping one call — P1 1/2, an unretouched ledger miss that localizes to one constant, not the boundary's structure. Grader label noise measured and disclosed (43%: pool parameters, not safety measures). Follow-up: the envelope's constants are **linear in block size K** (d = 4.14 − 0.427·K, c = 0.964·K − 8.98), and transporting the measured K=4→K=6 difference cuts the over-prediction from +19–37% to −1…+15% — most of the magnitude, none of the resolution, so the miss stands. A designed 12-cell (R, K) grid then rules **heterogeneity out** as the envelope's second argument — sweeping R = 1→30 at fixed p\* moves c by under 0.4 standard errors, and the joint envelope still matches only 1/2 of its resolving calls. A third grid crosses p\* with the **decision direction** — every envelope in this project was fitted one-sided, on p > τ — and finds both axes ~4× the refuted R axis at function level; direction- and p\*-matched constants lift the labelled diagnostic to **4/5**, recovering the missed call, so the envelope's arguments are block size, p\*, and direction (the miss still stands as scored). | Scored — miss reported | `results_safety.txt`, `results_safety_noise.txt`, `results_wsr_k.txt`, `results_wsr_rk.txt`, `results_wsr_pdir.txt` |
| 8 | **The RLA bridge: the same mathematics, priced in hand-counted ballots.** A risk-limiting election audit is an anytime-valid one-sided test of a rate against a threshold with county strata — the same object, in a field (SHANGRLA, ALPHA, Spertus et al.'s UI-TS, already shipped here) that owns the machinery but has no pre-observable design-selection rule. On Georgia's 2020 county structure (p\* = 0.501, R = 3.22) the frozen call moves along the margin axis — SINGLE at the real 0.24% margin, TIE at 2%, WSR at 5% — and scores **P1 1/1 HIT**, UI dominated (it never certifies at all), and the **risk limit held on a truly-tied pool (1/450 = 0.0022 ≤ α)**. The single-arm predictor lands at **0.0% error** on the 2% cell; the (K, p\*, direction)-matched WSR envelope, tested prospectively for the first time, errs ±12% in **both** signs. Payoff in ballots: the design choice is worth 1.09–1.22× between live arms and ≥3× against UI, and at Georgia's real margin *every* design needs a majority of the 4.94M ballots cast — so no ballot-polling audit beats a full hand count, which is what Georgia did. Non-claim: nothing here improves SHANGRLA/BRAVO/ALPHA/UI-TS and no procedure here is proposed for a real election. Porting the certifier also exposed a root-selection defect in the shipped UI optimizer (fixed, regression-tested). | Scored — P1/P2/P3 pass | `results_rla.txt` |

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
- A **34-row miss ledger** — every frozen prediction that failed, scored and
  kept. Failures here localized real theory (the o(1) term, the schedule
  dependence, the grid bias) rather than being noise to bury.

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
paper/DRAFT.md           the paper (v4.2)
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
