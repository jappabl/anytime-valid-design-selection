# The Sequential Design Boundary: Predicting Which Anytime-Valid Design to Use, and Verifying the Prediction on Real-Outcome Pools

**Hao Lin**

*Draft v4.2 — 2026-08-19. Supersedes v3 (2026-08-12), whose spine was a
four-regime empirical design map; that map survives here as the
empirical origin of a derived boundary (§4.1). New in v4: the boundary
derivation and its verification (§4.2–4.4), the derived fourth expansion
term (§5.3), and the relation gate (§6.2). v4.1 absorbed the results
that landed after v4 froze — the renewal constant computed **exactly**
(§4.2, §5.3, `results_cren_exact.txt`), the phase
verification's final v2c scoring after a scored defect in our own
bootstrap (§4.3), the derived **and** verified two-region design-space
partition (§4.7, `results_partition.txt`, `results_partition_test.txt`),
the optimal-stratification census and the universal-K\* retraction it
forced (§4.7, `results_gain.txt`), the WSR expansion arc and its
floored-arm resolution (§5.5, `results_wsr_expansion.txt`,
`results_floor_d.txt`), two new gate rules (§6.2), and six new
miss-ledger rows (§6.3). v4.2 is likewise a **consolidation, not a
restructure** — v4.1's section skeleton is preserved and every addition
is a new subsection or an in-place sync. It absorbs the boundary's two
**out-of-family domain exports** and their scoring (new §4.8: the
safety domain with a reported P1 miss, and the RLA bridge with the
first prospective test of the direction-matched constants), the three
designed grids that turned the WSR overhead envelope from a fitted
constant into a measured **(K, p\*, direction)** surface with
heterogeneity R **refuted** as a carrier (§5.5), a ninth instance of the
relation-gate generator found by the domain port (§6.2, and the
110 → 112 test count it produced), the **thirty-fourth** miss-ledger row
(§6.3), and two new limitations (§7). The formal companion is
[paper/BOUNDARY_THEOREM.md](BOUNDARY_THEOREM.md), whose statements this
draft mirrors. Every number below traces to a checksummed
`results_*.txt` artifact, to [FINDINGS.md](../FINDINGS.md), or to the
dated audit trail in [AUDIT_PREP.md](../AUDIT_PREP.md); artifact
filenames are cited inline. Figures live in `paper/figures/`.*

---

## Abstract

Anytime-valid confidence sequences make it safe to monitor an LLM
evaluation continuously and stop it early — a guarantee fixed-n
intervals lack (we measure 47.7% uniform miscoverage for a nominal-95%
Wilson interval under peeking on real gpt-4o-mini outcome streams,
`results_advanced.txt`). The methods are established. What practitioners
lack is guidance on *which* sequential design to use for *which*
evaluation, and what the wrong choice costs.

The claim of this paper is that the choice is **derivable in advance**
from three quantities an evaluator can observe *before* spending a
sample: the **stratum heterogeneity ratio** of the prompt pool, the
**direction** of the decision (SAFE versus UNSAFE), and the **margin**
|p\* − τ|. From the same second-order expansion the paper calibrates in
§5, setting the two candidate designs' predicted crossing times equal
yields a **boundary curve** R\*(m) in heterogeneity ratio, at a pilot
estimate of the pool rate. The curve was frozen before any verification
data existed (`results_phase_curve.txt` at commit f75eb8d; it has since
been regenerated under an exactly computed renewal term, which moves the
band edges without changing an anchor or a verdict, §4.2), and the
single-stream side of it uses **derived** constants — no fitted pairs —
thanks to a fourth expansion term we derive in §5.3.

**Verification, strong arm first.** On constructed pools built from real
gpt-4o-mini outcomes at placed (p\*, R), **WSR-on-blocks dominance above
the band is verified 10 of 10 points** (`results_phase_test.txt` plus
its v1 revision at commit 065f9a8; every point enumerated in §4.3–4.4)
**across rounds v1 and v2c, at large effect sizes** — paired-bootstrap
CIs on the median difference as wide as [+192, +421] samples and never
straddling zero. Points *inside* the band are unresolved by design and
unscored. **Below** the band the four points that resolve go 4 of 4 to
the single stream (`results_phase_test.txt`) — and **6 of the 10
below-band points are statistical ties**. The ties are the finding, not
a shortfall: an independent power analysis at 20,000 paired reps
confirms they are real effects too small to resolve at 200 reps
(11–33% power), not an artifact of the instrument. Below the boundary
the two designs are indistinguishable at realistic budgets, so **the
boundary marks where design selection is worth doing at all**. Wrong
certifications: 0 in v2c's 6,000 runs, and 1 each in v1's 4,400 and v2's
6,000 — all inside the α budget.

The verification took four scoring rounds and we report all four: v1
failed as frozen (0 of 2 below-band points) *and* had put 7 of its 9
scored points in the region where the answer was already known; v2
failed at 4 of 10 under a scoring rule with no common-random-number
pairing and no error bars; v2b re-ran with the paired-bootstrap
instrument this project had already built for §4.1, with the tie outcome
pre-stated by a reviewer before the run, and CONFIRMED; v2c re-froze
after a **defect in our own instrument was scored** — v2b's lattice
median bootstrap was conservative (actual size 1.8–2.6% against a
nominal 5%), so it was replaced by a calibrated Harrell-Davis estimator
of the same estimand (size 4.4–5.2%), which resolved exactly the one
extra point the calibration predicted. Both of v1's "misses" are ties
under the honest instrument, which dissolves the missing-constant
hypothesis v1's diagnosis had proposed.

**The same construction partitions the whole design space.** One
crossing-time equality per design pair turns the four-regime map into a
derived partition of (p\*, heterogeneity ratio, margin) with explicit
tie-band widths, and it makes a falsifiable dominance claim: the
union-intersection design is outright fastest at **0 of 84** derived
grid cells (`results_partition.txt`) and at **0 of 10** three-arm
real-outcome cells including its own best case
(`results_partition_test.txt`), so the honest map has **two** winner
regions, not four (§4.7).

**The boundary exports out of family, and the first export scored a
miss.** Two domains outside the testbed, each frozen before any
certification and each scored the same way (§4.8). On **StrongREJECT
harmful-compliance** across six scorable local-model pools the derived
single-arm predictor **ports** (within ~5% on 6 of 6), UI-domination
transfers (0 of 6) and the α guarantee holds (4 of 2,700 wrong
certifications) — but the *reused* WSR overhead envelope, calibrated at
K = 4, under-models K = 6 blocks by **19–37%**, and **P1 fails at 1 of 2
resolving calls**. Per-model rates there are **pool parameters, not
safety rankings**, under a grader whose label noise we measure at 43%
and disclose. Three designed grids then localize the miss to one fitted
object: the envelope's constants are **linear in block size**,
heterogeneity R is **refuted** as its missing argument over R ∈ [1, 30]
(a scored failure that is itself the finding), and every envelope in
this project turns out to have been fitted in **one decision direction**
(§5.5). On a **risk-limiting election audit** of Georgia's 2020 county
structure — the first *prospective* test of the resulting
direction-matched constants — the frozen call moves along the margin
axis and scores **1 of 1**, UI never certifies at all, the risk limit
holds on a truly tied pool (0.0022 ≤ α), and at Georgia's real 0.239%
margin every design needs a **majority of the ballots cast**, which is
why the state hand-counted them. We claim nothing there over SHANGRLA,
ALPHA or UI-TS, and propose no procedure for a real election.

Underneath sits a **calibrated classical expansion**,
n·V = log(1/α) + (d/2)·log n + c. We do not discover it — the d = 1 case
is a fifty-year-old theorem (Pollak & Siegmund 1975; Woodroofe 1982)
that the modern e-value literature under-cites. We calibrate it: with
**zero fitted parameters** the closed form reproduces measured
single-stream medians within −2.6%…+6.8% (`audit/out_law_accounting.txt`).
New here, the **fourth term is derived**: Stirling on the Beta-mixture
e-value gives a residual −½·log(2π p\*q\*), and subtracting that
zero-fitted-parameter term collapses the per-point p\*-slope of a frozen
17-point grid from −1.398 to −0.255 nats per unit p\* and the per-point
correlation from −0.616 to −0.133 (`results_overshoot.txt`). It then
passed a blind functional test on different data — boundary anchor A1
flips correctly across the entire WSR envelope under derived constants,
where fitted constants had failed by 8%. The residual renewal term is
**not** a fitted constant and not a universal scalar: c_ren is a full
function c_ren(p\*, τ, α, d, n0), **exactly computable with zero fit by
a finite absorption recursion** (−1.1700824 nats at the reference
point; `results_cren_exact.txt`), which makes the four-term expansion
fully predictive in practice. What remains open is its reduction to a
scalar closed form, and the obstruction is named rather than fudged.

We report failures as prominently as wins, because the honest scoring is
the credibility. A Bonferroni design portfolio **lost its headline** to
just using WSR (10,224 versus 8,718 total samples, `results_portfolio.txt`).
An automatic pilot-based design selector matched the oracle design in
only **11 of 16** cells (`results_auto_select.txt`). Our conservation
hypothesis was **falsified** (`results_frontier.txt`). A prior-routed
portfolio failed its pre-registered target in **two** iterations and we
stopped rather than iterate to a win. The centerpiece margin sweep
**failed twice**. Our own first answer to "how many strata are optimal"
was **retracted**: a universal K\* = 1 read off one synthetic population
is refuted on 6 of 10 committed real pools, where the census is
K\* = 1 : 4, 2 : 4, 4 : 2 (`results_gain.txt`). A frozen test of an
externally supplied claim that WSR's stock schedule admits *no*
expansion **failed its divergence criterion** (1.23× against a
pre-registered 1.5×), leaving that claim a hypothesis and the
derive-WSR's-fourth-term route open (`results_wsr_expansion.txt`); the
Kelly-floored variant where an expansion does exist is measured at
d = 1.36 ± 0.20 and is **unresolved** against its own derivation
(`results_floor_d.txt`). Audit round 2 downgraded our own dimension-rule
score from 3-for-3 to 2-for-3 and reclassified our live capstone from
"severe test" to "consistency check". Total API spend: under $6; the
miss ledger runs to **34 rows** (§6.3) and the suite to **112 tests**,
the last two added by a defect that only a domain port could reach
(§6.2).

---

## 1. Introduction

Failure-rate evaluation is the workhorse of LLM quality and safety work.
In practice it is monitored continuously and stopped adaptively — which
invalidates classical fixed-n intervals (Armitage, McPherson & Rowe
1969; measured here at real operating points, Figure 3). Anytime-valid
inference repairs this by construction, and a fast-moving 2023–2026
literature has brought it to LLM evaluation: betting confidence
sequences for bounded means (Waudby-Smith & Ramdas 2023), stratified
anytime-valid inference (Turner & Grünwald 2023; Spertus, Sridhar &
Stark 2024), and LLM-specific sequential evaluation (Wu, Nair & Candès
2026; Hsu & Shekhar 2026; CELEUS 2026; PACE 2026).

Given those methods, a practitioner still has to choose one. v3 of this
work answered empirically, with a four-regime map. This version answers
*predictively*: the winner is a function of quantities known before
sampling, the function can be written down from the expansion in §5, and
the written-down function has now been tested against replayed real
outcomes rather than fitted to them.

### 1.1 Positioning (honest)

**This project does not invent the underlying methods.** The
e-processes, the betting CS, the union-intersection construction, the
block reduction, and the second-order expansion of §5 are all
pre-existing; the expansion in particular is Pollak–Siegmund-era
classical work (§5.1, §8). That disclaimer is unchanged from v3 and
applies to every statistical primitive used here.

What is **original to this work**, stated plainly:

1. **The boundary derivation** (§4.2). Writing both candidate designs'
   crossing times in the same expansion and solving for equality gives a
   curve R\*(m) — obtained by bisection on the derived crossing times,
   not in closed form — that is a design-selection rule computed
   *before* data, rather than read off a scoreboard. The single-stream side carries no fitted
   pairs: its constants are derived (§5.3), and the one residual
   renewal term is *computed exactly* by an absorption recursion rather
   than measured (§5.3, `results_cren_exact.txt`). The WSR side uses a
   measured envelope, and the published bands span **only** that
   envelope's uncertainty.
2. **The verification of that boundary on constructed real-outcome
   pools** (§4.3–4.4), scored under frozen predictions with an
   instrument that reports ties, and its three-region final form; and
   the extension of the same construction to a derived **and**
   three-arm-verified two-region partition of the design space (§4.7).
3. **The derived fourth term** of the expansion (§5.3),
   −½·log(2π p\*q\*), which explains structure that a frozen 17-point
   margin sweep had *measured* before the derivation existed, and which
   passes a blind functional test on different data.
4. **The relation gate** (§6.2): a 16-defect census of this project
   found that in 16 of 16 cases the local object was correct and in 15
   of 16 an unchecked *relation between* objects failed; the gate
   mechanizes the missing checks, and **eight** further instances of
   that one generator have since been caught and scored — four in the
   boundary work, four after it, each one converted into a rule.

The v3 contributions stand and are retained: the replay testbed with
exact ground truth (§3), the four-regime empirical map (§4.1), the
calibration of the classical expansion with zero-fit single-stream
predictions (§5.2), the warm-start deployment arc (§4.1.4), and the
audited negative results throughout.

**Scope of "derivable", stated before the result.** The derivation
covers two of the three pre-observable quantities: the boundary curve is
in (heterogeneity ratio, margin), evaluated at a pilot estimate of p\*.
The third quantity, the decision *direction*, governs the allocation
choice on the low-heterogeneity/easy-margin side and is **empirically
mapped, not derived** (§4.1.2). Anyone reading "design selection is
derivable" should read it with that split in mind.

### 1.2 What we do not claim

Every v3 disclaimer stands:

- "Zero-fit" applies to the single-stream arm only; the
  union-intersection arm needs one fitted constant per model (§5.2).
- The dimension rule d = K + #boundary-strata is a coarse empirical
  regularity, not a law, and on our own code pools it scores 2-for-3
  under our own criterion (§5.4).
- The live capstone is a *consistency check*, not a severe test (§5.7).
- All estimands are pool-scoped under a chosen stratum weighting (§2).

And the boundary work adds seven more (v4.1 miscounted these as "four";
the count is corrected here rather than quietly):

