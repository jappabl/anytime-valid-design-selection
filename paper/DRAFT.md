# Which Sequential Design Should You Use? An Empirical Study of Anytime-Valid LLM Failure-Rate Evaluation

*Draft v2 — 2026-08-02, revised after four-way adversarial audit. All
numbers trace to checksummed artifacts regenerated from the corrected
outcome pools; figures in `paper/figures/`. FINDINGS.md carries the full
audit trail.*

## Abstract

Anytime-valid confidence sequences make it safe to monitor an LLM
evaluation continuously and stop it early — a guarantee fixed-n intervals
lack (we measure 48% uniform miscoverage for a nominal-95% Wilson
interval under peeking on real GPT-4o-mini outcome streams). The methods
are established; what practitioners lack is guidance on *which sequential
design to use for which decision*. We build a cheap, exactly-reproducible
replay testbed — three OpenAI models × two task families, 1,320 distinct
prompts, one temperature-0 call each, raw generations stored, exact
pool-level ground truth — and use it to compare designs head-to-head.
Findings: (i) the sampling design should follow the decision — for
certifying a failure rate ABOVE a threshold, decision-directed stratum
allocation is 3.3× faster than round-robin, while for certifying BELOW,
single-stream sampling wins by 3×; (ii) on stratified streams, mid-block
peeking silently breaks both estimation bias and coverage (exact-DP
counterexamples down to 75% uniform coverage), and one rule — never peek
mid-block — repairs both; (iii) a betting confidence sequence on iid
per-block means is provably anytime-valid *and* 1.0–2.4× tighter than
the per-sample mixture sequence it replaces; (iv) a well-specified Wald
SPRT is 10× faster than composite certification but its error rate
between hypotheses reaches 64%, versus ≤0.5% for the confidence-sequence
route; and (v) four progressively sophisticated candidate improvements —
game-theoretic allocation, adaptive priors, prediction-powered
refinement — each lost to the simple block reduction under pre-stated
predictions, mapping where sophistication pays and where it does not. A live temperature-0.7 deployment of the pipeline reproduced
pool-predicted behavior, including one pre-registered prediction that
failed exactly as the offline analysis implies it should. Total API
cost: ≈ $2.

## 1. Introduction

Failure-rate evaluation is the workhorse of LLM quality and safety work,
and in practice it is monitored continuously and stopped adaptively —
which invalidates classical fixed-n intervals (Armitage et al., 1969;
measured here at real operating points: Figure 3). Anytime-valid
inference repairs this by construction, and a rapidly-growing literature
brings it to LLM evaluation: betting confidence sequences for bounded
means (Waudby-Smith & Ramdas, 2023; Shekhar & Ramdas, 2023), stratified
anytime-valid inference (Turner & Grünwald, 2023; Spertus, Sridhar &
Stark, 2024), and LLM-specific sequential evaluation (Wu, Nair & Candès,
2026; Hsu & Shekhar, 2026; CELEUS, 2026; PACE, 2026; Zhou et al., 2026).

This paper does not propose new statistical machinery. It answers the
question the methods papers leave open: **given a concrete evaluation
decision — estimate a rate, certify it against a threshold, compare two
models — which of the available sequential designs should a practitioner
use, and what does the choice cost?** Answering requires an apparatus the
literature lacks: a testbed where real model behavior can be replayed
against every candidate design with an exactly-known estimand.

**Contributions.**

1. **A replay testbed with exact ground truth** (§3): structurally-graded
   prompt generators (1,000 JSON schemas; 320 parametrized code specs
   with reference solutions), evaluated at temperature 0 on three models,
   raw generations stored. Provenance is hash-auditable (design frozen
   before collection; verified 0/1000 mismatches). Sequential procedures
   replay against the pools with zero marginal API cost.
2. **Design-selection results** (§5–§7): the certification *direction*
   determines the winning allocation (3.3× for directed on UNSAFE; 3×
   for single-stream on SAFE); "never peek mid-block" unifies a bias
   artifact and a coverage failure we exhibit by exact dynamic
   programming; and stratify→block→bet — a classical reduction
   (interpenetrating subsampling) composed with a WSR betting CS — is
   both provably valid and empirically tightest among the routes tested
   (state-of-the-art union-intersection comparison: open, §9).
3. **Calibrated cautionary baselines** (§8): the SPRT speed/fragility
   trade measured; peeking miscoverage at real operating points; and a
   documented account of two label-corruption bugs (float multipleOf,
   selection-biased re-query) caught by adversarial audit — with the
   full symmetric re-collection that repaired them.

## 2. Setup and methods used

