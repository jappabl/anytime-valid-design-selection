# The Certification-Overhead Expansion (calibration of a classical result)

**STATUS AFTER ADVERSARIAL REFEREE (2026-08-11): what this document
initially called a conjectured "law" is, for the d = 1 case, a
fifty-year-old theorem — Pollak & Siegmund (1975), Woodroofe (1982,
Nonlinear Renewal Theory), with boundary shape from Schwarz (1962) and
Lai (1988), matching lower bound Pollak (1978), and the (d/2)·log n
term from Krichevsky–Trofimov / Rissanen / Clarke–Barron mixture
regret. Our contribution is repositioned honestly as: (i) a
CALIBRATION of the classical expansion on real LLM evaluation data,
with zero-free-parameter closed-form predictions matching measured
medians within ±5%; (ii) the boundary-stratum dimension rule
d = K + #boundary-strata for the UI statistic (classically related to
Xie–Barron 1997 / Watanabe's RLCT; apparently unstated in the modern
e-value literature); (iii) an ANTI-RESULT for the WSR schedule — its
predictable λ ∝ 1/√(t log t) forfeits the Kelly growth rate entirely
(achieved/optimal → 0), so its practical advantage is "a bounded rate
sacrifice beats a (K/2)·log n additive penalty when log n ≈ 6–8," and
our earlier "flat overhead" reading was a finite-window artifact; and
(iv) the observation that the modern e-value literature under-cites
this classical expansion (Agrawal–Ramdas stop at first order). The
referee's full report is summarized at the bottom; everything above the
verdict sections is preserved as honest history.**

**Original status line (superseded):** empirical law with frozen
out-of-sample test pending.
Provisional fits below use only medians already committed in
results\_\*.txt; the rate definitions and predictions were FROZEN
(2026-08-11, in [scripts/fit_overhead_law.py](scripts/fit_overhead_law.py))
before the definitive τ-sweep grid
([scripts/run_overhead_law.py](scripts/run_overhead_law.py)) completed,
making that grid a genuine out-of-sample test.

## The law

For an e-process certification method stopping when its statistic
crosses 1/α, the median sample count n at margin |p\* − τ| satisfies

    n · V  ≈  log(1/α) + (d_eff / 2) · log n + c            (†)

where:

- **V** is the method's *information rate* — the expected log-growth per
  sample of the method's statistic under the true distribution against
  its least-favorable null. Crucially, V is method-specific (frozen
  definitions):
  - single-stream mixture CS: V = KL(p\*, τ) (pooled Bernoulli rate);
  - UI product e-process with round-robin: the
    *allocation-constrained* boundary value
    min over {w·m = τ} of mean_k KL(p_k ‖ m_k) — NOT the max-min game
    value, which presumes optimal allocation;
  - WSR on block means: the exact per-sample optimal Kelly growth
    sup_λ E[log(1 + λ(M − τ))] / K over the (computable, 16-atom) block
    distribution — NOT the Cramér rate, which is a false-alarm exponent,
    not an e-process growth ceiling.
- **d_eff** is the effective number of parameters the statistic must
  learn (each costing ~½·log n of growth — the classical mixture/
  plug-in regret per dimension);
- **c** is a method constant (prior mass, discreteness, overshoot).

## Why (derivation sketch, not a proof)

Wald's identity gives E[τ_stop] ≈ (crossing level)/(growth rate). The
crossing level is log(1/α). A statistic that must learn d free
parameters pays the universal-coding price ~ (d/2)·log n relative to the
oracle that knows them (Krichevsky–Trofimov / mixture regret), raising
the effective crossing level to log(1/α) + (d/2)·log n + c. Dividing by
the per-sample rate V yields (†). The gap between "sketch" and "proof"
is real: overshoot, median-vs-mean, tracking terms, and the exact regret
constant for each statistic are unproven here — this is the open
formalization problem named in FINDINGS.

## Iteration history (full disclosure)

The rate definitions were corrected twice against already-committed
data before freezing — reported because a critic should ask:

1. First pass used the max-min game value for UI+RR: fit failed
   (d = 12, R² = 0.24). Diagnosis: round-robin cannot realize the
   optimal-allocation rate. Fix: allocation-constrained value.
2. First WSR pass used a Gaussian block approximation, second the
   Cramér rate: both failed with *negative* slopes. Diagnosis: an
   e-process's ceiling is its optimal Kelly growth, not a
   large-deviations false-alarm exponent. Fix: exact Kelly-block rate.

Each correction was a principled repair of an identified
mis-specification, not a free parameter — but the only clean answer to
the forking-paths concern is the frozen out-of-sample test now pending.

## Provisional fits (committed points only; ≥90% certification)

| method | d_eff | c | max resid | interpretation |
|---|---|---|---|---|
| single-stream | 0.66 | +0.78 | 0.35 nats | ~1 learned parameter |
| UI+RR | 2.26 | +7.04 | 0.37 nats | ≈ # failure-bearing strata (2) |
| WSR blocks | −0.18 | +2.27 | 0.22 nats | **zero** — constant ~1.7-nat tax |

The invention-round scoreboard follows from these three lines: WSR wins
hard margins because its overhead is flat in n while every alternative
pays d_eff/2 · log n; the sophisticated methods' larger V is consumed by
their larger d_eff until margins are extreme. Equating (†) between two
methods yields the crossover margin in closed form given (V, d, c).

## Frozen predictions and the OUT-OF-SAMPLE VERDICT (2026-08-11)

Scored against 30 fresh grid points
([results_overhead_law.txt](results_overhead_law.txt),
[results_overhead_fit.txt](results_overhead_fit.txt)):