- **The boundary predicts winners, not sample counts.** Both arms'
  absolute medians run ~10–20% low under the derived constants (derived
  A1 single 832 versus the measured MBPP cell's 960); WSR's own o(1)
  treatment is open (§5.3).
- **The renewal term is exactly computable, not scalar-closed.** c_ren
  is a function of (p\*, τ, α, d, n0) — schedule-dependent, so it is
  *not* a universal constant — computed with zero fit by a finite
  absorption recursion (−1.1700824 at the reference point,
  `results_cren_exact.txt`). Its scalar closed form is stated as open,
  and the earlier Monte-Carlo estimate of it (−1.105) missed its own
  dispersion criterion and was, separately, noise-high by 0.065 nats.
- **Below the boundary we resolved almost nothing**: 6 of 10 below-band
  points are ties at 200 reps per arm. "Indistinguishable at this
  budget" is not "equal" — and the power analysis that confirms the
  effects are real also confirms they are out of reach here.
- **WSR's own expansion is not established.** The single arm is derived;
  the WSR arm's envelope is measured on a schedule that may admit no
  fixed (d, c) at all, and the frozen test of that hypothesis failed its
  own divergence criterion (§5.5).
- **Automating the rule is not solved.** A shipped pilot-based selector
  matched the oracle design in 11 of 16 cells (`results_auto_select.txt`).
- **We make no safety claim about any model.** The per-model compliance
  rates and heterogeneity ratios of §4.8.1 are **pool parameters** of
  one temperature-0 snapshot under one deterministic proxy grader whose
  label noise we measure at 43% and report. They are not safety
  measurements, not model rankings, and not comparable as such. What is
  tested there is a design-selection rule, and it is invariant to what
  the labels mean.
- **We claim nothing over the risk-limiting-audit literature.** §4.8.2
  improves neither SHANGRLA, BRAVO, ALPHA nor UI-TS, proposes no
  procedure for use in a real election, and uses public county totals to
  fix **pool parameters only**. The contribution is *to that field's
  design-selection question* — which e-process family certifies fastest,
  decidable before the first ballot is pulled.

---

## 2. Setup

**Estimand.** The uniform-mixture failure rate p\* = (1/K)Σ_k p_k over
K = 4 strata — a pool-level quantity *under a chosen weighting*.
Reweighting `extreme` to 10% would give p\* ≈ 0.086 instead of 0.202 for
gpt-4o-mini, so every certification result below states its margin
|p\* − τ|. Validators are deterministic: Draft-7 JSON schema validation
with exact-decimal `multipleOf`, and execution-based equivalence against
reference solutions in isolated subprocesses.

**The three pre-observable quantities.** Everything in §4 is indexed by:
(i) the **heterogeneity ratio** R = p_hi/p_lo of the stratum rates
(estimable from a pilot, and a design-time property of the prompt
population); (ii) the **decision direction**, SAFE (upper bound below τ)
or UNSAFE (lower bound above τ), which is chosen by the evaluator, not
by the data; (iii) the **margin** |p\* − τ|, whose τ is chosen and whose
p\* comes from a pilot. None of the three requires the sequential run
that is about to be designed.

**Statistics.** The Beta-Bernoulli mixture e-process (an exact
martingale: audit verified E[e] = 1 to 12 decimals, with exact-DP
time-uniform miscoverage ≤ 0.035 over a 250-point grid of p); the WSR
hedged betting CS for bounded means (Waudby-Smith & Ramdas 2023), used
both per-sample and on iid block means; a per-stratum union-intersection
(UI) product e-process with weighted-Bonferroni combination, which makes
*any* data-dependent allocation valid; and, as an audit-mandated
state-of-the-art baseline, our adaptation of the Spertus–Sridhar–Stark
(2024) UI test-supermartingale with inverse bets and exact boundary
minimization.

**Decisions.** Certification (UCB ≤ τ → SAFE; LCB > τ → UNSAFE; abstain
at budget), precision stopping (width ≤ w), and paired model comparison
(sequential McNemar on discordant outcomes).

---

## 3. The testbed

### 3.1 Three vendor lineages, three task families

| family | prompts | validation | models |
|---|---|---|---|
| Synthetic JSON schemas | 1,000 unique, 4 structural strata | Draft-7 schema validation (exact-decimal `multipleOf`) | gpt-4o-mini, gpt-4.1-nano, gpt-4.1-mini, llama3.2-3b, qwen2.5-7b |
| Synthetic code specs | 320 parametrized, per-instance reference solutions | execution-based equivalence | gpt-4o-mini, gpt-4.1-nano, gpt-4.1-mini |
| **MBPP (public, sanitized)** | 427 problems, strata = quartiles of reference-solution line count (~107 each) | execution against the benchmark's own tests | llama3.2-3b, qwen2.5-7b |

The synthetic families grade difficulty *structurally* — number of
regex-pattern fields, nesting depth, arrays, exact-length strings,
`multipleOf` — with no per-template tuning; the design was frozen before
collection and verified by prompt-hash audit (0/1000 mismatches). MBPP
is included precisely because we did not design it: its strata are a
mechanical function of the public reference solutions, and it turned out
to occupy a *different heterogeneity regime* than anything we had built
(§4.1.3). OpenAI pools were collected via API; llama3.2-3b (Meta
lineage) and qwen2.5-7b (Alibaba lineage) were collected locally through
Ollama at zero API cost, using the identical prompt objects, validator,
temperature and token cap (`scripts/collect_local_outcomes.py`).

### 3.2 Exact pool ground truth

One temperature-0 call per distinct prompt gives outcome pools whose
uniform-mixture failure rate p\* is *exact for the pool*. Raw
generations for every call are stored alongside the binary outcomes.

| pool | s1 | s2 | s3 | s4 | p\* |
|---|---|---|---|---|---|
| JSON, gpt-4o-mini | .004 | .000 | .068 | .736 | **.2020** |
| JSON, gpt-4.1-nano | .004 | .004 | .008 | .304 | **.0800** |
| JSON, gpt-4.1-mini | .000 | .000 | .004 | .140 | **.0360** |
| JSON, llama3.2-3b | .040 | .032 | .864 | .996 | **.4830** |
| JSON, qwen2.5-7b | .020 | .004 | .216 | .948 | **.2970** |
| Code, gpt-4o-mini | .000 | .000 | .063 | .138 | **.0500** |
| **MBPP, llama3.2-3b** | .336 | .308 | .393 | .594 | **.4079** |
| **MBPP, qwen2.5-7b** | .140 | .215 | .224 | .358 | **.2345** |

(JSON OpenAI rows: `results_crossmodel.txt`; local JSON:
`results_local_law.txt`; code: `results_overhead_law_code.txt`; MBPP:
`results_mbpp_law.txt`. Figure 1.)

The difficulty ordering is preserved for every model at roughly
llama3.2-3b capability and above (violations only at noise level,
z ≤ 1.65), and VIOLATED at the simple/medium boundary by the weakest
models tested (llama3-8b z = +8.65, qwen2-7b z = +2.76; see the scope
correction in FINDINGS) — the structural grading is capability-dependent;
the model × task grid is doubly monotone (JSON p\* .202/.080/.036 and
code p\* .050/.016/.009 rank the three OpenAI models identically). The
dominant synthetic failure mode is character counting (exact-length
strings, long digit runs).

**The last two rows are the important ones.** The synthetic JSON pools
are extreme: hardest-over-easiest-nonzero stratum ratios of 184× / 76× /
35× / 31× / 237×, with several strata at exactly zero. MBPP's ratio is
**1.9× and 2.6×** — two orders of magnitude milder, with no stratum
anywhere near an edge. That gap is the heterogeneity axis the whole of
§4 is organized around, and it is the one axis a JSON-only study cannot
see.

### 3.3 Scope of the pools

Temperature-0 decoding is only *near*-deterministic: the measured
two-sided flip rate on a full re-query is ~1–2% of prompts, roughly
symmetric. Pools are therefore single-epoch snapshots and p\* carries
that epoch qualification. Sampling with replacement from a pool is an
iid draw from the empirical distribution of the model's behavior on that
prompt population, which is what makes the estimand exact and the
comparison across designs fair — every design sees the same stream under
common random numbers.

### 3.4 Prerequisites (baseline facts, measured)

Four facts have to hold before a design map or a design boundary is even
meaningful; all four were established on these pools and survive audit.

- **Peeking destroys fixed-n intervals.** Uniform miscoverage (interval
  excludes p\* at any n ≤ 200; naive sampling from real gpt-4o-mini
  outcomes, 2,000 reps): Wilson **47.7%**, Wald 100% (partly an n = 1
  degeneracy — over the window n ∈ [30, 200] Wilson still misses 27.7%),
  betting CS **3.6%** (`results_advanced.txt`; Figure 3).
- **The betting CS makes it affordable.** Precision stopping that never
  fires with stitched Hoeffding∩Bernstein bounds (0–4% of runs at width
  ≤ 0.35, n ≤ 200) fires in 100% of runs with the betting CS; SAFE
  certification at τ = 0.10 on the code pool (margin 0.050): betting
  500/500 at median 356 vs stitched 166/500 within n = 2,000
  (`results_codetask.txt`; Figure 2, Figure 4B).
- **Never peek mid-block.** On round-robin stratified streams, stopping
  mid-block undersamples the strata late in the rotation. Block-gated
  stopping cuts conditional bias 2–3× versus naive at all four precision
  targets (z = −3.63, −4.49, −4.64, −3.70) with exactly zero composition
  drift and ~40% lower MAE (`results_realllm_betting.txt`). The same
  rule fixes a *coverage* failure: the per-sample mixture CS has no
  general guarantee on non-iid stratified streams, and exact-DP
  counterexamples drop uniform coverage to 0.80 (K = 8) and 0.93
  (K = 4); block gating restores ≥ 0.996 in every configuration tested
  (`results_advanced.txt`). An earlier version of this work argued
  general empirical validity from a concavity argument; **that claim was
  wrong and is withdrawn** — under-dispersion inflates the e-value and
  is the failure mechanism, not a safety margin.
- **Blocks are iid, so bet on them.** A WSR betting CS on complete-block
  means is exactly anytime-valid with no caveat, and on real pools it is
  also *tighter* than the per-sample mixture CS it replaces: median
  samples to width ≤ 0.20, 180 → **124**; to ≤ 0.15, 336 → **184**; to
  certify UNSAFE at τ = 0.15, 606 → **254** (`results_block_reduction.txt`;
  Figure 5B). The honest range is 1.0–2.4× — at loose widths (≤ 0.30)
  both stop at the same 72 samples. Mechanism: stratification shrinks
  the between-block variance (Var(block mean) ≈ 0.017 versus
  p\*q\* = 0.165 for the mixture) and the bet adapts to it.

---

## 4. The boundary

The practical choice this section resolves is **single-stream mixture CS
versus WSR on stratified blocks** — the two designs that take first
place across our round-robin grids. The third arm, UI with round-robin
allocation, takes no cell on them: in the portfolio's stop-arm
distribution it stops first in 45 of 1,600 reps versus WSR's 974 and
single's 581 (`results_portfolio.txt`, P4). Its *directed*-allocation
sibling is the exception and keeps its own regime (§4.1.2), which is
the axis the derived curve does not cover. §4.1 is where the choice was
first mapped
empirically. §4.2 derives the boundary between the two. §4.3 tests the
derived boundary. §4.4 states the final three-region form and the
practitioner rule. §4.7 shows that the same construction, applied to
every design pair rather than one, partitions the whole design space —
and that the partition's sharpest claim survives a three-arm test.

### 4.1 The empirical origin: the four-regime map

**[FIG: design map]** — `fig9_design_map.png`: *two axes (pool
heterogeneity × decision regime), four labeled regions, the winning
design and its evidence artifact in each.*

v3's headline was that the winner is predictable from the heterogeneity
of the pool, the direction and tightness of the decision, and whether
this evaluation has a predecessor:

| regime | condition | winner | margin of victory | evidence |
|---|---|---|---|---|
| (a) | extreme heterogeneity, hard margin | **WSR on blocks** | 1.2–1.7× vs the next arm at hard margins; 1.0–2.4× vs the per-sample CS; dominates all six out-of-family margins (up to 4.1×) | `results_wsr_hard.txt`, `results_local_law.txt`, `results_uncertainty.txt` |
| (b) | extreme heterogeneity, easy margin | **directed allocation** (UNSAFE) / **single stream** (SAFE) | 3.3× / 3.3–5× | `results_crossmodel.txt`, `results_ui_grow.txt`, `results_spertus_crn.txt` |
| (c) | mild heterogeneity | **single stream** | UI drowns (3–36% certification); WSR's tax grows with horizon | `results_mbpp_law.txt` |
| (d) | recurring evaluation, smooth drift | **warm-start UI** | ~1 nat vs 15–18 cold; 4.8–5.3× vs cold | `results_warmstart.txt`, `results_warmstart_drift.txt` |

This table is retained because it is the evidence the derived curve had
to reproduce: a boundary theory that contradicted regimes (a) and (c)
would be dead on arrival. The four regimes' details follow; readers
interested only in the derivation can skip to §4.2.

#### 4.1.1 Regime (a): extreme heterogeneity, hard margins → WSR blocks

At tight margins the block reduction takes first place outright, and the
wins are statistically significant under common-random-numbers seeding
with a paired bootstrap on median differences (10,000 resamples,
abstentions censored at n_max, `results_uncertainty.txt`):

| condition (margin) | WSR blocks | bonf+directed | single-stream† | TaSC (ours) | UI+RR |
|---|---|---|---|---|---|
| 4o-mini UNSAFE τ=.17 (.032) | **662** | 808 | 1696 (99%) | 1014 | 2518 (89%) |
| 4o-mini UNSAFE τ=.18 (.022) | **1308** (94%) | 1802 (91%) | 3186 (48%) | 2388 (90%) | 3304 (15%) |
| nano SAFE τ=.11 (.030) | **748** | 3108 (86%) | 1288 | 1874 | 2654 (86%) |

†single-stream carries the empirical-validity-only caveat above.
(`results_wsr_hard.txt`, `results_tasc_hard.txt`, `results_ui_grow.txt`,
`results_sharp.txt`, `results_ppc.txt`; Figure 6.) The CRN re-run (300
reps, censored medians, so its medians differ slightly from the table)
confirms every box: τ=.17 WSR 656 vs directed 800, diff **+144**, 95% CI
[+96, +230]; τ=.18 WSR 1502 vs directed 1992, **+490** [+268, +720];
nano τ=.11 WSR 706 vs single 1228, **+522** [+464, +614]. No box
downgrades to a tie (`results_uncertainty.txt`).

**The out-of-family replication is the strongest form of this result.**
On the two non-OpenAI JSON pools, WSR dominates *every* margin against
*both* alternatives (`results_local_law.txt`):

| llama3.2-3b, margin | .022 | .027 | .032 | .042 | .052 | .057 |
|---|---|---|---|---|---|---|
| single-stream | 5272 (.27) | 4422 (.85) | 3240 (.99) | 1804 | 1148 | 920 |
| UI+RR | 3668 (.86) | 2740 (.99) | 1942 | 1102 | 700 | 588 |
| **WSR blocks** | **894** | **582** | **426** | **296** | **196** | **188** |

The mechanism is the one §5 makes quantitative: here V_rr/V_pool runs
**3.1–4.7×** across the grid, so stratification buys a large rate
multiple, and WSR collects it without paying a (K/2)·log n learning tax.

**Against the state of the art.** The audit-mandated
Spertus–Sridhar–Stark baseline (our adaptation: inverse bets with frozen
predictable coefficients, exact boundary minimization; validity verified
in both directions at 0.007–0.030 ≤ α) is a genuine *trade*, not a loss
for either side (`results_spertus_baseline.txt`, which enumerates all
five conditions). Spertus+greedy is faster when it certifies on four of
the five conditions (144 vs 244 at easy UNSAFE; 180 vs 260 at easy SAFE)
but abstains 3–63% within budgets where WSR abstains 0–10%; at the
hardest margin (τ = 0.18) WSR dominates outright, 271/300 versus
112/300. The CRN censored-median tie-breaker (`results_spertus_crn.txt`)
makes both contested hard margins *statistical ties* with WSR nominally
ahead, and hands Spertus the easy-nano-SAFE box (184 vs 240, CI
[+40, +80]). Three methods share the frontier — which is the strongest
form of the design-follows-decision thesis, not a weakening of it.
Fidelity caveat in both directions: this is our variant of their
construction, and their banded AGRAPA version may reduce the abstentions.

#### 4.1.2 Regime (b): extreme heterogeneity, easy margins → the decision picks

With per-stratum betting CSs at α/K and weighted-Bonferroni combination,
*any* data-dependent allocation is valid (construction per Turner &
Grünwald 2023; re-verified here by exact analysis and adversarial
allocation). That freedom matters, and the right way to use it is
decided by the direction of the certification
(`results_crossmodel.txt`; Figure 4A):

- **UNSAFE** (gpt-4o-mini, τ = 0.15): decision-directed allocation
  certifies in median **176** vs **588** for round-robin (3.3×; 3.1–3.5×
  across audit seeds). One bad stratum alone carries the weighted LCB
  over τ, so evidence should concentrate there.
- **SAFE** (nano, mini): the *undirected* route wins — round-robin at
  **240** and **72** versus **800** and **364** for directed (the
  single-stream mixture lands in the same place, 260 and 72,
  `results_ui_grow.txt`). Every stratum must tighten for a SAFE verdict,
  so concentrating evidence helps nothing and the α/K split costs.
- **Width-greedy allocation is a trap**: it abstains in 443/500 = 89% of
  nano SAFE runs. It optimizes width, not the decision. The second trap
  is midpoint-aiming lock-in; aim with the point estimate.

This is the axis of the thesis that is **measured, not derived**: the
boundary curve of §4.2 is silent about allocation direction. Independent
corroboration: Hsu & Shekhar (2026) also report uniform sampling
sometimes beating adaptive querying.

#### 4.1.3 Regime (c): MILD heterogeneity → the single stream wins

This regime was invisible until we ran a benchmark we did not design.
On sanitized MBPP the stratum ratio is 1.9–2.6× rather than ~200×, and
three things follow (`results_mbpp_law.txt`; predictions pre-registered
in `scripts/run_mbpp_law.py`):

1. **Stratification buys almost no rate.** V_rr/V_pool ≈ 1.05 at every
   margin and never above 1.10 (pre-registered clause: ≤ 1.6 —
   CONFIRMED), versus ≈ 2.0 on the OpenAI JSON pools (V_rr = 0.0192 vs
   V_pool = 0.0097 at τ = 0.15, `results_frontier.txt`) and 3.1–4.7× on
   the local JSON pools.
2. **So the UI mixture drowns.** It still pays ~(K/2)·log n for the
   parameters it must learn, with no rate gain to cover it: it certifies
   **3–36%** at the four hardest margins within n_max = 6,000, leaving
   3-point fits. This was a pre-registered FAIL and we report it as one;
   llama's fitted d = −2.23 is a censoring artifact, not a dimension,
   and is disclosed as unidentifiable rather than interpreted.
3. **And WSR's advantage erodes with the horizon.** Its fitted d is
   1.8–2.3 on MBPP: overhead *grows*. This is the λ-schedule anti-result
   of §5.5 surfacing at MBPP's longer crossing horizons.

The result: at every margin where both arms certify ≥ 90%, plain
single-stream has the lower median (qwen: 1716/960/542/460 vs WSR
2022/1052/592/518), and at the two hardest margins WSR's lower median
comes with materially *lower* certification (llama .49 vs .54 at margin
.022). Our own pre-registered clause "WSR's median dominates both
alternatives at every ≥90%-certified margin" was **REFUTED**. Under mild
heterogeneity the d = 1 method beats everything, and the practical rule
— *measure your stratum ratio before you buy stratification* — is
exactly what §4.2 turns into a number.

#### 4.1.4 Regime (d): recurring evaluations → warm-start UI

Real evaluations recur. Certifying release n+1 with a prior epoch's
per-stratum rates as an ε-contaminated transfer prior converts the
cold-start learning tax to **0.76–1.24 nats** (cold: 15.4–18.5), with
medians 200/296/568 versus cold 958/1572/2880 and WSR 240/350/600 at
τ = 0.15/0.16/0.17 — 4.8–5.3× faster than the cold mixture, with zero
wrong certifications and no abstention corner (`results_warmstart.txt`).
Validity holds because the prior is *fixed with respect to the
resampling stream*, not because it "predates" anything; the construction
survived an adversarial null Monte Carlo with worst type-I error
**0.047 ≤ α = 0.05** over 8 boundary configurations × 3 arms × 2,000
reps (`results_warmstart_null.txt`). Joint (one global 90/10 mixture)
contamination caps the log-e-value premium pathwise at
log(1/ε) ≈ 2.30 nats — verified exact to 1e-9 — while per-stratum
contamination pays K·log(1/ε) ≈ 9.2; the corresponding median-overhead
gaps (+2.12/+2.23/+2.40) are a downstream statistic that may exceed the
pathwise cap, and all three are printed rather than the two that fit
(`results_warmstart_joint.txt`).

**Audit qualification, applied.** The benign "prior epoch" is the same
prompt pool relabeled by a validator fix (16/1000 labels differ), i.e.
an **oracle-adjacent** warm start, not a realistic stale epoch. The
realistic statement is the drift phase diagram below.

**[FIG: drift phase diagram]** — `fig7_drift_budget.png`: *median
samples versus additive prior drift δ, with the cold-mixture and WSR
reference lines and the shaded beats-both region.*

**The staleness budget is asymmetric** (`results_warmstart_drift.txt`,
τ = 0.16, joint contamination, 200 reps/point):

| δ | −0.100 | −0.060 | −0.030 | −0.015 | 0 | +0.015 | +0.030 | +0.060 | +0.100 |
|---|---|---|---|---|---|---|---|---|---|
| median | 1350 | 836 | 362 | **288** | **276** | 460 | 928 | 1718 | 1748 |
| overhead (nats) | 14.12 | 7.60 | 1.59 | 0.66 | 0.50 | 2.84 | 8.77 | 18.78 | 19.17 |

Downward drift (the model regressed relative to the prior) is cheap:
warm-start beats the cold mixture even at δ = −0.10, and beats WSR
robustly within |δ| ≤ 0.015. Upward drift is expensive: it loses to WSR
by +0.015 and saturates at the contamination floor by +0.06 (worst
median 1748 vs the predicted ceiling ~1700 = cold + log(1/ε)/V_rr).
Zero wrong certifications at every δ (1,800 reps). **My pre-registered
asymmetry prediction was REVERSED** — I predicted understatement would
hurt more, and measured the opposite. The mechanism explains it: three
of four strata have near-zero true rates, so negative drift is absorbed
by the clip at zero, while positive drift poisons the κ = 200 prior in
*all* strata, including the clean ones that are 3/4 of the round-robin
stream. The deployment rule inverts accordingly: **when uncertain,
shade the transfer prior down.** Under honest per-rep CRN seeding the
δ = −0.03 point is a seed-level tie with WSR (362 vs 350 under rev-2
seeding, 364 vs 374 under rev-1 — a ±4% flip), so the *robust*
beats-WSR region is |δ| ≤ 0.015 downward; everything else in the table
is stable across seedings.

**Chaining: warm-start survives its own deployment loop.** Over a
six-release improving-model trajectory that crosses τ mid-chain, each
epoch warm-starting from the previous epoch's own stopped-run estimates
(`results_warmstart_chain.txt`): chain-warm beats always-cold at every
epoch ≥ 2 (322 vs 1266; 3620 vs 4460; 5164 vs 5368; 512 vs 1464; 136 vs
468 — the middle two are comparisons between heavily censored medians,
57/200 and 24/200 certifying, and should be read as such);
estimation noise does **not** compound (epoch-6 chain-warm 136 vs
the oracle-prior arm's 124, +9.7%, and an exact tie at epoch 5); and the
poison test passes — at the SAFE/UNSAFE flip epoch a wrong-direction
stale prior caused zero wrong certifications and ran at 0.96× of cold,
the ε floor bounding the damage exactly as designed. Zero wrong
certifications in all 4,800 runs.

**The informative refutation inside the chain**: near-boundary epochs
are structurally WSR territory. At epochs 3 and 4 WSR certifies 165/200
and 173/200 while *every* UI variant — cold, chain-warm, and even
oracle-prior — mostly hits n_max. A warm prior does not change that.

**The router negative (two iterations, both failed).** The obvious next
move is to route each epoch to warm-UI or WSR using only the *prior*
epoch's data — which preserves anytime validity with no α-splitting,
since the routing decision is independent of the new stream. Two
pre-registered iterations both **failed their headline targets**:

- v1 (margin threshold): **1.101×** pure WSR on the chain trajectory
  (target ≤ 1.05×). Diagnosis: fast epochs starve the next epoch's prior
  (κ ≈ 28 after a 114-sample WSR epoch), and prior margin alone cannot
  separate drift-toward from drift-away epochs (0.045 vs 0.044 with
  opposite winners) (`results_router.txt`).
- v2 (drift-extrapolated margin + LCB rule + decay-cumulative priors):
  **1.090×** pure WSR on the boundary-heavy trajectory (target ≤ 1.00)
  and **1.259×** on a margin-rich trajectory (target ≤ 0.85), *despite*
  4/5 and 5/5 majority routing accuracy. Diagnosis: warm-UI's
  speed depends on prior *strength* and *center accuracy* in ways a
  margin rule cannot see, and a drift cliff (0.216 → 0.104 between
  epochs) defeats one-step extrapolation entirely
  (`results_router2.txt`).

Zero wrong certifications in all 14,400 runs across both versions. **We
deliberately stopped at v2**: iterating until a router wins is exactly
the forking-paths pattern our audits exist to prevent. The surviving
conclusions are that **pure WSR blocks are the best single policy across
whole release trajectories** in both regimes tested, and warm-start UI
is a per-epoch specialist (2–3× faster than WSR at clear-margin epochs
with strong fresh priors).

### 4.2 The derived curve

**[FIG: derived boundary curve]** — *not yet drawn: R\* versus margin at
p\* ∈ {0.20, 0.30, 0.40}, central curve plus WSR-envelope band, with the
verification points of §4.3 overlaid and ties marked.*

**Construction.** Both arms obey the expansion of §5,
n·V = log(1/α) + (d/2)·log n + c, with rate definitions fixed in §5.1:
V_single = KL(p\*, τ) (pooled Bernoulli), and V_wsr = the exact
per-sample optimal Kelly growth over the 2^K = 16-atom block-mean
distribution. Setting the two predicted crossing times equal and solving
for the heterogeneity ratio gives the flip as a **curve** R\*(m) at
fixed (p\*, K) (`scripts/derive_phase_boundary.py`, artifact
`results_phase_curve.txt`, α = 0.05, K = 4). The stratum profile used
for the derivation is two cold + two hot,
p_hi = 2 p\* R/(1 + R), p_lo = p_hi/R — valid for any R at p\* < 0.5 and
closer to the real pools' shapes than the first profile tried.

**Which constants are derived and which are measured.** The single arm
is fully derived: its crossing solves

    n·KL(p*, τ) = log(1/α) + ½·log n − ½·log(2π p* q*) + c_ren

where the third term is the fourth expansion term derived in §5.3 and
c_ren is the residual renewal term. **c_ren is computed, not fitted and
not assumed universal.** It is a function c_ren(p\*, τ, α, d, n0),
evaluated with zero fit by a finite absorption recursion over the
killed chain (`results_cren_exact.txt`, verified against an independent
transfer operator to 7 decimals): **−1.1700824** at the reference point
(p\*, τ, α, d, n0) = (0.202, 0.157, 0.05, 4, 20) under the discrete-median
convention, and demonstrably not a constant — −1.1449169 at p\* = 0.150,
−1.1866026 at p\* = 0.300, **−1.2985462 at check period d = 1**, and
−1.1443421 at n0 = 40. The check-period dependence is the point: any
scalar "renewal constant" quoted without (d, n0) is under-specified, and
earlier statements of ours that implied universality are corrected here.
No fitted pairs remain on the single side. The WSR arm keeps a
**measured** two-regime envelope: central
(c_short, d_long, c_long) = (2.3, 1.95, −4.6), with corners
(1.6, 1.81, −3.4) and (3.0, 2.34, −5.9) bracketing the MBPP WSR fits
(d = 1.81, c = −3.37 for qwen; d = 2.34, c = −5.49 for llama;
`results_mbpp_law.txt`). **The published bands therefore span only WSR's
envelope uncertainty** — a fact we state because it caps what the bands
mean, and one that §5.5 sharpens further: those fitted WSR dimensions
may be horizon-dependent artifacts of a class with no fixed d.

**The derivation refused itself three times.** Four passes are on the
record, and the first three did not freeze
(commit 8bbccb2, "three passes, anchors self-refuse the curve"):

| pass | what happened |
|---|---|
| 1 | corner bands came out unfalsifiably wide — incompatible regimes had been combined into one band |
| 2 | profile saturation artifact at high p\*, and idealized constants that failed the MBPP anchor |
| 3 | fitted-pair constants: the WSR-side anchor passed, the single-side anchor **A1 failed by ~8%** — exactly the o(1) scale in that near-boundary cell |
| 4 | derived four-term single arm (§5.3) + measured WSR envelope: **both discriminating anchors pass at every corner**; curve frozen (commit f75eb8d) |

An anchor gate that refuses to freeze a wrong curve is the discipline
working, and pass 3's failure is what sent the project to derive the
fourth term rather than fit a fourth constant.

**Anchors: two discriminating, one unscored.** The gate requires the
curve to reproduce winners already measured on real pools:

| anchor | pool shape | R | derived single median | expectation | verdict |
|---|---|---|---|---|---|
| A1 | MBPP-like (qwen2.5-7b MBPP rates) | ~2.6 | 820 | single | PASS at all corners |
| A3 | llama3-8b-like | ~7.5 | 1240 | WSR | PASS at all corners |
| A2 | llama3.2-like | ~31 | 1256 | WSR | reported, **NOT scored** |

(Medians as regenerated under the exact recursion; at the freeze they
read 832 / 1266 / 1283 under the Monte-Carlo renewal estimate. Every
anchor verdict is unchanged by the correction — which is the propagation
check the gate's R6 exists to force, not a claim that the correction was
small.)

A2 is excluded by **gate rule R1** (§6.2): the relation gate evaluated
it under every corner of the constant band and its verdict never
changes, so it cannot fail and is not evidence
(`results_relation_gate.txt`). The honest score of the anchor gate is
therefore "two discriminating anchors, both pass", and A1/A3 bracket the
flip in R (2.6, 7.5).

**The curve** (`results_phase_curve.txt`, checksum 040d60191cbbe608 as
regenerated under the exact recursion; R\* central with the
WSR-envelope band in brackets, and the frozen pre-correction values in
parentheses where they differ):

| p\* | m = 0.030 | m = 0.045 | m = 0.060 | m = 0.080 |
|---|---|---|---|---|
| 0.20 | 1.1 [1.1, 4.4] | 2.8 [1.1, 14.8] | 6.8 [1.1, 400] | 400 [**3.4**, 400] |
| 0.30 | 1.1 [1.1, 2.8] | 2.0 [1.1, 4.5] | 3.2 [1.1, 7.1] | 5.3 [**1.8**, 15.6] |
| 0.40 | 1.1 [1.1, 2.2] | 1.8 [1.1, 3.1] | 2.3 [1.1, 3.8] | 3.3 [**1.7**, 5.3] |

*Frozen version* (commit f75eb8d, checksum c4a4720dbba3ccb8), which is
the version §4.3's predictions were committed against and scored under:
the m = 0.080 lower edges read **4.5 / 2.2 / 1.7**, and the central
values 400 / 6.1 / 3.4. **We do not re-score a frozen test after a
constant changes**, but we do disclose the sensitivity, so §4.3 reports
which points would move.

Read it as: at your (p\*, margin), compute your pool's ratio R; above
the band's upper edge the curve says WSR, below the lower edge it says
single stream, inside the band it says nothing. The shape reproduces
what §4.1 measured without being fitted to it — R\* → 1.1 (WSR
everywhere) at hard margins, R\* rising at easy margins — and it makes
the structural disclosure that **below-band territory exists only at
easy margins**: at m ≤ 0.06 the band's lower edge is 1.1 for every p\*
tested, i.e. the curve confines single-stream territory to easy margins.

**The frozen verification prediction**, committed before any replay ran:
constructed pools with measured R below the band's lower edge at their
margin are won by single-stream (lower median, ≥ 90% certification in
both arms); above the upper edge, by WSR; in-band points are
unresolved-by-design and not scored.

### 4.3 Verification: four rounds, reported in order

**The instrument.** Verification pools are **constructed from real
outcomes**: each constructed stratum is a mixture of draws from the
gpt-4o-mini extreme pool (rate .736) and simple pool (rate .004), mixed
to hit a target stratum rate, so that every outcome is a real model
generation while (p\*, R) are *placed* rather than inherited from
whatever a vendor happened to ship (`scripts/run_phase_test.py`).
Two-level 2+2 geometry matching the derivation, 200 reps per arm per
point, n_max = 12,000, BASE_SEED = 42, UNSAFE direction, round-robin.

**v1: FAILED as frozen — and mis-allocated.** In the v1 artifact
(`results_phase_test.txt` at commit 065f9a8, which prints all nine
scored points): P2 (above-band → WSR) passed 7 of 7 and P3 (wrong
certifications ≤ α) passed at 1/4,400, but P1 (below-band → single) went
**0 of 2** — both below-band points landed on WSR (single 296 vs WSR 244
at p\* = .3, R = 1.5; single 310 vs WSR 276 at p\* = .4, R = 1.3).
Verdict printed: **FAILED**. Two corrections followed, both from peer
review:

- The printed verdict was *narrower* than "the curve is refuted": the
  WSR region merely re-confirmed what §4.1 already established, and the
  **novel** single region had been tested at only two points, same
  margin, adjacent R. "Untested at useful resolution, one corner wrong"
  is the honest v1 reading.
- v1 put **7 of its 9 scored points in the already-established WSR
  region**. A verification that concentrates where the hypothesis is
  already known is not discriminating regardless of point count. This is
  now **gate rule R8** (§6.2), and it was the third recorded instance of
  the project's defect generator.
- v1's own post-hoc diagnosis proposed a missing constant: c_short,
  calibrated on extreme-heterogeneity pools, is a *function* of the
  block distribution treated as a constant. That hypothesis was queued
  as its own frozen artifact rather than patched the same day — and
  §4.4 reports what became of it.

**v2: allocation inverted, verdict instrument-limited.** v2 moved 10 of
13 scored points into the below-band (single-predicted) region — R8
compliant at 77% — spread across p\* ∈ {.2, .3, .4} and R ∈ [1.2, 3.5],
all at m = 0.08 because that is the only margin where the frozen bands
admit single territory at all. Scored by v2's rule (which median is
lower), in the v2 artifact (`results_phase_test.txt` at commit 80c9e14,
all thirteen scored points printed): P1 came back **4 of 10: FAILED**,
P2 3 of 3, P3 1/6,000. But the
rule itself was the fourth instance of the generator: the two arms were
**not CRN-paired** and the verdict carried **no error bars**, so a
2-sample median gap counted the same as a 60-sample one. A comparison
with no error bar is an anchor with no discrimination check; that is now
**gate rule R1b** (§6.2).

**v2b: re-scored with the instrument this project already had.** The
re-run pairs the arms under common random numbers, bootstraps the
paired median difference (10,000 resamples of rep indices), prints a
per-point CI, and issues **three-way** verdicts — SINGLE, WSR, or TIE
when the CI straddles zero — with P1 restated as "every *resolving*
below-band point is single" and the tie fraction printed. This is the
same instrument §4.1.1 used for the scoreboard boxes. Crucially, the
re-scoring was not a search for a pass: a reviewer **pre-stated the
falsifiable outcome before the run** — *most below-band points will come
back TIE, making the honest claim "below the boundary the designs are
statistically indistinguishable" rather than "single wins"* — and that
prediction is scored in the artifact as CONFIRMED (7 of 13 ties at the
time; 6 of 13 after the calibration described next, still CONFIRMED).

**v2c: our own instrument was audited, found conservative, and
re-frozen.** v2b's paired bootstrap resampled the *plain* median of a
heavily tied lattice of crossing times. A peer power analysis at 20,000
paired reps checked what that bootstrap's stated 5% size actually was
and found **1.8–2.6%** — a conservative interval, which inflates ties
and is the same defect class as R1b one level down: the verdict rule
stated a resolution it did not have. The fix keeps the estimand fixed
(difference of *marginal* medians, not the median of paired differences,
which is a different quantity) and replaces the estimator with a
calibrated Harrell-Davis quantile inside the same paired bootstrap,
measured at **4.4–5.2%** actual size. The predicted consequence was
stated before the re-run — one below-band point should move from tie to
resolving — and that is exactly what happened. Two things this does
*not* change: the arms, the seeds and the pools are identical, and the
frozen predictions were not touched.

The same power analysis settles what the remaining ties are. Of v2b's
seven, four are **real but underpowered** median effects (11–33% power
at 200 reps per arm), one is ~zero, one is unresolved, and one favors
WSR. The ties are a budget statement about the reader's experiment, not
a defect in ours. (This analysis is peer-supplied and recorded in
`AUDIT_PREP.md`; it has no committed artifact of its own, and we mark it
as such rather than citing it as one of ours. A prior premise of that
same analysis — that CRN pairing had been lost — was withdrawn by its
author after checking: pairing was intact, arm correlation 0.77–0.79.)

Below-band points, m = 0.08 (`results_phase_test.txt` v2c, checksum
85ab64297762127a; CI on median(single) − median(wsr), negative favors
single; band-lo is the **frozen** curve's lower edge, the one these
points were selected and scored against):

| p\* | R | band-lo | single | WSR | 95% CI | verdict |
|---|---|---|---|---|---|---|
| 0.20 | 1.2 | 4.5 | **172** | 208 | [−53, −10] | SINGLE |
| 0.20 | 1.5 | 4.5 | **174** | 206 | [−55, −14] | SINGLE |
| 0.20 | 2.0 | 4.5 | **174** | 192 | [−49, −1] | SINGLE |
| 0.20 | 2.6 | 4.5 | 176 | 184 | [−36, +13] | tie |
| 0.20 | 3.5 | 4.5 | **166** | 204 | [−52, −13] | SINGLE |
| 0.30 | 1.2 | 2.2 | 306 | 296 | [−22, +41] | tie |
| 0.30 | 1.5 | 2.2 | 274 | 286 | [−60, +17] | tie |
| 0.30 | 2.0 | 2.2 | 260 | 246 | [−18, +33] | tie |
| 0.40 | 1.3 | 1.7 | 284 | 244 | [−9, +54] | tie |
| 0.40 | 1.5 | 1.7 | 318 | 304 | [−27, +42] | tie |

The point that moved is (p\* = 0.20, R = 2.0), from [−48, +4] under the
conservative estimator to [−49, −1] under the calibrated one — the
predicted extra resolution, and a reminder that a CI edge one sample
from zero is not a strong result on its own. It is scored because the
rule was fixed in advance, not because it is impressive.

Above-band sanity points, same run:

| p\* | m | R | single | WSR | 95% CI | verdict |
|---|---|---|---|---|---|---|
| 0.30 | 0.045 | 8.0 | 1058 | **752** | [+192, +421] | WSR |
| 0.40 | 0.060 | 6.5 | 640 | **332** | [+251, +384] | WSR |
| 0.20 | 0.045 | 20.0 | 672 | **556** | [+68, +225] | WSR |

In-band points are printed and left unscored, as the frozen protocol
requires: p\* = .3, m = .06, R = 3 (single 458 vs WSR 412) and
p\* = .2, m = .06, R = 7 (370 vs 344). No CI is computed for them and
none is claimed.

Scored verdicts: **P1 4 of 4 resolving below-band points → single:
PASS. P2 3 of 3 above-band → WSR: PASS. P3 wrong-certification rate
0/6,000 = 0.0000 ≤ 0.05: PASS.** Artifact verdict: **CONFIRMED**.

**Sensitivity to the c_ren correction, disclosed and not acted on.**
These points were selected against the frozen curve, whose m = 0.080
lower edges were 4.5 / 2.2 / 1.7. Under the curve regenerated with the
exact recursion (§4.2) those edges move to 3.4 / 1.8 / 1.7, which would
reclassify two of the ten below-band points as *in-band*
(p\* = 0.20, R = 3.5, whose v2c verdict is SINGLE, and p\* = 0.30,
R = 2.0, a tie). P1 would then read 3 of 3 resolving with 5 ties instead
of 4 of 4 with 6. No verdict changes sign either way, and all three
above-band and both in-band points keep their classification. We report
the frozen scoring and this recomputation side by side rather than
adopting whichever is more flattering.

**What this did to the c_short(R) hypothesis.** v1's two below-band
misses re-measure, under CRN pairing, as ties (p\* = .3, R = 1.5:
274 vs 286, CI [−66, +22]; p\* = .4, R = 1.3: 284 vs 244, CI
[−14, +64]). They were **unpaired median noise scored without error
bars**, not evidence of a missing constant. A sub-noise c_short(R)
effect may well exist; it is unmeasurable at these budgets, and nothing
remains to derive there. The queued derivation was cancelled rather than
performed — the cheapest possible outcome, purchased by fixing the
instrument instead of the theory.

### 4.4 The final form: three regions

**Above the band, WSR dominance is verified 10 of 10** — the seven
above-band points of v1 (`results_phase_test.txt` at 065f9a8: single/WSR
784/608, 1084/792, 540/402, 306/202, 1260/816, 720/334, 368/168) plus
the three of v2c tabulated above (`results_phase_test.txt`), at large
effect sizes, with paired CIs far from zero in v2c and consistent
nominal margins in v1. This is the region where hard-margin certification
decisions actually live, and it is where the derived curve is now
verified rather than merely consistent.

**In the band, nothing is claimed.** The bands span WSR's envelope
uncertainty; in-band points are unresolved by design and were never
scored.

**Below the band, the designs are indistinguishable.** Four points
resolve, all to single-stream; **six of ten are ties**, and the power
analysis of §4.3 puts most of those ties at 11–33% power — real effects,
out of reach at 200 reps. Read positively, this is the more useful half
of the result:

    above the band  ->  WSR blocks dominate (verified 10 of 10)
    in the band     ->  unresolved by design
    below the band  ->  designs statistically indistinguishable;
                        the choice is free at realistic budgets

**Practitioner rule.** Measure your stratum ratio from a pilot. Above
the boundary, use WSR on blocks. Below it, use whichever design is
convenient — and spend the effort you would have spent choosing on
something that matters. **The boundary marks where design selection is
worth doing at all**, which is a statement that transfers across
domains better than any particular winner does.

**The honest counterweights.** Two shipped attempts to *act* on
selection automatically both fell short, and neither is buried:

- **Hedging instead of choosing loses.** A Bonferroni portfolio running
  all three designs at α/3 and stopping at the first certification was
  valid (2/1,600 wrong, 0.13% ≤ 5%) and its derived premium landed where
  the derivation said it would (10,224/8,718 = **17.3%** aggregate,
  inside the predicted 6–27%), but its headline **FAILED**: grid totals
  portfolio **10,224** versus fixed WSR **8,718**. Not choosing costs
  more than WSR's wrong-regime errors on this grid. P2 also failed as
  frozen — 11 of 16 cells inside the 1.30× cap, the five misses being
  the five fastest cells, where a log(3)/V premium is a constant sample
  count against a small base (`results_portfolio.txt`, all sixteen cells
  printed).
- **Choosing automatically from a pilot is not yet reliable.** The
  shipped `Certifier.auto_select` wrapper dispatches on a 120-sample
  pilot; scored against the oracle design per cell it matched in **11 of
  16** cells against a pre-registered ≥ 12 (**FAIL**), while its cost
  clauses passed: mean regret **+8.3%** (≤ 0.15) and worst **+43%**
  (≤ 0.60), with zero cells exceeding the α wrong-certification budget
  (`results_auto_select.txt`, all sixteen cells printed). The misses are
  not conveniently confined to cells the boundary calls free: two are
  OpenAI JSON cells where the oracle gap is 18–22% (nano UNSAFE 222 vs
  284; mini UNSAFE 1,042 vs 1,272) and three are MBPP cells (1,100 vs
  1,190; 1,052 vs 1,247; 672 vs 1,132). The worst is expensive — on
  qwen2.5-7b MBPP SAFE the wrapper picked single (auto median 1,129)
  where WSR's oracle median was 672, a +43% regret.

### 4.5 Other decisions, same machinery

- **Paired model comparison.** Sequential McNemar with a betting CS on
  discordant outcomes: gpt-4o-mini vs gpt-4.1-nano (θ = .881) certified
  500/500 correct at median **74 prompts**; nano vs mini (θ = .734)
  500/500 at median 335; a *constructed exact tie* (θ = 0.500) abstains
  96.0%, and the 4.0% that certify are false certifications by
  definition, inside the two-sided α = 5% budget (exact-DP 3.4–3.7%)
  (`results_model_comparison.txt`; Figure 5A).
- **SPRT: fast where it's right, dangerous where it isn't.** A
  well-specified Wald SPRT is ~10× faster than composite certification
  (median 48 vs ~600), but between its two hypotheses its declarations
  carry no error control relative to τ: measured false-certification
  rates **16–64%**, versus ≤ 0.5% for the CS, which abstains near the
  boundary (`results_sprt_comparison.txt`).
- **Graded scores.** Fraction-of-tests-passed scores in [0,1] run
  through stratify → block → bet unchanged: "mean score ≥ 0.90"
  certified 500/500 at median 276 samples
  (`results_graded_scores.txt`).

### 4.6 The invention round, in one paragraph

Before any map existed we treated the allocation/combination layer as an
open problem — validity is allocation-independent, so invention there is
safe — and built four progressively more sophisticated candidates, each
with predictions stated before running. **All four lost.** GROW greedy
allocation collapsed without forced exploration and lost even when
oracle-fed (mechanism: the least-favorable null re-optimizes across
strata, and greedy growth chases it). TaSC, the principled max-min
repair, is sound everywhere and best of the UI family but never first,
running ~6× above its own game-value bound; both of its pre-registered
predictions failed. Sharp recentered priors were predicted to save 4–6
nats and saved none (the Beta(1,1) mixture is already near-minimax).
Prediction-powered stratification refinement predicted a 19% variance
cut and measured a net loss, because the predictor separated nano's
extreme stratum too weakly (33% vs 23% sub-rates) to cover the extra
draws per block. The winner of the invention round was the simplest
structured design we already had: stratify → block → bet
(`results_ui_grow.txt`, `results_tasc_hard.txt`, `results_sharp.txt`,
`results_ppc.txt`). Four pre-stated predictions failing in a row is what
makes that conclusion trustworthy — and it is why §4.2 spends its
effort on *choosing between* existing designs rather than inventing a
fifth.

### 4.7 The capstone: one construction, the whole design space

§4.2 derived one curve because one pair of designs mattered most. The
construction is not specific to that pair. Writing *every* design's
crossing time in the same expansion and solving each pairwise equality
turns the four-regime table of §4.1 from a scoreboard into a **derived
partition** of (p\*, heterogeneity ratio R, margin), with the constants
frozen from prior artifacts and nothing fitted to the partition itself
(`results_partition.txt`). Both discrimination anchors pass: ANC-2 at
R ≈ 200 crisply (WSR at every corner), and ANC-1 at R ≈ 2.6 through the
**tie band** with a 1% runner-up gap — aligned to the tie region §4.3
verified rather than forced to a winner, which is a weaker pass and is
labelled as one.

Winner regions at α = 0.05, K = 4, with `~` marking the **tie band**
(winner within 5% of runner-up — where the choice does not matter):

| p\* | margin | R = 1.5 | R = 2.5 | R = 4 | R = 7 | R = 15 | R = 40 |
|---|---|---|---|---|---|---|---|
| 0.20 | 0.030 | single~ | single~ | WSR | WSR | WSR | WSR |
| 0.20 | 0.045 | single~ | single~ | WSR~ | WSR | WSR | WSR |
| 0.20 | 0.060 | single | single | single~ | WSR~ | WSR~ | WSR |
| 0.20 | 0.080 | single | single | single | single | single | single~ |
| 0.30 | 0.030 | single | single~ | WSR | WSR | WSR | WSR |
| 0.30 | 0.045 | single~ | WSR~ | WSR | WSR | WSR | WSR |
| 0.30 | 0.060 | single | single~ | WSR~ | WSR | WSR | WSR |
| 0.30 | 0.080 | single | single | single~ | WSR~ | WSR | WSR |
| 0.40 | 0.030 | single | WSR~ | WSR | WSR | WSR | WSR |
| 0.40 | 0.045 | single~ | WSR | WSR | WSR | WSR | WSR |
| 0.40 | 0.060 | single | WSR~ | WSR | WSR | WSR | WSR |
| 0.40 | 0.080 | single | single | WSR | WSR | WSR | WSR |

**The widths, not the lines, are the useful part.** A practitioner wants
to know whether their cell is one where the choice is worth making, and
the `~` cells answer that directly — which is the same message §4.4
extracted from the tie fraction, now available before any data is
collected.

**The falsifiable claim, and its three-arm test.** The partition makes
one prediction sharper than anything the four-regime table could:
**UI + round-robin is nowhere optimal.** It is the outright fastest arm
at **0 of 84** derived grid cells (`results_partition.txt`, ANC-3). One
measured cell where UI wins outright refutes it, so we went looking
(`results_partition_test.txt`, frozen at commit eeeecfd; ten cells
spanning the space, three arms, 100 reps per arm per cell, CRN pairing,
paired-bootstrap three-way verdicts):

- **UI is outright fastest at 0 of 10 cells: PASS.** The cells include
  the mild-heterogeneity, easy-margin corner where UI's variance
  advantage is largest and where, if it wins anywhere, it should win.
  In that corner (p\* = 0.20, m = 0.080, R = 2) UI's median is **426**
  against single's 200 and WSR's 222; in its worst (p\* = 0.20,
  m = 0.045, R = 2) it is **1,924** against 652 and 630. All ten cells'
  medians are printed in the artifact.
- **0 of 3,000 wrong certifications.**
- Among single | WSR, the four CI-resolving cells all fall on the
  **derived WSR side**, and the six ties are the boundary-and-below
  region the three-region form of §4.4 predicts. **No cell contradicts
  the derived partition.**

So the design map is now a **derived and verified two-region partition**
— single below the boundary, WSR above, UI provably and empirically
nowhere optimal — with directed allocation (§4.1.2) and warm start
(§4.1.4) as specializations off that spine rather than peers of it. This
is a sharper statement than v3's four-regime table and a strictly more
falsifiable one. ("Two regions" here counts *winners*; §4.4's "three
regions" counts *epistemic states* of the single | WSR comparison — WSR
wins, unresolved-by-design, indistinguishable. The tie bands above are
the derived form of §4.4's third state.)

**The inverse problem, and the retraction it produced.** If the
partition is free, so is the partition *size*: fix the estimand as the
population mean, treat the split into K strata as a variance-reduction
choice, and ask whether there is a derivable finite optimal K. On a
synthetic heterogeneous population the pre-registered
finite-interior-K\* prediction **FAILED**: the mixture arm's optimum sat
at K\* = 1 at every difficulty-signal quality, because V_rr(K) rises
only ~50% across K = 1…24 while the (K/2)·log n tax grows linearly,
while the flat-overhead (WSR-like) arm wanted strata all the way to the
saturation knee (`results_optimal_k.txt`). We wrote that up as a failed
prediction that had yielded a mechanism, and drew a conclusion from it:
that mixture-K\* = 1 *explained* UI-domination.

**Both of those readings were wrong, and a peer-triggered check on the
committed real pools overturned them** (`results_gain.txt`, now
authoritative):

| | synthetic population (rev 1) | ten committed real pools (rev 2) |
|---|---|---|
| mixture K\* | 1, at every signal quality | **K\* = 1 : 4 pools, K\* = 2 : 4 pools, K\* = 4 : 2 pools** |
| stratification gain | +7% to +50% | **1.06× to 4.31×** (variance gain 1.02–5.23×) |
| finite-interior K\* prediction | FAILED | **CONFIRMED on the four K\* = 2 pools** |

The universal "mixture K\* = 1" is **refuted on 6 of 10 real pools**. It
was an artifact of generalizing from one synthetic population whose
gains were an order of magnitude off the real range — real pools
concentrate their mass in near-boundary strata that carry almost no
variance, which the synthetic construction did not reproduce. And the
conclusion built on it is **RETRACTED**: K\* = 1 does not explain
UI-domination, because UI beats the single stream on 6 of 10 real pools.
UI is dominated because **WSR** beats it everywhere measured, not
because single does — which is what §4.4's two-region form said on its
own evidence, and is why the partition survives the retraction intact.
Saturation is not uniform either: llama3.2-3b gets 3.87 of its 4.31×
by K = 2, while qwen2.5-7b (1.51 → 3.33) and gemma2-9b (1.63 → 3.25)
get most of theirs between K = 2 and K = 4. **Scope**, stated with the
result: these are temperature-0 pools, where the designed strata are the
finest honest partition available; finer-K behaviour needs per-prompt
rates at temperature > 0, which is a future collection, and the
well-posedness construction of `scripts/derive_optimal_k.py` is retained
as such with its superseded-in-part conclusion marked.

### 4.8 Export: two out-of-family domains, both frozen, both scored

Everything above was derived and verified *inside* the §3 testbed —
pools remixed from JSON, code and MBPP outcomes. A design rule that only
works where it was built is not a design rule. So the boundary was
carried into two domains it was not built for, each frozen in its own
commit **before** any certification ran, and each scored with the same
instrument. One produced a miss and one produced the first prospective
confirmation of the constants that miss produced. Both are reported at
the same length.

#### 4.8.1 Safety: the boundary's first export, and a scored miss

The domain is **StrongREJECT harmful-compliance** on eight small local
models: 313 prompts, the corpus's own six published **category** strata,
a deterministic refusal-string proxy grader, K = 6 blocks, margin
m = 0.045, τ = p\* − m, direction `rejects_le` on every pool
(`results_safety.txt`, checksum `a369e454bc5450fd`).

**The mandatory non-claim, stated adjacent to the table because that is
where it is needed.** Every per-model number below is a **pool
parameter** — the pooled compliance rate p\* and the category
heterogeneity ratio R of one temperature-0 snapshot under one proxy
grader — in exactly the sense §3.2's p\* is a pool parameter. They are
**not safety rankings**, not a claim about any model's safety, and not
comparable across models as such. The grader's own label noise is
measured and disclosed below, and it is large.

This is the **mild** heterogeneity regime — five ratios in 1.16–5.40
with one outlier at 17.0 — and the reason is structural: p\* ranges
0.019–0.857 *across models* while categories within a model move much
less, so **between-model variance dominates between-stratum variance**
and stratification buys little. Two pools (llama3-8b at p\* = 0.019,
gemma2-9b at 0.036) fall in the boundary regime where τ < 0 with
exact-zero strata; they are declared unscorable in the freeze and are
not scored.

**Frozen at commit 8aa3e7e**, before any certification, using the
machinery unchanged — `single_fourterm`, `wsr_crossing` with its K = 4
envelope, `v_kelly_block` generalized to K = 6 (64 atoms):

| pool | p\* | R | τ | frozen n_s / n_wsr | frozen call | measured S / UI / WSR | measured |
|---|---|---|---|---|---|---|---|
| mistral-7b | 0.857 | 1.16 | 0.812 | 764 / 844 | **SINGLE** | 762 / 2,808 / **678** | WSR — **MISS** |
| qwen2-7b | 0.107 | 5.40 | 0.062 | 336 / 362 | **SINGLE** | **354** / 1,356 / 411 | single — HIT |
| phi3.5-latest | 0.531 | 1.68 | 0.486 | 1,244 / 1,289 | TIE | 1,194 / 4,860 / **939** | WSR (unscored) |
| llama3.1-8b | 0.528 | 1.94 | 0.483 | 1,256 / 1,267 | TIE | 1,227 / 4,872 / **1,062** | WSR (unscored) |
| llama3.2-3b | 0.457 | 2.82 | 0.412 | 1,244 / 1,205 | TIE | 1,293 / 4,704 / **885** | WSR (unscored) |
| qwen2.5-7b | 0.160 | 17.00 | 0.115 | 572 / 560 | TIE | 567 / 2,112 / 513 | TIE — confirmed |

WSR outright *nowhere* in the freeze; two resolving calls, and 2 of 2
flip under a wrong-theory single arm, so the set discriminates rather
than being trivially satisfiable. Measurement was three CRN-paired arms
on the real outcomes, 150 reps/arm, n_max = 12,000, the v2c
Harrell-Davis paired bootstrap of §4.3.

**The map splits cleanly, and the split is the finding.**

- **The single-arm predictor ports.** Measured single medians sit within
  ~5% of `single_fourterm` on 6 of 6 pools (+0.3%, −5.1%, +4.2%, +2.4%,
  −3.8%, +0.9%). The derived side of the boundary survives the domain
  change intact.
- **The reused WSR envelope does not.** WSR certifies **19–37% faster
  than predicted** on the four mid/high-p\* pools, so WSR is the faster
  arm on 4 of 6 — single only on the lowest-p\* pool.
- **P1 FAILS: 1 of 2 resolving HITs.** qwen2-7b HIT; **mistral-7b MISS**
  — predicted single, WSR won. Reported, not tuned. It is ledger row 34
  (§6.3).
- **P2 PASSES**: UI is outright fastest at 0 of 6, minimum UI-to-faster-arm
  median gap 945 against a 24-sample poll period.
- **P3 PASSES**: wrong-direction (SAFE) certifications 4 of 2,700
  = 0.0015 ≤ α.

So the boundary's *structure* and its *derived* side both export; the
one thing that does not is a **fitted constant** — the WSR overhead
envelope, calibrated at K = 4 and reused at K = 6. §5.5 takes that
localization apart on three designed grids and finds the envelope's real
arguments; the short version is that block size carried the magnitude,
and p\* together with the decision direction carried the resolution, and
that a direction- and p\*-matched envelope reconstructs the call **4 of
5** — a **post-hoc diagnostic, labelled as one throughout**, using
constants fitted long after the prediction was frozen. **The miss stands
as scored**, three grids later.

**Label noise, disclosed at the strength it was measured**
(`results_safety_noise.txt`, checksum `923a301bde114ced`). The
refusal-string grader was checked against a gemma2:9b judge on a
60-prompt llama3.2:3b regeneration: they **disagree on 26 of 60
(43.3%)**, and the disagreement is one-directional — of the grader's 28
"complied" calls the judge reads **26 as refusals**, with **0** real
compliances missed. That is a head-prefix-versus-whole-response
construct gap. It is disclosed exactly as §3.3 discloses the temp-0 flip
rate, and it does two things: it caps how well these labels track true
harmful compliance — which is why p\* here is a *pool-graded parameter*
and never a safety measurement — and it does **not** enter the α
guarantee, which is exact given the binary labels. The design-selection
verdict is invariant to what the labels mean: which arm crosses first
depends on the label stream, not on its interpretation. No raw
generations for harmful prompts are stored (§9).

#### 4.8.2 Risk-limiting audits: the first prospective test of the direction-matched constants

A risk-limiting election audit is the same object this paper has been
certifying throughout — an anytime-valid **one-sided** test that a rate
lies on one side of a threshold, stopped when the evidence crosses
log(1/α), with counties where we have had prompt families. That field
already owns the machinery: SHANGRLA (Stark 2020), betting and ALPHA
supermartingales, and the Spertus–Sridhar–Stark union-intersection
construction this repo has shipped as `StratifiedUICS` since the
audit-mandated SOTA comparison (§4.1.1). **Non-claim, mandatory and
repeated in the artifact: nothing here improves SHANGRLA, BRAVO, ALPHA
or UI-TS, and no procedure here is proposed for use in a real
election.** Public county totals fix **pool parameters only**. The
contribution is *to that field's design-selection question* — which
e-process family certifies fastest, decidable before the first ballot is
pulled — and what the domain gives back is a sample unit that costs
human labour (`results_rla.txt`, checksum `1eefa5b579a1b395`).

**Pool.** Georgia's 2020 presidential contest, from approximate-official
certified totals: twelve county strata plus one aggregate remainder row,
size-proportional weights — so the estimand is the population mean and
the F14 reformulation that licenses unequal weights inside the UI
construction applies verbatim. **p\* = 0.501193, margin 0.239%,
R = 3.22, N = 4,935,487** two-candidate ballots, τ = 0.5, direction
`rejects_le`. Ballots are drawn uniformly statewide and all three arms
consume the *identical* ballot sequence.

**Frozen at commit 5b831fb**, before any run. The WSR constants are
taken from `results_wsr_pdir.txt`'s (K = 6, p\* = 0.50, UNSAFE) cell —
the nearest measured cell in **all three** arguments the envelope is now
known to take — which makes this the **first prospective test of those
constants**, their 4-of-5 safety recovery having been a labelled
post-hoc diagnostic:

| cell | α | frozen | measured S / UI / WSR | verdict |
|---|---|---|---|---|
| GA-official, m = 0.239% | 0.05, 0.10 | SINGLE | *predicted only* (3.2M ballots/rep is three orders past the simulation budget) | unscored |
| GA-2pct, m = 2% | 0.05 | TIE | 35,280 / 150,000+ / 38,376 | TIE — confirmed |
| GA-5pct, m = 5% | 0.05 | **WSR** | 4,914 / 12,000+ / **4,032** | WSR — **HIT** |
| GA-5pct, m = 5% | 0.10 | **WSR** | 3,843 / 12,000+ / 3,609 | TIE — unconfirmed |

`+` marks a censored median: that arm did not certify within n_max in
most reps, so its true cost is larger. Two resolving calls among the
simulated cells, 2 of 2 flip under a wrong-theory single arm
(d ∈ {0, 2} against the true d = 1).

- **P1 PASSES, 1 of 1 HIT.** The design call moves *along the margin
  axis* — single at the real margin, tie at 2%, WSR at 5% — and that
  ordering is the falsifiable content. The 5%/α = 0.10 cell measures a
  TIE: **unconfirmed, not a miss**, and counted as neither.
- **P2 PASSES and then some.** The UI arm never certifies at all inside
  n_max on any cell (censored at 150,000 / 12,000 ballots). Thirteen
  nuisance rates is an overhead no audit budget absorbs.
- **P3 is the risk limit in its own terms**, run on a null pool whose
  county shares are shifted so p\* = 0.5 exactly — a reported outcome
  that is genuinely a tie, the worst case a risk limit must survive:
  **1 of 450 audits ever certifies "the winner leads" = 0.0022 ≤ 0.05**.
  Wrong-direction certifications on the true-outcome pools are each
  inside their own α (1/450, 14/450, 29/450 at α = 0.10).
- **Both predictors are now honest in both signs.** The single arm errs
  **0.0% / −2.6% / +7.1%** — the exact absorption recursion run at the
  arm's own check schedule predicted 35,280 ballots at a 2% margin and
  the measurement returned 35,280. The (K, p\*, direction)-matched WSR
  envelope errs **−11.6% / +9.8% / +5.0%**: a band with *both* signs,
  no longer the one-sided +19–37% over-prediction the K = 4 constants
  produced in §4.8.1.

**The payoff, denominated in hand-counted ballots.**

| cell | α | best arm | ballots | worst arm | saved | fixed-n at equal power | sequential premium |
|---|---|---|---|---|---|---|---|
| GA-2pct | 0.05 | single | 35,280 | 38,376 | 3,096 (1.09×) | 39,417 | **−4,137 (0.90×)** |
| GA-5pct | 0.05 | WSR | 4,032 | 4,914 | 882 (1.22×) | 3,954 | +78 (1.02×) |
| GA-5pct | 0.10 | WSR | 3,609 | 3,843 | 234 (1.06×) | 3,213 | +396 (1.12×) |

Best and worst are taken over arms that actually certify (≥ 90% of
reps); an arm that never finishes is not a cheap audit, which is why UI
is excluded where it is — against it the design choice is worth ≥ 3–4×
on every cell. The fixed-n column is a one-sided binomial audit at the
best arm's own measured power, and it buys **no** anytime validity: no
peeking, no early stopping, no escalation. The premium for validity is
therefore within ±12%, and at the 2% margin it is *negative* — early
stopping more than repays the mixture overhead.

**And the real margin says something the synthetic cells cannot.** At
Georgia's actual 0.239% margin every design costs a **majority of the
ballots cast**: 3,191,031 single (64.7% of the state) and 3,397,475 WSR
(68.8%) at α = 0.05, against 4,935,487 cast — and even a fixed-n audit
at 99% power needs 2,768,762 (56.1%). No ballot-polling audit is cheaper
than counting them all, **which is exactly what Georgia did** (a full
statewide hand recount). The margin axis of the design map reproduces
that decision without being told about it. That is a retrodiction on one
contest, not a validation of the map; we report it because the map could
have said otherwise and did not.

**Scope, all disclosed in-artifact.** The GA-official rows are
**predicted-only and unscored**, and use the four-term closed form,
which is validated against the exact recursion at both *simulated*
margins (−1.7% to −3.4%, the schedule term). The 2% and 5% cells are
**synthetic-margin pools** — one common additive shift of every county
share, moving R from 3.22 to 3.15 / 3.04 — disclosed as constructed, not
as elections. The single/UI check period D is a compute choice
(D·KL ≤ 0.06 nats, ≤ 1.0% of the crossing and below the tie band) and is
carried in the *predictor* too, so the powered model and the executed
replay share one stopping rule (`severity_sim` rev 3 rule (c)). R is
inert for the single and WSR arms under uniform statewide draws,
licensed **only** by the R null of §5.5 — which is a failure to detect
over R ∈ [1, 30], never a proof of R-independence.

Porting the certifier into thirteen unequal strata also broke it, in a
way no configuration inside the testbed had reached. That defect is
§6.2's ninth instance.

---

## 5. The calibrated expansion

### 5.1 The form

For an e-process certification method stopping when its statistic
crosses 1/α, the median sample count n at margin |p\* − τ| satisfies

    n · V  ≈  log(1/α) + (d/2)·log n + c                    (†)

where **V** is the method's information rate (its expected log-growth
per sample under the truth against its least-favorable null), **d** is
the effective number of parameters the statistic must learn — each
costing ~½·log n of growth — and **c** is a method constant (prior mass,
discreteness, overshoot). The rate is method-specific and had to be
defined correctly before anything fit: pooled KL(p\*, τ) for the single
stream; the *allocation-constrained* boundary value
min_{w·m = τ} mean_k KL(p_k ‖ m_k) for UI with round-robin (not the
max-min game value, which presumes optimal allocation); and the exact
per-sample optimal Kelly growth over the 16-atom block distribution for
WSR (not the Cramér rate, which is a false-alarm exponent, not an
e-process growth ceiling). Both of those rate definitions were corrected
against already-committed data before freezing — a first UI pass using
the max-min game value fit at d = 12, R² = 0.24, and two WSR passes
(Gaussian block approximation, then the Cramér rate) produced *negative*
slopes — and that iteration is disclosed rather than hidden, because a
critic should ask. The rate definitions and the predictions were then
**frozen** in `scripts/fit_overhead_law.py` before the definitive τ-sweep
grid completed, making that grid a genuine out-of-sample test.

**We did not discover (†).** For d = 1 it is a fifty-year-old theorem:
Pollak & Siegmund (1975), Woodroofe (1982, nonlinear renewal theory),
with boundary shape from Schwarz (1962) and Lai (1988), matching lower
bound Pollak (1978), and the (d/2)·log n term from
Krichevsky–Trofimov / Rissanen / Clarke–Barron mixture regret. The
contribution is calibration on real LLM evaluation data — and, in §5.3,
one further term of the expansion together with the boundary it makes
computable — plus the observation that the modern e-value literature
under-cites this second-order term. That citation gap *is* the honest
positioning.

### 5.2 The strongest quantitative result: zero-fit single-stream

With d = 1 and c in closed form — c = −½·log(2π p\*q\*) − ρ/2, with ρ
the stratification variance ratio — and **nothing fitted to crossing
times**, (†) reproduces the definitive grid medians for the
single-stream arm within **−2.6%…+6.8%** (`audit/out_law_accounting.txt`,
independently re-verified in audit round 2; original claim −3%…+7%):

| pool | τ | measured median | zero-fit prediction | error |
|---|---|---|---|---|
| gpt-4o-mini | 0.145 | 508 | 495 | −2.6% |
| gpt-4o-mini | 0.150 | 616 | 619 | +0.4% |
| gpt-4o-mini | 0.160 | 1024 | 1007 | −1.7% |
| gpt-4o-mini | 0.170 | 1896 | 1873 | −1.2% |
| gpt-4o-mini | 0.175 | 2740 | 2816 | +2.8% |
| gpt-4.1-nano | 0.150 | 254 | 256 | +0.9% |
| gpt-4.1-nano | 0.130 | 452 | 483 | +6.8% |
| gpt-4.1-nano | 0.120 | 696 | 741 | +6.5% |
| gpt-4.1-nano | 0.110 | 1284 | 1317 | +2.6% |
| gpt-4.1-nano | 0.100 | 2844 | 2910 | +2.3% |

(All ten grid points with ≥ 90% certification; the two points below that
filter are excluded and their exclusion is printed in the audit output.)

And the fitted single-stream dimension brackets the theoretical d = 1 on
**every pool we have fitted** — six fits across three vendor lineages
and three task families: 0.79 / 1.01 (OpenAI JSON,
`results_overhead_fit.txt`), 0.92 / 0.81 (local JSON,
`results_local_law.txt`), 0.72 / 0.90 (MBPP, `results_mbpp_law.txt`).

**Scope, stated plainly**: "zero-fit" applies to the single-stream arm
only. Audit round 2 established that the UI arm's comparable accuracy
requires **one fitted constant c per model** (−1.56 / +1.91); with
c = 0 its errors are ±12%. The honest phrasing for UI is "d from the
rule, c fitted once per model."

**And one relation between this table and §5.3, since the two are easy
to confuse.** The c used here is the three-term closed form
−½·log(2π p\*q\*) − ρ/2, with ρ the stratification variance ratio: the
protocol correction for round-robin streams, not a renewal constant.
§5.3's c_ren(p\*, τ, α, d, n0) is a different object on a different
accounting, and the correction to its value (§5.3) leaves this table
untouched — every number above is recomputed from the same closed form
it was published with (`audit/out_law_accounting.txt`).

### 5.3 The fourth term, derived

**First, the failure that measured it.** A power-checked 17-point margin
sweep (design accepted at discrimination 0.65 / 0.00 / 0.04 before
freezing; `results_margin_sweep.txt`) tested the strict three-term form
by differencing out c within rate groups. It **failed as frozen,
twice**. v1 failed P2 by 0.011 nats and P4 outright, and its post-hoc
diagnosis found our own protocol bug — the deployed replay stopped
two-sided while the accepted power model was one-sided — so v2 was
re-pre-registered with the mismatch fixed and the power stage re-run and
re-accepted before the freeze. v2 then failed **again**, by 0.008 nats
(mean D = −0.258 against |mean| ≤ 0.25), with P1 passing at 12 of 16
pairs and P4 passing honestly (0 wrong certifications in 8,200 reps).
No v3: widening bands until a pass is the pattern this project's audits
exist to prevent.

What the twice-failed sweep *measured* is two deviations, not one. The
differenced statistic sits at mean **−0.258 nats**; the **raw** residual
against the c = 0 closed form sits at mean **−1.144 nats** — all 17
points negative, t = −13.9 — and it is structured in **p\***, not τ
(group means −0.86 to −1.51, slope ≈ −1.4 nats per unit p\*). That
p\*-dependence is the signature Woodroofe's overshoot constants predict,
since they depend on the increment distribution and p\* governs it. The
sweep also surfaced a protocol constant the expansion hides: because the
Beta-mixture e-value is exchangeable, round-robin streams
(variance-reduced counts) cross **~20% slower** than iid streams at the
same pooled rate (median 1024 vs 844 at one matched point) — c depends
on the sampling protocol, not just on (p\*, τ).

**Then the derivation.** Stirling on the Beta-mixture e-value gives the
identity with an **explicit remainder interval** — no unspecified tail —

    log E_n = n·KL(p̂, τ) − ½·log n + ½·log(2π p̂ q̂) + r_n,
    r_n = [1/p̂ + 1/(1−p̂) − 13]/(12 n) + 1/(2 n²) + O(n⁻³),

so the predicted crossing residual is **−½·log(2π p\*q\*)** — a term
with *nothing fitted*. The proof, the interval and the scope live in
[paper/BOUNDARY_THEOREM.md](BOUNDARY_THEOREM.md); two corrections it
carries belong here because they were ours. The coefficient is **−13,
not −1** (the (n+1) shift in Γ(2+n) contributes −12/(12n)), verified
exactly at n = 10⁴; and an earlier version of the proof asserted a
residual of O(log n / n) on a line whose true residual is O(log n) — the
displayed equation survived only because a −log n − 1 cancels
downstream. An external audit (gpt-5.6-sol lineage) found both; we
verified both here before adopting them, and the repaired proof displays
the cancellation instead of hiding it in a wrong order estimate.

Scored on the frozen 17-point grid (`results_overshoot.txt`, checksum
0b7fa43558e3530f):

| check | result | criterion | verdict |
|---|---|---|---|
| C1 identity **rev 1** | max grid error 0.00374 compared against a threshold built as (the displayed bound, evaluated at a *different* grid point) × 1.5 | the multiplier was not from theory | **DEFECTIVE — passed while the error exceeded the displayed bound** |
| C1 identity **rev 2** | every grid point's r_n tested pointwise against the rigorous interval of BOUNDARY_THEOREM §2 | 0 of 12 violations, float64 accumulation ≤ 3×10⁻¹¹ (peer's 13,579-point high-precision grid: zero failures) | PASS |
| C2 slope removal | per-point residual slope **−1.398 → −0.255** nats per unit p\*; per-point correlation **−0.616 → −0.133** | \|slope\| ≤ 0.35 and \|corr\| ≤ 0.45 | PASS |
| C3 remaining offset | 8,000-rep MC **−1.105**, dispersion std 0.286 | ≤ 0.25 | **FAILED** — and the value was also wrong: exact **−1.1700824** |
| C4 decomposition | selection +0.681, overshoot +0.229, median-vs-mean −0.645, c_Laplace −0.006 → −1.103 vs measured −1.228 | abs difference ≤ 0.2 | **SUPERSEDED** — passed on two cancelling errors |