Estimand: the uniform-mixture failure rate p\* = (1/K)Σ p_k over K = 4
difficulty strata, **a pool-level quantity under a chosen weighting**
(reweighting `extreme` to 10% would give p\* ≈ 0.086 instead of 0.202
for gpt-4o-mini — every certification below states its margin |p\*−τ|).
Validators are deterministic (Draft-7 JSON schema with exact-decimal
multipleOf; execution-based code equivalence vs reference solutions in
isolated subprocesses).

Confidence sequences: the Beta-Bernoulli mixture e-process (exact
martingale; audit verified E[e] = 1 to 12 decimals and exact-DP
time-uniform miscoverage ≤ 0.035 over a 250-point grid of p) and the
WSR hedged betting CS for bounded means (Waudby-Smith & Ramdas, 2023).
Stopping: precision (width ≤ w) or certification (UCB ≤ τ → SAFE,
LCB > τ → UNSAFE, abstain at budget).

## 3. The testbed

[Table as in FINDINGS.md — corrected rates; gpt-4o-mini p\* = .2020,
gpt-4.1-nano .0800, gpt-4.1-mini .0360, code task .0500. Figure 1.]

Difficulty ordering is preserved across the three models and both
families; the dominant failure mode is character counting. Temperature-0
decoding is only near-deterministic: full re-query flips ~1–2% of
prompt outcomes (measured, roughly symmetric) — pools are single-epoch
snapshots, and all claims are pool-scoped.

## 4. Peeking and feasibility (baseline facts, measured)

Wilson 95% uniform miscoverage 47.7% (n ≤ 200; 27.7% monitoring from
n = 30); betting CS 3.6% (Figure 3). Stitched Hoeffding∩Bernstein
sequences cannot stop or certify in this regime (0–4% of precision runs
fire; 0/400 certifications) where the betting CS always stops and
certifies 500/500 at median 356 samples on the code pool (margin 0.050;
Figure 4B).

## 5. The design should follow the decision

Per-stratum betting CSs at α/K combine into an anytime-valid mixture
interval under any data-dependent allocation (construction per Turner &
Grünwald 2023; validity re-verified here by exact analysis and
adversarial-allocation simulation). On corrected pools (Figure 4A):
UNSAFE certification at τ = 0.15 on gpt-4o-mini — round-robin 588,
width-greedy 224, decision-directed **176** (3.3×; 3.1–3.5× across audit
seeds). SAFE certification on the two strong models — single-stream 240
and 72 vs directed 800 and 364. Width-greedy allocation abstains in 89%
of SAFE runs: it optimizes width, not the decision. Two diagnosed traps:
greedy starvation; midpoint-aiming lock-in (aim with the point
estimate). Hsu & Shekhar (2026) independently report uniform sampling
beating adaptive querying in related settings.

## 6. Never peek mid-block; then bet on blocks

**Bias**: mid-block stopping under round-robin systematically
undersamples late-rotation strata; block-gated stopping cuts conditional
bias 2–3× vs naive at all four precision targets (z = −3.63, −4.49,
−4.64, −3.70) with zero drift and ~40% lower MAE.

**Coverage**: the per-sample mixture CS has no guarantee on non-iid
streams, and exact-DP counterexamples drop uniform coverage to 0.80
(K=8) and 0.93 (K=4) under every-n peeking; block gating restores
≥ 0.996 in every configuration tested. (An earlier claim of general
empirical validity, argued from variance concavity, was wrong and is
withdrawn — under-dispersion inflates the e-value and is the failure
mechanism.)

**Provable route**: blocks are iid, so a WSR CS on block means carries
an exact guarantee — and empirically dominates (1.0–2.4× vs the
per-sample CS depending on criterion, the 1.0× tie at loose widths
included; Figure 5B). Benchmarking against Spertus–Sridhar–Stark (2024)
union-intersection with optimized allocation is the top open item.

## 7. Paired model comparison

Sequential McNemar with a betting CS on discordant outcomes (classical:
Armitage 1954; e-process contemporaries: Turner et al. 2022, PACE 2026):
gpt-4.1-nano certified better than gpt-4o-mini in median **74 prompts**
(500/500 correct); mini better than nano in 335; on a constructed exact
tie the procedure abstains 96.0% with false certifications (4.0%) inside
the two-sided α = 5% budget (exact-DP 3.4–3.7%). Figure 5A.

## 8. Baselines and extensions