- single-stream: window d ∈ [0.4, 1.6] → measured **0.79 / 1.01**
  (pooled 0.94, R² 0.91, resid ≤ 0.17 nats): **PASS**, centered on the
  theoretical d = 1.
- WSR: window d ∈ [−0.5, 0.5], c ∈ [1.6, 3.0] → measured **0.00 /
  −0.44**, c 2.31 / 2.83 (resid ≤ 0.39): **PASS** per model (pooled
  c = 3.27 marginally outside).
- UI+RR: window d ∈ [1.5, 3.5] → measured **3.37 / 4.04** (pooled
  3.83, R² 0.95): **WINDOW MISSED.** The law's form fits superbly, but
  the pre-registered "≈ #active strata" interpretation was WRONG: the
  dimension is ≈ K = 4, the full parameter count. The provisional
  d = 2.26 was four-point noise; the freeze caught the
  misinterpretation, which is what it was for.
- residual window (≤ 1.5 nats): PASS everywhere (max 0.39).

**Post-verdict statement, superseded within hours — see the referee
report below.** An earlier revision here claimed d = K. The adversarial
referee (2026-08-11) corrected it: **d = K + #boundary-strata** (strata
with rate exactly 0 or 1 cost a FULL log n each — the Beta(1,1)
marginal of an all-success stratum is 1/(n+1); classically this is the
boundary/singular coefficient of Xie–Barron 1997 and Watanabe's RLCT),
verified on eight controlled synthetic configurations to ±0.21.

**LIVE ADJUDICATION (frozen while the code-pool grid was still
computing):** my earlier window predicted d_UI ∈ [3, 5] on the code
pools. The referee's rule predicts d_UI ≈ K + #boundary = **6**
(gpt-4o-mini code: rates 0/0/.063/.138), **6** (nano code:
0/.013/0/.05), **7** (mini code: 0/0/.037/0 — wait, .037 stratum and
three zero strata: 4 + 3 = 7). If the code grid fits d_UI in [5, 8],
the referee's rule wins and my window loses again; if [3, 5], the
reverse. Both predictions frozen before
results_overhead_law_code.txt existed.

## What this would mean if it holds

A practitioner could choose the certification design *before sampling*
from three computable numbers per candidate method — and the open
theory problem sharpens from "why do simple methods win?" to "prove (†)
with explicit constants for these three statistics," a concrete,
attackable formalization target.


## Referee verdicts (adversarial audit, 2026-08-11; independent
## replication of our grid at 10,000 reps agreed cell-by-cell)

- UI rate V_rr (allocation-constrained boundary value): **SOUND** —
  re-verified in audit round 2 by three independent minimizers agreeing
  to 6 decimal places (audit/sim_vrr_check.py). The round-1 "measured
  E[LLR]/(nV) → 1.002" line had no surviving script and is WITHDRAWN as
  evidence; the conclusion stands on the round-2 verification.
- WSR rate V_kelly: **REFUTED as a rate** — it is a ceiling the WSR
  schedule never approaches (achieved/Kelly = 0.73 → 0.29 and falling;
  overhead grows ~linearly; the wide-sweep data is U-shaped with max
  residual 2.37 nats, violating our own frozen criterion; the grid
  "pass" had R² = 0.000 — a flat scatter passing a window is not
  evidence).
- Single-stream: **SOUND at first order**; d = 1 EXACTLY (derivation via
  Laplace + Wald); our fitted 0.66–0.94 were stopping-time artifacts
  (overshoot, median-vs-mean, check-grid rounding — all quantified).
  Even c is derivable in closed form: ½log n − ½log(2π p*q*) − ρ/2 with
  ρ the stratification variance ratio.
- d_eff interpretation: **CORRECTED** to d = K + #boundary-strata
  (eight synthetic configs, measured within ±0.21 of prediction).
  AUDIT ROUND 2 DOWNGRADE (2026-08-12): the rule is a coarse empirical
  regularity, not a law. An independent path measurement on the 4o-mini
  JSON pools gives 4.06–4.38 — the earlier "path-measured 4.99" did not
  reproduce and had no script; it is WITHDRAWN. The rule misses on 2 of
  5 pools in opposite directions, and fitted d drifts with τ inside a
  single pool (6.23 → 5.04 on nano JSON), which no statistic-level
  dimension can do. What the code-pool adjudication actually
  discriminates is "d ≈ 6, not ≈ 4" — see results_adjudication.txt
  (bootstrap CIs [4.81, 7.96], [3.19, 10.57], [3.09, 9.55]; the rule
  and a constant d ≡ 6 are nearly indistinguishable, and under our own
  ≤0.75-nat criterion the score is 2-for-3, not 3-for-3).
- Fit methodology: **d = 0 vs d = 1 not identifiable** at 200 reps × 6
  points (bootstrap CIs span both; corr(d̂, ĉ) = −0.994); the residual
  criterion was vacuous (P(pass) = 1.00); functional form untested
  (√log n and log log n fit equally over our windows).
- Prior art: see status header. The positioning opportunity is
  citation, not discovery.

## What survives, verified constructively by the referee

