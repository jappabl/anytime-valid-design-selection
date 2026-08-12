# Which Sequential Design Should You Use? An Audited, Replayable Design-Selection Study for Anytime-Valid LLM Failure-Rate Certification

**Hao Lin**

*Draft v3 — 2026-08-12. Supersedes v2 (2026-08-02), which predates the
theory thread, the cross-vendor and public-benchmark pools, the
warm-start deployment arc, and adversarial audit round 2. Every number
below traces to a checksummed `results_*.txt` artifact or to
[FINDINGS.md](../FINDINGS.md); artifact filenames are cited inline.
Figures live in `paper/figures/`.*

---

## Abstract

Anytime-valid confidence sequences make it safe to monitor an LLM
evaluation continuously and stop it early — a guarantee fixed-n
intervals lack (we measure 47.7% uniform miscoverage for a nominal-95%
Wilson interval under peeking on real gpt-4o-mini outcome streams,
`results_advanced.txt`). The methods are established. What practitioners
lack is guidance on *which* sequential design to use for *which*
evaluation, and what the wrong choice costs. We build a cheap,
exactly-reproducible replay testbed — three vendor lineages (OpenAI,
Meta, Alibaba), three task families including the public sanitized-MBPP
benchmark, 1,747 distinct prompts, one near-deterministic call per
prompt, raw generations stored, exact pool-level ground truth — and use
it to compare designs head-to-head under pre-registered predictions and
two rounds of adversarial audit.

The headline is a **four-regime design map**. (i) Under *extreme*
prompt heterogeneity at *hard* margins, a WSR betting CS on iid block
means wins, and wins out-of-family: it dominates all six margins on both
non-OpenAI pools (`results_local_law.txt`). (ii) Under extreme
heterogeneity at *easy* margins, the winner flips with the direction of
the decision — decision-directed stratum allocation certifies UNSAFE
3.3× faster than round-robin, while for SAFE the plain single stream is
3.3–5× faster than directed (`results_crossmodel.txt`). (iii) Under
*mild* heterogeneity — the regime a public benchmark actually occupies —
the plain single-stream mixture CS beats both: stratification buys
almost no rate (V_rr/V_pool ≈ 1.05) while the union-intersection
mixture still pays its (K/2)·log n learning tax and drowns, certifying
3–36% at the four hardest margins (`results_mbpp_law.txt`). (iv) For
*recurring* evaluations, a transfer prior from the previous epoch cuts
the learning tax from 15.4–18.5 nats to 0.76–1.24
(`results_warmstart.txt`), with an asymmetric staleness budget we map
(`results_warmstart_drift.txt`) and a chaining result showing no
compounding (`results_warmstart_chain.txt`).

Underneath the map sits a **calibrated classical expansion**,
n·V = log(1/α) + (d/2)·log n + c. We do not discover it — the d = 1 case
is a fifty-year-old theorem (Pollak–Siegmund 1975; Woodroofe 1982) that
the modern e-value literature under-cites. We calibrate it: with **zero
fitted parameters** the closed form reproduces measured single-stream
medians within −2.6%…+6.8% (`audit/out_law_accounting.txt`), and the
fitted single-stream dimension lands in [0.72, 1.01] on six pools across
three vendors and three task families.

We report the failures as prominently as the wins, because the honest
scoring is the credibility. Our conservation hypothesis was
**falsified** by a faithful split-LRT arm at 0.373×/0.398× of the
mixture overhead (`results_frontier.txt`). A prior-routed portfolio
failed its pre-registered target in **two** iterations (1.090× and
1.259× of pure WSR) and we stopped rather than iterate to a win
(`results_router.txt`, `results_router2.txt`). A pre-registered live
certification prediction failed outright. Four invented allocation
schemes lost to the simplest reduction. Audit round 2 downgraded our own
dimension-rule score from 3-for-3 to 2-for-3 and reclassified our live
capstone from "severe test" to "consistency check" with the severity
quantified (P(pass) ≈ 0.94). Total API spend: under $5.

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