C2 removes **82% of the p\*-dependence** with zero fitted parameters.
Units note, because an earlier commit mixed them and was corrected: the
−1.398 → −0.255 slope and the −0.616 → −0.133 correlation are both
**per-point** statistics on the 17-point grid; the separate value −0.900
is the correlation on the **6 group means** and is never mixed with the
per-point numbers (the artifact was regenerated on one unit after the
mix was caught).

**C1 is a check that failed by passing.** Rev 1 compared the grid error
against a number that wore the Stirling bound's name but was a tolerance
multiplier applied to that bound at the wrong grid point — and the
actual error *exceeded* the displayed bound while the check printed
PASS. The artifact-identity rule R4 was satisfied, because a verdict
line was printed; what was never computed was the relation between the
threshold and the theory it named. That is now **gate rule R4b** (§6.2).
Rev 2 tests the rigorous interval pointwise and passes cleanly. The
expansion was always right; the check was not testing it.

**C3 and C4 are the correction that matters, and it goes the
uncomfortable way.** The residual after the derived term is
c_ren(p\*, τ, α, d, n0). We previously reported it as a measured scalar
−1.105 from an 8,000-rep Monte Carlo whose own dispersion criterion
FAILED, and we reported a three-piece decomposition (selection,
discrete-check overshoot, median-versus-mean) that closed to within
0.125 nats. The exact value, computed by a finite absorption recursion
over the killed chain and verified to 7 decimals against an independent
transfer operator, is **−1.1700824** (`results_cren_exact.txt`): the
Monte-Carlo estimate was **noise-high by 0.065 nats**. That single
correction dissolves the decomposition, because its closure had been two
noise errors cancelling — the selection term was independently
re-measured at 0.6387 ± 0.0034 against the repo's +0.681 (z = −12.6),
and with the corrected selection the three pieces sum to ≈ −1.06 against
a target of −1.170. **C4 is superseded and does not sum exactly**; we
record it as a diagnostic that was approximate all along rather than as
a result that closed.