Zero-free-parameter predictions (d and c from theory/sample paths only,
never fitted to crossing times) reproduce the definitive grid medians
for the SINGLE-STREAM arm within −3%…+7% with nothing fitted — audit
round 2 independently re-verified this at −2.6%…+6.8%, making it the
strongest quantitative result in the arc. AUDIT ROUND 2 CORRECTION: the
UI arm's "−5%…+4%" requires ONE fitted constant c per model (−1.56 /
+1.91); with c = 0 its errors are ±12%. The honest phrasing for UI is
"d from the rule, c fitted once per model." Also disclosed: the τ-grid
points share one RNG stream (common random numbers), so grid R² values
overstate independent information, and the grids cannot by themselves
distinguish (d/2)·log n from a log log n form — the functional form is
adopted from theory (Rissanen/Clarke–Barron), not established by fit.
The invention-round headline stands with a corrected mechanism: **the simple block reduction wins at
practical sample sizes because it sacrifices a bounded factor of rate
while every mixture-based alternative pays an additive
(K + #boundary)/2 · log n that dominates when log n ≈ 6–8.**


## The frontier experiment (conservation hypothesis: FALSIFIED)

**Original reading (2026-08-11): "SUPPORTED." That reading was wrong
twice over, and audit round 2 caught both errors
(audit/AUDIT_LAW_CAPSTONE.md).** First, the original artifact never
printed its own pre-registered ratios: epoch-split landed at
1.67/1.72/1.48× the mixture — the support window [0.7, 1.5] was MISSED
at 2 of 3 margins, not confirmed. Second and decisive: the original
"one-shot split" arm was an accidental strawman — it bet at p = 0.5
through its burn-in and charged ~111 nats of estimation loss to the
martingale, which the split-LRT lineage it cited
(Wasserman–Ramdas–Balakrishnan) never does.

REVISION 2 ([results_frontier.txt](results_frontier.txt)) adds the
faithful discard-burn-in split-LRT (estimation half contributes nothing
to log E; validity gated at the null boundary): at ≥95% certification
it reaches **0.373× the mixture's overhead at τ = 0.15 (b = 50) and
0.398× at τ = 0.16 (b = 100)** — across the pre-registered
falsification line of 0.5×. The conservation hypothesis AS
PRE-REGISTERED is falsified: **sample splitting escapes the
(d/2)·log n learning tax at the n ~ 10³ scales this project studies.**
The refined true statement: splitting converts the log n adaptivity tax
into a burn-in-tuned constant plus an abstention tail that binds only
at razor margins (at τ = 0.17 the corner is visible: 24–90%
certification depending on burn-in). The asymptotic mixture-redundancy
statement is untouched — but it was not what was pre-registered.

**Answer to the reframed open problem, as corrected:** the stratified
rate CAN be approached cold-start without the full log n tax — by
sample splitting (frozen bets, abstention risk at razor margins), by
rate-sacrifice (WSR's corner), or, best of all where a prior epoch
exists, by warm-starting (~1 nat, adaptive, full certification). The
binding design question is therefore not "mixture vs allocation" but
"which tax-escape fits the deployment": burn-in freeze (cold, moderate
margins), block reduction (any margin, robust), or transfer prior
(recurring evals). The matching lower-bound mathematics for the
adaptive-uniformly-powerful class remains open (Rissanen 1984; Pollak
1978; Lai–Zhang 1994) — but it now excludes split constructions by
construction, which is exactly why they escape.


## Solving the bottleneck in its loophole: warm-start certification

The learning tax binds fully-adaptive cold-start procedures (the
frontier experiment's split-LRT escape pays for its freedom with frozen
bets and an abstention tail; see above). Real evaluations recur, and a
prior epoch converts the tax to a ~1-nat constant with validity
untouched and no abstention corner
([results_warmstart.txt](results_warmstart.txt),
[results_warmstart_joint.txt](results_warmstart_joint.txt); predictions
pre-registered per arm, three misses honestly logged):

- **Benign transfer prior** (the archived stale/mislabeled epoch — a
  realistic warm start): overhead **0.58–1.37 nats** (cold: 15.5–18.4),
  medians 186/~300/548 — 4.7–5.2× faster than the cold mixture and
  **faster than every incumbent including WSR at all margins tested**.
  (Pre-registered overhead window [1.5, 6] missed LOW — favorably wrong
  is still logged as wrong.)
- **Worst case** (adversarially inverted prior): per-stratum
  ε-contamination pays K·log(1/ε) ≈ 9.2 nats (measured +9.9 — my "3–4
  nats" pre-statement forgot the K factor; the property-test that
  "caught a bug" was itself wrong, the implementation was exact).
  **Joint contamination** (one global 90/10 mixture) caps the premium at
  log(1/ε) ≈ 2.3 nats total — measured **+2.3/+2.8** vs cold, on the
  bound to the decimal. Zero wrong certifications anywhere.
- **Partial drift**: intermediate, with a characterized tradeoff —
  joint owns the worst case, per-stratum degrades more gracefully under
  partial drift (each stratum falls back independently). Hierarchical
  contamination is the natural refinement (future work).

Deployment statement: **the adaptivity tax binds only at first contact
with a model; every recurring evaluation can convert it to ~1 nat with
a provably-capped insurance premium.** Informative priors in test
martingales are classical; the contribution here is the measured
deployment story and the per-stratum-vs-joint contamination tradeoff.


## Live capstone: pre-registered pass, severity quantified

The frozen prediction (window [800, 1450] around theory-central 1045;
≥14/16 UNSAFE; zero SAFE) passed against a live temperature-0.7 stream
at the fresh threshold τ = 0.16: **16/16 UNSAFE, zero SAFE, median
1200** ([results_live_prediction.txt](results_live_prediction.txt)).
The run survived a process crash (lossless log-replay resume) and an
API requests-per-day crawl. The freeze itself is beyond doubt — audit
round 2 verified the commit contains the byte-identical script stating
the window 11 seconds after the log's first line, the crash-resume
replay is bit-exact at all 1017 possible crash points, and all 16
reported reps reproduce from the raw log.

AUDIT ROUND 2 SEVERITY DISCLOSURE (what the pass is worth):
- Two of the three criteria were near-unfalsifiable: simulating the
  exact procedure 20,000 times gives P(≥14/16 UNSAFE) ≈ 1.000,
  P(zero SAFE) ≈ 1.000, and P(median ∈ window) ≈ 0.94. The pass
  discriminates only ±1 in d (d = 0 and d = 2 fall outside the
  window), not the full theory.
- The window was frozen but NOT blind: results_overhead_law.txt,
  written 44 minutes before launch, already contained the offline
  replay median 1024 at the same τ, same method, and the IDENTICAL
  1000-prompt population (seed 42). Fresh threshold and fresh sampling
  randomness — not a fresh population.
- theory-central recomputes to 1052, not 1045; and [800, 1450] was a
  hand-tightened band, not the output of the stated p ∈ [0.195, 0.209]
  propagation (which gives [761, 1545]).
- The +15% median gap needs no causal story: the live rate is not
  resolvable to better than ±40% in median terms from this data (MLE
  0.2002 vs prefix estimator 0.2072 disagree by 0.67pp; both unbiased).

Honest summary: the capstone shows the frozen pipeline, the theory
constants, and a live stream are mutually consistent under new
randomness at a new threshold — a consistency check passed, not a
severe test. The severe zero-fit result in this arc is the
single-stream grid prediction above, which needed no fitting at all.


## Warm-start drift phase diagram (staleness budget)

Sweep of additive prior drift delta on all strata (joint contamination,
tau=0.16, 200 reps; results_warmstart_drift.txt). Pre-registered
scoring — two confirmed, one half, one REVERSED:

1. CONFIRMED: zero wrong certifications at every delta (1800 reps).
2. CONFIRMED: damage saturates at the contamination floor — worst
   median 1770 vs predicted ceiling ~1700 = cold + log(1/eps)/V_rr.
3. HALF: breakeven vs WSR predicted |delta| in [0.015, 0.06]; the
   negative side lands inside it (between 0.03 and 0.06), the positive
   side breaks even BELOW 0.015.
4. REVERSED (the informative miss): predicted understatement hurts
   more; measured the opposite — delta=+0.03 gives median 1008 vs 364
   at -0.03; even -0.10 (826..1312) beats the cold mixture, while
   +0.06 saturates at 1770. Mechanism: three of four strata have
   near-zero true rates, so negative drift is absorbed by the clip at
   zero (misspecification concentrates in the one hot stratum), while
   positive drift poisons the kappa=200 prior in ALL strata — including
   the clean ones that are 3/4 of the round-robin stream, where the
   prior keeps predicting failures that never arrive.

Deployment rule: the staleness budget is ~0.015-0.03 downward drift
but only ~0.01 upward; when uncertain, shade the transfer prior DOWN —
a "model may have regressed" prior costs almost nothing, an alarmist
prior costs the full learning tax back.

REVISION 2 (per-rep CRN seeding, audit round 2): the -0.03 point is a
seed-level TIE with WSR (rev 1: 364 vs 374, winning; rev 2: 362 vs
350, losing — a ±4% flip across seedings), so the robust beats-WSR
region is |delta| <= 0.015 downward. Everything else is stable across
seedings: asymmetry direction (362 vs 928 at ±0.03), saturation at the
contamination ceiling (1748 vs ~1753 predicted), cold beaten even at
-0.10, and zero wrong certifications. The pre-registered breakeven
window [0.015, 0.06] still contains the negative-side breakeven.


## Multi-epoch chaining (the deployment loop, pre-registered)

Six-release improving-model trajectory crossing tau mid-chain, each
epoch warm-starting from the previous epoch's own stopped-run estimates
(results_warmstart_chain.txt). Scores:

1. HALF: zero wrong certifications in all 4800 runs (validity through
   the flip) and the UI arms abstained heavily at the razor-margin flip
   epochs as predicted — but WSR REFUTED the "every method abstains
   >=30%" clause, certifying 165-173/200 with medians ~2000-2350 where
   every UI variant (cold, chain-warm, oracle-prior) mostly hit n_max.
   Near-boundary epochs are structurally WSR territory; a warm prior
   does not change that.
2. CONFIRMED: chain-warm beats always-cold at every epoch >= 2
   (322 vs 1266, 3620 vs 4460, 5164 vs 5368, 512 vs 1464, 136 vs 468);
   the epoch-6 prediction window [250, 700] missed in the favorable
   direction (136).
3. CONFIRMED (poison test): at the flip epoch the wrong-direction
   stale prior caused ZERO wrong certifications and ran at 0.96x of
   cold — the eps floor bounded the damage exactly as designed.
4. CONFIRMED (no compounding): epoch-6 chain-warm within +-25% of the
   oracle-prior arm (136 vs 124, +9.7%; exact tie at epoch 5) — chained
   estimation noise does not accumulate.

Design consequence — PRIOR-ROUTED PORTFOLIO: route each epoch to
warm-UI vs WSR by the PRIOR epoch's estimated margin |p_prior - tau|.
The routing decision uses only prior-epoch data, hence is
data-independent of the new stream: anytime validity holds with NO
alpha-splitting. Epoch-level readout from the chain table (threshold
0.05): the router picks the per-epoch winner at 4 of 5 routed epochs
and lands within ~2% of the hindsight-best portfolio. Full per-rep
router experiment queued.


## Prior-routed portfolio: a characterized negative (v1 + v2)

The chain result suggested routing each epoch to warm-UI vs WSR by
prior-epoch signals (valid with no alpha-split since routing uses only
prior-epoch data). Two pre-registered iterations both FAILED their
headline targets and are reported as failures
(results_router.txt, results_router2.txt):

- v1 (margin threshold): 1.101x pure WSR on the chain trajectory
  (target <= 1.05x). Diagnosis: fast epochs starve the next epoch's
  prior (kappa ~ 28 after a 114-sample WSR epoch), and prior margin
  alone cannot separate drift-toward from drift-away epochs (0.045 vs
  0.044 with opposite winners).
- v2 (drift-extrapolated margin + LCB rule + decay-cumulative priors):
  1.090x pure WSR on the boundary-heavy trajectory (target <= 1.00)
  and 1.259x on a margin-rich trajectory (target <= 0.85), despite
  4/5 and 5/5 majority routing accuracy. Diagnosis: warm-UI's speed
  depends on prior STRENGTH and CENTER accuracy in ways margin rules
  cannot see; a drift cliff (0.216 -> 0.104 between epochs) defeats
  one-step extrapolation entirely. Zero wrong certifications in all
  14,400 runs across both versions.

Conclusions that survive: (1) pure WSR blocks are the best SINGLE
policy across whole release trajectories in both regimes tested — its
robustness extends from single evaluations to chains; (2) warm-start
UI is a per-epoch specialist, 2-3x faster than WSR at clear-margin
epochs with strong fresh priors (the smooth-drift steady state);
(3) the project meta-finding — sophisticated adaptivity fails to beat
simple robustness at practical scales — now has a third independent
confirmation at the policy level (after allocation: GROW/TaSC, and
priors under drift). We deliberately stop at v2: iterating until a
router wins would be the forking-paths pattern our audits exist to
prevent.


## Out-of-family verdict: the expansion on local models (2026-08-12)

The strongest generalization test yet: pools from two NON-OpenAI model
families collected locally (Ollama; llama3.2-3b p* = 0.483, qwen2.5-7b
p* = 0.297 — regimes far from the calibration pools), frozen margin
grid, predictions pre-registered in scripts/run_local_law.py,
independent per-(margin, method) seeds (fixing the shared-stream defect
audit round 2 found in the original grid).

With the project's frozen >= 90%-certification filter
(results_local_law.txt):

- UI+RR: fitted d = 4.22 (llama) and 4.31 (qwen) vs the rule's
  out-of-family prediction d = K + #boundary = 4 + 0 = 4 — PASS, both
  within 0.35, max residuals 0.13/0.18 nats. After the code-pool
  downgrade (2-for-3, "only discriminates 6-vs-4"), this is the rule
  recovering credibility exactly where it makes a sharp prediction.
- single-stream: d = 0.92 / 0.81 vs theoretical d = 1 — PASS
  (residuals 0.07/0.11 nats).
- WSR at its Kelly ceiling: d = -0.19 / +0.46 — PASS (sub-logarithmic
  regime); the c in [1,3] clause FAILED for qwen (c = 0.09).
- Partial P4 miss: llama single-stream certified 85% at margin 0.027
  (predicted >= 95%); and the zero-wrong clause was VACUOUS by
  construction (only UNSAFE decisions possible on these grids) — noted
  per the audit's own lesson about vacuous evidence.
- Functional form: log n and log log n remain indistinguishable on
  these windows (residuals within 0.03 nats of each other) — the form
  stays theory-adopted, not data-established.

Scoreboard reading on local pools: WSR blocks dominate all six margins
on both models (its rate V_kelly ~ V_rr here while paying no log n),
consistent with the calibrated design map's hard-margin prediction.
REV 1 of this artifact omitted the certification filter (censored
medians flattened every slope); the bug and both revisions are in git.


## MBPP verdict: a fourth design-map regime (mild heterogeneity)

The public-benchmark grid (results_mbpp_law.txt; predictions
pre-registered in scripts/run_mbpp_law.py) scored 1 pass, 2 fails, and
a half — and the fails carry the finding:

- P2 PASS: single-stream d = 0.72 / 0.90 — five pools across three
  vendors now bracket the theoretical d = 1.
- P1 FAIL BY CENSORING (disclosed): UI+RR certifies 3-36% at the four
  hardest margins, leaving 3-point fits (llama's d = -2.23 is a
  censoring artifact, not a dimension). Mechanism, visible in the raw
  V columns: MBPP heterogeneity is mild, so V_rr / V_pool ~ 1.05 (P4
  first clause CONFIRMED, predicted <= 1.6) — stratification buys ~no
  rate while still paying ~(K/2) log n, so the UI mixture drowns at
  n_max = 6000.
- P3 FAIL, INFORMATIVE: WSR's fitted d = 1.8-2.3 on MBPP — its
  overhead GROWS with horizon. This is the law-referee's anti-result
  (the predictable lambda schedule forfeits the Kelly rate;
  achieved/Kelly falls with t) surfacing at MBPP's longer crossing
  horizons. The "flat WSR tax" in earlier grids was a short-horizon
  artifact; the law's WSR line is valid only where crossings happen
  within a few hundred samples.
- P4 second clause FAIL, and the headline: SINGLE-STREAM WINS nearly
  every MBPP margin (equal-or-higher certification, lower medians than
  WSR and UI). Under mild heterogeneity the d = 1 method beats
  everything.

Design map, extended (heterogeneity is the axis the JSON-only study
could not see):
- extreme heterogeneity (stratum ratio >> 10): WSR blocks at hard
  margins; directed allocation for easy-UNSAFE; single-stream for
  easy-SAFE;
- mild heterogeneity (ratio ~ 2-4): plain single-stream mixture CS —
  stratification and block reduction both buy nothing and cost
  either log n (UI) or the Kelly shortfall (WSR);
- recurring evaluations with smooth drift: warm-start UI (~1 nat);
- cold-start moderate margins where a frozen bet is acceptable:
  split-LRT (frontier rev 2).


## Asymmetric contamination: the first designed-method WIN

Every earlier invention attempt (GROW, TaSC, sharp priors, PPC
refinement, routers v1-v2) lost its pre-registered test. This one won,
and the difference is the design source: it was built FROM the drift
phase diagram's measured asymmetry, not from an optimality intuition
(results_asym_prior.txt; predictions frozen in the script header
before running).

Arm A — center the concentrated component at clip(prior - 0.015):
ALL FIVE clauses PASS. Benign cost 1.04x (limit 1.08); protection at
+0.015 drift 0.60x (limit 0.70); at +0.03 drift 0.50x (limit 0.60);
downward robustness at -0.03 1.27x (limit 1.35); zero wrong
certifications in all 3,000 runs. Worst case over the drift grid:
460 vs the symmetric baseline's 928 — the staleness worst case is
HALVED for a 4% benign premium.

Arm B (two-center mixture) also wins the worst-case criterion (0.44x)
with one clause narrowly missed (+0.015 protection 0.77x vs the 0.75
limit — logged as a miss).

PRODUCTION RECOMMENDATION (updated): recurring-eval warm starts should
use joint eps-contamination with the concentrated center shaded down
by 0.015. The mechanism is the drift table's clipping asymmetry:
understatement is absorbed by zero-rate strata, overstatement poisons
every stratum; a built-in downward shade buys insurance against the
expensive direction at the cheap direction's price. Validity is
untouched (any data-independent prior is valid).


## Shade refinements: both lost (the win does not compound)

Two mechanism-designed refinements of the flat-shade win were
pre-registered and both FAILED (results_shade_refine.txt):
proportional (one-prior-sd) shading lost 2 of 3 clauses (1.12x flat at
+0.03 drift, 1.17x benign — deeper hot-stratum shading costs more than
the drift table's arithmetic suggested), and the kappa-ladder lost
both clauses (1.07x worst case, 1.23x benign — the medium-resolution
component dilutes more than it insures). The flat-shade control
reproduced its banked result exactly (worst case 0.50x baseline; P4
sanity PASS). Zero wrong certifications in 4,000 runs.

Reading: the asymmetric-prior win came from the mechanism DIRECTION
(shade down), not from fine-tuning its shape; the simplest
instantiation of the right insight beats sophisticated versions of the
same insight. Fourth in-project confirmation of simplicity-first, now
measured WITHIN a winning method family. Flat shade 0.015 remains the
production recommendation.


## Kelly-floored lambda: the second designed-method win

Designed from the referee's measured pathology (the stock WSR schedule
forfeits the Kelly rate; MBPP horizons exposed it as overhead growth):
floor the bet at a shrunk Kelly plug-in after a 10-block warmup —
still predictable, so validity is unchanged by construction
(results_kelly_floor.txt; null MC 0.0335/0.0325 <= alpha).

Scoring (honest): the pathology fix is emphatic — llama-MBPP stock
fitted d = 2.46 collapses to 0.51 with uniformly higher certification
fractions, and medians improve 15-33% on ALL THREE pools including the
short-horizon JSON control. Clause misses logged: the qwen d-clause
missed by 0.02 (1.02 vs <= 1.0); the JSON prediction band (within
+/-5% of stock) was exceeded FAVORABLY (8-30% faster — a miss is a
miss); and "zero wrong" P4 failed at 2/7,200 runs — localized to ONE
SAFE per arm at the two razor-thin llama margins, i.e. the per-run
alpha budget behaving as designed, not an asymmetry (the zero-claim
was the error, as audit round 1 already taught us once).

Promoted to src/eval_harness/stats/wsr_kelly_floor.py as an OPT-IN
class (stock WSRBlockCS untouched so all committed artifacts remain
byte-reproducible). Together with the shade win: both project method
wins were designed from measured failure mechanisms; all seven
intuition-designed methods lost.


## Shade in the chain: deployment win, extrapolation strikes out

results_chain_shaded.txt (pre-registered): shading the chained
estimates beats the unshaded chain at EVERY epoch (P2 main clause
PASS; the epoch-3 magnitude clause missed at 1.12x vs the predicted
1.5x — at razor margins better centering cannot replace missing
information), and the flip-epoch deciding power rises 1.44x / 2.17x
(82 vs 57 correct at epoch 3; 52 vs 24 at epoch 4) — the shaded chain
DECIDES where the unshaded chain abstains. Zero wrong certifications
in 3,600 runs. The extrapolated-center variant failed its e3-e4
clause (ratio 1.27 at epoch 3 — overshoots into the boundary) even on
a smooth trajectory: third independent strike against
drift-extrapolation (after routers v1-v2). Production chain
recommendation: chained estimates, flat shade 0.015, no extrapolation.


## The severe live test: FAILED, as pre-registered tests are allowed to

The test built to fix every severity defect of the first capstone
(fresh population, fresh vendor, pilot-centered windows, disclosed
P(pass|theory) = 0.59, frozen at commit fe01a4c) returned:

    C1 median(tau1) 982  vs [396, 632]   FAIL
    C2 median(tau2) 252  vs [148, 240]   FAIL
    C3 ratio      0.2566 vs [0.258, 0.561]  FAIL (by 0.0014)
    C4 zero wrong certifications in 40/40  PASS

(results_severe_live.txt, regenerated deterministically from the
committed journal.) The frozen interpretation rule said a C3 failure
indicts the log-n overhead structure; the verdict therefore stands as
FAILED, and it is not re-scored after the fact.

POST-HOC DIAGNOSIS (labeled as such): both arms inflated as if the
live rate were ~0.54 rather than the pilot's 0.558 — 2.5-4 pilot
standard errors, or genuine day-scale drift of sampled decoding at 3B
scale. Under that correction the predicted ratio is ~0.29 and the
observed 0.2566 is within 20-rep median noise of it; the miss landed
0.0014 outside the frozen edge. What failed decisively was not the
fifty-year-old expansion but our ability to PIN A SMALL MODEL'S LIVE
RATE — the second, sharper form of finding F12: at 3B scale, even a
4,000-sample same-population pilot from the previous day does not
transfer to test day. Rate stability, not theory, is the binding
constraint on live prediction at small scale.

INDEPENDENT RE-ANALYSIS (peer session, 2026-08-14; verified against
the journal before adoption — all three claims reproduce):

1. RESOLUTION DEFICIT: bootstrapping the realized stopping times, the
   C3 ratio statistic at 20 reps/arm has 95% interval [0.21, 0.40] and
   P(landing inside the frozen window | the realized data) ~ 0.57 —
   the window is narrower than the statistic's own sampling noise. The
   frozen FAIL stands, but C3 is additionally scored
   UNRESOLVED-BY-DESIGN: a miss by 0.0014 at this resolution carries
   almost no evidential weight about the log-n structure. Design
   lesson (added to the severity methodology): a criterion's window
   must be wider than its estimator's noise, or it tests a coin.
2. DEAD ZONE: once the tau1 arm closed at median 982, C2 required
   median(tau2) <= 240 while C3 required >= 253.4 — mutually
   exclusive. Two of the three failures were geometrically forced
   before the second arm finished; "3 of 4 criteria failed" therefore
   overstates the evidence against the theory. Severity calibrators
   must check cross-criterion window compatibility conditional on a
   realized first arm.
3. RATE CLAIM SOFTENED: the selection-free live-rate estimate (fixed
   windows every rep reached) is 0.545 +/- 0.003 vs pilot 0.558 — a
   marginal -1.3pp offset (t ~ -2), not the "~2pp / 2.5-4 se" first
   written here; no detectable within-run drift. And the
   reconstruction "all criteria pass at the corrected rate" ASSUMES
   the 1/(p-tau)^2 structure that C3 was probing — it is labeled as
   conditional-on-the-theory, not evidence for it.

What survives untouched: anytime validity (40/40 correct UNSAFE, zero
SAFE — now 56/56 across both live prediction exercises), the offline
calibrations (26/26 byte-reproducible), the pilot transfer finding,
and the honest-severity methodology itself — which now includes two
measured design lessons (resolution, window compatibility) that the
next severe test inherits.


## Severity validator, revision 2 (the failed test's methodology yield)

severity_sim.py now (a) checks joint satisfiability of multi-arm
criteria across the FULL stressed range of realized first-arm
outcomes, and (b) computes each criterion's discriminating power
P(inside window | d = 0 / 1 / 2), refusing any design whose d = 1
advantage is under 0.30. Run retroactively on the V1 severe-test
design it REFUSES on both grounds and yields the definitive number:
C3's d-discrimination gap was +0.02 (P(inside) 0.76 under d = 0 vs
0.84 under d = 1) — the ratio criterion structurally could not
distinguish the hypotheses at 20 reps/arm. The V1 failure is thereby
fully decomposed: a marginal rate offset moved the medians, a dead
zone forced two criteria, and the arbitrating criterion had no
resolution. The redesign (ISEF_PLAN 1.1) replaces the two-arm ratio
with a many-point margin sweep scored against a pre-registered
residual band — free, offline, and power-checked by this validator
before freezing.


## Within-lineage boundary-premium test: the rule weakens further

The sharpest available test of d = K + #boundary-strata (frozen at
commit 9a87f13 before any fitting): llama3.1-8b carries the first
exact-boundary stratum in a local pool (simple = 0/250) inside a
lineage whose siblings have none. Scored honestly
(results_lineage_d.txt):