### 1.1 Positioning (honest)

**This project does not invent those methods.** The e-processes, the
betting CS, the union-intersection construction, the block reduction,
and the second-order expansion in §5 are all pre-existing. What we
contribute is the *comparative* apparatus and the *selection* knowledge
that the methods papers leave open, plus a set of audited negative
results:

1. **A replay testbed with exact ground truth** (§3) spanning three
   vendor lineages, three task families (two synthetic, one public
   benchmark), and two heterogeneity regimes — cheap enough that every
   candidate design can be replayed against real model behavior at zero
   marginal API cost, and reproducible byte-identically (`reproduce.sh`).
2. **The four-regime design map** (§4): which design wins is determined
   by the *heterogeneity* of the prompt pool, the *direction* and
   *tightness* of the decision, and whether the evaluation *recurs*. The
   heterogeneity axis is invisible in a synthetic single-vendor study —
   we only found it by running a public benchmark we did not design.
3. **A calibration of a classical expansion** (§5) on real LLM
   evaluation data, including zero-free-parameter predictions for the
   single-stream arm, an honest status report on a coarser dimension
   rule, and an anti-result for the popular predictable-λ WSR schedule.
4. **A warm-start deployment story** (§4.4): the cold-start learning tax
   binds only at first contact with a model; every recurring evaluation
   with smooth drift can convert it to ~1 nat, with a provably capped
   insurance premium, a mapped staleness budget, and no compounding
   across epochs.
5. **Methodology as a deliverable** (§6): two adversarial audit rounds
   with the corrections applied and named, pre-registration with *all*
   misses scored and printed inside the artifacts themselves, and an
   information-bound guard that caught two invalid baseline
   implementations before they became results.

### 1.2 What we do not claim

"Zero-fit" applies to the single-stream arm only; the
union-intersection arm needs one fitted constant per model (§5.2). The
dimension rule d = K + #boundary-strata is a coarse empirical
regularity, not a law, and on our own code pools it scores 2-for-3 under
our own criterion (§5.3). The live capstone is a *consistency check*,
not a severe test (§5.6). All estimands are pool-scoped under a chosen
stratum weighting (§3.3).

---

## 2. Setup

**Estimand.** The uniform-mixture failure rate p\* = (1/K)Σ_k p_k over
K = 4 strata — a pool-level quantity *under a chosen weighting*.
Reweighting `extreme` to 10% would give p\* ≈ 0.086 instead of 0.202 for
gpt-4o-mini, so every certification result below states its margin
|p\* − τ|. Validators are deterministic: Draft-7 JSON schema validation
with exact-decimal `multipleOf`, and execution-based equivalence against
reference solutions in isolated subprocesses.

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
(§4.3). OpenAI pools were collected via API; llama3.2-3b (Meta lineage)
and qwen2.5-7b (Alibaba lineage) were collected locally through Ollama
at zero API cost, using the identical prompt objects, validator,
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

The difficulty ordering is preserved for every model and family tested;
the model × task grid is doubly monotone (JSON p\*
.202/.080/.036 and code p\* .050/.016/.009 rank the three OpenAI models
identically). The dominant synthetic failure mode is character counting
(exact-length strings, long digit runs).

**The last two rows are the important ones.** The synthetic JSON pools
are extreme: hardest-over-easiest-nonzero stratum ratios of 184× / 76× /
35× / 31× / 237×, with several strata at exactly zero. MBPP's ratio is
**1.9× and 2.6×** — two orders of magnitude milder, with no stratum
anywhere near an edge. That gap is what §4.3 turns into a design regime,
and it is the one axis a JSON-only study cannot see.

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

Four facts have to hold before a design map is even meaningful; all four
were established on these pools and survive audit.

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

## 4. The design map

**[FIG: design map]** — *two axes (pool heterogeneity × decision
regime), four labeled regions, the winning design and its evidence
artifact in each.*

The map's claim is not that one design dominates. It is that the winner
is *predictable from three things you know before sampling*: the
heterogeneity of the pool, the direction and tightness of the decision,
and whether this evaluation has a predecessor.