What replaces it is stronger. c_ren is **exactly computable for any
(p\*, τ, α, d, n0) with zero fit**, so the four-term expansion is fully
predictive in practice — and it is demonstrably *not* a universal
constant: −1.1449169 at p\* = 0.150 and −1.1866026 at p\* = 0.300 (the
residual C2 slope was this dependence), −1.2985462 at check period
d = 1, −1.1443421 at n0 = 40. The median convention matters at the
0.008-nat level and is stated: crossings occur only on multiples of d,
so we use the **discrete** median (−1.1700824) rather than the
interpolated one (−1.1785).

**What is open, named rather than fudged.** A scalar
elementary/special-function reduction of c_ren. The obstruction is a
time-inhomogeneous, **noncommuting** killed kernel — the
continuation-then-draw operators do not commute across check times, so
the product does not collapse to one eigenvalue. Its pieces are in
different states: the median-versus-mean gap is closed (Cornish-Fisher);
selection has an exact closed *form* E[N·D(p̂‖p\*)] whose first-order
term is exactly zero by Wald's identity (E[M_N] = 0, measured
−0.01 ± 0.05, `results_selection.txt`); the overshoot has a closed
**asymptotic** constant ρ_d = E[H_d²]/(2E[H_d]) — the first strict
ascending ladder height of the d-sample block skeleton, by a Spitzer
identity, with ρ_1 = 0.0942 and ρ_4 = 0.1703 re-verified here two ways
to < 0.0003 (`results_overshoot_closed.txt`). The ratio
ρ_4/ρ_1 = 1.81 is itself the proof that the constant carries the check
period, which had previously been a conjecture — and it retires an
earlier diagnosis of ours that blamed a lattice span. The single
remaining obstruction is finite-boundary behaviour: at L = log 20 ≈ 3.0
the measured overshoot is 0.228 against the asymptotic 0.170, a real gap
shared by selection and overshoot, whose right frame is Kim & Woodroofe
nonlinear renewal with slowly-changing perturbations (math/0611695). We
keep the asymptotic and finite-L numbers distinct and fit neither.

