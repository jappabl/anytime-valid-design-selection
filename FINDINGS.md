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

The difficulty ordering is preserved for the three OpenAI models,
both task families, and the two stronger local models (llama3.2-3b
z = 0.48, qwen2.5-7b z = 1.65 on the simple-vs-medium boundary — noise
level). SCOPE CORRECTION (2026-08-14, release-trajectory pools): the
ordering BREAKS for the weakest models tested — llama3-8b has simple
3.6x HARDER than medium (0.456 vs 0.128, z = +8.65) and qwen2-7b
violates at z = +2.76. The structural grading (frozen before any
collection, no per-template tuning) induces the intended order for
capable models and breaks down at the simple/medium boundary for weak
ones — a scoping finding of the same shape as the temp-0 transfer
boundary: the testbed's assumptions are capability-dependent, and the
violation size grows as capability falls. Dominant failure mode for
capable models: character counting (exact-length strings, long digit
runs). The pre-audit table had gpt-4.1-mini at
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
   downward prior drift (model regressed) is cheap (robust beats-WSR
   region |delta| <= 0.015; the -0.03 point is a seed-level tie with
   WSR — 362 vs 350 under rev-2 CRN, 364 vs 374 under rev-1; beats
   cold even at -0.10) while upward drift is expensive (loses to WSR
   by +0.015, saturates at the contamination floor by +0.06); zero
   wrong certifications at every drift. My pre-registered asymmetry prediction was REVERSED — the
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

8. Prior-routed portfolio: two pre-registered router iterations BOTH
   failed their targets (1.090x and 1.259x pure WSR on the two test
   trajectories; targets <= 1.00 / <= 0.85) with zero wrong
   certifications; failure mechanisms characterized (prior starvation
   after fast epochs; drift cliffs defeating extrapolation;
   kappa-blindness of margin rules). Pure WSR is the best single
   policy across whole release trajectories; warm-start remains the
   per-epoch specialist. Third independent confirmation of the
   meta-finding that simple robustness beats sophisticated adaptivity
   at practical scales ([results_router.txt](results_router.txt),
   [results_router2.txt](results_router2.txt)).

9. Conservation hypothesis FALSIFIED (audit round 2 + frontier
   revision 2): the original "supported" reading rested on an artifact
   that never printed its own pre-registered ratios (epoch-split
   actually MISSED the support window at 2 of 3 margins) and on a
   strawman one-shot arm that charged its burn-in to the martingale. A
   faithful discard-burn-in split-LRT crosses the pre-registered
   falsification line (0.373x / 0.398x of the mixture overhead at >=95%
   certification) — sample splitting escapes the learning tax at
   practical scales, paying with an abstention tail that binds only at
   razor margins. The cold-start design map gains a third escape route
   alongside rate-sacrifice (WSR) and transfer priors
   ([results_frontier.txt](results_frontier.txt)).

### F15. The design boundary ported out-of-family: what survives, what breaks (safety domain)

