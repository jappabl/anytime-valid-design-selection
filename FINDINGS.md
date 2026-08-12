# Which Sequential Design Should You Use? Anytime-Valid Evaluation of LLM Failure Rates on a Replay Testbed

**Research synthesis — 2026-08-10, revision 3 (post-audit, post-bolstering).**
All numbers below were regenerated from the corrected outcome pools after
a four-way adversarial audit (statistics, experimental design, code,
prior art); see [Audit trail](#audit-trail-what-the-adversarial-review-changed).

## Positioning (honest)

Anytime-valid sequential evaluation of LLMs is an active 2024–2026
literature (betting confidence sequences: Waudby-Smith & Ramdas 2023;
stratified anytime-valid inference: Turner & Grünwald 2023, Spertus,
Sridhar & Stark 2024; sequential LLM evaluation: Wu, Nair & Candès 2026,
Hsu & Shekhar 2026, CELEUS 2026, PACE 2026). **This project does not
invent those methods.** Its contributions are:

1. **A cheap, exactly-reproducible replay testbed** for comparing
   sequential evaluation designs against real model behavior with an
   exactly-known estimand (three models × two task families, one
   temperature-0 call per distinct prompt, raw generations stored).
2. **Empirical design-selection findings** the methods literature does
   not provide: which design wins depends on the *decision being
   certified*; a block-reduction WSR sequence beats both the per-sample
   mixture CS and a Bonferroni-stratified route on realistic LLM
   heterogeneity; and mid-block peeking on stratified streams breaks
   both bias *and* coverage, with a single rule ("never peek mid-block")
   repairing both.
3. **Measured cautionary results**: an SPRT baseline that is 10× faster
   when well-specified but catastrophically miscalibrated between its
   hypotheses; fixed-n intervals losing 48% uniform coverage under
   peeking on real streams; and two label-corruption bugs (a float
   `multipleOf` trap, a selection-biased re-query) found by adversarial
   audit and repaired with full re-collection.

## The testbed

Two task families with *structurally* graded difficulty (no per-template
tuning; design frozen before collection, verified by prompt-hash audit):

- **JSON schema generation**: 1,000 unique schemas, 4 strata (regex
  patterns, nesting, arrays, exact-length strings, multipleOf).
- **Code generation**: 320 unique parametrized specs with per-instance
  reference solutions (independently re-implemented and confirmed
  0-mismatch by adversarial audit) and execution-based validation.

One temperature-0 call per distinct prompt gives outcome pools whose
uniform-mixture failure rate p\* is exact *for the pool*. Raw generations
for every call are stored. Decoding at temperature 0 is only
*near*-deterministic: measured two-sided flip rate on full re-query is
~1–2% of prompts (roughly symmetric), so pools are single-epoch
snapshots and p\* carries that epoch qualification.

**Corrected per-stratum failure rates** (after fixing a float
`multipleOf` validator bug that had corrupted 59 labels, and a full
symmetric re-collection of all 3,000 JSON outcomes):

| Task, model | simple | medium | complex | extreme | p\* (pool) |
|---|---|---|---|---|---|
| JSON, gpt-4o-mini | .004 | .000 | .068 | .736 | **.2020** |
| JSON, gpt-4.1-nano | .004 | .004 | .008 | .304 | **.0800** |
| JSON, gpt-4.1-mini | .000 | .000 | .004 | .140 | **.0360** |
| Code, gpt-4o-mini | .000 | .000 | .063 | .138 | **.0500** |

The difficulty ordering is preserved for all three models tested and
both families. Dominant failure mode: character counting (exact-length
strings, long digit runs). The pre-audit table had gpt-4.1-mini at
p\* = .083; most of that was the validator bug.

## Findings

### F1. Peeking destroys fixed-n intervals; the betting CS survives — measured

Uniform miscoverage (interval excludes pool p\* at ANY n ≤ 200, naive
sampling from real gpt-4o-mini outcomes, 2,000 reps): **Wilson 47.7%**,
Wald 100% (partly an n=1 degeneracy artifact — Wald's interval is a
point at n=1; over the window n ∈ [30, 200] Wilson still misses ~28%),
betting CS **3.6%** ([results_advanced.txt](results_advanced.txt), E1;
Figure 3). This is a property of Bernoulli streams at the pool's rate —
classical since Armitage et al. 1969 — measured here at real-model
operating points.

### F2. The betting CS makes sequential evaluation affordable where stitched bounds fail

Known in theory (WSR 2023); measured consequences on real pools:
precision stopping that never fires with stitched Hoeffding∩Bernstein
bounds (0–4% of runs at width ≤ 0.35, n ≤ 200) fires in 100% of runs
with the betting CS; SAFE certification at τ = 0.10 on the code pool
(margin 0.050): betting 500/500 at median 356 samples vs stitched
166/500 within n = 2,000 ([results_codetask.txt](results_codetask.txt)).

### F3. Never peek mid-block: one rule fixes both bias and coverage

Two failures of mid-block peeking on round-robin stratified streams,
one discovered here empirically, one established by our audit's exact
dynamic-programming analysis:

- **Bias**: stopping mid-block systematically undersamples the strata
  later in the rotation; plain "stratified" sampling was sometimes more
  biased than naive at the stopping time. With block-gated stopping,
  conditional bias is 2–3× smaller than naive at ALL four precision
  targets (z = −3.63, −4.49, −4.64, −3.70 on corrected pools) with
  exactly zero composition drift and ~40% lower MAE
  ([results_realllm_betting.txt](results_realllm_betting.txt)).
- **Coverage**: the per-sample mixture CS has NO general guarantee on
  non-iid stratified streams. Exact-DP counterexamples: uniform coverage
  0.80 (K=8 adversarial) and 0.93 (K=4 adversarial) under every-n
  peeking. Block-gated peeking restored ≥ 0.996 in every configuration
  tested ([results_advanced.txt](results_advanced.txt), E2). An earlier
  version of this document claimed general empirical validity with a
  concavity argument; **that claim was wrong and is withdrawn** — the
  audit showed under-dispersion is the failure mechanism, not a safety
  margin.

Group-sequential and survey-sampling literatures know incomplete-block
artifacts; the contribution here is the measured demonstration for
stratified LLM evaluation plus the unified peek-gating rule.

### F4. Stratify → block → bet: provable validity that is also tightest

Complete blocks are iid even when single draws are not, so a WSR betting
CS on block means is exactly anytime-valid — no caveat needed. On real
pools it also *beats* the per-sample mixture CS (which holds only
empirically, F3) and the α/K-Bonferroni per-stratum route
([results_block_reduction.txt](results_block_reduction.txt), Figure 5B):

| criterion | per-sample CS† | WSR on blocks | binarized | stitched EB |
|---|---|---|---|---|
| width ≤ 0.30 | 72 | 72 (1.0×) | 272 | 1288 |
| width ≤ 0.20 | 180 | **124** (1.5×) | 700 | never |
| width ≤ 0.15 | 336 | **184** (1.8×) | 1324 | never |
| certify UNSAFE τ=0.15 | 606 | **254** (2.4×) | 51% certify | 0% |

†empirical validity only, and at full α vs the provable arms' stricter
budgets — the comparison favors the baseline, which still loses.
The honest range is **1.0–2.4×** (no advantage at loose widths, where
both stop at the minimum block count — itself informative). Mechanism:
Var(block mean) = mean p_k q_k / K ≈ 0.017 vs p\*q\* = 0.161, and the
bet adapts to it. The ingredients are classical (interpenetrating
subsampling; WSR); we did not find this composition benchmarked in the
stratified anytime-valid literature. The state-of-the-art comparison
(Spertus–Sridhar–Stark 2024) has now been run — see F10: a genuine
speed/reliability trade, not a clean win for either side.

### F5. The sampling design should follow the decision

With per-stratum betting CSs (α/K, weighted-Bonferroni combination —
construction validated by exact analysis; cf. Turner & Grünwald 2023),
any data-dependent allocation is valid. On corrected pools
([results_crossmodel.txt](results_crossmodel.txt), Figure 4A):

- **UNSAFE certification** (gpt-4o-mini, τ=0.15): decision-directed
  allocation certifies in median **176 vs 588** samples for round-robin
  (3.3×; range across audit seeds 3.1–3.5×) — one bad stratum alone
  carries the weighted LCB over τ, so evidence concentrates there.
- **SAFE certification** (nano/mini): the single-stream mixture CS wins
  (240 and 72 vs 800 and 364 for directed) — every stratum must
  tighten and the α/K split costs. Width-greedy allocation is worse
  still (abstains in 89% of nano SAFE runs): it optimizes width, not
  the decision.
- Two allocation traps, diagnosed and fixed: width-greedy starvation,
  and midpoint-aiming lock-in (aim with the point estimate).

Independent corroboration: Hsu & Shekhar (2026) also find uniform
sampling sometimes beats adaptive querying. Zero wrong certifications
across all certification experiments on corrected pools; the earlier
absolute claim "zero anywhere" was falsified by audit at one seed
(2 wrong in a binarized arm, within the α budget) and is retired —
the guarantee is P(wrong) ≤ α, and observed rates are consistent with
it.

### F6. Paired model comparison: decisive quickly, honest on ties

Sequential McNemar (classical: Armitage 1954; e-process versions exist —
Turner et al. 2022; PACE 2026): discordant outcomes update a betting CS
on θ = P(A fails, B passes | disagreement)
([results_model_comparison.txt](results_model_comparison.txt), Fig 5A):

- gpt-4o-mini vs gpt-4.1-nano (θ = .881): 500/500 correct, median **74
  prompts** (12 discordant).
- gpt-4.1-nano vs gpt-4.1-mini (θ = .734 on corrected pools — the
  pre-audit "near-tie" at θ = .509 was a validator-bug artifact):
  500/500 correct, median 335 prompts.
- **Constructed exact tie** (synthetic, θ = 0.500): abstains 96.0%;
  the 4.0% that certify are false certifications by definition and sit
  within the two-sided α = 5% budget (exact-DP: 3.4–3.7%).

### F7. SPRT baseline: fast where it's right, dangerous where it isn't

Well-specified SPRT is ~10× faster than CS certification (median 48 vs
~600 on real pools) — Wald optimality, reported plainly. Between its two
hypotheses its declarations carry no error control relative to τ:
measured false-certification rates **16–64%** (vs ≤ 0.5% for the CS at
every true rate, which abstains near the boundary)
([results_sprt_comparison.txt](results_sprt_comparison.txt)).

### F8. Graded scores and live validation

- Fraction-of-tests-passed scores (bounded [0,1]) run through
  stratify→block→bet unchanged: "mean score ≥ 0.90" certified 500/500
  at median 276 samples ([results_graded_scores.txt](results_graded_scores.txt)).
- Live at temperature 0.7 (fresh sequential API calls, decisions
  online): live p̂ = 0.209 vs the contemporaneous pool estimand 0.208;
  per-stratum rates within 1.5pp. **The τ = 0.15 arm was pre-registered
  and its written prediction (UNSAFE in every replication) FAILED**:
  11/12 abstained at the 300-call budget — in hindsight the margin
  implies median ~600 samples, a budget we under-specified; the
  procedure abstained rather than erring, but the prediction was wrong.
  **The τ = 0.10 arm was exploratory, not pre-registered** (run after
  observing arm 1), and due to a seeding bug used a *different prompt
  population* (measured live rate ≈ 0.186, so its true margin was
  ≈ 0.086, not 0.108 as first reported): 8/8 correctly certified
  UNSAFE, median 172 calls
  ([results_live_certification.txt](results_live_certification.txt),
  [results_live_certification_tau0.1.txt](results_live_certification_tau0.1.txt)).

### F9. The invention round: four attempts, one map, and a clear winner

Treating the allocation/combination layer as an open problem (validity is
allocation-independent, so invention there is safe), we built and tested
four progressively more sophisticated candidates, each with predictions
stated before running. All four lost. The complete measured map
(median samples to certify, alpha=0.05; artifacts:
[results_ui_grow.txt](results_ui_grow.txt),
[results_tasc_hard.txt](results_tasc_hard.txt),
[results_wsr_hard.txt](results_wsr_hard.txt),
[results_sharp.txt](results_sharp.txt),
[results_ppc.txt](results_ppc.txt)):

| condition (margin) | WSR blocks | bonf+directed | single-stream† | TaSC (ours) | UI+RR |
|---|---|---|---|---|---|
| 4o-mini UNSAFE τ=.15 (.052) | 254 | **190** | 596 | 324 | 944 |
| nano SAFE τ=.15 (.070) | 268 | 792 | **260** | 448 | 520 |
| mini SAFE τ=.15 (.114) | **160** | 356 | 72† | 172 | 176 |
| 4o-mini UNSAFE τ=.17 (.032) | **662** | 808 | 1696 | 1014 | 2518 |
| 4o-mini UNSAFE τ=.18 (.022) | **1308** (94%) | 1802 (91%) | 3186 (48%) | 2388 (90%) | (15%) |
| nano SAFE τ=.11 (.030) | **748** | 3108 (86%) | 1288 | 1874 | 2654 |

†single-stream carries the empirical-validity-only caveat (F3);
(percentages) = certification rate where below 100%. Zero wrong
certifications by any method anywhere.

**The four attempts, each a documented negative:**

1. **GROW greedy allocation** — collapsed without forced exploration;
   even oracle-fed it lost (the least-favorable null re-optimizes across
   strata; greedy growth chases it). Mechanism: nuisance escape.
2. **TaSC (Track-and-Stop certification)** — the principled max-min
   version: sound everywhere (zero wrong, best of the UI family,
   beats single-stream on hard UNSAFE), but never first. Its
   pre-registered predictions failed twice: bonf+directed was 4x better
   than modeled at τ=.17, and the nano "parity" control was lost by
   45%. Realized performance sits ~6x above its own game-value bound —
   the K-parameter learning overhead, tracking slack, and forced
   exploration eat the theoretical advantage at every margin we could
   test within n=4000.
3. **Sharp (predictable recentered) priors** — predicted to save 4-6
   nats; measured to save none and cost a little (recentering on a
   10-observation estimate concentrates the prior in the wrong place
   often enough to lose). The Beta(1,1) mixture is already
   near-minimax; the overhead is the price of learning K parameters,
   not a removable constant.
4. **Prediction-powered refinement** — using gpt-4o-mini's cached
   outcomes to refine the stratification predicted a 19% variance
   cut but measured a net loss: the predictor separates nano's extreme
   stratum too weakly (33% vs 23% sub-rates), and the extra
   draws-per-block overwhelm the gain. The design rule survives:
   refine only when the predictor splits rates strongly enough that
   the variance cut exceeds the K'/K block-cost ratio.

**The winner of the invention round is the simplest structured design we
had already built: stratify -> block -> bet (F4).** It takes first place
outright in three of six conditions — ALL the hard margins — and in four
of six among provably-valid methods (single-stream edges it by 8 samples
on easy-nano but carries the empirical-validity caveat) — the regime where
certification is actually expensive — and holds the estimation-width
crown, with a proof, no allocation machinery, no tuning, and no
mid-block-peeking caveat. Easy-UNSAFE belongs to directed-Bonferroni;
easy-SAFE nominally to single-stream (with its validity caveat; among
provable methods WSR takes it too).

The meta-finding, and the honest headline of the whole exercise:
**on stratified real-model failure streams at practical budgets, one
well-chosen simple reduction beats game-theoretic allocation, adaptive
priors, and prediction-powered refinement — and four pre-stated
predictions failing in a row is what made that conclusion trustworthy.**

### F10. The bolstering round: error bars, the SOTA baseline, and live validation of the champion

Six hardening moves, run after the invention round
([results_uncertainty.txt](results_uncertainty.txt),
[results_spertus_baseline.txt](results_spertus_baseline.txt),
[results_live_wsr.txt](results_live_wsr.txt), `reproduce.sh`,
[DEFENSE.md](DEFENSE.md)):

1. **All six scoreboard wins are statistically significant** under
   common-random-numbers seeding + paired bootstrap on median differences
   (10,000 resamples; abstentions censored at n_max). Tightest win:
   single-stream over WSR on easy-nano, +20 samples, 95% CI [+8, +32].
   No fig6 box downgrades to a tie.

2. **The audit-mandated SOTA baseline (Spertus–Sridhar–Stark 2024) is
   implemented and the verdict is a genuine trade, not a clean win for
   either side.** Our adaptation (inverse bets with frozen predictable
   coefficients, exact boundary minimization; validity verified in both
   directions at 0.007–0.030 ≤ α): the Spertus+greedy UI-TS is FASTER
   when it certifies on 4 of 5 conditions (e.g. 144 vs 244 at easy
   UNSAFE; 176–180 vs 260 at easy SAFE) but abstains 3–63% within the
   same budgets where WSR abstains ~0–10%; at the hardest margin
   (τ=0.18) WSR dominates outright (90% vs 37% certification). The CRN
   censored-median tie-breaker
   ([results_spertus_crn.txt](results_spertus_crn.txt)): **Spertus+greedy
   TAKES the easy-nano-SAFE box** (184 vs single-stream 240, 95% CI
   [+40,+80]); easy-4o-mini-UNSAFE becomes a Spertus/directed
   statistical tie (156 vs 178, CI [−2,+42]); both contested hard
   margins (τ=0.17, nano τ=0.11) are Spertus/WSR statistical ties, with
   WSR nominally ahead; τ=0.18 stays WSR's outright. Final map: THREE
   methods share the frontier — the strongest form of the
   design-follows-decision thesis. Fidelity caveat,
   both directions: this is our variant of their construction (their
   banded AGRAPA version may reduce the abstentions).

3. **It took three attempts to implement the baseline validly**, and
   both invalid drafts were caught by an information-bound smell test
   (medians faster than log(1/α)/game-value are physically impossible):
   draft one used vertex minimization, which requires η-oblivious bets;
   draft two mis-assigned flat (zero-failure) strata to the top of the
   null boundary, starving failure strata. The guard is now built into
   the artifact and flags any arm violating the bound — a small
   methodological export in its own right.

4. **The champion is validated live.** Pre-registered WSR-on-blocks run
   at temperature 0.7 (prediction fixed before launch: UNSAFE ≥ 7/8,
   median in [150, 450], zero SAFE): observed **7/8, median 224, zero
   SAFE** — CONFIRMED, $0.25.

5. **The model × task grid is complete and doubly monotone**: JSON p\*
   (.202/.080/.036) and code p\* (.050/.016/.009) rank the three models
   identically — difficulty ordering transfers across tasks, model
   ordering transfers across families.

6. **Push-button reproduction**: `./reproduce.sh [quick|all|script]`
   re-runs offline experiments from the committed pools and diffs
   checksums (smoke test: byte-identical). [DEFENSE.md](DEFENSE.md)
   carries the judge-defense material. Cross-vendor replication remains
   blocked on a non-OpenAI API key.

### F11. The theory thread: from "law" to calibrated classical expansion

The frontier push (full history in [THEORY.md](THEORY.md)) ended
somewhere better than where it aimed:

1. We conjectured an overhead law n·V = log(1/α) + (d/2)·log n + c,
   froze rates and predictions, and confirmed the FORM out-of-sample
   (R² 0.89–0.98, residuals ≤ 0.39 nats on 30 fresh grid points) —
   while our pre-registered dimension window for the UI statistic
   MISSED (d ≈ 4, not ≈ 2).
2. An adversarial referee then established: the d = 1 case is a
   fifty-year-old theorem (Pollak–Siegmund 1975; Woodroofe 1982;
   Schwarz 1962; Lai 1988; mixture regret per Clarke–Barron), with the
   constant in closed form; our WSR "flat overhead" was a
   finite-window artifact (its λ schedule forfeits the Kelly rate —
   achieved/optimal → 0 — an anti-result worth publishing as a caution
   about the popular predictable-plug-in schedule); and the correct
   dimension rule is **d = K + #boundary-strata** (zero-rate strata
   cost a full log n; cf. Xie–Barron 1997 / Watanabe's RLCT).
3. A live adjudication favored the referee's rule over our window
   (d = 6.50/5.56/6.76 vs predicted 6/6/7; our [3,5] failed on every
   model). AUDIT ROUND 2 DOWNGRADE: under our own ≤0.75-nat criterion
   the score is **2-for-3** (nano-code d=6 gives 0.81; d=5 passes),
   bootstrap CIs are wide enough to contain the rejected window for
   two of three models, and the rule is nearly indistinguishable from
   a constant d ≡ 6 — the test's whole discriminating content is
   "d ≈ 6, not ≈ 4"
   ([results_adjudication.txt](results_adjudication.txt), new artifact).
4. The salvage, as corrected by audit round 2: **the single-stream
   closed form reproduces measured medians within −3%…+7% with ZERO
   fitted parameters** (independently re-verified) — the strongest
   quantitative result in the arc. The UI arm needs one fitted
   constant per model (±12% without it). The invention-round
   scoreboard has a citable mechanism: the simple block reduction
   wins at practical n because it sacrifices a bounded rate factor
   while mixture-based methods pay a ~(d/2)·log n learning overhead.
   The modern e-value literature under-cites this classical
   second-order term; that citation gap is the honest positioning.
5. Capstone: pre-registered pass, severity quantified by audit round
   2. The freeze and the crash-resume replay are verified beyond doubt
   and all three criteria passed (**median 1200 ∈ [800, 1450], 16/16
   UNSAFE, zero SAFE**) — but two criteria were near-unfalsifiable
   (P ≈ 1.000 under the prior), P(median-in-window) was ≈ 0.94, and
   the live run reused the calibration prompt population at a new
   threshold. A consistency check passed, not a severe test; THEORY.md
   has the full disclosure
   ([results_live_prediction.txt](results_live_prediction.txt)).

6. Drift phase diagram: warm-start's staleness budget is ASYMMETRIC —
   downward prior drift (model regressed) costs almost nothing (still
   beats WSR at delta=-0.03, beats cold even at -0.10) while upward
   drift is expensive (loses to WSR by +0.015, saturates at the
   contamination floor by +0.06); zero wrong certifications at every
   drift. My pre-registered asymmetry prediction was REVERSED — the
   miss is documented in THEORY.md with the mechanism (zero-rate strata
   absorb negative drift via clipping; positive drift poisons all
   strata). Rule: shade transfer priors down when uncertain
   ([results_warmstart_drift.txt](results_warmstart_drift.txt)).

7. Multi-epoch chaining: warm-start survives its own deployment loop —
   beats cold at every epoch, zero wrong certifications through the
   SAFE/UNSAFE flip (poisoned-prior epoch runs at 0.96x cold, never
   catastrophic), and chained estimates track the oracle prior within
   10% after five epochs. The informative refutation: WSR dominates the
   near-boundary epochs (certifying where all UI variants abstain), so
   the production design is a PRIOR-ROUTED PORTFOLIO — margin-based
   routing decided from prior-epoch data only, valid with no
   alpha-splitting
   ([results_warmstart_chain.txt](results_warmstart_chain.txt)).

### F12. Warm-start certification: the bottleneck solved where it matters

The learning tax (F11) binds only cold-start. Using a prior epoch (the
archived stale/mislabeled pools — realistic, not oracle) with
ε-contaminated transfer priors: overhead drops 15.5–18.4 → **0.6–1.4
nats**, medians beat every incumbent including WSR at all tested
margins, worst-case adversarial-prior degradation is provably and
measurably capped at log(1/ε) ≈ 2.3 nats (joint contamination), and
zero wrong certifications occurred in any arm
([results_warmstart.txt](results_warmstart.txt),
[results_warmstart_joint.txt](results_warmstart_joint.txt)). Three
pre-registered prediction misses en route are logged in THEORY.md.
Practical statement: first-contact evaluation pays the tax; every
recurring evaluation lives in the loophole.

## Audit trail: what the adversarial review changed

Four independent adversarial audits (statistics, experimental design,
code, prior art) ran on 2026-08-02. Material corrections, all applied:

1. **Float multipleOf validator bug** — 59 labels corrupted (52 for
   gpt-4.1-mini); validator fixed with exact decimal arithmetic,
   regression-tested.
2. **Selection-biased first repair** — re-querying only failures
   exploited temp-0 nondeterminism one-sidedly; replaced by full
   symmetric re-collection of all 3,000 JSON outcomes (flip matrices
   published above; originals archived in
   `data/archive_pre_multipleof_fix/`).
3. **E2 validity claim withdrawn** — exact-DP counterexamples found;
   replaced by the block-gating result (F3) and the provable WSR route
   (F4).
4. **"Zero wrong certifications anywhere" retired** — falsified at one
   seed by an instrumentation-blind arm; instrumentation fixed, claim
   restated as the α guarantee plus observed rates.
5. **Pre-registration language corrected** (F8) — arm 2 relabeled
   exploratory; arm 1's failed prediction reported as failed.
6. **Live arm-2 population bug** — `--seed-offset` unintentionally
   re-seeded the prompt dataset; script fixed, numbers requalified.
7. **Selective ranges restored** — the 1.0× row is back in F4's table;
   all four z-values reported in F3; Wald's 100% flagged as partly
   degenerate; "near-tie" replaced by a constructed exact tie.
8. **WSR grid-edge bug fixed** — true means at exactly 0 or 1 were
   silently excluded; bounds now extend to true endpoints
   (regression-tested).
9. **Three assert-free test files** removed from the suite (moved to
   scripts/); multipleOf and WSR-edge regression tests added. Suite: 76
   passing tests.
10. **Claims scoped to pools** — p\* is a pool property under a chosen
    uniform stratum weighting (a design choice: reweighting `extreme`
    to 10% gives p\* ≈ 0.086 for gpt-4o-mini); τ margins are stated
    with each certification cost; "the model's failure rate" language
    is bound to "on this pool" throughout.

Verified by audit (attacks that failed): the Beta-Bernoulli e-process is
an exact martingale (E[e] = 1 to 12 decimals) with exact-DP time-uniform
miscoverage ≤ 0.035 at every p on a 250-point grid; WSR predictability,
positivity, and hedging are correct; the weighted-Bonferroni
construction survives adversarial allocation (exact); all 320 code-task
reference solutions match their specs (independent re-implementation,
0 mismatches); prompt-hash audit confirms no post-pilot dataset tuning
(0/1000 mismatches); headline comparisons hold across seeds
{7, 2024, 99999}.

## Open items (highest value next)

1. Benchmark F4 against Spertus–Sridhar–Stark (2024) union-intersection
   with optimized allocation — without it, F4's dominance claim is
   against non-state-of-the-art baselines.
2. Commit the repository (nothing is under version control — the
   reproducibility section of any paper is not honest until it is).
3. Related-work integration in [paper/DRAFT.md](paper/DRAFT.md) per the
   prior-art audit (CELEUS, PACE, Hsu & Shekhar, Wu–Nair–Candès,
   Zhou et al. 2026).
4. MC error bars on headline medians (bootstrap), and common-random-
   number seeding across arms.

## Ledger

~8,600 API calls total (3,000 + 3,000 re-collection JSON, 320 code,
376 discarded asymmetric re-query, ~4,800 live), ≈ **$2.02** spent,
all collection scripts idempotent with hard caps. All results files
carry SHA256 checksums (tamper-evidence, not proof of reproduction).

| Artifact | Content |
|---|---|
| [results_betting_cs.txt](results_betting_cs.txt) | Betting CS fix validation |
| [results_realllm_betting.txt](results_realllm_betting.txt) | Precision stopping: naive vs stratified vs block-gated |
| [results_advanced.txt](results_advanced.txt) | E1 peeking, E2 exact-DP coverage analysis, E3 allocation, E4 variance theory |
| [results_crossmodel.txt](results_crossmodel.txt) | 3 models, certification, directed allocation |
| [results_codetask.txt](results_codetask.txt) | Second task family |
| [results_model_comparison.txt](results_model_comparison.txt) | Sequential McNemar incl. constructed tie |
| [results_block_reduction.txt](results_block_reduction.txt) | Stratify→block→bet vs alternatives |
| [results_sprt_comparison.txt](results_sprt_comparison.txt) | Wald SPRT baseline |
| [results_graded_scores.txt](results_graded_scores.txt) | Bounded-score certification |
| [results_live_certification*.txt](results_live_certification.txt) | Live temp-0.7 arms (see F8 qualifications) |
| [EXTENSIONS.md](EXTENSIONS.md) | Cross-domain mapping |
| [paper/DRAFT.md](paper/DRAFT.md) | Paper draft (revision pending per audit) |