| regime | condition | winner | margin of victory | evidence |
|---|---|---|---|---|
| (a) | extreme heterogeneity, hard margin | **WSR on blocks** | 1.2–1.7× vs the next arm at hard margins; 1.0–2.4× vs the per-sample CS; dominates all 6 out-of-family margins (up to 4.1×) | `results_wsr_hard.txt`, `results_local_law.txt`, `results_uncertainty.txt` |
| (b) | extreme heterogeneity, easy margin | **directed allocation** (UNSAFE) / **single stream** (SAFE) | 3.3× / 3.3–5× | `results_crossmodel.txt`, `results_ui_grow.txt`, `results_spertus_crn.txt` |
| (c) | mild heterogeneity | **single stream** | UI drowns (3–36% certification); WSR's tax grows with horizon | `results_mbpp_law.txt` |
| (d) | recurring evaluation, smooth drift | **warm-start UI** | ~1 nat vs 15–18 cold; 4.8–5.3× vs cold | `results_warmstart.txt`, `results_warmstart_drift.txt` |

### 4.1 Regime (a): extreme heterogeneity, hard margins → WSR blocks

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
for either side (`results_spertus_baseline.txt`). Spertus+greedy is
faster when it certifies on 4 of 5 conditions (144 vs 244 at easy
UNSAFE; 180 vs 260 at easy SAFE) but abstains 3–63% within budgets where
WSR abstains 0–10%; at the hardest margin (τ = 0.18) WSR dominates
outright, 271/300 versus 112/300. The CRN censored-median tie-breaker
(`results_spertus_crn.txt`) makes both contested hard margins
*statistical ties* with WSR nominally ahead, and hands Spertus the
easy-nano-SAFE box (184 vs 240, CI [+40, +80]). Three methods share the
frontier — which is the strongest form of the design-follows-decision
thesis, not a weakening of it. Fidelity caveat in both directions: this
is our variant of their construction, and their banded AGRAPA version
may reduce the abstentions.

### 4.2 Regime (b): extreme heterogeneity, easy margins → the decision picks

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

Independent corroboration: Hsu & Shekhar (2026) also report uniform
sampling sometimes beating adaptive querying.

### 4.3 Regime (c): MILD heterogeneity → the single stream wins

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
   of §5.4 surfacing at MBPP's longer crossing horizons.

The result: at every margin where both arms certify ≥ 90%, plain
single-stream has the lower median (qwen: 1716/960/542/460 vs WSR
2022/1052/592/518), and at the two hardest margins WSR's lower median
comes with materially *lower* certification (llama .49 vs .54 at margin
.022). Our own pre-registered clause "WSR's median dominates both
alternatives at every ≥90%-certified margin" was **REFUTED**. Under mild
heterogeneity the d = 1 method beats everything, and the practical rule
is: *measure your stratum ratio before you buy stratification*.

### 4.4 Regime (d): recurring evaluations → warm-start UI

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

**[FIG: drift phase diagram]** — *median samples versus additive prior
drift δ, with the cold-mixture and WSR reference lines and the shaded
beats-both region.*

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
  4/5 and 5/5 majority routing accuracy. Diagnosis: warm-UI's speed
  depends on prior *strength* and *center accuracy* in ways a margin
  rule cannot see, and a drift cliff (0.216 → 0.104 between epochs)
  defeats one-step extrapolation entirely (`results_router2.txt`).

Zero wrong certifications in all 14,400 runs across both versions. **We
deliberately stopped at v2**: iterating until a router wins is exactly
the forking-paths pattern our audits exist to prevent. The surviving
conclusions are that **pure WSR blocks are the best single policy across
whole release trajectories** in both regimes tested, and warm-start UI
is a per-epoch specialist (2–3× faster than WSR at clear-margin epochs
with strong fresh priors).

### 4.5 The invention round, in one paragraph

Before the map existed we treated the allocation/combination layer as an
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
makes that conclusion trustworthy.