A fourth task family stress-tests the derived single-vs-WSR boundary in a
domain nobody built it for: StrongREJECT harmful-compliance on eight small
local models (313 prompts, 6 published category strata, a deterministic
refusal-string proxy grader). Per-model numbers here are POOL PARAMETERS
(pooled compliance p\*, category heterogeneity ratio R) reported exactly like
the JSON/MBPP pools — **not** safety rankings; single small models, one
corpus, one proxy grader, no human calibration, pool-scoped estimand. This is
the MILD-to-moderate regime (five ratios 1.16–5.40, one outlier 17.0; p\*
0.019–0.857 *across* models): between-**model** variance dominates
between-stratum variance, so stratification buys little. FROZEN before any
certification ([results_safety.txt](results_safety.txt)), the reused machinery
(single_fourterm; wsr_crossing with its K=4 envelope; v_kelly_block
generalized to K=6) called **SINGLE** on two pools and **TIE** on four —
WSR outright on none. Measurement (three CRN-paired arms, v2c Harrell-Davis
bootstrap, 150 reps/arm) splits the map cleanly: the **single-arm predictor
PORTS** (measured single medians within ~5% of single_fourterm on all six
pools), but the **WSR arm certifies 19–37% faster than its K=4 envelope
predicts** on the four mid/high-p\* pools, so WSR is the faster arm on 4/6
(single wins only on the lowest-p\* pool, qwen2-7b; qwen2.5 ties, as frozen).
**P1 FAILS — 1/2 resolving HITs (qwen2-7b HIT; mistral-7b MISS: predicted
single, WSR won).** The miss localizes precisely: the WSR overhead envelope is
K=4-derived and under-models the larger variance reduction of K=6 stratified
blocks — the boundary's *structure* and *single-arm predictor* port, the
fitted WSR *constant* does not (re-derive it for K=6). What else ports: UI+RR
is dominated everywhere (P2 — UI 2–5× slower than the faster arm, min median
gap 945), the α guarantee holds (P3 — 4/2700 = 0.0015 wrong certifications),
and the boundary's one TIE call it could resolve (qwen2.5) is confirmed. A
reportable MISS, not tuned to pass — the out-of-family test names the single
non-portable constant and confirms the rest of the map transfers. The string
grader is a coarse proxy — it disagrees with a gemma2:9b judge on **43%** of a
60-response regeneration (over-counting compliance: 26/28 of its "complied"
calls the judge reads as refusals; a head-prefix-vs-whole-response construct
gap, [results_safety_noise.txt](results_safety_noise.txt)) — which is exactly
why p\* here is a *pool-graded parameter*, never a compliance measurement. The
design-selection result is invariant to that: the certification mechanics
(which arm crosses first, α coverage) depend only on the binary labels, not on
what they mean.

**Addendum (2026-08-19) — the miss's one constant, measured.**
[results_wsr_k.txt](results_wsr_k.txt) re-measures the WSR overhead envelope at
K ∈ {2, 4, 6, 8} on a single frozen grid (iid Bernoulli pools, three p × five
margins, the shipped `WSRBlockCS`, common random numbers across K, 60/60 rungs
≥97% certified). The envelope is K-dependent and its constants are **linear in
K** — d_K = 4.141 − 0.427·K and c_K = 0.964·K − 8.980, residuals ≤5% of each
constant's range — so larger blocks carry a smaller effective dimension and
less overhead at the horizons the boundary actually uses; a short-horizon
plateau appears at K = 4, 6, 8 but not at K = 2. Read from the envelope side,
the committed K=4 constants over-predict n_wsr by **+19.3% to +37.2%** on the
four mid/high-p\* safety pools — the same +19–37% the certification measured,
arrived at independently. A labelled post-hoc diagnostic transports the
measured K=4→K=6 *difference* onto the committed envelope (the absolute level
is not transportable: this grid is homogeneous, R = 1, while c_short = 2.3 was
calibrated on extreme-heterogeneity pools, so the regression anchor P1 FAILS
for that pre-stated reason and not for a K reason). The transport shrinks the
over-prediction to [−0.9%, +14.5%] and moves mistral-7b off SINGLE — but to
TIE, not to the measured WSR, and it collapses the qwen2-7b HIT to TIE as
well, leaving the domain with zero resolving predictions. **Block size accounts
for most of the magnitude and none of the resolution**: the miss stands as
scored, and the honest next clause is a joint c(R, K), not a K-only patch.