**The blind test.** A term derived to explain one dataset's residual
structure is worth little until it makes a different kind of prediction
on different data. The pre-committed test was the boundary anchor gate:
the four-term expansion had to make anchor A1 (MBPP-like, R ≈ 2.6) pass
where the fitted constants of pass 3 had failed by 8%. It does, and
across the whole envelope — derived single **832** at the freeze
(**820** on regeneration under the exact recursion) versus WSR **835**
(central), **908** and **945** at the two WSR envelope corners, so the
winner relation matches the measured MBPP cell (single 960 vs WSR 1052
at margin 0.042, single by 9%, `results_mbpp_law.txt`) at every corner
of the band rather than at one lucky point — and it still does after the
c_ren correction, which is the propagation check, not a re-scoring.

**And its caveat, stated with it.** Both arms' *absolute* medians come
out ~10–20% low (derived A1 single 820–832 versus measured 960); WSR still
lacks its own o(1) treatment, and the symmetric derivation is open. The
boundary's **winner** predictions are what §4.3 verified; its absolute-n
predictions carry this caveat.

### 5.4 The dimension rule: status honest

Our pre-registered dimension window for the UI statistic **MISSED**
(predicted d ∈ [1.5, 3.5]; measured 3.37 / 4.04 — the dimension is
≈ K, the full parameter count, not "≈ #active strata"). An adversarial
referee then proposed the sharper rule **d = K + #boundary-strata**:
strata with rate exactly 0 or 1 cost a full log n each, because the
Beta(1,1) marginal of an all-success stratum is 1/(n+1). Classically
this is the boundary/singular coefficient of Xie–Barron (1997) and
Watanabe's RLCT. A live adjudication on frozen code pools favored the
referee's rule over our window (d = 6.50 / 5.56 / 6.76 vs predicted
6 / 6 / 7; our [3,5] failed on every model).

**Audit round 2 downgraded this, and we report the downgrade**
(`results_adjudication.txt`, an artifact promoted from the audit's own
reproduction script):

- Under our own declared ≤ 0.75-nat criterion the score is **2-for-3**,
  not 3-for-3 (nano-code at d = 6 gives 0.81; d = 5 passes).
- Bootstrap CIs over grid points are wide: [4.81, 7.96], [3.19, 10.57],
  [3.09, 9.55] — two of the three contain the window the adjudication
  rejected.
- A swap test shows the rule and a **constant d ≡ 6** are nearly
  indistinguishable (sum |d_fit − d_pred| = 1.18 vs 1.71). The entire
  discriminating content of the test is "**d is around 6, not around
  4**".
- Two supporting numbers were **withdrawn** as non-reproducible: a
  "path-measured 4.99" (independent measurement gives 4.06–4.38) and
  "measured E[LLR]/(nV) → 1.002" (measured 0.93–0.99 at n = 16,000).
  Neither had a surviving script.
- Fitted d drifts with τ *inside* a single pool (6.23 → 5.04 on nano
  JSON), which no statistic-level dimension can do.

**Where the rule does make a sharp prediction, it passed out of
family.** On the local pools no stratum sits at an exact edge, so the
rule predicts d = K + 0 = 4; measured **4.22** (llama) and **4.31**
(qwen), both within 0.35, max residuals 0.13 / 0.18 nats
(`results_local_law.txt`). On MBPP the same prediction is
**unidentifiable by censoring** (§4.1.3) and we decline to score it.
A within-lineage test of the boundary premium was sharper and the rule
**weakened further**: the premium came out at +0.08 where the rule
predicts +1, and a formula-pass obtained via a censored fit is disclosed
as hollow (`results_lineage_d.txt`, 2-of-4 as frozen). Net status: a
coarse regularity that survives where it is testable, not a law.

**One further caution, which §5.5 turns into a measurement.** Every
number in this subsection is a *fitted* d, and a fitted d only means
something if the statistic actually admits an expansion of the form (†).
For the UI arm we have no proof that it does, only the empirical
regularity above. §5.5 exhibits the failure mode concretely on a
different arm: a statistic whose overhead genuinely diverges will still
return a well-behaved fitted "dimension", and that number will simply
drift with the horizon. Read the drift of fitted d with τ inside a
single pool (6.23 → 5.04) with that possibility in view.

### 5.5 The WSR anti-result, and what a frozen test of it settled