- P1 PASS: llama3.1-8b fitted d_UI = 4.30, inside [4.0, 6.0] — but
  0.7 below the rule's central prediction of 5.
- P2 HALF: llama3.2-3b 4.22 in-window; llama3-8b UNIDENTIFIABLE
  (3 surviving points after the >=90% filter at p* = 0.609; d = 1.55
  with max residual 0.01 — the censoring pathology again).
- P3 PASS-AS-WRITTEN (+1.41) BUT HOLLOW: the differential clears +0.5
  only through the unidentifiable sibling. Against the clean
  comparator the boundary premium is +0.08 — ABSENT at +/-0.3 fit
  noise where the rule predicts +1.
- P4 FAIL AS FROZEN (correction per peer review — the frozen clause
  said all three pools, and llama3-8b's censored 0.15 is outside
  [0.3, 1.5]): the identifiable pools pass at 0.81 / 0.92 (sixth and
  seventh consecutive), the frozen scoring is 2-of-4 (not the 3-of-4
  an earlier commit message implied), and the artifact now prints its
  own verdicts including the P3 hollow-pass disclosure.

Reading: the +1-per-boundary-stratum clause does not survive its
sharpest test. Combined with the code-pool adjudication ("~6 not ~4")
this suggests the boundary premium is NOT a clean additive constant —
plausibly it appears only when boundary strata carry a large share of
the certification pressure (code pools: 2-3 boundary strata of 4;
here: 1 of 4 with the hot stratum dominating V). The Month-2
formalization inherits a sharper question: prove what the Beta(1,1)
boundary marginal contributes AS A FUNCTION of the margin structure,
not as a stratum count.