**Second addendum (2026-08-19) — the joint (R, K) surface: R is not the missing
argument.** [results_wsr_rk.txt](results_wsr_rk.txt) measures that clause on a
designed 12-cell grid — K ∈ {2, 4, 6} × R ∈ {1, 3, 10, 30}, two-level
K-stratum pools (half the strata at p_lo, half at p_hi, ratio R, mean exactly
p\*), one draw per stratum per block into the shipped `WSRBlockCS`, the τ ladder
solved per (p\*, R) to a *common* median window so that no cell's effective
local fit spans a different n-range, and V the exact Poisson-binomial
block-mean Kelly rate (it matches the shipped 2^K enumeration at K = 4 to
1.4e−17); 96/96 rungs certified ≥99%. The result is a **null on R**: at fixed K,
c is non-monotone in R, and the entire R = 1 → 30 endpoint change is −0.64 /
−0.15 / +0.63 nats at K = 2 / 4 / 6 — inconsistent in sign and each at most
0.37 of its own standard error, so the pre-registered monotonicity predicate
fails in the informative direction. The fitted surface says it quantitatively:
d = 4.171 − 0.463·K − 0.019·log R and c = −8.245 + 0.919·K − 0.108·log R, whose
log R terms move the constants by 3.5% and 10.0% of what K moves them by, well
inside the residual scatter — log R is rejected as a carrier because the R
*effect* is null, not because some other R-carrier is wanted, and the K
coefficients independently reproduce the K artifact's linear laws on a
different profile family. The regression anchor (P1) passes at K = 2 and K = 6
and fails at K = 4, where the two independently measured envelopes nonetheless
agree to within 0.45 nats — about 7% in n — across the fitted range: a d↔c
trade-off inside a two-parameter local fit, not a disagreement about the
envelope. Plugged back into the safety freeze at (K = 6, each pool's own R),
the joint envelope resolves three pools instead of two but matches the measured
winners **1/2, exactly the frozen rate** (llama3.2-3b gained, the qwen2-7b HIT
lost, mistral-7b again moving only to TIE). The miss stands as scored, twice
over, and the outstanding clause is closed in the negative: *heterogeneity is
not what the K = 4 envelope was missing.* Across the six safety pools p\* and
log R are confounded at −0.87, so the pools alone could never have separated
those two — which is exactly why a designed grid was needed, and what it says
is that with p\* held fixed, R does essentially nothing.

### F13. The design-space partition (derived, field-opening)

The four-regime design map is now a DERIVED partition of
(p*, heterogeneity ratio, margin), one crossing-time equality per
design pair in the shared expansion (results_partition.txt). Two
results: winner regions come with TIE-BAND WIDTHS (where design choice
is free, the practically useful part), and UI+RR is provably DOMINATED
(outright fastest at 0/84 derived cells, matching every grid where
observed), collapsing the honest map to TWO regions (single | WSR).
The single|WSR boundary is verified (phase v2b); the UI-dominated
claim is derived + grid-consistent, three-arm verification queued.
Falsifiable: one measured UI-outright-win refutes it. Follow-on:
optimal stratification as the inverse problem (finite derivable K).

### F12. Warm-start certification: the bottleneck solved where it matters

The learning tax (F11) binds fully-adaptive cold-start procedures.
Using a prior epoch with ε-contaminated transfer priors converts it to
**0.6–1.4 nats** (from 15.5–18.4) with no abstention corner and zero
wrong certifications in any arm
([results_warmstart.txt](results_warmstart.txt),
[results_warmstart_joint.txt](results_warmstart_joint.txt)).

AUDIT ROUND 2 QUALIFICATIONS (audit/AUDIT_WARMSTART.md), all applied:
the benign "prior epoch" is the SAME prompt pool relabeled by a
validator fix (16/1000 labels differ — 0.0014 nats of residual KL), so
the benign arm measures an ORACLE-ADJACENT warm start; realistic
staleness is the drift phase diagram (item 6: robustly beats WSR
within ~0.015 downward drift, breaks by +0.015 upward; -0.03 is a
seed-level tie). "Beats every incumbent including WSR"
holds for fresh strong priors at clear margins — per-epoch, not
trajectory-wide (items 7–8: WSR wins whole release chains). Validity
holds because the prior is fixed w.r.t. the resampling stream, not
because it "predates" anything — and it survived a genuinely
adversarial null Monte Carlo (worst type-I 0.047 ≤ α = 0.05, now a
first-class artifact:
[results_warmstart_null.txt](results_warmstart_null.txt)). The ε-cap
bounds the log e-value premium PATHWISE (verified exact to 1e-9);
median crossing-time gaps are a downstream statistic and all three are
disclosed. Four pre-registered prediction misses en route are logged
in THEORY.md. Practical statement: first-contact evaluation pays the
tax (or splits, F11 item 9); every recurring evaluation with smooth
drift lives in the loophole.

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