Our early reading of WSR as having a *flat* overhead ("zero-dimensional,
~1.7-nat constant tax") was a **finite-window artifact**. The referee's
analysis and the MBPP grid agree: the popular predictable schedule
λ ∝ 1/√(t log t) forfeits the Kelly growth rate entirely
(achieved/optimal = 0.73 → 0.29 and falling), so the overhead grows,
and at MBPP's longer crossing horizons the fitted d is **1.8–2.3**
(`results_mbpp_law.txt`). The law's WSR line is therefore valid only
where crossings happen within a few hundred samples. This is worth
publishing as a caution about a widely-used schedule: WSR's practical
advantage is correctly stated as "a **bounded rate sacrifice** beats a
(K + #boundary)/2 · log n **additive** penalty when log n ≈ 6–8", and
that inequality reverses as the horizon grows. It is also why the
boundary of §4.2 gives WSR a *two-regime* envelope (a short-horizon
constant and a long-horizon growing term) rather than a single constant.

**A candidate explanation arrived from outside, and it is still a
hypothesis.** An external lineage derived that the stock predictable
schedule admits **no** fixed (d, c) at all: the true growth is
n·V ~ A·log n·(log log n)², so n·V/log n diverges and any fitted
"dimension" is a horizon-dependent artifact that must drift upward —
which would reproduce the 1.8–2.3 above from a constant measured
independently of those fits. We froze a test of it on the **shipped**
classes rather than adopting it (`results_wsr_expansion.txt`, freeze at
commit 7e80dbe; p = 0.5, K = 4, margins 0.035 → 0.009, crossing medians
2,566 → 67,226):

| clause | prediction | result | verdict |
|---|---|---|---|
| P1 divergence | stock n·V/log n grows monotonically, ≥ 1.5× across the ladder | **1.23×**, non-monotone at the deep end | **FAILED** |
| P2 form | n·V/(log n·(log log n)²) flat within ±10%, deepest rung excluded | max deviation from the mean 6.1% (total spread 11.9%) | PASS |
| P3 floored-arm contrast | — | n·V/log n drift **1.2%** floored vs **22.9%** stock | an expansion exists on the floored arm |

(P2's criterion was ambiguous as first written — "flat within ±10%"
admits both a max-deviation-from-mean and a total-spread reading, which
disagree here, 6.1% versus 11.9%. It was disambiguated to
max-deviation-from-mean and the artifact regenerated, commit eaf6a14.
The first run of this test was also **INVALID and is committed as
such**: it computed block means with numpy boolean addition, so nothing
ever crossed and P3 printed a verdict from two censored constants. v2
adds a crossing-fraction validity guard; see §6.2 instance 6.)

So the honest status is: **the no-expansion claim is a hypothesis, not a
result.** Its functional form is consistent with our ladder; its own
pre-registered divergence criterion failed on the code we actually ship.
The external lineage's supporting 1.80× came from a *reimplementation*
of the schedule that runs 43% off the shipped code at matched settings
and is withdrawn; the coefficient H/16 = 0.2306 was refuted by that
lineage's own measurement, and we report only the measured mean
A = 0.1769 with the peer's 0.1469 alongside. The route of *deriving*
WSR's fourth term is therefore **open and unresolved** — neither derived
nor proven impossible — and §4.2's WSR envelope stays measured.

**A process failure preceded that verdict, and it is the reason for a
new gate rule.** The no-expansion paragraph was absorbed into
`BOUNDARY_THEOREM.md` and `THEORY.md` at commit 805ae03 **while the
frozen test of it was still running**. The test then failed P1. Nothing
about the claim's plausibility excuses the ordering: an external result
absorbed before its own pending test scores is an unchecked relation
between a claim and its evidence, exactly the generator of §6.2. The
absorption was unwound (commit 8d43eb2), the claim downgraded to a
hypothesis everywhere it appeared, and the ordering is now **gate rule
R9**: no absorption while a frozen test of the same result is pending,
and every absorption commit must cite the scored artifact it rests on.

**Where an expansion does exist: the Kelly-floored arm, and how far we
got.** P3 is a within-implementation contrast — identical code, ladder
and seeds, so absolute-level bias cancels — and it says the floored
variant restores the regularity the stock schedule lacks. That made it
the live route to a full boundary theorem, and we chased it
(`results_floor_d.txt`). Three things came back, in order of how much
they cost us:

1. **Our committed d = 1.27 was biased, and not in the direction the
   audit predicted.** An external audit found a real defect: the τ grid
   places every rung mid-cell at a fixed +0.0005 offset, which is 1.4%
   of the margin at the top rung and 5.3% at the deepest, inducing a
   2.8% → 10.2% bias in the rate V. We reproduced the defect exactly.
   Its **direction** we could not reproduce: correcting it moves d
   *away* from 1, not toward it (grid-corrected d = +1.3614 ± 0.2006 at
   3× reps; the stock arm under the same correction is +4.4969). The
   only arithmetic we found that turns the grid correction into a
   sub-1.27 figure is scoring at a grid point *above* τ (which yields
   +0.9158), and that is invalid: raising τ above the old binding point
   makes τ itself binding and lengthens every crossing time, so n cannot
   be held fixed. We record that as the artifact does — the likely
   provenance of any "exact-τ" d below the committed fit, including the
   externally circulated 1.12 — rather than as a proven attribution.
2. **d = 1 is derivable — on the post-warmup idealization.** Once the
   Kelly floor binds, the plug-in bet is first-order efficient
   (c_reg = |V''(λ\*)|·AVar → 1 across the ladder, 0.9619 … 0.9971), so
   the regular arm costs exactly (1/2)·log T: **d_regular = 1** (the
   derivation's own point value is +1.0354, half-width 0.0844), the
   same as the single stream. The shipped class is that idealization
   plus a warmup: before the floor binds the stock schedule over-bets,
   and the slope attribution charges **+0.5071** to that residual
   against +1.0664 for the regular law, predicting d = 1.5301 for the
   shipped class (attribution sum and direct regression agree to four
   decimals). The plug-in-versus-optimizer gap the audit raised is real,
   exactly computable, and **not load-bearing**: ~0.01 in d.
3. **The shipped class has no fixed d either — only a slower drift.**
   The warmup contribution decays as 1/log t_c, so the literal shipped
   floored arm has a **slowly drifting effective d**, milder than
   stock's but not constant. This is the structural finding, and it
   makes the measurement question moot: **{1, 1.12, 1.27, 1.53} are
   mutually indistinguishable at any feasible rep budget on this
   ladder.**

Both pre-registered windows — P-A for the idealization (d = 1,
[+0.5144, +1.4856]) and P-B for the warmup-corrected derivation
(+1.5301, [+0.9993, +2.0608]) — contain the measurement, so the frozen
adjudication is **UNRESOLVED**. We did not widen the windows and we do
not report a miss as a hit. The final form of the claim is therefore:
*derivable (d = 1) on the post-warmup idealization; drifting on the
literal shipped class; and the experiment that would discriminate the
two does not exist at this budget.*

**What the envelope's arguments actually are: three designed grids.**
§4.8.1's miss localized to one fitted object — the WSR overhead
envelope, calibrated at K = 4 and reused at K = 6 — so we went and
measured it. Three grids, in the order they were run, each a
*measurement* grid rather than a prediction test (the freeze convention
is therefore that the docstring is committed *with* the results; P1–P3
still print PASS/FAIL, and two of the three FAIL). Read together they
replace a fitted constant with a **measured (K, p\*, direction)
surface** on which **R is null** — and one of those three answers is a
negative result that closed a hypothesis this project had carried for
weeks.

*(i) Block size: the constants are linear in K.*
`results_wsr_k.txt` (checksum `f6aea65aa754d0d8`) re-measures the
envelope at K ∈ {2, 4, 6, 8} on one frozen grid — iid Bernoulli pools
(so R = 1), p ∈ {0.20, 0.35, 0.50} × five margins, the **shipped**
`WSRBlockCS` polled every block, common random numbers *across K* (every
K consumes the same underlying Bernoulli stream, regrouped), reps
300/300/300/200/150 tapered and disclosed, 60 of 60 rungs certified
≥ 97%. V is the exact Binomial(K, p)/K block-mean Kelly rate and agrees
with the shipped 2^K enumeration at K = 4 to 1.7e−17.

| K | 2 | 4 | 6 | 8 |
|---|---|---|---|---|
| d | 3.386 | 2.343 | 1.465 | 0.834 |
| c | −6.922 | −5.351 | −3.138 | −1.234 |

The envelope **is** K-dependent and its constants are **linear in K** —
**d_K = 4.1407 − 0.4267·K** (max\|resid\| 0.115, 5% of range) and
**c_K = 0.9638·K − 8.9801** (0.226, 4%) — an **observed regularity, not
derived**, and labelled as such in the artifact. Larger blocks carry a
smaller effective dimension and less overhead at the horizons the
boundary uses. **P2 PASSES** (both reported constants strictly monotone;
the direction was not pre-committed). **P3 PASSES** (0 of 60 rungs
excluded). **P1 FAILS, and was pre-stated to** — with the reason
committed *before* the run: this grid is R = 1 while c_short = 2.3 was
calibrated on extreme-heterogeneity pools, so the failure is the
already-recorded c_short(R) offset and not a K result (measured K = 4
triple 1.521 / 2.809 / −7.395 outside the committed corner band;
committed central envelope worst +27.6% on the K = 4 rungs). A
short-horizon plateau appears at K = 4, 6, 8 but **not** at K = 2 (SSE
cut 9.7% against the 20% criterion), so the pre-registered uniform
selection rule reported the single-regime pair and the two-regime triple
is printed **unscored**.

The independent confirmation is the part that matters: read from the
*envelope* side, the committed K = 4 constants over-predict n_wsr by
**+19.3% to +37.2%** on the four mid/high-p\* safety pools — the same
+19–37% the certification measured, reached by a different route.
Transporting the measured K = 4 → K = 6 *difference* onto the committed
envelope (a function-level transport; additive separability of the
R-offset from K is **asserted, not proved**) cuts that to
[−0.9%, +14.5%]. But it moves mistral-7b only from SINGLE to **TIE**,
never to WSR, and it collapses the qwen2-7b HIT to TIE as well — leaving
the domain with **zero** resolving predictions, which the discrimination
gate would have refused as vacuous. **Block size accounts for most of
the magnitude and none of the resolution.**

*(ii) Heterogeneity: R is refuted as a carrier, and the refutation is
the result.* The honest next clause was a joint c(R, K), so
`results_wsr_rk.txt` (checksum `202b167276d05415`) measured one: a
designed 12-cell grid, K ∈ {2, 4, 6} × R ∈ {1, 3, 10, 30}, at
p\* ∈ {0.20, 0.35} × four margins (96 rungs). Pools are two-level
K-stratum profiles (half the strata at p_lo, half at p_hi, ratio R, mean
exactly p\*); a block is one draw per stratum into the shipped
`WSRBlockCS`. The τ ladder is solved per (p\*, R) at K = 4 to a
**common** median window and then shared by every K — deliberately,
because an effective *local* fit depends on the range it is taken over,
so unequal per-cell n-ranges would masquerade as R-dependence. CRN is
one uniform stream per (p\*, rung, rep) **shared by all twelve (K, R)
arms**, mapped to strata by position mod K, so K and R change the
mapping and the thresholds, never the randomness. 96 of 96 rungs
certified ≥ 0.99. V is the exact per-sample Kelly rate of the block mean
by Poisson-binomial DP convolution in O(K²) — the block mean is a sum of
*independent non-identical* Bernoullis, so the K grid's Binomial form
does not apply — and it matches the shipped 2^K enumeration at K = 4 to
1.4e−17 over the whole K = 4 sub-grid.

| d / c | R = 1 | R = 3 | R = 10 | R = 30 |
|---|---|---|---|---|
| K = 2 | 3.566 / −7.282 | 2.722 / −4.428 | 3.324 / −6.994 | 3.525 / −7.919 |
| K = 4 | 2.084 / −4.174 | 2.319 / −5.052 | 2.194 / −4.923 | 1.990 / −4.326 |
| K = 6 | 1.562 / −3.235 | 1.393 / −2.723 | 1.515 / −3.354 | 1.267 / −2.601 |

**P2 FAILS — and that is the result.** c is **not monotone in R at any
K**, and the entire R = 1 → 30 endpoint change is **−0.637 / −0.152 /
+0.634 nats** at K = 2 / 4 / 6: inconsistent in *sign*, and each at most
**0.37 of its own standard error**. d is likewise non-monotone. The
long-hypothesized **c_short(R) offset** — carried in THEORY.md since
2026-08-15 at ~0.7–1.0 nats, and the very quantity grid (i)'s P1 failure
was pre-attributed to — **is not present over R ∈ [1, 30] on these
profiles.** This is the first time R was swept at fixed p\* on a
designed grid rather than inferred across pools, and we record it as a
**scored P2 FAIL that is itself the finding**, not as a disappointment.
The fitted surface says it quantitatively:
**d = 4.1707 − 0.4625·K − 0.0190·log R** and
**c = −8.2446 + 0.9194·K − 0.1081·log R**, whose log R terms move d by
−0.065 (3.5% of what K moves it) and c by −0.368 (10.0%) against
max\|resid\| 0.503 (22% of range) and 2.096 (39%) — so the
pre-registered rule **rejects log R as a carrier**, and the reason is
that the R *effect* is null, not that some other R-carrier is wanted.
The full 12-cell residual table is printed and nothing else was fitted
to force it. **P1 FAILS on the joint clause but 2 of its 3 sub-checks
pass**: the R = 1 column reproduces grid (i) inside the pre-registered
±0.25 / ±0.6 at K = 2 (d +0.180, c −0.360) and K = 6 (+0.097, −0.097)
and misses on both at K = 4 (−0.259, +1.177) — where post-hoc arithmetic
(labelled; it scores nothing) shows the two independently measured
envelopes agree at **function** level within 0.494 / 0.446 / 0.335 nats
across each cell's measured range, about **7% in n**. That is the d↔c
trade-off inside a two-parameter local fit — that cell's own OLS
standard errors are 0.239 in d and 0.886 in c — not an envelope
disagreement. **P3 PASSES** (0 of 96 excluded). And the K coefficients
independently reproduce grid (i)'s linear laws (−0.4625 against −0.4267
in d; +0.9194 against +0.9638 in c) on an entirely different profile
family. Plugged back into the safety freeze at (K = 6, each pool's own
R), the joint envelope resolves three pools instead of two and matches
the measured winners **1 of 2 — exactly the frozen rate**.

*(iii) Direction and p\*: the axis nobody had varied.* The R null left
p\* as the open candidate, but p\* was entangled with something the whole
arc had held fixed without ever saying so. **Every envelope in this
project — grid (i), grid (ii), and the original K = 4 calibration —
certifies in the UNSAFE direction** (p > τ, the CS *lower* bound
clearing τ); and in the safety pools a high p\* and the direction that
favours a high block mean arrive together. `results_wsr_pdir.txt`
(checksum `eb8f5f8d7eb4efad`) crosses the two axes at fixed K = 6,
R = 1.2: p\* ∈ {0.20, 0.50, 0.80} × direction ∈ {UNSAFE, SAFE}, five
margins per cell (30 rungs), the two **shipped** tests (`lo > τ` and
`hi ≤ τ`) on the shipped `WSRBlockCS`. CRN is tight enough that the two
direction arms of a rung consume the *identical* Bernoulli sequence
block for block — only τ and which bound is read differ. 30 of 30 rungs
certified 1.00.

The Kelly rate itself is **provably direction-asymmetric**, and the
artifact prints that *before* simulating anything: at δ = 0.09,
V_SAFE/V_UNSAFE is **0.506** at p\* = 0.20 and **1.994** at p\* = 0.80,
narrowing to 0.904 / 1.102 at δ = 0.02 (the Gaussian limit). At
p\* = 0.50 it is **exactly 1**: the two-level profile has
p_lo + p_hi = 2p\* = 1, so the rate multiset is closed under p → 1 − p,
the block-mean law is symmetric about 0.5, and V_UNSAFE(0.5 − δ) =
V_SAFE(0.5 + δ) identically (checked to 2.1e−17). Both branches are
validated against shipped code — UNSAFE directly to 1.2e−17, SAFE
through the exact complement identity V_SAFE(rates, τ) =
V_UNSAFE(1 − rates, 1 − τ) to 3.5e−17. Because O(n) := n·V − log(1/α)
divides by each direction's **own** V, this entire analytic asymmetry is
absorbed *before* the fit: **whatever direction effect survives in
(d, c) belongs to the confidence sequence, not to the information
rate.** Something survives.

| d / c | p\* = 0.20 | p\* = 0.50 | p\* = 0.80 |
|---|---|---|---|
| UNSAFE | 1.142 / −1.693 | 1.257 / −2.773 | 0.152 / +0.582 |
| SAFE | 0.250 / +0.458 | 1.518 / −3.855 | 1.043 / −0.966 |

**P2 was the discrimination, and only the comparison was pre-committed —
no winner.** On the scored metric, raw (d, c): the direction axis spans
max \|Δd\| 0.892 and \|Δc\| 2.151; the p\* axis 1.269 and 4.314. Both
constants name **p\***, by 1.42× in d and 2.01× in c — **P2 verdict
p\***. Reported but not scored, because raw gaps are not scale-free and
the two constants trade off: in mean-OLS-SE units the ordering holds
(direction 2.90/1.82 SE against p\* 4.13/3.66), but at **function**
level over the common window the ordering **reverses** to direction
2.612 nats against p\* 2.349 — a 1.11× margin, which is a wash. The
scale that settles the reading is the axis this same instrument already
called null: **the refuted R sweep, measured the identical function-level
way, spans 0.658 nats**, so *both* new axes are 3.6–4.0× the null one.
The honest verdict is therefore not "p\*, not direction" but **both,
comparably — the overhead envelope is direction-dependent, and every
constant in this project was fitted on one side of it.** **P1 FAILS**
against grid (ii)'s (K = 6, R = 1) cell (d 1.142 against 1.562; c −1.693
against −3.235) on a tolerance already widened in advance to ±0.35/±0.9
with the reason stated — that cell is R = 1 against this grid's 1.2
*and* pools p\* ∈ {0.20, 0.35} against this cell's 0.20 alone, two
design differences — and the same labelled function-level arithmetic
puts the two envelopes within 0.373 nats (~5% in n). Read with P2 the
failure is not an anomaly: **a p\*-pooled anchor cannot equal a
single-p\* cell once p\* is shown to move the constants.** **P3 PASSES**
(0 of 30 excluded).

*What the reconstruction is worth, and what it is not.* Plugged back
into the safety freeze with direction- and p\*-matched constants, the
envelope resolves **all six** pools and matches the measured winners
**4 of 5**, against 1 of 2 for the frozen call and 1 of 2 for the (R, K)
surface; prediction error goes from [−11.8%, +37.2%] to
[−23.7%, +18.1%]. mistral-7b — the pool that produced the scored miss —
moves SINGLE → WSR and lands on the measured winner (n_wsr 844 → 649
against a measured 678, error +24.5% → −4.3%); llama3.1-8b goes +19.3%
→ +2.8% and qwen2.5-7b +9.2% → +0.3%; the one new miss is qwen2-7b at
the *lowest* p\*. **This is a post-hoc diagnostic and is labelled as one
in all three artifacts**: it reuses `run_safety_cert`'s prediction path
verbatim with only the overhead swapped (each artifact asserts that its
COMMITTED column reproduces the frozen table exactly, and each does), it
uses constants fitted long after the prediction was frozen, and it
scores nothing. **The §4.8.1 miss stands as scored, three times over,
and the miss ledger is unchanged by all three grids.**

*The standing statement, and its scope.* The WSR overhead envelope is
no longer a constant with a corner band: it is a **measured surface in
block size K, pool rate p\*, and decision direction, with heterogeneity R
ruled out over [1, 30]**. Three scope conditions travel with that, all
disclosed in-artifact. Every envelope here is an **effective local fit
over the range it was measured on**, not an expansion claim — the stock
schedule may admit no fixed (d, c) at all, which is the open hypothesis
earlier in this section. τ is held on the 0.001 lattice at mid-cell in
every grid (0.5–4.5% of margin, printed per rung, and
direction-symmetric by construction) so grid quantization cannot
masquerade as a K, R or direction effect. And the R null is a **failure
to detect over R ∈ [1, 30] on two-level profiles**, never a proof of
R-independence — every later use of it, including §4.8.2's, is licensed
only that far. The residual has not vanished; it has **moved**, from the
high-p\* pools to the low-p\* one.

### 5.6 The conservation hypothesis: FALSIFIED

**[FIG: frontier overheads]** — `fig8_frontier.png`: *overhead in nats
versus certification fraction for the mixture, epoch-split, split-LRT
(b = 25/50/100), and single-stream arms at τ = 0.15/0.16/0.17, with the
0.5× falsification line drawn.*

We pre-registered a conservation hypothesis: any method escaping the
(d/2)·log n learning tax should pay for it elsewhere, with a support
window of [0.7, 1.5]× the mixture's overhead and a falsification line at
0.5×. Two errors were caught by audit round 2 and both are corrected in
`results_frontier.txt`:

1. The original artifact **never printed its own pre-registered
   ratios**. Scored properly, the epoch-split arm landed at
   1.674 / 1.716 / 1.484× — the support window was **MISSED at two of
   the three margins**, not confirmed.
2. The original "one-shot split" comparator was an accidental
   **strawman**: it bet at p = 0.5 through its burn-in and charged ~111
   nats of estimation loss to the martingale, which the split-LRT
   lineage it cited (Wasserman, Ramdas & Balakrishnan) never does.

Revision 2 adds the faithful **discard-burn-in split-LRT** (the
estimation half contributes nothing to log E; validity gated at the null
boundary). At ≥ 95% certification it reaches **0.373×** the mixture's
overhead at τ = 0.15 (b = 50) and **0.398×** at τ = 0.16 (b = 100) —
across our own falsification line. **The conservation hypothesis as
pre-registered is falsified**: sample splitting escapes the (d/2)·log n
learning tax at the n ~ 10³ scales this project studies. The refined
true statement is that splitting converts the log n adaptivity tax into
a burn-in-tuned constant plus an abstention tail that binds only at
razor margins (at τ = 0.17 the corner is visible: 24–90% certification
depending on burn-in). The asymptotic mixture-redundancy statement is
untouched — but it was not what was pre-registered.

The design consequence is that the cold-start map has **three** tax
escapes, not two: rate sacrifice (WSR blocks, any margin, robust),
burn-in freeze (split-LRT, cold start, moderate margins, abstention risk
at razor margins), and transfer priors (recurring evaluations, §4.1.4).
The binding design question is not "mixture versus allocation" but
"which tax escape fits the deployment".

### 5.7 The live capstone: a consistency check, with the severity quantified

A frozen zero-fit prediction — median ∈ [800, 1450] around theory-central
1045; ≥ 14/16 UNSAFE; zero SAFE — was tested against a live
temperature-0.7 stream at a fresh threshold τ = 0.16. Result: **16/16
UNSAFE, zero SAFE, median 1200** (`results_live_prediction.txt`). The
run survived a process crash via lossless log-replay resume.

The freeze itself is beyond doubt: audit round 2 verified that the
commit contains the byte-identical script stating the window 11 seconds
after the log's first line, that the crash-resume replay is bit-exact at
all 1,017 possible crash points, and that all 16 reported reps reproduce
from the raw log. But the audit also quantified what the pass is
*worth*, and we report that rather than the headline:

- Simulating the exact procedure 20,000 times gives
  P(≥ 14/16 UNSAFE) ≈ 1.000 and P(zero SAFE) ≈ 1.000 — **two of the
  three criteria were near-unfalsifiable** — and P(median in window)
  ≈ **0.94**. The pass discriminates only ±1 in d.
- The window was frozen but **not blind**: an offline replay at the same
  τ, same method, and the *identical* 1,000-prompt population had
  produced a median of 1024 forty-four minutes earlier. Fresh sampling
  randomness and a fresh threshold — not a fresh population.
- theory-central recomputes to 1052, not 1045, and [800, 1450] was a
  hand-tightened band, not the output of the stated p ∈ [0.195, 0.209]
  propagation (which gives [761, 1545]).

**Honest summary**: the capstone shows that the frozen pipeline, the
theory constants, and a live stream are mutually consistent under new
randomness at a new threshold. A consistency check passed, not a severe
test. The severe zero-fit results in this arc are the single-stream grid
prediction of §5.2, which needed no fitting at all, and the blind anchor
test of §5.3, which was scored on data the derivation never saw.

---

## 6. Methodology as a contribution

### 6.1 Two adversarial audit rounds

**Round 1** (2026-08-02; four independent audits: statistics,
experimental design, code correctness, prior art) found and we repaired:
a float `multipleOf` validator bug that had **corrupted 59 labels** (52
for gpt-4.1-mini); a **selection-biased repair** — re-querying only
failures exploits temp-0 nondeterminism one-sidedly — replaced by a full
symmetric re-collection of all 3,000 JSON outcomes with the flip
matrices published and originals archived; exact-DP counterexamples that
**refuted our per-sample-CS validity claim** on non-iid streams
(coverage 0.80/0.93), replaced by block gating and the provable WSR
route; a falsified absolute claim ("zero wrong certifications anywhere"
— retired in favor of the α guarantee plus observed rates); mislabeled
pre-registration on a live arm, plus a `--seed-offset` bug that gave
that arm a **different prompt population**; restoration of selective
ranges (the 1.0× tie row, all four z-values, Wald's partly-degenerate
100%); a WSR grid-edge bug; and three assert-free test files removed
from the suite.

**Round 2** (2026-08-12; two independent agents against the previously
unaudited warm-start, overhead-law and capstone arcs) found and we
applied: the **strawman split arm** (§5.6); a **CRN defect** (streams
desynchronize after replication 1) that made four of six bootstrap CIs
straddle zero as published, fixed by a correctly paired re-run; a
**cherry-picked value** (two contamination premiums reported, the third
— which breached the cap — omitted; all three now printed); **vacuous
evidence** ("zero wrong certifications" cited as validity evidence when
no replication was under the null, fixed by the adversarial null MC of
§4.1.4; and a residual criterion with P(pass) = 1.00); an
**oracle-adjacent prior framed as a realistic stale epoch** (16/1000
labels differ), fixed by promoting the drift phase diagram to the
realistic statement; the 3-for-3 → 2-for-3 dimension-rule downgrade and
two withdrawn non-reproducible numbers (§5.4); a shared-RNG-stream
defect across τ-grid points (fixed with per-(τ, method) seeds in the
local and MBPP grids); and the capstone severity analysis (§5.7). Every
verdict table from both rounds is in `audit/`.

### 6.2 The relation gate: one generator behind sixteen defects

This is the strongest methodological claim in the project, and it came
from counting our own mistakes rather than from theory.

**The census.** A peer census of **every** defect surfaced in one
session — 16 in total — found a single invariant: in **16 of 16** the
local object was correct, and in **15 of 16** an unchecked **relation
between** objects had failed. The relations that broke were of a kind:
criterion ↔ hypotheses, window ↔ window, powered model ↔ executed code,
artifact ↔ claim, per-cell ↔ aggregate, result ↔ its other asserting
sites, code ↔ runtime budget. Every one of these is computable; none of
them was being computed.

**The gate.** `scripts/relation_gate.py` mechanizes the missing checks
and runs before freezes and before verdict-asserting commits. Three
relational rules already lived in the severity calibrator for experiment
designs (joint satisfiability across criteria; discriminating power
against rival hypotheses; procedure identity between the powered model
and the executed replay, plus gate-every-clause,
`scripts/severity_sim.py` revisions 2–3). The gate adds their
non-experiment forms:

| rule | what it computes |
|---|---|
| **R1** discrimination | an anchor whose verdict is invariant across the entire constant band discriminates nothing; `--anchors` evaluates every anchor at every corner and flags invariant ones |
| **R1b** scoring resolution | any verdict comparing two measured quantities must state its resolution (CI) and report ties as unresolved-by-measurement; a comparison with no error bar is an anchor with no discrimination check |
| **R4** artifact–claim identity | any artifact cited *with a verdict* must itself print PASS/FAIL/VERDICT lines |
| **R4b** threshold identity | any check whose pass criterion cites a *named* theoretical quantity must COMPUTE that quantity from the theory at the point being tested — never a tolerance multiplier wearing the bound's name; `--thresholds` scans for multiplicative fudge adjacent to bound-naming words |
| **R5** aggregation transparency | n-of-m and "all pass" claims must cite an artifact that enumerates the cells |
| **R6** propagation | `--propagate <term>` lists every site asserting a quantity, so changing it comes with an explicit still-holds check |
| **R7** resource invariants | the shipped wall-clock regression runs, so "fast enough" is a tested relation |
| **R8** allocation discrimination | a verification whose scored points concentrate where the hypothesis is already established is not discriminating regardless of point count; ≥ 50% of scored points must carry the novel-region prediction |
| **R9** absorption ordering | an external result may not be absorbed into the paper or THEORY while a frozen test *of that same result* is pending; every absorption commit must cite the scored artifact it rests on |

**Nine instances of the one generator have now been caught and
scored** — four in the boundary work, five after it — which is why §4
and §5 read the way they do. Each one is a relation nobody computed, and
each is now a rule:

1. **Anchor A2** (R1): its WSR verdict is invariant across the whole
   constant band, so it was never evidence. Mechanically confirmed by
   the gate's first run and reported unscored ever since
   (`results_relation_gate.txt`).
2. **c_short as a constant**: a quantity that is a *function* of the
   block distribution was carried as a scalar, and v1's misses were
   attributed to it (§4.3). The relation was later shown to be below
   measurement noise — so the diagnosis itself was an uncomputed
   relation.
3. **Allocation** (R8): v1 put 7 of 9 scored points in the
   already-established region — a verification that concentrates where
   the answer is known. Now a gate rule.
4. **Scoring resolution** (R1b): v2 compared two medians with no CRN
   pairing and no error bars. Now a gate rule, and the reason v2b
   exists.
5. **Threshold identity** (R4b): C1 rev 1 printed PASS against a
   threshold that named the Stirling bound but was that bound at the
   wrong grid point times an unexplained 1.5 — while the true error
   exceeded the displayed bound (§5.3). R4 was satisfied; the relation
   between the threshold and the theory it cited was not computed. Found
   under external audit, verified here, now mechanized.
6. **Verdict without validity**: the first run of the WSR expansion test
   computed block means with numpy boolean addition (logical OR, capped
   at 0.25 < τ), so nothing ever crossed — both arms returned identical
   censored rows and P3 printed "expansion EXISTS" from two censored
   constants. The per-clause verdicts were all locally well-formed; what
   was never computed was the relation between a verdict and the
   *validity of the run producing it*. v2 adds a crossing-fraction guard
   (≥ 90% per rung or the artifact declares itself INVALID), and the
   invalid v1 is committed as the record rather than discarded
   (commit bb618ec). The same shape recurs at §4.3, where v2b's ties
   came from a bootstrap whose stated 5% size was really 1.8–2.6%.
7. **Absorption ordering** (R9): an external no-expansion claim entered
   the documents while its own frozen test was still running; the test
   then failed P1 (§5.5). The relation between a claim and the evidence
   pending for it.
8. **Synthetic-population generalization**: a universal K\* = 1 was read
   off one synthetic population and used to explain UI-domination
   (§4.7). The relation between the population the claim was measured on
   and the populations it was asserted over was never checked; on the
   ten real pools the census is 1 : 4, 2 : 4, 4 : 2 and the explanation
   is retracted.
9. **Configuration space versus asserted scope — a root-selection
   defect in our own shipped optimizer**, found by porting the
   certifier to §4.8.2's thirteen unequal county strata.
   `StratifiedUICS._m_of_lambda` picked the wrong root of the KKT
   quadratic whenever a stratum is **saturated** (s = 0 or f = 0):
   there the quadratic factors as (m − 1)(a·m − f) — respectively
   m·(a·m − (s + a)) — so the admissible root **is** an endpoint of
   [0, 1] and can land one ulp outside it, after which the test
   `in1 = (r1 ≥ 0) & (r1 ≤ 1)` rejected it and the code took the other
   root, which lies outside [0, 1] and is clipped to the **opposite**
   endpoint. The consequence is not subtle: `min_log_e` returned values
   exceeding log E at feasible points of its own null set by up to
   **100 nats**, producing spurious `ge`-direction certifications at
   n = 42 ballots — wrong-direction certifications in a *majority* of
   reps on the UI arm. Fixed with an endpoint tolerance, and the
   regression test asserts the **mathematical invariant** (an infimum
   cannot exceed a feasible point) on the real Georgia weights rather
   than a snapshot; it fails on the old code. **110 → 112 tests.** The
   relation nobody computed is the one instance 8 names in a different
   costume: **the configurations an object has been exercised in versus
   the configurations it is asserted over.** The object was correct in
   every configuration it had ever been run in and wrong in the first
   one it had not. Scope of impact, checked rather than assumed: the
   defect lives in the k > 1 constrained optimizer only, so it can move
   UI-arm results and wrong-direction counts and **cannot** move any
   frozen prediction, the single arm, or the WSR arm. Prior artifacts
   that use UI (`results_partition_test.txt`, `results_safety.txt`)
   reported UI as dominated and their P3 wrong-certification counts were
   small (4/2,700 in §4.8.1), so **no prior verdict flips**; they were
   not regenerated, and that exposure is recorded here rather than
   waived. It is worth naming what caught it: not a proof, not a review,
   and not the census — **carrying the machinery into a domain whose
   stratum structure the original design never anticipated.**

**The gate caught itself.** Its first R4 implementation flagged 27
artifacts by checking each artifact *as an object* (does it contain
verdict strings?) instead of checking the *citation relation* — the
exact defect the gate exists to catch, found by a reviewer running the
gate on the gate. Rev 2 flags only verdict-asserting citations. In the
same episode, a commit message reported "18 R4" where the artifact
printed 27 — an R5 violation inside the R5 commit — and the correct
count is recorded in `AUDIT_PREP.md` rather than quietly fixed. After
three retrofit batches (commits 6656373, 66cecd5, b6b7151) R4 came back
clean, and R8 passes for the phase verification (10 of 13 scored points
in the novel region, 77% ≥ 50%).

**And it flags this draft — including one flag this consolidation
created.** Run against v4.1; the v4.2 additions (§4.8, the §5.5 grid
block) have **not** been re-scanned, and being made of per-cell tables
they would add to the R5 count below rather than reduce it:

- **R4 raises one flag**: `results_cren_exact.txt` is cited here with a
  verdict but prints a `STATUS:` block rather than a PASS/FAIL/VERDICT
  line, so it does not self-score. The citation is new in v4.1, which
  means the retrofit that closed R4 did not cover an artifact written
  after it. Recorded as an open item, not waived and not fixed by
  editing the artifact to suit the paper.
- **R5 raises 46 n-of-m claims** against the draft (33 against v4, 4
  against v3), because a verification section and a partition section
  are made of such claims. Most are enumerated *in this paper* — the
  per-point tables of §4.3, the anchor table of §4.2, the partition
  tables of §4.7, the ledger of §6.3 — which R5 as implemented does not
  see: it looks only for enumeration inside a cited artifact. That is
  the same object-versus-relation gap R4 already had to fix, and it
  stays an open methodology item. Two flags are substantive rather than
  cosmetic: "10 of 10" above-band and the v1 counts span a *superseded*
  artifact version (065f9a8), so no single committed artifact enumerates
  them — which is why §4.3–4.4 print those points in full.
- **R4b and R8 are clean**, and R4b is clean on a mechanical scan only:
  it is semi-mechanical by construction, so a clean scan is weaker
  evidence than a clean R8.

The census's falsifiable prediction stands, and instance 9 is the one
test of it that arrived after v4.1 was written: **the next defect will
also be an uncomputed relation.** It was — though the honest caveat is
that we classified it ourselves, and a generator broad enough to absorb
every new defect is a generator that predicts nothing. The check that
keeps it falsifiable is a defect whose local object is *wrong on its
own terms*; we have not found one yet, and we are still looking.

### 6.3 Pre-registration with every miss scored

Predictions were frozen in the scripts that produce the artifacts, and
the **scoring is printed inside the artifact**, misses included. The
complete miss ledger for the second half of the project:

| prediction | verdict |
|---|---|
| UI dimension window d ∈ [1.5, 3.5] | MISSED (measured 3.37 / 4.04) |
| Warm-start benign overhead ∈ [1.5, 6] nats | MISSED LOW at all three margins (0.76–1.24) — favorably wrong is still wrong |
| Drift asymmetry direction | **REVERSED** (mechanism diagnosed, rule inverted) |
| Inverted-prior premium "3–4 nats" | wrong (forgot the K factor; measured ≈ +9.9 per-stratum) |
| Conservation window [0.7, 1.5]× | epoch-split MISSED at two of three margins; split-LRT FALSIFIES |
| Chain P1 "every method abstains ≥ 30% at flip epochs" | REFUTED by WSR (165–173/200) |
| Router v1 ≤ 1.05× WSR; v2 ≤ 1.00× / ≤ 0.85× | BOTH FAILED (1.101×; 1.090× / 1.259×) |
| MBPP P1 (UI d ∈ [3, 5]) | FAIL by censoring, disclosed as unidentifiable |
| MBPP P3 (WSR sub-logarithmic) | FAIL, informative (d = 1.8–2.3) |
| MBPP P4 (WSR dominates every ≥90% margin) | REFUTED — single-stream wins |
| Local P4 (cert ≥ 95% at margin ≥ 0.027) | PARTIAL MISS (llama single-stream 85% at 0.027); zero-wrong clause noted as **vacuous by construction** |
| Live τ = 0.15 arm: UNSAFE every replication | FAILED (11/12 abstained at an under-specified 300-call budget) |
| TaSC (two pre-registered predictions) | BOTH FAILED |
| Sharp priors: save 4–6 nats | FAILED (saved none) |
| Prediction-powered refinement: 19% variance cut | FAILED (net loss) |
| Severe live test (C1/C2/C3 windows, disclosed severity 0.59) | **FAILED as frozen**; C3 later shown to have d-discrimination gap +0.02 — a coin (`results_severe_live.txt`) |
| Shade refinements (proportional, κ-ladder) | BOTH LOST to the flat-shade control (`results_shade_refine.txt`) |
| Real-chain supplementary S1a (downward jump ≤ 1.15× cold) | MISSED by 0.01 (`results_real_chain.txt`, `PREREG_S1.md`) |
| Within-lineage boundary premium ≥ +0.5 | **ABSENT** (+0.08 vs the clean sibling where the rule predicts +1; formula-pass via a censored fit disclosed as hollow, `results_lineage_d.txt`) |
| Margin sweep v1 (P2, P4) | **FAILED**; caught our own two-sided/one-sided protocol bug; P4 zero-claim ill-posed and restated (`results_margin_sweep.txt` v1) |
| Margin sweep v2 (P2, one-sided protocol) | **FAILED by 0.008 nats** (mean D −0.258) at power-checked severity 0.65 — the deviation is the o(1) structure §5.3 then derived |
| Bonferroni design portfolio P2 (≤ 1.30× oracle) / P3 (beat every fixed design) | P2 **FAILED as frozen** (11 of 16 cells); P3 **HEADLINE LOST** — portfolio 10,224 vs fixed WSR 8,718 (`results_portfolio.txt`) |
| Auto-select P1 (≥ 12 of 16 cells match the oracle design) | **FAILED** (11 of 16); cost clauses passed (mean regret +8.3%, worst +43%) (`results_auto_select.txt`) |
| Overshoot C3 (renewal offset dispersion ≤ 0.25) | **FAILED** (std 0.286); C1/C2/C4 passed; closed form declared open (`results_overshoot.txt`) |
| Phase-curve verification v1 (P1: below-band → single) | **FAILED as frozen** (0 of 2); verdict then *restated* — the novel region was untested at resolution and 7 of 9 scored points sat in the established region (now gate rule R8) |
| Phase-curve verification v2 (P1 ≥ 8 of 10) | **FAILED as frozen** (4 of 10) — then shown **instrument-limited**: arms not CRN-paired, verdicts by bare median comparison (now gate rule R1b) |
| Phase-curve verification v2b (P1/P2/P3 under CRN pairing + paired bootstrap) | **CONFIRMED** — 3 of 3 resolving below-band → single, 3 of 3 above-band → WSR, 7 of 13 points TIES (reviewer's pre-stated tie prediction confirmed), 0/6,000 wrong — *later superseded by v2c after its own bootstrap was found conservative* |
| v2b's paired median bootstrap: stated size 5% | **DEFECT, ours** — actual size 1.8–2.6% on the tied crossing-time lattice; re-frozen as v2c with a calibrated Harrell-Davis estimator (4.4–5.2%), same estimand, and the one predicted extra resolution appeared: 4 of 4 resolving + 6 ties (`results_phase_test.txt` v2c) |
| Stratification-gain magnitude quoted from one synthetic population | **MISQUOTED** — the +7%/+50% synthetic gains are an order of magnitude below the real committed-pool range 1.06–4.31× (`results_gain.txt`) |
| F14 rev 1: "the mixture's optimal K\* = 1", and "K\* = 1 explains UI-domination" | **REFUTED on 6 of 10 real pools** (census K\* = 1 : 4, 2 : 4, 4 : 2); the pre-registered finite-interior-K\* prediction, declared failed in rev 1, is **CONFIRMED** on the four K\* = 2 pools; the UI-domination explanation is **RETRACTED** (`results_gain.txt`) |
| WSR stock-schedule no-expansion P1 (n·V/log n monotone, ≥ 1.5× across the ladder) | **FAILED as frozen** (1.23×, non-monotone at depth) — the claim is downgraded to a hypothesis, form-consistent only (P2 max deviation 6.1%); the external 1.80× came from a reimplementation 43% off the shipped code and is withdrawn (`results_wsr_expansion.txt`) |
| Absorption ordering at commit 805ae03 | **PROCESS MISS, ours** — an external result was absorbed into the documents while its own frozen test was pending; the test then failed P1. Unwound at 8d43eb2; now gate rule R9 |
| Floored-arm d: committed +1.27, and the frozen windows P-A (idealization d = 1) / P-B (warmup-corrected +1.5301) | **GRID-BIASED** — the τ grid sits mid-cell (+0.0005, 1.4→5.3% of margin), biasing d **low**, not high as the external audit claimed; corrected +1.3614 ± 0.2006. Both windows contain the measurement → **UNRESOLVED**; windows not widened (`results_floor_d.txt`) |
| Safety-domain export P1 (every resolving pool matches the frozen design call) | **FAILED as frozen** — 1 of 2 resolving (mistral-7b: predicted single, WSR won; qwen2-7b HIT). P2/P3 passed and the single-arm predictor ported within ~5% on 6/6. Localized to the reused K = 4 WSR overhead envelope; three later designed grids moved a **labelled post-hoc** reconstruction to 4/5 **without re-scoring it** (`results_safety.txt`, §4.8.1) |

**Thirty-four rows, and three scored FAILs that deliberately are not
rows.** The three envelope grids of §5.5 print P1 FAIL / P2 PASS,
P1 FAIL / P2 FAIL, and P1 FAIL, and none is entered here. The reason is
a distinction we would rather state than let a reader discover: those
are **measurement** grids, not frozen predictions about the world. Their
P1 clauses are regression anchors against a previously measured
envelope, two of the three failed for a reason committed *before* the
run, and grid (ii)'s P2 failure **is the finding** it was run to get.
Entering them would inflate the ledger with self-scored diagnostics of
our own instruments while the one prediction that was actually frozen
about a new domain — the row above — is the entry that carries the cost.
`AUDIT_PREP.md` records all three verdicts in full and is authoritative
on the count.

Three entries deserve emphasis rather than burial. The **margin-sweep
pair**: the centerpiece experiment failed, received one legitimate
mechanical bug fix, and **failed again** under the corrected protocol —
while excluding d = 0 and d = 2 decisively both times, and while
measuring the structure §5.3 later derived. The **phase-verification
sequence**: two frozen failures preceded the confirmation, the second
failure was of our *instrument* rather than our theory, the re-scoring
that produced the confirmation was gated by a reviewer's pre-stated
prediction of the tie outcome — without that pre-statement it would have
been indistinguishable from iterating until a pass — and then the
confirming instrument was itself audited and found conservative, which
cost a fourth round. The **optimal-K pair**: a prediction we declared
failed on synthetic data turns out to be confirmed on 4 of 10 real
pools, and the explanation we built on the failure is retracted. Getting
a *failure* wrong is the same error as getting a success wrong, and it
is listed the same way.

Against this ledger, the **load-bearing passes** are: the single-stream
zero-fit prediction (§5.2), the out-of-family dimension prediction
(§5.4), the live WSR arm (predicted UNSAFE ≥ 7/8, median ∈ [150, 450],
zero SAFE; observed 7/8, median 224, zero SAFE, $0.25 —
`results_live_wsr.txt`), the blind anchor test of the derived fourth
term (§5.3), the above-band verification of the boundary (§4.4), and the
three-arm partition test, whose UI-dominance clause was falsifiable by a
single cell and came back 0 of 10 (§4.7). Others passed too — chain
P2–P4, local-pool P1–P3, MBPP P2, the drift
validity and saturation clauses, the capstone (at the severity of §5.7)
— but several of those were, by our own audit's finding,
near-unfalsifiable, and we say so rather than counting them.

### 6.4 The information-bound guard

It took **three attempts** to implement the Spertus baseline validly,
and both invalid drafts were caught by a smell test rather than by
inspection: *a median faster than log(1/α) / game-value is physically
impossible*. Draft one used vertex minimization, which requires
η-oblivious bets; draft two mis-assigned flat (zero-failure) strata to
the top of the null boundary, starving the failure strata. The guard is
now built into the artifact, which prints the information bound
alongside each condition (~60 / ~175 / ~385 samples) and flags any arm
violating it (`results_spertus_baseline.txt`). We offer it as a small
methodological export: any comparison of e-process methods should print
this bound.

---

## 7. Limitations

1. **Single-epoch pools.** Each pool is one temperature-0 pass; p\* is
   exact *for that pool*, not for the model in general.
2. **Temperature-0 is only near-deterministic.** Full re-query flips
   ~1–2% of prompt outcomes, roughly symmetric — that is the label
   stability floor for every pool-scoped number here.
3. **Pool-scoped estimand under a chosen weighting.** Uniform stratum
   weights are a design choice; reweighting `extreme` to 10% moves
   gpt-4o-mini's p\* from 0.202 to ≈ 0.086.
4. **The capstone reused its calibration population.** Fresh threshold
   and fresh sampling randomness, same 1,000 prompts (§5.7).
5. **Functional form is theory-adopted, not data-established.** Over our
   windows, (d/2)·log n, √log n and log log n fit within 0.03 nats of
   each other (`results_local_law.txt`, `results_mbpp_law.txt`); on the
   adjudication basis log log n fits marginally *better*
   (`results_adjudication.txt`). We adopt the log n form from
   Rissanen / Clarke–Barron, not from these fits.
6. **Three-point censored fits are disclosed, not interpreted.** The UI
   arm on MBPP certifies too rarely at hard margins to identify a
   dimension; llama's d = −2.23 is a censoring artifact.
7. **d = 0 vs d = 1 is not identifiable** at 200 reps × 6 points
   (bootstrap CIs span both; corr(d̂, ĉ) = −0.994).
8. **No cross-vendor LIVE runs.** Every live arm is gpt-4o-mini; the
   Meta and Alibaba lineages appear only as replayable pools.
9. **The per-sample mixture CS has empirical validity only** on non-iid
   stratified streams. Block gating restored uniform coverage ≥ 0.996 in
   every configuration we tested — but "every configuration tested" is
   not a guarantee; use the WSR block route when one is required.
10. **Chain and router trajectories are synthetic**, anchored to real
    epoch-2 rates — a six-release trajectory of real model versions is
    the obvious next data collection.
11. **The Spertus comparison is to our variant** of their construction;
    their banded AGRAPA version may reduce the abstentions that drive
    our reliability finding.
12. **Formalization is open.** (†) is calibrated, not proved, for these
    three statistics. The single-stream arm is the exception and is
    formalized in `paper/BOUNDARY_THEOREM.md` with an explicit remainder
    interval; even there, Eq. (3) is a *definition* of c_ren, not a
    corollary of the expansion. c_ren itself is exactly computable
    (−1.1700824 at the reference point, absorption recursion) but has no
    scalar closed form, and the named obstruction — a noncommuting
    killed kernel, plus a finite-boundary gap at L ≈ 3 shared by the
    selection and overshoot pieces — is mathematical, not a matter of
    more compute.
13. **The boundary is derived for one geometry.** K = 4, a two-level
    (2 cold + 2 hot) stratum profile, α = 0.05, and p\* ∈ {0.20, 0.30,
    0.40}. §5.5's three grids since measured the WSR envelope out to
    K ∈ {2, 4, 6, 8}, p\* ∈ {0.20, 0.50, 0.80}, R ∈ [1, 30] and both
    decision directions — but that is the *envelope*, not the derived
    boundary, every cell is still a two-level profile, and α = 0.05
    throughout. Other profile shapes and other α remain unverified.
14. **The boundary's bands are WSR's uncertainty only.** The single arm
    is derived; the WSR arm's two-regime envelope is measured, so the
    published band understates total uncertainty by whatever the single
    arm's own error is (~10–20% on absolute medians, §5.3). Worse than
    "measured": the schedule that envelope describes may admit no fixed
    (d, c) at all, which would make its fitted dimensions
    horizon-dependent. That is a hypothesis whose own divergence test
    failed, and the derivation route is open (§5.5).
15. **Below the boundary, almost nothing was resolved.** 6 of 10
    below-band points are ties at 200 reps per arm.
    "Indistinguishable at this budget" is not "equal": a power analysis
    puts four of them at 11–33% power, so a larger budget should reopen
    the region rather than confirm equality.
16. **A frozen scoring boundary moved under a later correction.** The
    verification points were selected against the pre-correction curve;
    under the regenerated one, two of the ten below-band points become
    in-band (§4.3). No verdict changes, but the classification is not
    invariant to the constant.
17. **The floored-arm dimension is unresolved, and may be
    unresolvable.** {1, 1.12, 1.27, 1.53} are mutually indistinguishable
    at any feasible rep budget on this ladder, and the shipped class's
    warmup term decays as 1/log t_c, so it has no fixed d to measure in
    the first place (§5.5).
18. **The optimal-K census is ten pools at temperature 0.** The
    designed strata are the finest honest partition available there;
    finer-K behaviour and the interior optimum's shape need per-prompt
    rates at temperature > 0 (§4.7).
19. **Verification pools are constructed.** Real gpt-4o-mini outcomes
    remixed to place (p\*, R) — real behavior in a designed
    configuration, not an independently sampled model × task pair. The
    two anchors (MBPP-like, llama3-8b-like) are the closest thing here
    to naturally occurring test points.
20. **Automated selection is unsolved.** The pilot-based selector
    matched the oracle design in 11 of 16 cells
    (`results_auto_select.txt`), and the hedge that avoids choosing lost
    outright (`results_portfolio.txt`).
21. **The safety domain's labels are a coarse proxy, and we measured how
    coarse.** The deterministic refusal-string grader disagrees with a
    gemma2:9b judge on **26 of 60 responses (43.3%)** of a llama3.2:3b
    regeneration, and the disagreement is one-sided: of its 28
    "complied" calls the judge reads **26 as refusals**, with **0** real
    compliances missed — a head-prefix-versus-whole-response construct
    gap (`results_safety_noise.txt`). This is disclosed at the same
    standing as limitation 2's temp-0 flip rate, and it bounds one thing
    and not another. It bounds how well those labels track true harmful
    compliance, which is why every safety p\* and R in §4.8.1 is a
    **pool parameter under a named grader** and never a safety
    measurement or a model ranking. It does **not** enter the α
    guarantee, which is exact *given* the binary labels, and it does not
    touch the design-selection verdict: which arm crosses first is a
    function of the label stream, not of what the labels mean. A
    better-graded corpus would move p\* and could move the pool into a
    different cell of the map; it would not change what the map does
    with a cell.
22. **Each domain export is one frozen set, and two of the RLA cells are
    constructed.** §4.8.1 is six scored pools from one corpus with one
    grader; §4.8.2 is one contest, whose GA-official rows are
    **predicted-only and unscored** and whose 2% and 5% cells are
    **synthetic-margin** pools built by a common additive shift of every
    county share. Both exports treat R as inert for the single and WSR
    arms on the authority of §5.5's R null, which is a failure to detect
    over R ∈ [1, 30] on two-level profiles — not a proof of
    R-independence, and the pools run R up to 17.0.

---

## 8. Related work

**Anytime-valid inference and betting.** Betting confidence sequences
for bounded means (Waudby-Smith & Ramdas 2023) supply the WSR hedged CS
and the predictable-λ schedule we both use and criticize (§5.5);
Shekhar & Ramdas (2023) and Waudby-Smith, Stark & Ramdas (2021, RiLACS)
are the adjacent estimation and audit lines. Turner, Ly & Grünwald
(2022) and Turner & Grünwald (2023) supply the anytime-valid contingency
and stratified constructions behind our per-stratum α/K combination.
Spertus & Stark (2022) and **Spertus, Sridhar & Stark (2024)** give the
union-intersection test-supermartingale with optimized allocation that
serves as our state-of-the-art baseline (§4.1.1).

**Risk-limiting audits.** The election-audit literature is where this
machinery is oldest and most operational, and §4.8.2 borrows from it
rather than adding to it. **Stark (2020, SHANGRLA)** reduces a very
general class of social-choice audits to sequential tests that a set of
nonnegative assorter means each exceed 1/2 — the reduction our τ = 0.5
formulation is an instance of; **Stark (2023, ALPHA)** and
**Waudby-Smith & Ramdas (2023)** supply the betting supermartingales
those tests are now run with, the same family as our WSR arm;
**Waudby-Smith, Stark & Ramdas (2021, RiLACS)** is the
confidence-sequence treatment of the same problem; and **Spertus,
Sridhar & Stark (2024)** is the stratified union-intersection
construction we ship as `StratifiedUICS` and run as the third arm.
**Explicit non-claim**: we improve none of these, and propose no
procedure for a real election. What that literature does not supply — and
what §4.8.2 tests — is a *pre-observable design-selection rule*: which
e-process family certifies fastest, decidable from the contest's own
published margin and county structure before the first ballot is pulled.
The traffic runs the other way too. The audit setting gave us the first
prospective test of §5.5's direction-matched constants, a sample unit
denominated in human labour rather than API calls, and — through a
stratum geometry no LLM pool had produced — the defect of §6.2's
instance 9.

**Sequential LLM evaluation.** Wu, Nair & Candès (2026), Hsu & Shekhar
(2026), CELEUS (2026), PACE (2026) and Zhou et al. (2026) bring
sequential and e-value machinery to LLM evaluation. Hsu & Shekhar
independently report uniform sampling beating adaptive querying, which
corroborates our regime-(b) and regime-(c) findings. None of these
provide a heterogeneity-indexed design boundary, a replayable
multi-vendor testbed, or a derived-then-verified selection rule, which
is the gap this paper fills.

**Classical sequential analysis and universal coding.** The
second-order expansion of §5 is classical: Wald (1945) for the SPRT;
Schwarz (1962) and Lai (1988) for boundary shape; Pollak & Siegmund
(1975), Pollak (1978) and Woodroofe (1982, nonlinear renewal theory) for
the d = 1 expansion and its matching lower bound; Rissanen (1984),
Clarke & Barron and Krichevsky–Trofimov for mixture regret; **Xie &
Barron (1997)** (and Watanabe's RLCT) for the boundary/singular
coefficient behind d = K + #boundary. The fourth term we derive in §5.3
is a Stirling/Laplace evaluation of the same Beta mixture those lines
study, and the residual it leaves is exactly the overshoot and
median-versus-mean structure of nonlinear renewal theory. Its pieces are
classical too: **Spitzer's (1956)** fluctuation identity gives the
overshoot's asymptotic ladder-height constant, and **Kim & Woodroofe
(2006, math/0611695)** — nonlinear renewal with slowly-changing
perturbations — is the right frame for the finite-boundary gap we
report as open. We claim the calibration, the exact absorption recursion
for the residual, and the design boundary built on them, not the
classical apparatus. Armitage (1954) and Armitage, McPherson & Rowe (1969) are the
peeking and sequential-McNemar ancestors; Mahalanobis (1946) is the
interpenetrating-subsampling ancestor of the block reduction.
**Wasserman, Ramdas & Balakrishnan** (universal inference / split-LRT)
is the lineage of the arm that falsified our conservation hypothesis
(§5.6). Our positioning with respect to all of this is citation, not
discovery.

---

## 9. Reproducibility and artifacts

Every offline experiment replays from the committed outcome pools with
no API access. `./reproduce.sh [quick|all|<script>]` re-runs them and
diffs SHA256 checksums against the committed artifacts; the smoke test
is **byte-identical**, and the full sweep of 2026-08-13 reproduced 26/26
offline artifacts byte-identically. All results are deterministic given
the pools (BASE_SEED = 42; headline comparisons re-verified at seeds
{7, 2024, 99999}). Checksums are tamper-evidence, not proof of
reproduction — `reproduce.sh` is the actual demonstration. Raw
generations for every call are stored under `data/`, including the
pre-fix archives (`data/archive_pre_multipleof_fix/`), with **one
exception**: the safety family of §4.8.1 stores prompt hashes, category
strata and binary outcomes only — **no raw completions for harmful
prompts are committed**. The StrongREJECT corpus itself is public and
re-downloadable, and every statistical claim in §4.8.1 reproduces from
the committed outcome records without the generated text. The boundary
artifacts print their own checksums (`results_phase_curve.txt`
040d60191cbbe608 as regenerated, c4a4720dbba3ccb8 as frozen at f75eb8d;
`results_phase_test.txt` 85ab64297762127a for v2c;
`results_overshoot.txt` 0b7fa43558e3530f;
`results_cren_exact.txt` 7b03c4008a44bc83;
`results_partition.txt` 633da7306797abd8;
`results_partition_test.txt` 9394f2ca9ee52755;
`results_gain.txt` 6741923850ff0c66;
`results_wsr_expansion.txt` 1d90b32264342885;
`results_floor_d.txt` 28f029828284b752;
`results_safety.txt` a369e454bc5450fd;
`results_safety_noise.txt` 923a301bde114ced;
`results_wsr_k.txt` f6aea65aa754d0d8;
`results_wsr_rk.txt` 202b167276d05415;
`results_wsr_pdir.txt` eb8f5f8d7eb4efad;
`results_rla.txt` 1eefa5b579a1b395) and their superseded versions
remain in the history (phase test v1 at commit 065f9a8, v2 at 80c9e14,
v2b at a1f37ac, v2c at 52b6c9f; the pre-correction phase curve at
f75eb8d).
Superseded artifacts are kept, not deleted: `results_cren.txt` and
`results_overshoot.txt`'s C4 row are retained for history and marked
superseded in place.

**Ledger.** ≈ 8,600 OpenAI API calls through the bolstering round at
≈ $2.02 (FINDINGS ledger; includes the $0.25 live WSR arm,
`results_live_wsr.txt`), plus ≈ $2.68 for the live capstone
(`results_live_prediction.txt`) and ≈ $0.35 for the paused severe-v2
pilot (`data/severe2_pilot_log.jsonl`) — under $6 total. All local
pools (llama3.2-3b, llama3.1-8b, llama3-8b, qwen2.5-7b, qwen2-7b,
both MBPP sets, the fresh populations, and every
trajectory/sweep/boundary replay) cost nothing: collected locally
through Ollama with the identical protocol, as do the eight safety pools
of §4.8.1. Test suite: **112 passing tests** (110 before §6.2's ninth
instance added its invariant regression).

**Figures.** Figure 1 (pool heterogeneity), Figure 2 (width vs n),
Figure 3 (peeking miscoverage), Figure 4 (certification: allocation and
feasibility), Figure 5 (paired comparison; block reduction), Figure 6
(invention-round scoreboard), Figure 7 (`fig7_drift_budget.png`,
§4.1.4), Figure 8 (`fig8_frontier.png`, §5.6), and Figure 9
(`fig9_design_map.png`, §4.1) are in `paper/figures/`. The derived
boundary curve with its verification points overlaid (§4.2–4.4) is not
yet drawn.

**Key artifacts by section.**

| section | artifacts |
|---|---|
| §3 testbed | `results_crossmodel.txt`, `results_local_law.txt`, `results_mbpp_law.txt`, `results_overhead_law_code.txt` |
| §3.4 prerequisites | `results_advanced.txt`, `results_codetask.txt`, `results_realllm_betting.txt`, `results_block_reduction.txt` |
| §4.1 empirical map | `results_wsr_hard.txt`, `results_tasc_hard.txt`, `results_uncertainty.txt`, `results_spertus_baseline.txt`, `results_spertus_crn.txt`, `results_local_law.txt`, `results_crossmodel.txt`, `results_ui_grow.txt`, `results_mbpp_law.txt`, `results_warmstart*.txt`, `results_router.txt`, `results_router2.txt` |
| §4.2 derived curve | `results_phase_curve.txt`, `scripts/derive_phase_boundary.py`, `results_cren_exact.txt`, `results_relation_gate.txt` |
| §4.3–4.4 verification | `results_phase_test.txt` (v2c; v1 at 065f9a8, v2 at 80c9e14, v2b at a1f37ac), `results_portfolio.txt`, `results_auto_select.txt` |
| §4.7 partition | `results_partition.txt`, `results_partition_test.txt`, `results_optimal_k.txt`, `results_gain.txt`, `scripts/derive_partition.py`, `scripts/run_partition_test.py`, `scripts/derive_optimal_k.py`, `scripts/measure_gain.py` |
| §5 expansion | `results_overhead_law.txt`, `results_overhead_fit.txt`, `results_overhead_law_code.txt`, `results_margin_sweep.txt`, `results_overshoot.txt`, `results_cren_exact.txt`, `results_selection.txt`, `results_overshoot_closed.txt`, `results_adjudication.txt`, `results_lineage_d.txt`, `results_frontier.txt`, `results_live_prediction.txt`, `audit/out_law_accounting.txt`, `paper/BOUNDARY_THEOREM.md` |
| §4.8 domain exports | `results_safety.txt`, `results_safety_noise.txt`, `results_rla.txt`, `scripts/run_safety_cert.py`, `scripts/run_rla_bridge.py` |
| §5.5 WSR expansion | `results_wsr_expansion.txt`, `results_floor_d.txt`, `scripts/run_wsr_expansion.py`, `scripts/derive_floor_d.py`, `results_mbpp_law.txt` |
| §5.5 envelope grids | `results_wsr_k.txt`, `results_wsr_rk.txt`, `results_wsr_pdir.txt` |
| §6 methodology | `audit/AUDIT_LAW_CAPSTONE.md`, `audit/AUDIT_WARMSTART.md`, `AUDIT_PREP.md`, `results_relation_gate.txt`, `results_live_wsr.txt`, `scripts/relation_gate.py` |

---

## References

Armitage (1954); Armitage, McPherson & Rowe (1969); Wald (1945);
Mahalanobis (1946); Spitzer (1956); Schwarz (1962); Pollak & Siegmund
(1975); Pollak (1978); Woodroofe (1982); Rissanen (1984); Lai (1988);
Lai & Zhang (1994); Clarke & Barron (1990); Krichevsky & Trofimov
(1981); Xie & Barron (1997); Kim & Woodroofe (2006, math/0611695);
Watanabe (2009); Maurer & Pontil (2009); Stark (2020, SHANGRLA);
Wasserman, Ramdas & Balakrishnan (2020); Waudby-Smith, Stark & Ramdas
(2021, RiLACS); Spertus & Stark (2022); Turner, Ly & Grünwald (2022);
Stark (2023, ALPHA); Waudby-Smith & Ramdas (2023); Shekhar & Ramdas
(2023); Turner & Grünwald
(2023); Spertus, Sridhar & Stark (2024, arXiv:2409.06680); Wu, Nair &
Candès (2026, arXiv:2601.20251); Hsu & Shekhar (2026, arXiv:2607.17409);
CELEUS (2026, arXiv:2606.20820); PACE (2026, arXiv:2606.08106); Zhou et
al. (2026, arXiv:2605.07002); Resolution Diagnostics (2026,
arXiv:2605.30315).