## Margin sweep v1: FAILED as frozen — by finding my design bug

The centerpiece's first frozen run (results_margin_sweep.txt):
P1 PASS (12/16 pairs in band), P2 FAIL by 0.011 nats (mean D = -0.261
vs |mean| <= 0.25), P4 FAIL (10 SAFE certifications vs a frozen zero).
Scored as FAILED, no re-scoring.

POST-HOC DIAGNOSIS (labeled): (1) the deployed replay stopped
TWO-SIDED (SAFE exits allowed) while the accepted power model was
ONE-SIDED — SAFE exits remove exactly the slowest failure-sparse
streams at hard margins, biasing conditional UNSAFE medians down by
roughly the size of the P2 miss; the power stage structurally could
not see a selection effect its own model excluded. (2) P4 was the
project's THIRD vacuous zero-claim (10/~7,000 = 0.36% wrong, well
inside the per-run alpha = 5% budget — validity intact, prediction
fragile). Both defects are mechanical protocol mismatches, not
theory evidence; the D-statistic's P1 band held.

Sweep v2 is pre-registered with the mismatch fixed: one-sided
stopping (matching both the power model and the sweep's UNSAFE-only
semantics, and the original grids' protocol), P4 restated as
wrong-certification rate <= alpha, power stage re-run and re-accepted
before the freeze. Iteration count on this design: v2 (disclosed).


## Margin sweep v2 — final verdict: strict form FAILED, structure survives

The centerpiece's final frozen run (results_margin_sweep.txt, v2
protocol with the one-sided fix): P1 PASS (12/16 pairs within the
band), P2 FAIL by 0.008 nats (mean D = -0.258 vs |mean| <= 0.25),
P4 PASS under its honest form (0 wrong certifications in 8,200 reps).
FAILED as frozen; no v3 — widening bands until a pass would be
iterate-until-pass, the pattern this project's audits exist to
prevent.