### 4.6 Other decisions, same machinery

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
critic should ask. The rate definitions
and the predictions were then **frozen** in
`scripts/fit_overhead_law.py` before the definitive τ-sweep grid
completed, making that grid a genuine out-of-sample test.

**We did not discover (†).** For d = 1 it is a fifty-year-old theorem:
Pollak & Siegmund (1975), Woodroofe (1982, nonlinear renewal theory),
with boundary shape from Schwarz (1962) and Lai (1988), matching lower
bound Pollak (1978), and the (d/2)·log n term from
Krichevsky–Trofimov / Rissanen / Clarke–Barron mixture regret. The
contribution is calibration on real LLM evaluation data, plus the
observation that the modern e-value literature under-cites this
second-order term. That citation gap *is* the honest positioning.

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

### 5.3 The dimension rule: status honest

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
  [3.09, 9.55] — two of three contain the window the adjudication
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
**unidentifiable by censoring** (§4.3) and we decline to score it. Net
status: a coarse regularity that survives where it is testable, not a
law.

### 5.4 The WSR anti-result

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
that inequality reverses as the horizon grows.

### 5.5 The conservation hypothesis: FALSIFIED

**[FIG: frontier overheads]** — *overhead in nats versus certification
fraction for the mixture, epoch-split, split-LRT (b = 25/50/100), and
single-stream arms at τ = 0.15/0.16/0.17, with the 0.5× falsification
line drawn.*

We pre-registered a conservation hypothesis: any method escaping the
(d/2)·log n learning tax should pay for it elsewhere, with a support
window of [0.7, 1.5]× the mixture's overhead and a falsification line at
0.5×. Two errors were caught by audit round 2 and both are corrected in
`results_frontier.txt`:

1. The original artifact **never printed its own pre-registered
   ratios**. Scored properly, the epoch-split arm landed at
   1.674 / 1.716 / 1.484× — the support window was **MISSED at 2 of 3
   margins**, not confirmed.
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
at razor margins), and transfer priors (recurring evaluations, §4.4).
The binding design question is not "mixture versus allocation" but
"which tax escape fits the deployment".

### 5.6 The live capstone: a consistency check, with the severity quantified

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
  P(≥ 14/16 UNSAFE) ≈ 1.000 and P(zero SAFE) ≈ 1.000 — **two of three
  criteria were near-unfalsifiable** — and P(median in window) ≈ **0.94**.
  The pass discriminates only ±1 in d.
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
test. The severe zero-fit result in this arc is the single-stream grid
prediction of §5.2, which needed no fitting at all.

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
applied: the **strawman split arm** (§5.5); a **CRN defect** (streams
desynchronize after replication 1) that made 4 of 6 bootstrap CIs
straddle zero as published, fixed by a correctly paired re-run; a
**cherry-picked value** (two contamination premiums reported, the third
— which breached the cap — omitted; all three now printed); **vacuous
evidence** ("zero wrong certifications" cited as validity evidence when
no replication was under the null, fixed by the adversarial null MC of
§4.4; and a residual criterion with P(pass) = 1.00); an
**oracle-adjacent prior framed as a realistic stale epoch** (16/1000
labels differ), fixed by promoting the drift phase diagram to the
realistic statement; the 3-for-3 → 2-for-3 dimension-rule downgrade and
two withdrawn non-reproducible numbers (§5.3); a shared-RNG-stream
defect across τ-grid points (fixed with per-(τ, method) seeds in the
local and MBPP grids); and the capstone severity analysis (§5.6). Every
verdict table from both rounds is in `audit/`.

### 6.2 Pre-registration with every miss scored

Predictions were frozen in the scripts that produce the artifacts, and
the **scoring is printed inside the artifact**, misses included. The
complete miss ledger for the second half of the project:

| prediction | verdict |
|---|---|
| UI dimension window d ∈ [1.5, 3.5] | MISSED (measured 3.37 / 4.04) |
| Warm-start benign overhead ∈ [1.5, 6] nats | MISSED LOW at all three margins (0.76–1.24) — favorably wrong is still wrong |
| Drift asymmetry direction | **REVERSED** (mechanism diagnosed, rule inverted) |
| Inverted-prior premium "3–4 nats" | wrong (forgot the K factor; measured ≈ +9.9 per-stratum) |
| Conservation window [0.7, 1.5]× | epoch-split MISSED at 2 of 3 margins; split-LRT FALSIFIES |
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

Against this ledger, the three *load-bearing* passes are: the
single-stream zero-fit prediction (§5.2), the out-of-family dimension
prediction (§5.3), and the live WSR arm (predicted UNSAFE ≥ 7/8, median
∈ [150, 450], zero SAFE; observed 7/8, median 224, zero SAFE, $0.25 —
`results_live_wsr.txt`). Others passed too — chain P2–P4, local-pool
P1–P3, MBPP P2, the drift validity and saturation clauses, the capstone
(at the severity of §5.6) — but several of those were, by our own audit's
finding, near-unfalsifiable, and we say so rather than counting them.

### 6.3 The information-bound guard

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
   and fresh sampling randomness, same 1,000 prompts (§5.6).
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
    three statistics: overshoot, median-versus-mean, tracking terms and
    the exact regret constants are unproven here.

---

## 8. Related work

**Anytime-valid inference and betting.** Betting confidence sequences
for bounded means (Waudby-Smith & Ramdas 2023) supply the WSR hedged CS
and the predictable-λ schedule we both use and criticize (§5.4);
Shekhar & Ramdas (2023) and Waudby-Smith, Stark & Ramdas (2021, RiLACS)
are the adjacent estimation and audit lines. Turner, Ly & Grünwald
(2022) and Turner & Grünwald (2023) supply the anytime-valid contingency
and stratified constructions behind our per-stratum α/K combination.
Spertus & Stark (2022) and **Spertus, Sridhar & Stark (2024)** give the
union-intersection test-supermartingale with optimized allocation that
serves as our state-of-the-art baseline (§4.1).

**Sequential LLM evaluation.** Wu, Nair & Candès (2026), Hsu & Shekhar
(2026), CELEUS (2026), PACE (2026) and Zhou et al. (2026) bring
sequential and e-value machinery to LLM evaluation. Hsu & Shekhar
independently report uniform sampling beating adaptive querying, which
corroborates our regime-(b) and regime-(c) findings. None of these
provide a heterogeneity-indexed design map or a replayable multi-vendor
testbed, which is the gap this paper fills.

