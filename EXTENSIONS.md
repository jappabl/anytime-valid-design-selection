# Beyond LLM Evals: Where This Machinery Applies

**2026-08-02.** The core object here is domain-agnostic: a stream of
expensive, bounded observations; a composite question ("is the mean above
or below τ?", "which of two systems is better?"); and the need for
guarantees that survive continuous monitoring and early stopping. Every
mapping below is grounded in an experiment already in this repository —
nothing speculative is claimed.

## What we actually built (domain-neutral statement)

| Capability | Guarantee | Measured cost (this repo) |
|---|---|---|
| Estimate a rate/mean with a monitor-safe interval | anytime-valid, composite | ~2× stitched bounds; Fig 2 |
| Certify rate ≤ τ or > τ | false-certification ≤ α at *every* true rate | 356 samples at 2× margin ([results_codetask.txt](results_codetask.txt)) |
| Certify with a hostile stratum driving the decision | same, any data-dependent allocation | 3.3× faster via decision-directed allocation (UNSAFE direction; single-stream wins for SAFE) ([results_crossmodel.txt](results_crossmodel.txt)) |
| Stratified population, provable validity | exact (blocks are iid) | *tighter* than unstratified, 1.0–2.4× by criterion ([results_block_reduction.txt](results_block_reduction.txt)) |
| Compare two systems on paired trials | anytime-valid sequential McNemar | decisive pair: 74 trials; constructed exact tie: abstains 96% ([results_model_comparison.txt](results_model_comparison.txt)) |
| Graded (bounded) scores instead of pass/fail | unchanged (WSR CS needs only boundedness) | "mean ≥ 0.90" in 276 samples ([results_graded_scores.txt](results_graded_scores.txt)) |
| vs the classical answer (Wald SPRT) | SPRT is 10× faster **iff** both hypotheses are right; between them its error rate hits 16–64% vs our ≤0.5% | [results_sprt_comparison.txt](results_sprt_comparison.txt) |

## Field-by-field mapping

### 1. Manufacturing quality control / acceptance sampling
The oldest home of sequential testing (Wald's SPRT was invented for WWII
munitions acceptance). Modern acceptance sampling still uses fixed plans or
SPRT-style simple-vs-simple tests. Mapping: unit inspection → Bernoulli
draw; lot defect threshold → τ; product lines / suppliers → strata. Our
SPRT experiment is directly on point: when the true defect rate sits
between the plan's p0 and p1 — the common real case — SPRT's declarations
carry no error control relative to the contractual threshold (measured
16–64% false rates), while CS certification keeps ≤ α at every true rate
and yields a defensible interval for the audit trail.

### 2. Clinical AI deployment monitoring
A deployed diagnostic model's error rate must stay below a threshold, and
monitoring is *continuous by definition* — the peeking problem is not a
corner case, it is the operating mode. Mapping: case-level error → outcome;
regulatory error ceiling → τ; patient subgroups (site, demographic,
acquisition device) → strata. The block-stratified WSR route matters
doubly here: subgroup balance is an equity requirement, and it comes with
*provable* validity plus a variance bonus. Certify-UNSAFE = automatic
model-recall trigger with controlled false-alarm rate.

### 3. Software release gates and canary deploys
Canary analysis is sequential testing run by people who peek every few
minutes. Mapping: request/session failure → outcome; SLO error budget → τ;
endpoints or traffic segments → strata. Decision-directed allocation has a
concrete ops meaning: route more canary traffic to the segment most likely
to settle the rollback decision (our measured 3.3×). The near-tie
abstention behavior of the paired comparison is exactly what a
promote/rollback gate should do when versions are equivalent.

### 4. A/B testing on matched traffic
The paired sequential McNemar maps directly: same user/context served both
variants (or matched pairs) → discordant outcomes carry all the
information. 77-trial decisions on clear winners and honest abstention on
ties is the anytime-valid alternative to the industry's chronically
peeking t-tests.

### 5. Annotation-pipeline and rater quality assurance
Human labelers and LLM judges are themselves models with failure rates.
Mapping: audited label correct/incorrect → outcome; contract accuracy
floor → τ; item types → strata. Graded agreement scores fit the bounded
WSR route unchanged. Certifying a rater ABOVE a floor with a 276-sample
audit (measured, at 2× margin on graded scores) is cheaper than typical
fixed-size audit batches, and the abstain outcome maps to "extend the
audit," not "fire the rater."

### 6. Adaptive mastery testing in education
"Certify mastery ≥ τ" over a skill mixture, strata = skill areas,
block-stratified sampling = balanced skill coverage at every possible
stopping point (the partial-block bias fix is literally a fairness
property for adaptive tests: no student stops right after the easy-skill
items). Early stopping shortens tests for clearly-above and clearly-below
students; the boundary students correctly get longer tests.

### 7. Ecology / epidemiology field sampling
Prevalence estimation with expensive site visits: sites → strata,
prevalence threshold for intervention → τ. The stratify→block→bet result
says the practical field design (rotate through sites in blocks) is not
just logistically convenient — done with a WSR CS on block means it is
provably valid and *more* sample-efficient than pooled sampling.

## What does NOT transfer automatically

- Non-stationarity: everything here assumes the rate is fixed during the
  evaluation window. Drifting rates (model updates mid-eval, seasonal
  effects) need time-varying extensions (e.g., restart schedules or
  discounting) that we have not built or validated.
- Dependent outcomes: our streams are independent by design. Queued
  requests, clustered patients, or serially-correlated rallies violate
  this; block-level independence must be argued per domain.
- Adversarial distribution shift between the sampled pool and the
  deployment distribution is out of scope — the guarantee is about the
  sampled distribution.

## Cost of the guarantee (the fair summary)

Anytime validity is not free: at a fixed n our intervals are ~2–3× wider
than a fixed-n Wilson interval (Fig 2). The claim is not "tighter than
classical statistics"; it is "the only one of these numbers you may look
at while it is being computed" — and, via sequential stopping, the total
sample cost to a *decision* is usually far below the fixed-n plan sized
for the same worst case.