What the failure measures: the persistent -0.26-nat mean deviation is
far from the d = 0 / d = 2 signatures (+/-0.5-1.25 nats; both
excluded by P1's pattern and the accepted power analysis) and matches
the KNOWN o(1) corrections the truncated three-term expansion drops —
Woodroofe's overshoot and median-vs-mean terms, which the law-referee
had already identified as why fitted d lands at 0.7-0.9 instead of 1.
The disclosed severity operated as designed: P(false fail | exact
process) = 0.35, and the strict-form criterion failed while every
d-discriminating criterion passed.

Sweep conclusion for the paper, sharpened by peer re-analysis (both
numbers re-derived from the artifact): there are TWO measured
deviations, not one. The differenced statistic (c removed) sits at
mean -0.258 nats; the RAW residual against the c = 0 closed form sits
at mean -1.144 nats — all 17 points negative, t = -13.9 — and it is
STRUCTURED IN p*, not tau (group means -0.86 to -1.51, slope ~ -1.4
nats per unit p*; within each group tau varies and D differences c
out, so the earlier "c constant-in-tau is refuted" phrasing named the
wrong variable and is corrected here). The p*-dependence is the
signature the overshoot reading predicts (Woodroofe's constants
depend on the increment distribution, which p* governs). The Month-2
formalization target is therefore falsifiable and specific: derive
the o(1)/overshoot correction and reproduce a deviation of slope
~ -1.4 nats per unit p* plus a differenced remainder of ~ -0.26
nats.

Meta-observation, restated after peer review caught the first
phrasing overclaiming: across the three severity-quantified tests
(capstone 0.94, severe live 0.59, margin sweep 0.65) the disclosed
severities predict 2.18 passes; 1 was observed, and
P(<=1 | severities correct) = 0.17. At n = 3 that is NO EVIDENCE OF
MISCALIBRATION and nothing more — the earlier "the machinery is
calibrated" claim was the same vacuous-validation shape this project
polices elsewhere, and is withdrawn.


## Target 2 verdict: the portfolio LOSES its headline — honestly

The Bonferroni portfolio (all three designs at alpha/3, stop at first
certification; frozen at 6487058) scored: P1 validity PASS (2/1600
wrong, 0.13% <= 5%); P2 FAIL as frozen (11/16 cells within the 1.30x
premium cap — the five misses are the five FASTEST cells, where the
log(3)/V premium is a constant sample count against a small base:
the derived mechanism, confirmed, with my cap mis-set for tiny-n
cells); P3 HEADLINE FAIL: grid totals portfolio 10,224 vs fixed WSR
8,718 — NOT CHOOSING COSTS MORE THAN WSR'S WRONG-REGIME ERRORS on
this testbed. P4 descriptive: the portfolio's stopping arm is WSR in
974/1600 reps, single in 581 (the mild-heterogeneity cells), UI in 45.

Reading: the derivation was right (aggregate premium 17.3%, inside
the predicted 6-27%) and the DESIGN still loses, because this grid's
fixed-design regret is smaller than the hedge premium — WSR's
robustness again. Scope for the paper: a Bonferroni portfolio pays
only where wrong-regime regret exceeds ~log(3)/(log(1/alpha)+OH),
i.e. on grids more mild-heterogeneity-heavy than ours. Fourth
independent confirmation of the meta-finding: routing lost twice, and
now hedging-instead-of-routing loses to just-use-WSR too.


## Target 3, first blood: the fourth term is derived

The p*-structure the margin sweep measured is now DERIVED
(results_overshoot.txt, commit d392c74). Stirling on the Beta-mixture
e-value gives the exact-to-O(1/n) identity

    log E_n = n KL(p_hat, tau) - (1/2) log n + (1/2) log(2 pi p_hat q_hat),

so the predicted crossing residual is -(1/2) log(2 pi p* q*) — and
subtracting that zero-fitted-parameter term from the frozen 17-point
grid collapses the measured slope from -1.398 to -0.255 nats per unit
p* and the correlation from -0.900 to -0.133 (C2 PASS). The remaining
p*-independent offset (~ -1.10 nats) decomposes numerically to within
0.125 nats as selection (-0.68) + discrete-check overshoot (+0.23) +
median-vs-mean (-0.65); its closed form (Woodroofe ladder heights) is
the stated remaining open clause. Disclosure: this explains structure
measured BEFORE the derivation; its blind test is next — the
four-term expansion must make the phase-boundary anchor A1 pass with
derived constants where fitted ones failed by 8%.