**Classical sequential analysis and universal coding.** The
second-order expansion of §5 is classical: Wald (1945) for the SPRT;
Schwarz (1962) and Lai (1988) for boundary shape; Pollak & Siegmund
(1975), Pollak (1978) and Woodroofe (1982, nonlinear renewal theory) for
the d = 1 expansion and its matching lower bound; Rissanen (1984),
Clarke & Barron and Krichevsky–Trofimov for mixture regret; **Xie &
Barron (1997)** (and Watanabe's RLCT) for the boundary/singular
coefficient behind d = K + #boundary. Armitage (1954) and Armitage,
McPherson & Rowe (1969) are the peeking and sequential-McNemar
ancestors; Mahalanobis (1946) is the interpenetrating-subsampling
ancestor of the block reduction. **Wasserman, Ramdas & Balakrishnan**
(universal inference / split-LRT) is the lineage of the arm that
falsified our conservation hypothesis (§5.5). Our positioning with
respect to all of this is citation, not discovery.

---

## 9. Reproducibility and artifacts

Every offline experiment replays from the committed outcome pools with
no API access. `./reproduce.sh [quick|all|<script>]` re-runs them and
diffs SHA256 checksums against the committed artifacts; the smoke test
is **byte-identical**. All results are deterministic given the pools
(BASE_SEED = 42; headline comparisons re-verified at seeds {7, 2024,
99999}). Checksums are tamper-evidence, not proof of reproduction —
`reproduce.sh` is the actual demonstration. Raw generations for every
call are stored under `data/`, including the pre-fix archives
(`data/archive_pre_multipleof_fix/`).

**Ledger.** ≈ 8,600 OpenAI API calls through the bolstering round at
≈ $2.02 (FINDINGS ledger; includes the $0.25 live WSR arm,
`results_live_wsr.txt`), plus ≈ $2.68 for the live capstone
(`results_live_prediction.txt`) — under $5 total. The llama3.2-3b,
qwen2.5-7b and both MBPP pools cost nothing: they were collected locally
through Ollama with the identical protocol. Test suite: 76 passing
tests.

**Figures.** Figure 1 (pool heterogeneity), Figure 2 (width vs n),
Figure 3 (peeking miscoverage), Figure 4 (certification: allocation and
feasibility), Figure 5 (paired comparison; block reduction), Figure 6
(invention-round scoreboard) are in `paper/figures/`. Three figures are
in preparation: **[FIG: design map]** (§4), **[FIG: drift phase
diagram]** (§4.4), **[FIG: frontier overheads]** (§5.5).

**Key artifacts by section.**

| section | artifacts |
|---|---|
| §3 testbed | `results_crossmodel.txt`, `results_local_law.txt`, `results_mbpp_law.txt`, `results_overhead_law_code.txt` |
| §3.4 prerequisites | `results_advanced.txt`, `results_codetask.txt`, `results_realllm_betting.txt`, `results_block_reduction.txt` |
| §4.1 hard margins | `results_wsr_hard.txt`, `results_tasc_hard.txt`, `results_uncertainty.txt`, `results_spertus_baseline.txt`, `results_spertus_crn.txt`, `results_local_law.txt` |
| §4.2 easy margins | `results_crossmodel.txt`, `results_ui_grow.txt` |
| §4.3 mild heterogeneity | `results_mbpp_law.txt` |
| §4.4 warm start | `results_warmstart.txt`, `results_warmstart_joint.txt`, `results_warmstart_null.txt`, `results_warmstart_drift.txt`, `results_warmstart_chain.txt`, `results_router.txt`, `results_router2.txt` |
| §4.5–4.6 | `results_ui_grow.txt`, `results_sharp.txt`, `results_ppc.txt`, `results_model_comparison.txt`, `results_sprt_comparison.txt`, `results_graded_scores.txt` |
| §5 expansion | `results_overhead_law.txt`, `results_overhead_fit.txt`, `results_overhead_law_code.txt`, `results_adjudication.txt`, `results_frontier.txt`, `results_live_prediction.txt`, `audit/out_law_accounting.txt` |
| §6 methodology | `audit/AUDIT_LAW_CAPSTONE.md`, `audit/AUDIT_WARMSTART.md`, `AUDIT_PREP.md`, `results_live_wsr.txt` |

---

## References

Armitage (1954); Armitage, McPherson & Rowe (1969); Wald (1945);
Mahalanobis (1946); Schwarz (1962); Pollak & Siegmund (1975); Pollak
(1978); Woodroofe (1982); Rissanen (1984); Lai (1988); Lai & Zhang
(1994); Clarke & Barron (1990); Krichevsky & Trofimov (1981); Xie &
Barron (1997); Watanabe (2009); Maurer & Pontil (2009); Wasserman,
Ramdas & Balakrishnan (2020); Waudby-Smith, Stark & Ramdas (2021,
RiLACS); Spertus & Stark (2022); Turner, Ly & Grünwald (2022);
Waudby-Smith & Ramdas (2023); Shekhar & Ramdas (2023); Turner & Grünwald
(2023); Spertus, Sridhar & Stark (2024, arXiv:2409.06680); Wu, Nair &
Candès (2026, arXiv:2601.20251); Hsu & Shekhar (2026, arXiv:2607.17409);
CELEUS (2026, arXiv:2606.20820); PACE (2026, arXiv:2606.08106); Zhou et
al. (2026, arXiv:2605.07002); Resolution Diagnostics (2026,
arXiv:2605.30315).