SPRT: median 48 samples when well-specified (10× faster than composite
certification) but 16–64% false-certification rates between its
hypotheses vs ≤ 0.5% for the CS (which abstains near the boundary) —
for composite claims, the CS guarantee is the one the claim needs.
Graded scores (fraction-of-tests-passed) run through stratify→block→bet
unchanged: "mean score ≥ 0.90" certified 500/500 at median 276 samples.
Cross-domain mappings (acceptance sampling, clinical monitoring, canary
deploys, annotation QA): `EXTENSIONS.md`.

## 9. The invention round: four candidate improvements, four negatives

With the map above in hand we treated the allocation/combination layer
as an open problem and built four progressively sophisticated
candidates, each with predictions stated before running: greedy
growth-maximizing allocation (GROW); its principled max-min repair
(TaSC — Track-and-Stop-style game allocation with a union-intersection
e-process stop); predictable recentered priors to cut mixture overhead;
and prediction-powered stratification refinement using an
already-evaluated model's cached outcomes as free side information.
All four lost to the simple designs, informatively: GROW fails by
nuisance escape (the least-favorable null re-optimizes across strata);
TaSC is sound everywhere but runs ~6× above its own game-value bound —
K-parameter learning overhead, tracking slack, and forced exploration
consume the theoretical advantage at every margin testable within
n = 4000, and its two pre-registered predictions both failed; sharp
priors saved none of the predicted 4–6 nats (the Beta(1,1) mixture is
already near-minimax); and predictor-refined stratification lost
because the predictor split the target stratum too weakly to cover the
extra per-block draws. **Stratify → block → bet took first place outright in three of six
certification conditions — all the hard margins — and in four of six
among provably-valid methods**
(662/1308/748 vs TaSC's 1014/2388/1874 and single-stream's
1696/3186/1288; `results_tasc_hard.txt`, `results_wsr_hard.txt`,
`results_sharp.txt`, `results_ppc.txt`). The meta-finding: at practical
budgets on real stratified failure streams, one well-chosen simple
reduction beats game-theoretic allocation, adaptive priors, and
prediction-powering — a conclusion made trustworthy precisely by the
four pre-stated predictions that failed.

## 10. Live validation and honest misses

Live temperature-0.7 sequential certification (fresh API calls,
decisions online): live p̂ 0.209 vs contemporaneous pool estimand 0.208;
per-stratum rates within 1.5pp. The **pre-registered** τ = 0.15 arm's
written prediction (UNSAFE every replication) **failed** — 11/12
abstained at a 300-call budget that in-hindsight analysis (median ≈ 600)
shows was under-specified; the procedure abstained rather than erring,
but the prediction was wrong and we report it as such. A follow-up
**exploratory** (not pre-registered) τ = 0.10 arm certified UNSAFE 8/8
at median 172 calls; a seeding bug gave it a different prompt population
(live rate ≈ 0.186, margin ≈ 0.086), corrected in the script and
disclosed here.

## 11. Limitations

Pool-scoped claims (finite pools under a chosen stratum weighting; ~1–2%
re-query flip rate defines label stability); per-sample mixture-CS
validity is configuration-dependent even block-gated (use the WSR block
route for a guarantee); no state-of-the-art stratified union-intersection
baseline yet; medians lack bootstrap error bars; three models, one
vendor, two task families; nothing yet under version control.

## 12. Reproducibility and audit

≈ 8,600 API calls, ≈ $2. All experiments deterministic given pools
(BASE_SEED = 42; headline results re-verified at seeds {7, 2024,
99999}). Four independent adversarial audits (statistics, experimental
design, code, prior art) ran before this revision; every material
finding and its repair is enumerated in FINDINGS.md §Audit-trail,
including two label-corruption bugs repaired by full symmetric
re-collection, one withdrawn claim (E2 general validity), one retired
absolute claim ("zero wrong anywhere"), and corrected pre-registration
language. Checksums on results files are tamper-evidence, not proof of
reproduction.

## References (to integrate)

Armitage (1954); Armitage, McPherson & Rowe (1969); Wald (1945);
Mahalanobis (1946); Waudby-Smith & Ramdas (2023); Shekhar & Ramdas
(2023); Waudby-Smith, Stark & Ramdas (2021, RiLACS); Turner, Ly &
Grünwald (2022); Turner & Grünwald (2023); Spertus & Stark (2022);
Spertus, Sridhar & Stark (2024); Wu, Nair & Candès (2026,
arXiv:2601.20251); Hsu & Shekhar (2026, arXiv:2607.17409); CELEUS
(2026, arXiv:2606.20820); PACE (2026, arXiv:2606.08106); Zhou et al.
(2026, arXiv:2605.07002); Resolution Diagnostics (2026,
arXiv:2605.30315); Locatelli et al. (2016); Kano et al. (2019).
