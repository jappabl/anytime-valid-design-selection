# Audit Preparation Document - REVISED

**Date**: 2026-08-10 (Bolstering round: error bars, SOTA baseline, live WSR)
**Previous Update**: 2025-12-29 (Decision-level impact added)
**Previous Update**: 2025-12-28 (Post-audit fixes complete)
**Purpose**: Third-party audit of implementation validity
**Status**: All critical bugs fixed, claims updated to match evidence, practical impact demonstrated

---

## Executive Summary

**UPDATE 2026-08-10 (bolstering round)**: CRN + paired-bootstrap error bars confirm all six scoreboard wins ([results_uncertainty.txt](results_uncertainty.txt)). The Spertus–Sridhar–Stark UI-TS baseline was implemented from the paper (arXiv:2409.06680) — TWO invalid drafts were caught by an information-bound guard now built into the artifact (draft 1: vertex minimization with η-aware bets; draft 2: flat strata pinned high on the null boundary); the valid version shows a speed/reliability trade vs WSR-on-blocks ([results_spertus_baseline.txt](results_spertus_baseline.txt), CRN box-check in [results_spertus_crn.txt](results_spertus_crn.txt)). Live pre-registered WSR validation CONFIRMED (7/8 UNSAFE, median 224 in predicted [150,450] — [results_live_wsr.txt](results_live_wsr.txt)). Code-task grid completed for nano/mini (model ranking monotone across both task families). reproduce.sh added (byte-identical smoke test); DEFENSE.md added. Spend this round ≈ $0.45.

**UPDATE 2026-08-02 (adversarial audit + full correction pass)**: Four independent adversarial audits (statistics, experimental design, code correctness, prior art) were run against the project. They found: a float `multipleOf` validator bug corrupting 59 labels; a selection-biased failure-only re-query (temp-0 decoding is only ~98–99% reproducible — measured); exact-DP counterexamples refuting the per-sample mixture-CS validity claim on non-iid streams (coverage down to 0.80; block-gating repairs all cases); an instrumentation-blind arm behind a falsified "zero wrong certifications" claim; mislabeled pre-registration on the live τ=0.10 arm plus a dataset-seeding bug giving it a different prompt population; a WSR grid-edge bug; three assert-free test files; and substantial prior art requiring repositioning (Waudby-Smith & Ramdas 2023; Turner & Grünwald 2023; Spertus, Sridhar & Stark 2024; PACE/CELEUS/Hsu & Shekhar 2026). ALL corrections applied: validator fixed + regression-tested, full symmetric re-collection of all 3,000 JSON outcomes (flip matrices published; originals archived in `data/archive_pre_multipleof_fix/`), every offline experiment regenerated on corrected pools, claims rescoped and ranges restored, [FINDINGS.md](FINDINGS.md) rewritten (rev 2, includes the complete audit trail), [paper/DRAFT.md](paper/DRAFT.md) rewritten (v2, repositioned as an empirical design-selection study). Attacks that FAILED: betting-CS martingale exactness, WSR predictability/positivity, weighted-Bonferroni validity under adversarial allocation, all 320 code reference solutions (0 mismatches), post-pilot dataset provenance (0/1000 hash mismatches), seed robustness of headline comparisons. Corrected key numbers: gpt-4o-mini JSON p\*=0.2020, gpt-4.1-nano 0.0800, gpt-4.1-mini 0.0360 (was 0.083 — mostly the validator bug), code 0.0500.

**UPDATE 2026-08-02 (late evening)**: Three further contributions: (1) anytime-valid paired model comparison — sequential McNemar via betting CS on discordant outcomes; certifies the better model in a median of 77 prompts, abstains 96.2% on a near-tie ([results_model_comparison.txt](results_model_comparison.txt)); (2) **stratify → block → bet**: a WSR hedged betting CS on iid block means ([src/eval_harness/stats/wsr_block_cs.py](src/eval_harness/stats/wsr_block_cs.py), tested) is PROVABLY anytime-valid under stratified sampling and empirically ~1.9× tighter than the per-sample mixture CS ([results_block_reduction.txt](results_block_reduction.txt)) — this resolves the E2 validity caveat constructively; (3) a pre-registered LIVE sequential certification run at temperature 0.7 ([results_live_certification.txt](results_live_certification.txt)). Full paper draft: [paper/DRAFT.md](paper/DRAFT.md).

**UPDATE 2026-08-02 (evening)**: The full research synthesis now lives in [FINDINGS.md](FINDINGS.md) — it is the current source of truth for claims. New since the morning update: cross-model results (gpt-4.1-nano, gpt-4.1-mini on the same 1000 prompts — [results_crossmodel.txt](results_crossmodel.txt)), a second task family (parametrized code generation with execution-based validation — [results_codetask.txt](results_codetask.txt)), the peeking-miscoverage demonstration, a validity stress test of the CS under non-iid stratified streams, decision-directed allocation (3.3× faster UNSAFE certification), and the variance-theory agreement check (all in [results_advanced.txt](results_advanced.txt)). Figures in [paper/figures/](paper/figures/). Total API spend: $0.45.

**UPDATE 2026-08-02**: The contribution set has been substantially revised after real-LLM validation. See [Real-LLM Experiments on Cached GPT-4o-mini Outcomes](#real-llm-experiments-on-cached-gpt-4o-mini-outcomes-new-2026-08-02) for the current headline results: (1) betting CS makes real-LLM sequential evaluation feasible where stitched bounds cannot stop or certify; (2) block-stratified sampling reduces conditional bias 2–3× and MAE ~40% vs naive on real GPT-4o-mini outcomes; (3) a newly-discovered partial-block bias in plain round-robin stratification, with fix. The previous real-LLM dataset (6 templates) is invalidated.

**Main Contribution (synthetic, pre-2026)**: Stratified sequential evaluation reduces conditional bias by ~50% under precision stopping with heterogeneous prompts; associated with elimination of composition drift (causal pathway not isolated)

**Practical Impact - Main Evidence (Experiment B2, 2025-12-29)**: Stratified eliminates 99% of composition drift (0.1-0.3 ×10⁻⁴ vs 17-25 ×10⁻⁴ for naive) but does not reliably reduce decision error under precision stopping with plug-in decision rules. Under common random numbers coupling with fixed threshold, error rates differ by ±1% (within sampling noise). This honest null result demonstrates that drift matters for estimation (Experiment A) but not for accept/reject decisions in this regime.

**Practical Impact - Stress Test (Experiment B1)**: Under boundary conditions (independent RNG streams, median-tuned threshold), naive and stratified make opposite decisions 49.2% of the time, demonstrating maximum disagreement potential. [Demoted to appendix - see B2 for controlled comparison]

**Secondary Contribution**: ~~Intersection bounds~~ WITHDRAWN (not beneficial in our regime after bug fix)

**Implementation Status**:
- ✅ All critical bugs fixed (Bernstein constant, hash nondeterminism)
- ✅ Comprehensive test coverage added (13 new unit tests)
- ✅ Empirical validation complete with proper statistical rigor
- ✅ Reproducible artifacts provided

---

## Formal Estimand Definition

**Target of Inference**: The failure rate p under a specified target distribution over evaluation prompts.

### Mathematical Definition

For K strata with stratum-specific failure rates p_k and target weights w_k:

```
p = Σ_{k=1}^K w_k · p_k
```

**In our experiments**:
- K = 4 strata (simple, medium, complex, extreme difficulty)
- Uniform target mixture: w_k = 1/4 for all k
- Therefore: p = (1/4) Σ_k p_k

### Critical Distinction: Unconditional vs Conditional Bias

**At fixed sample size n** (traditional evaluation):
- E[p̂_n] = p for both naive and stratified sampling
- Both are unbiased estimators of the mixture failure rate

**At stopping time τ** (sequential evaluation with data-dependent stopping):
- Naive: E[p̂_τ | stopped] ≠ p (selection-induced bias)
- Stratified: E[p̂_τ | stopped] ≠ p (residual selection bias remains)
- **Key finding**: Stratified exhibits ~50% less conditional bias than naive

**Why stratified reduces bias**:
Precision stopping creates selection bias in both methods (only samples with narrow CIs trigger stopping). Naive suffers an additional bias component from composition drift under heterogeneity. Stratified maintains zero composition drift by enforcing fixed composition at all n, which is associated with ~50% less conditional bias (causal pathway not isolated; see Future Work).

**Harm metric**: Conditional bias at stopping time
```
Bias = E[p̂_τ - p | τ ≤ n_max, stopping rule triggered]
```

### Validation

**Experiment A - Statistical Bias Quantification** (synthetic with controlled heterogeneity):
- Demonstrates conditional bias emerges under precision stopping **in this synthetic setup**
- Quantifies bias reduction: 0.66%-1.17% (≈51%-54% relative reduction)
- Strongest evidence at aggressive precision targets (w∈{0.40,0.45} pass Bonferroni correction)
- Scope: Synthetic strata, wide targets, conservative bounds; causal pathway not isolated
- See: [Conditional Bias from Early Stopping](#conditional-bias-from-early-stopping---experimentally-validated)

**Experiment B1 - Decision Disagreement Stress Test** (NEW: 2025-12-29):
- **Finding**: Under boundary conditions (independent RNGs, tuned threshold), naive and stratified disagree 49.2% of the time
- **Role**: Demonstrates maximum disagreement potential; **demoted to appendix** due to confounds
- See: [Experiment B: Decision Disagreement](#experiment-b-decision-disagreement-under-precision-stopping-new-2025-12-29)

**Experiment B2 - Decision Error (Main Evidence)** (NEW: 2025-12-29 Evening):
- **Core Finding**: Stratified eliminates 99% of drift but error rates differ by only ±1% (within noise)
- **Honest null result**: Drift matters for estimation (Exp A), not for decisions in this regime
- All 4 surgical fixes: common random numbers, drift for both, fixed threshold, error metrics
- **Status**: ✅ CREDIBLE WITHIN SCOPE (all confounds controlled)
- See: [Experiment B2: Decision Error](#experiment-b2-decision-error-under-precision-stopping-coupled-design-new-2025-12-29-evening)

**Real LLM experiments** (GPT-4o-mini):
- Demonstrates heterogeneity exists in practice
- Shows stratified maintains perfect balance
- Hit budget cap → conditional bias not measured (addressed by Experiment A)

---

## Critical Bug Fixes (2025-12-28)

### 1. Bernstein Constant Bug (CRITICAL) - FIXED ✅

**What was wrong**:
```python
# OLD (INCORRECT - caused undercoverage)
range_term = log_term / (3 * n)

# NEW (CORRECT per Maurer & Pontil 2009)
range_term = (7/3) * log_term / (n - 1)
```

**Impact**: The old formula violated the 95% coverage guarantee (~7x too small)

**Consequence**: Invalidated Claim 2 about intersection bounds being tighter

**Files modified**:
- [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py) (lines 196-203, 226-233)

**Validation**: Re-ran Monte Carlo coverage validation - achieves 200/200 coverage with 95% Wilson CI [0.981, 1.000]

### 2. Hash Nondeterminism - FIXED ✅

**What was wrong**: Used `hash(stratum)` for seed derivation, which varies across Python sessions

**Impact**: Experiments not reproducible

**Fix**: Replaced with deterministic `STRATUM_SEED_OFFSETS` mapping

**Files modified**:
- [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py) (lines 22-27, 60)

### 3. Incomplete Test Coverage - FIXED ✅

**What was missing**: No tests for α-splitting, intersection mechanics, Bernstein constants, or stratified balance

**Fix**: Created [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py)

**Coverage**: 13 tests, all passing:
- 2 tests: α-splitting logic
- 2 tests: Intersection mechanics
- 3 tests: Bernstein constants (7/3, n-1, edge cases)
- 3 tests: Stratified sampler balance
- 3 tests: Reproducibility

### 4. Artifact Quality Issues - FIXED ✅

**What was wrong**:
- Coverage validation reported "100%" without CI → looked suspicious
- Bounds comparison used randomness → not reproducible
- No files written → claims not falsifiable

**Fixes**:
- Coverage now reports Wilson CIs: 200/200 coverage, CI [0.981, 1.000]
- Bounds comparison now deterministic: `failures = round(p_true * n)`
- All results written to files with full configuration headers

**New artifacts**:
- [scripts/validate_coverage.py](scripts/validate_coverage.py) - Statistical rigor with Wilson CIs
- [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py) - Deterministic, writes to file
- [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) - Complete mathematical specification
- [results_bounds_comparison.txt](results_bounds_comparison.txt) - Audit trail

---

## Revised Claims (Audit-Safe)

### Claim 1: Intersection Bounds Maintain Valid Coverage ✅

**Statement**: The intersection CI_h(α/2) ∩ CI_b(α/2) achieves coverage ≥ 1-α under time-uniform validity.

**Theoretical Basis**: Bonferroni union bound
```
P(p ∈ CI_h ∩ CI_b) = 1 - P(p ∉ CI_h ∪ p ∉ CI_b)
                     ≥ 1 - [P(p ∉ CI_h) + P(p ∉ CI_b)]
                     ≥ 1 - [α/2 + α/2] = 1 - α
```

**Evidence**: Monte Carlo validation with 200 replications per condition

| Method | True p | Coverage | 95% CI | Status |
|--------|--------|----------|--------|--------|
| Hoeffding | 0.01 | 200/200 | [0.981, 1.000] | ✓ PASS |
| Intersection | 0.01 | 200/200 | [0.981, 1.000] | ✓ PASS |
| Hoeffding | 0.05 | 200/200 | [0.981, 1.000] | ✓ PASS |
| Intersection | 0.05 | 200/200 | [0.981, 1.000] | ✓ PASS |
| ... | ... | ... | ... | ... |

*Coverage event*: true_p ∈ [L, U] at final n=100

**Conclusion**: ✅ VALIDATED - Intersection maintains valid coverage after bug fix

**Reference**: [scripts/validate_coverage.py](scripts/validate_coverage.py)

---

### Claim 2: Intersection Provides Tighter Bounds ❌ WITHDRAWN

**Original Statement**: "Intersection bounds are 40-60% tighter for low p"

**Status**: ❌ **CLAIM WITHDRAWN** after fixing Bernstein constant bug

**What Actually Happens** (with correct formula):

| Regime | Intersection vs Hoeffding | Reason |
|--------|---------------------------|--------|
| n ≤ 200 (our experiments) | +2.3% WIDER on average | α-splitting overhead dominates |
| n ≥ 500, p ≤ 0.05 | -13.7% narrower on average | Variance adaptation overcomes overhead |

**Detailed Results**: [results_bounds_comparison.txt](results_bounds_comparison.txt)

**Technical Analysis**:
1. **α-splitting overhead**: Adding log(2) to log term → ~2.8% width increase (NOT √2 ≈ 1.41x)
   - Derivation: `sqrt(1 + log(2)/log(2/δ_n))` where log(2/δ_n) ≈ 12 at n=100
   - Result: sqrt(1.058) ≈ 1.028 → +2.8%

2. **Bernstein range term**: (7/3) * log(2/δ_n) / (n-1) dominates at small n
   - Makes Bernstein worse than Hoeffding until n ≥ 500

**New Position**:
- Intersection is a valid implementation choice (maintains coverage)
- Does NOT provide efficiency gains in our experimental regime (n ≤ 200)
- NOT claimed as a contribution

**Reference**: [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py), [TECHNICAL_SPEC.md#9](TECHNICAL_SPEC.md)

---

### Claim 3: Stratified Sampling Maintains Perfect Balance ✅

**Statement**: Round-robin stratified sampling maintains exact balance across difficulty strata at all stopping times (zero composition drift at all n), which is associated with reduced conditional bias under precision stopping (causal pathway not isolated; see Experiment A).

**Theoretical Basis**:

**Problem**: Naive uniform sampling can exhibit imbalance at the stopping time when prompts have heterogeneous difficulty:
- E.g., by chance sample more hard prompts early → inflated p̂ → tighter CI → stop early with biased estimate
- Stopping time τ can correlate with stratum composition → E[p̂ | stopped at τ] ≠ p

**Solution**: Round-robin sampling guarantees exact balance at all n:
- At any n divisible by K (number of strata), each stratum has exactly n/K samples
- Composition is fixed → zero composition variance at all n
- Observed result: ~50% reduction in conditional bias (mechanism not causally isolated; see Future Work)

**Algorithm**: [src/eval_harness/prompts/stratified_json_prompts.py#128-169](src/eval_harness/prompts/stratified_json_prompts.py)

```python   
def sample_next():
    # Select least-sampled stratum
    min_count = min(samples_per_stratum.values())
    candidates = [s for s in strata if samples_per_stratum[s] == min_count]
    stratum = rng.choice(candidates)  # Break ties randomly

    prompt = sample_from_stratum(stratum)
    samples_per_stratum[stratum] += 1
    return stratum, prompt
```

**Empirical Validation**: Paired experiments on GPT-4o-mini with JSON schema generation

**Setup**:
- 4 difficulty strata: Simple, Medium, Complex, Extreme (NIGHTMARE mode)
- 2 experiments: Naive (uniform random) vs Stratified (round-robin)
- 1000 samples each, both use same model, prompts, stopping criteria
- Configs: [configs/stratified_gpt4mini_naive.yaml](configs/stratified_gpt4mini_naive.yaml), [configs/stratified_gpt4mini_stratified.yaml](configs/stratified_gpt4mini_stratified.yaml)

**Results**:

**Heterogeneity** (extreme case):
- Simple/Medium/Complex strata: 0% failure rate
- Extreme stratum: 100% failure rate
- Overall p = 0.25 (since extreme is 25% of prompts)

**Balance**:

| Method | Simple | Medium | Complex | Extreme | Variance |
|--------|--------|--------|---------|---------|----------|
| Naive | 244 | 251 | 256 | 249 | σ² = 18.5 |
| Stratified | 250 | 250 | 250 | 250 | σ² = 0.0 |

**Stratum variance**:
- Naive: σ² = 18.5 (natural sampling variation)
- Stratified: σ² = 0.0 (perfect balance)

**Composition Drift Risk**:
With extreme heterogeneity (p_extreme = 1.0, p_others = 0.0), stratum imbalance directly translates to biased p̂:
- Naive: p̂ = (# extreme samples) / n → varies with random composition
- Stratified: p̂ = (n/4) / n = 0.25 exactly → unbiased

**Caveat**: Both experiments hit max_samples=1000 (budget cap), did not actually stop early
- We demonstrated: perfect balance (mechanism)
- We did NOT demonstrate: actual bias from early stopping (outcome)

**Conclusion**: ✅ VALIDATED - Stratified sampling achieves perfect balance, maintaining zero composition drift at all n (association with bias reduction demonstrated in Experiment A; causal pathway not isolated)

**Reference**: [EXPERIMENTS.md#experiment-3](EXPERIMENTS.md), [analyze_stratified_results.py](analyze_stratified_results.py)

---

## What We Can Prove

| Claim | Evidence Type | Artifact | Status |
|-------|---------------|----------|--------|
| Intersection maintains coverage | Monte Carlo (200 reps) | [validate_coverage.py](scripts/validate_coverage.py) | ✅ Validated |
| Intersection NOT tighter at n≤200 | Deterministic grid | [comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py) | ✅ Verified |
| Stratified achieves perfect balance | Real LLM experiment | [EXPERIMENTS.md](EXPERIMENTS.md) | ✅ Validated |
| Time-uniform validity | Implicit in coverage | [validate_coverage.py](scripts/validate_coverage.py) | ✅ Validated |
| Implementation correctness | Unit tests (13 tests) | [test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) | ✅ Validated |

## What We Cannot Prove

1. **Exact improvement percentages**: Data-dependent, varies with (n, p)
2. **Naive always exhibits bias**: Requires heterogeneity + actual early stopping
3. **Intersection helps at very large n**: Our experiments capped at n=1000
4. **Coverage is exactly 95%**: Monte Carlo has finite-sample variance (we show ≥ 95%)

## What We Acknowledge

1. **Early stopping not demonstrated**: Experiments hit budget cap, didn't stop early
   - Showed: perfect balance (mechanism)
   - Did NOT show: bias from imbalance (outcome)

2. **Intersection bounds not a contribution**: Valid implementation but provides no benefit in our regime

3. **Estimand assumption**: Stratified assumes uniform target mixture
   - If true population weights ≠ uniform, need weighted estimator
   - Our use case: equal-sized evaluation slices → uniform is correct

4. **Conservative bounds**: Hoeffding uses worst-case assumptions
   - Tighter methods exist (betting-based CS, etc.)
   - Not explored due to time constraints

---

## Technical Specifications

**Complete mathematical specification**: [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)

**Key formulas** (for audit verification):

### Time-Uniform Stitching
```python
delta_n = alpha / (n * (n + 1))  # Robbins (1970)
```

### Two-Sided Hoeffding
```python
log_term = log(2.0 / delta_n)
epsilon = sqrt(log_term / (2 * n))
CI = [max(0, p_hat - epsilon), min(1, p_hat + epsilon)]
```

### Two-Sided Empirical Bernstein (Maurer & Pontil 2009)
```python
log_term = log(2.0 / delta_n)
var_hat = p_hat * (1 - p_hat)

var_term = sqrt(2 * var_hat * log_term / n)
range_term = (7/3) * log_term / (n - 1)  # CRITICAL: 7/3 and (n-1)

epsilon = var_term + range_term
CI = [max(0, p_hat - epsilon), min(1, p_hat + epsilon)]
```

### Intersection with α-Splitting
```python
alpha_h = alpha / 2
alpha_b = alpha / 2

CI_h = hoeffding_two_sided(alpha_h)
CI_b = bernstein_two_sided(alpha_b)

lower = max(CI_h[0], CI_b[0])
upper = min(CI_h[1], CI_b[1])
```

**Reference**: [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) for complete derivations

---

## Reproducibility

**All results are fully deterministic**:

1. **Coverage validation**:
   ```bash
   python3 scripts/validate_coverage.py
   # Seed: 42 + replication_id
   # Output: Deterministic with Wilson CIs
   ```

2. **Bounds comparison**:
   ```bash
   python3 scripts/comprehensive_bounds_comparison.py
   # Failures: round(p_true * n) - no randomness
   # Output: results_bounds_comparison.txt
   ```

3. **Unit tests**:
   ```bash
   python3 tests/test_intersection_and_stratified.py
   # 13 tests, all deterministic
   ```

4. **Stratified experiments** (requires API key):
   ```bash
   python3 run_stratified_experiments.py
   # Seed: 42 (in config)
   # Deterministic prompt generation (fixed seed offsets)
   # LLM calls: temperature=0 (deterministic sampling)
   ```

---

## Summary for Auditor

**What changed after audit**:
1. Fixed critical Bernstein bug (~7x error in range term)
2. Fixed hash nondeterminism (PYTHONHASHSEED issue)
3. Added 13 comprehensive unit tests
4. Added statistical rigor (Wilson CIs) to coverage validation
5. Made bounds comparison fully deterministic
6. Withdrew Claim 2 (intersection bounds not beneficial in our regime)
7. Created complete technical specification

**What we claim**:
- ✅ **Stratified sequential evaluation** maintains perfect compositional balance (Claim 3)
- ✅ Intersection bounds are valid but not tighter in our regime (Claim 1, revised)
- ✅ Implementation is correct (tests + coverage validation)

**What we don't claim**:
- ❌ Intersection bounds as a methodological contribution
- ❌ Exact bias from naive sampling (didn't demonstrate early stopping)
- ❌ Optimality of our bounds (acknowledged conservative)

**Artifacts for review**:
1. [scripts/validate_coverage.py](scripts/validate_coverage.py) - Statistical validation with CIs
2. [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py) - Deterministic comparison
3. [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) - Unit tests
4. [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) - Mathematical specification
5. [results_bounds_comparison.txt](results_bounds_comparison.txt) - Audit trail
6. [EXPERIMENTS.md](EXPERIMENTS.md) - Full experimental results

**Confidence levels**:
- Implementation correctness: HIGH (all tests pass, coverage validated)
- Stratified balance: HIGH (σ² ≈ 0 empirically demonstrated)
- Bias reduction effect: MODERATE-HIGH (0.66%-1.17% reduction across w∈{0.35,0.45}; p<0.05 all targets uncorrected, p<0.0125 for w∈{0.40,0.45} under Bonferroni; effect ≈5%-8.5% relative to base rate p=0.1375)

---

## Known Limitations and Future Work

### Experiment Artifacts from Pre-Fix Code

**Issue**: The stratified experiment results in [EXPERIMENTS.md](EXPERIMENTS.md) and the experiment databases were generated with the pre-fix prompt generator that used `hash(stratum)` for seeding.

**Impact**:
- Results are valid (stratified balance still holds)
- Prompts are **not reproducible** with the new deterministic STRATUM_SEED_OFFSETS
- To verify reproducibility with new code, experiments should be rerun

**What's Already Validated** (without rerun):
- ✅ Perfect balance mechanism (proven by algorithm + unit tests)
- ✅ Extreme heterogeneity observed (p_extreme=1.0, p_others=0.0)
- ✅ Time-uniform validity (all CIs valid)

**What Requires Rerun** (for full reproducibility):
- Exact same prompts with fixed seed
- Demonstration with current deterministic implementation

**Recommendation**: Rerun stratified experiments with corrected code to update EXPERIMENTS.md with fully reproducible results.

### Conditional Bias from Early Stopping - EXPERIMENTALLY VALIDATED

**Experiment A: Precision Stopping Bias Validation**

**Design**:
- Setting: Controlled heterogeneity with 4 strata (p ∈ {0.00, 0.05, 0.10, 0.40})
- True mixture: p = 0.1375 (uniform weights)
- Stopping rule: Precision stopping at width thresholds w ∈ {0.35, 0.38, 0.40, 0.45}
- Budget: n_max = 200, α = 0.05
- Replications: 200 per (method, width) condition
- Artifact: [results_precision_stopping_bias.txt](results_precision_stopping_bias.txt)
- Code: [scripts/validate_precision_stopping_bias.py](scripts/validate_precision_stopping_bias.py)

**Key Results** (summary across all tested widths):
- **Conditional bias difference**: Ranges from 0.0066 to 0.0117 across w∈{0.35,0.45}
  - All four targets show naive > stratified bias (p<0.05 uncorrected)
  - Two targets remain significant under Bonferroni correction (w∈{0.40,0.45}, p<0.0125)
- **Effect size**: 0.66%-1.17% absolute bias reduction (≈51%-54% relative reduction)
- **Detailed results by width**:

  | Width | Naive Bias | Strat Bias | Difference | p-value | Bonferroni | Median n (N/S) |
  |-------|------------|------------|------------|---------|------------|----------------|
  | 0.35  | -0.0123    | -0.0057    | 0.0066     | 0.027   | No         | 140/149        |
  | 0.38  | -0.0152    | -0.0075    | 0.0077     | 0.020   | No         | 102/111        |
  | 0.40  | -0.0181    | -0.0089    | 0.0092     | 0.011   | **Yes**    | 82/90          |
  | 0.45  | -0.0223    | -0.0106    | 0.0117     | 0.005   | **Yes**    | 52/60          |

- **Early stopping**: 88%-100% of replications stopped before budget
- **Composition drift**: Naive σ²=10.2-26.3 vs Stratified σ²≈0.1 (100× difference maintained)
- **Coverage at stopping**: Both 100% (Wilson CI [0.981,1.000]) in this experiment; reflects conservative time-uniform bounds; general nominality not established

**Interpretation**:
Precision stopping induces conditional bias in both methods **in this synthetic setup**. Stratified exhibits approximately 50% less bias than naive (associated with elimination of composition drift; causal pathway not isolated, see Future Work). Both methods remain biased at stopping (stratified bias: -0.0057 to -0.0106), indicating residual selection bias from the precision-stopping mechanism itself. Effect is small in absolute terms (0.66%-1.17%) but statistically significant at w∈{0.40,0.45} under Bonferroni correction.

**Peeking Tax and Selection Mechanism**:
The width sweep reveals the interaction between time-uniform validity costs and selection bias **in this experimental regime**:
- At n_max=200, achievable widths range from 0.35-0.45 (not 0.15 as with fixed-n CIs); tighter targets not evaluated
- Tighter precision (earlier stopping) applies a stronger selection filter:
  - w=0.45 (median n≈56): Bias difference = 1.17%
  - w=0.35 (median n≈140): Bias difference = 0.66%
- Paradoxically, composition drift is SMALLER at earlier stopping (σ²=10.2 vs 26.3)
- This pattern suggests bias arises primarily from **selection filter strength**, with composition drift as a secondary amplifier for naive sampling (mechanism not causally isolated)

**Mechanism** (observed pattern; causal pathway not isolated):
1. **Primary**: Precision stopping selects samples with unusually narrow CIs → selection-induced bias (affects both methods)
2. **Secondary**: Under naive sampling, narrow-CI samples correlate with non-representative stratum composition → additional drift-induced bias
3. Stratified maintains zero composition drift (component 2 absent) while selection bias (component 1) remains in both methods

**Status**: **EFFECT DEMONSTRATED**
- Balance mechanism: Stratified maintains perfect compositional balance (proven via round-robin + unit tests)
- Bias reduction: Stratified exhibits ~50% less conditional bias across all tested precision targets
- Significance: Robust across multiple widths (p<0.05 uncorrected); strongest evidence at w∈{0.40,0.45} (survives Bonferroni correction)
- Causal pathway: Not isolated; bias reduction is associated with zero composition drift, but confounds from later stopping times and selection-filter interactions not ruled out (see Future Work)

### Future Work: Mechanism Isolation

**Current limitation**: The observed bias reduction could stem from (1) elimination of composition drift, (2) stratified stopping slightly later (median n difference), or (3) interaction effects.

**Proposed ablation**:
- Hold stopping time fixed across both methods
- Option A: Sample from naive/stratified stopping-time distribution, evaluate bias at those fixed n values
- Option B: Use shared "shadow" sequence to determine stopping time, apply to both methods
- If bias gap persists at matched n, confirms drift (not just later stopping) drives the effect

**Expected result**: Bias gap should persist but potentially narrow, isolating drift contribution from selection timing.

---

### Decision-Level Impact Demonstration

**Experiment B: Decision Disagreement Under Precision Stopping** (NEW: 2025-12-29)

**Motivation**: Experiment A demonstrated statistically significant bias reduction (p<0.0125 under Bonferroni). However, a skeptical reviewer could ask: "Small effect, who cares?" This experiment demonstrates that the bias has **practical impact at the decision level**.

**Design**:
- **2×2 factorial**: Heterogeneity (high vs low) × Method (naive vs stratified)
- **Models**:
  - High heterogeneity: p ∈ {0.00, 0.05, 0.10, 0.40}, mean = 0.1375
  - Low heterogeneity: p ∈ {0.12, 0.13, 0.14, 0.16}, mean = 0.1375
- **Decision rule**: Plug-in heuristic - accept if p̂_τ < threshold, else reject
  - **Critical**: This is NOT a valid certification bound, just a decision rule for demonstration
- **Adaptive threshold**: τ = 0.1236 (median of pilot p̂_τ distribution, ensures sensitivity)
- **Stopping**: Precision stopping at width ≤ 0.40
- **Budget**: n_max = 200, α = 0.05
- **Replications**: 200 per condition (800 total runs)
- **Randomness coupling**: Paired comparison with same base seed for naive/stratified on same replication
- **Artifact**: [DECISION_IMPACT_RESULTS.md](DECISION_IMPACT_RESULTS.md)
- **Code**: [scripts/validate_decision_impact.py](scripts/validate_decision_impact.py)

**Key Results**:

| Model | Decision Disagreement | Composition Drift (Naive) |
|-------|----------------------|--------------------------|
| High heterogeneity | **52.5%** (105/200) | Naive: ≈22×10⁻⁴ |
| Low heterogeneity | **46.0%** (92/200) | (drift not reported) |
| **Overall** | **49.2%** (197/400) | Stratified: not computed |

**Interpretation**:
Under same budget constraint (n_max=200) and stopping criteria (width ≤ 0.40), naive and stratified sequential evaluation make **OPPOSITE decisions** about whether to accept or reject the same model in nearly half of cases (methods use independent RNG streams per replication). This demonstrates that conditional bias translates to **different decisions**, not just different statistical estimates.

**Heterogeneity Trend**: High heterogeneity shows 6.5 percentage points more disagreement (52.5% vs 46.0%); difference not statistically significant (95% CI includes zero).

**Composition Drift Pattern**: Naive exhibits composition variance ≈22×10⁻⁴ in high-heterogeneity case; stratified drift not computed but expected near zero by round-robin design.

**Critical Observation**: Neither method is uniformly superior in terms of false accept/reject rates. Disagreements occur in both directions depending on model structure. This is more honest than claiming "stratified is always better" - the point is that **sampling strategy changes decisions**, demonstrating practical impact.

**Practical Impact**: This moves the contribution from "statistically significant but small effect" to "different decisions 49% of the time under realistic constraints." Answers the "so what?" question for practitioners.

**Status**: **STRESS TEST** (Demoted to Appendix)
- Decision-level disagreement: 49.2% overall, 52.5% for high heterogeneity (independent RNG streams)
- Heterogeneity trend: +6.5 pp for high vs low (not statistically significant at α=0.05)
- Composition drift: Naive ≈22×10⁻⁴ (high het); stratified not computed, expected near zero by design
- RNG coupling: Partial (same base seed per replication, different streams per method)
- Honest limitations: Neither method uniformly superior; results specific to this regime (wide CIs, small budgets, plug-in heuristic)
- **Role**: Demonstrates maximum disagreement under boundary conditions; not main evidence due to confounds

---

**Experiment B2: Decision Error Under Precision Stopping (Coupled Design)** (NEW: 2025-12-29 Evening)

**Motivation**: Experiment B1 showed 49% disagreement but had 4 failure modes: (1) drift measured only for naive, (2) independent RNG streams confound policy with luck, (3) median-tuned threshold not pre-registered, (4) disagreement metric doesn't indicate which method is better. B2 implements all 4 surgical fixes to achieve "CREDIBLE WITHIN SCOPE" status.

**Design - All 4 Fixes Implemented**:
1. ✅ **Drift measured for both methods**: `compute_composition_drift()` works for any sampling policy
2. ✅ **Common random numbers coupling**: Pre-generate outcome pools per stratum; both methods draw from same pools (differ only in ORDER)
3. ✅ **Fixed pre-registered threshold**: τ = 0.13 (not tuned)
4. ✅ **Decision error metrics**: False accept/reject rates vs ground truth (not disagreement)

**Safe/Unsafe Straddle**:
- **Safe models**: p = 0.11 < τ=0.13 → Correct decision = ACCEPT
- **Unsafe models**: p = 0.15 > τ=0.13 → Correct decision = REJECT
- **Margin**: ε = 0.02 on each side (tight straddle for sensitivity)

**2×2×2 Factorial**: (Safe/Unsafe) × (High/Low heterogeneity) × (Naive/Stratified)

**Parameters**:
- Precision stopping: width ≤ 0.40
- Budget: n_max = 200, α = 0.05
- Replications: 200 per model (1,600 total runs)
- Base seed: 42 (deterministic)
- **Artifact**: [DECISION_ERROR_RESULTS.md](DECISION_ERROR_RESULTS.md)
- **Code**: [scripts/validate_decision_error.py](scripts/validate_decision_error.py)
- **Results**: [results_decision_error.txt](results_decision_error.txt) (checksum: b5af422b80238ec4)

**Key Results**:

| Model | Naive Error | Stratified Error | Difference | Naive Drift | Stratified Drift |
|-------|-------------|------------------|------------|-------------|------------------|
| Safe High Het | 23.0% | 22.0% | +1.0% | 25.22 ×10⁻⁴ | 0.29 ×10⁻⁴ |
| Unsafe High Het | 34.5% | 35.0% | **-0.5%** | 17.08 ×10⁻⁴ | 0.12 ×10⁻⁴ |
| Safe Low Het | 23.5% | 23.5% | 0.0% | 22.68 ×10⁻⁴ | 0.26 ×10⁻⁴ |
| Unsafe Low Het | 34.0% | 34.5% | **-0.5%** | 16.89 ×10⁻⁴ | 0.13 ×10⁻⁴ |

**Critical Finding - Honest Null Result**:
Despite stratified eliminating **99% of composition drift** (0.1-0.3 ×10⁻⁴ vs 17-25 ×10⁻⁴ for naive), decision error rates are **nearly identical** (±1%, within sampling noise). In 2/4 conditions, stratified performs slightly worse.

**Interpretation**:
This is NOT a failure—it's **scientifically valuable negative evidence**. Composition drift is statistically real (99% reduction confirmed) but does **not translate to improved decision accuracy** under precision stopping with plug-in decision rules in this regime.

**Contrast with Experiment A**:
- **Experiment A**: Stratified reduces conditional bias at stopping (statistical estimation)
- **Experiment B2**: Stratified doesn't reduce decision error (practical decision-making)
- **Implication**: Statistical bias reduction ≠ decision improvement for plug-in heuristics

**Why This Is More Credible Than B1**:
- ✅ Common random numbers isolate policy effect (not confounded with RNG luck)
- ✅ Drift measured for both methods (symmetric evidence)
- ✅ Fixed threshold (no tuning bias)
- ✅ Error metrics show which method is better (not just disagreement)

**Status**: ✅ **CREDIBLE WITHIN SCOPE** (Main Evidence)
- All 4 surgical fixes implemented and verified
- Drift elimination confirmed: 99% reduction (stratified 0.1-0.3 vs naive 17-25 ×10⁻⁴)
- Decision error null result: ±1% difference (within sampling noise)
- Common random numbers coupling verified
- Honest negative evidence with controlled confounds
- No overclaims, all scope limitations acknowledged

**What We Can Claim**:
> "Stratified sampling eliminates 99% of composition drift but does not reliably reduce decision error under precision stopping with plug-in decision rules (error differences ±1%, within sampling noise). This null result, obtained with common random numbers coupling and fixed threshold, suggests that composition drift matters for statistical estimation (Experiment A) but not for accept/reject decisions in this regime. Scope: synthetic 4-stratum heterogeneity, wide precision targets (w=0.40), small budgets (n≤200), conservative time-uniform bounds, plug-in heuristics."

---

## Betting CS: Critical Bug Fix and Validation (NEW: 2026-08-02)

**Context**: The real-LLM validation run ([results_llm_validation.txt](results_llm_validation.txt)) failed to demonstrate the early-stopping phenomenon: all 60 replications hit the n_max=100 budget because the Hoeffding/Bernstein intersection bounds cannot reach width ≤ 0.35 by n=100 (width ≈ 0.51 at n=100, p̂=0.25). Bias reduction measured: 0.0000. **Status: ❌ Experiment A NOT replicated on real LLM** — not because the phenomenon is absent, but because early stopping never triggered.

**Bug found**: The new betting-based CS ([src/eval_harness/stats/bernoulli_cs_betting.py](src/eval_harness/stats/bernoulli_cs_betting.py)) had inverted binary searches in `_find_ucb`/`_find_lcb` (on rejection, the search moved the wrong endpoint). Result: bounds were vacuous — at f=25, n=100 it returned (0.0, 1.0).

**Fix**: Corrected both bisection loops. At f=25, n=100 the bounds are now (0.130, 0.404).

**Validation** ([scripts/validate_betting_cs.py](scripts/validate_betting_cs.py), [results_betting_cs.txt](results_betting_cs.txt), checksum db05507e69ac14d6):
1. **Correctness**: The sequential Beta-predictive e-value equals the closed form log[Beta(a+f, b+s)/Beta(a,b)] − log f_{p₀}(data) to 3×10⁻¹⁴ (the product telescopes to the marginal likelihood ratio).
2. **Time-uniform coverage**: Miss = true p outside CS at ANY n ≤ 200. Coverage 0.953–0.980 across p ∈ {0.02, 0.05, 0.1375, 0.25, 0.5} (400 reps each) — all ≥ 95% nominal.
3. **Width**: Betting CS is ~2× tighter than the intersection at every tested (p, n) (ratio 0.45–0.62).
4. **Real-LLM rescue**: At p=0.25, width ≤ 0.35 is first reached at n=57 (betting) vs n=253 (intersection — outside the n_max=100 budget). The failed real-LLM experiment becomes feasible without raising the budget.
5. **Certification**: At true p=0.05, certifying UCB ≤ 0.15 takes n=108 (betting) vs n=767 (intersection) — a ~7× sample saving.

**Unit tests**: [tests/test_betting_cs.py](tests/test_betting_cs.py) — 9 tests including a non-vacuous-bounds regression test for the inversion bug and a time-uniform coverage smoke test. All pass.

**Implication**: Betting CS supersedes the intersection bounds as the recommended CS for both precision and certification stopping in this regime. The real-LLM Experiment A replication should be rerun with betting CS before any claims about real-model early-stopping bias are made.

---

## Real-LLM Experiments on Cached GPT-4o-mini Outcomes (NEW: 2026-08-02)

### Fatal flaw discovered in the previous real-LLM dataset

The "easy JSON" dataset used in the failed live run contains only **6 distinct
prompt templates** (2 simple, 2 medium, 1 complex, 1 extreme). At
temperature=0 each template yields an essentially fixed outcome, so the
experiment measured a mixture over ~6 deterministic coin flips — not a prompt
distribution. This also explains the repeated "Goldilocks" schema hand-tuning
in the commit history. **All previous real-LLM results should be considered
invalid as evidence about prompt-distribution failure rates.**

### New dataset: diverse, structurally-graded difficulty

[src/eval_harness/prompts/diverse_json_prompts.py](src/eval_harness/prompts/diverse_json_prompts.py):
250 distinct randomly-composed schemas per stratum (1000 total, verified
unique, all valid Draft7). Difficulty is controlled structurally (number of
regex-pattern fields, nesting depth, arrays, exact-length strings,
multipleOf) — no per-template tuning. Design was fixed before data collection;
one 160-prompt pilot verified rates were non-degenerate, no knobs were changed
after the pilot. Tests: [tests/test_diverse_json_prompts.py](tests/test_diverse_json_prompts.py).

### Data collection

[scripts/collect_llm_outcomes.py](scripts/collect_llm_outcomes.py) — one
temperature-0 call per distinct prompt (GPT-4o-mini, seed=42), full outcome
cache in [data/llm_outcomes_diverse_json.jsonl](data/llm_outcomes_diverse_json.jsonl).
Total spend ≈ $0.10. Because decoding is deterministic at temperature=0,
sampling with replacement from the cached pools is an iid draw from the
empirical distribution of the model's behavior, so the uniform-mixture
estimand is known EXACTLY: no "estimated true p".

**Measured per-stratum failure rates (real heterogeneity, n=250 each)**:

| Stratum | Failure rate | Dominant failure mode |
|---------|-------------|----------------------|
| simple  | 0.004 | — |
| medium  | 0.000 | — |
| complex | 0.080 | long digit-run patterns |
| extreme | 0.748 | exact-length strings (character counting), multi-group regexes |

**Exact estimand**: p* = 0.2080. All failures are schema-validation errors
(zero parse/truncation artifacts).

### Results ([scripts/run_realllm_offline.py](scripts/run_realllm_offline.py), [results_realllm_betting.txt](results_realllm_betting.txt), checksum dd46a7eea9f8c2da)

1000 replications per condition, n_max=200, min n=20, α=0.05, BASE_SEED=42.

**R2 — why the live experiment failed**: With the intersection CS, precision
targets w ≤ 0.35 stop in 0–4% of replications within n=200. With the betting
CS, 100% stop (median n=35–110). The betting CS reaches w=0.40 at median n=35
vs 186 for intersection (~5× fewer samples).

**R1 — naive vs stratified at the stopping time (betting CS, real outcomes)**:

- **Partial-block bias discovered**: plain round-robin stratification visits
  strata in fixed order, so at stopping times not divisible by K the last
  strata in the rotation (here `extreme`, the hardest) are systematically
  undersampled → the bias comparison vs naive flips sign across widths
  (z ∈ {+1.12, −1.25, −1.53, +2.51}).
- **Fix — block stopping**: evaluate the stopping rule only at n divisible by
  K (`stratified_block`). Composition is then exactly balanced at every
  possible stopping time.
- **With the fix**, on real model outcomes: conditional bias is 2–3× smaller
  than naive at every width (e.g. w=0.35: −0.0058 vs −0.0189; z = −5.25),
  drift is exactly 0, and MAE is ~40% lower than naive at every width.
  Direction is consistent at all 4 widths; 3 of 4 differences exceed |z|>2.
- Coverage ≥ 0.999 everywhere (conservative time-uniform bounds).

**R3 — certification on real outcomes** (one-sided, τ decisions, n_max=1000):
Certifying UNSAFE at τ=0.15 (truth: unsafe, p*=0.208): betting certifies
390/400 with 0 errors, median n=460; intersection certifies **0/400**.
Certifying SAFE at τ=0.25 (margin 0.042): betting 109/400 with 0 errors;
intersection 0/400. The intersection CS cannot make either certification
within 1000 samples in this regime.

### Revised claims (2026-08-02)

- ✅ **Real heterogeneity demonstrated** on a real model with a diverse
  (1000 distinct prompts) task distribution — no template tuning.
- ✅ **Betting CS enables sequential evaluation of real LLMs** in budgets
  where stitched Hoeffding/Bernstein bounds cannot stop or certify at all.
- ✅ **Block-stratified sequential evaluation** reduces conditional bias 2–3×
  and MAE ~40% vs naive at the stopping time on real-model outcomes.
- ⚠️ **New caveat**: plain (non-block) round-robin stratification has a
  systematic partial-block composition bias at stopping; use block stopping.
- Scope: single model (GPT-4o-mini), single task family (JSON schema
  generation), temperature 0, empirical-pool resampling design.

---

## Next Steps for Audit

1. ✅ Review technical specification ([TECHNICAL_SPEC.md](TECHNICAL_SPEC.md))
2. ✅ Run validation scripts to verify reproducibility
3. ✅ Review unit tests ([tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py))
4. ⏳ Verify claims match evidence (all artifacts provided above)
5. ⏳ Request clarification on any remaining questions

**Contact**: All artifacts are in the repository with full documentation

- 2026-08-11: results_warmstart_drift.txt (scripts/run_warmstart_drift.py,
  offline, deterministic) — warm-start staleness budget. Pre-registered
  predictions scored in header/THEORY.md: validity + saturation CONFIRMED,
  breakeven window half-right, asymmetry prediction REVERSED (documented
  as an honest miss with mechanism). No claims withdrawn; adds the
  deployment rule "shade transfer priors down."
- 2026-08-11: adversarial audit round 2 IN PROGRESS (two independent
  agents) against the previously-unaudited arcs: warm-start validity/
  coverage/contamination math; overhead-law accounting; capstone
  pre-registration integrity + crash-resume replay. Reports will land in
  audit/AUDIT_WARMSTART.md and audit/AUDIT_LAW_CAPSTONE.md.
- 2026-08-12: results_warmstart_chain.txt (scripts/run_warmstart_chain.py,
  offline, synthetic 6-epoch trajectory anchored to real epoch-2 rates) —
  chaining verdict. Pre-registered scoring: P2/P3/P4 CONFIRMED, P1 half
  (zero wrong everywhere, but WSR refuted the all-methods-abstain clause
  at flip epochs — documented as the informative miss). New design
  consequence: prior-routed portfolio (validity-preserving, no
  alpha-split). Local-model pool collection (Ollama; llama3.2-3b,
  qwen2.5-7b) in progress via scripts/collect_local_outcomes.py.
- 2026-08-12: AUDIT ROUND 2 (law/capstone agent) landed:
  audit/AUDIT_LAW_CAPSTONE.md. Corrections applied:
  (1) "3-for-3" d-rule adjudication DOWNGRADED to 2-for-3 under our own
  criterion; new artifact results_adjudication.txt (promoted from the
  audit's reproduction script) with bootstrap CIs and the honest reading
  ("d is around 6, not around 4"); "path-measured 4.99" and
  "E[LLR]/(nV) -> 1.002" WITHDRAWN (no scripts; did not reproduce).
  (2) Capstone "CONFIRMED" reframed to "pre-registered pass, severity
  quantified": freeze + replay verified beyond doubt; two criteria
  near-unfalsifiable (P ~ 1.000), P(median window) ~ 0.94; window frozen
  but informed by an offline median (1024) on the identical prompt
  population; theory-central corrects 1045 -> 1052.
  (3) Zero-fit claim scoped to the single-stream arm (correct with
  nothing fitted, -2.6%..+6.8% re-verified); UI arm needs one fitted
  constant per model.
  (4) Conservation-hypothesis rewrite pending the frontier rerun with
  the faithful discard-burn-in split-LRT arm (the audit shows 0.377x of
  the mixture overhead at tau=0.16 — inside the pre-registered
  falsification region; the original one-shot arm charged burn-in to
  the martingale and was a strawman; original artifact preserved at
  audit/results_frontier.ORIGINAL.txt).
  (5) Code hardening: replay-order assertion + labeled abstain reasons
  in resume_live_prediction.py; per-(tau,method) seeds in the new local
  law grid; functional-form (log n vs log log n) honesty line added.
- 2026-08-12: results_router.txt + results_router2.txt — prior-routed
  portfolio, two pre-registered iterations, BOTH failed headline targets
  (documented as characterized negatives; mechanisms diagnosed; zero
  wrong certifications in 14,400 runs). Deliberately stopped at v2 to
  avoid iterate-until-win forking. Local pools committed (llama3.2-3b
  p*=0.483, qwen2.5-7b p*=0.297).
- 2026-08-12: REV-2 warm-start family regenerated with per-rep CRN +
  printed verdicts (results_warmstart{,_joint,_drift}.txt) and the
  promoted null-coverage artifact (results_warmstart_null.txt: worst
  type-I 0.047 <= alpha over 8 boundary configs x 3 arms x 2000 reps).
  Benign window [1.5,6] MISSED LOW at all three margins — now printed
  in-artifact. Inverted premiums +2.12/+2.23/+2.40 vs cap 2.30, all
  disclosed with correct units language. Drift breakeven tightened
  under honest seeding (robust region |delta| <= 0.015 downward; -0.03
  is a seed-level tie). Frontier rev-2: conservation FALSIFIED as
  pre-registered (split-LRT 0.373x/0.398x at >=95% certification);
  THEORY.md and FINDINGS.md rewritten accordingly.
- 2026-08-12: results_local_law.txt rev 2 (frozen >=90% cert filter;
  rev 1 omitted it — censored medians flattened slopes; both revisions
  in git). Out-of-family PASS: UI d 4.22/4.31 vs rule 4; single
  0.92/0.81 vs 1; WSR sub-log. Partial misses disclosed (qwen WSR c;
  llama single cert fraction; vacuous zero-wrong clause noted).
  Cross-model generalization arc complete: three vendor lineages.
- 2026-08-12: results_mbpp_law.txt (scripts/run_mbpp_law.py, frozen
  protocol from run_local_law.py). Scored: P2 PASS (single d 0.72/0.90),
  P1 FAIL-BY-CENSORING (UI 3-point fits disclosed as unidentifiable),
  P3 FAIL informative (WSR d 1.8-2.3 — Kelly-shortfall anti-result at
  long horizons), P4 half (V-ratio confirmed; WSR-dominance REFUTED —
  single-stream wins mild heterogeneity). Design map extended with the
  heterogeneity axis. MBPP pools committed at e38d04f.
- 2026-08-12: paper/DRAFT.md v3 (four-regime design map spine; failures
  promoted; every number artifact-cited). Reconciliations from the draft
  agent's cross-check: single-stream d fits count is SIX pools (FINDINGS
  said five; corrected); results_block_reduction.txt prints "p*q* =
  0.165" while exact pool p*q* = 0.1612 — the artifact value appears to
  be the realized-stream empirical variance; cosmetic, no conclusion
  depends on it; both values disclosed here. Figures 7-9 committed;
  reproduce.sh registry extended to the full new artifact family
  (spot-check: run_adjudication PASS byte-identical).
- 2026-08-12: SEVERE LIVE TEST frozen at commit fe01a4c (design-stage
  skeleton committed separately at 921431e to prove windows postdated
  it). Disclosed severity P(all|theory) = 0.59 central. Pilot finding
  (F-item 12): temp-0 pools do not transfer to temp-0.7 at 3B scale
  (+7.3pp); windows pilot-centered. Test running (~8h). Also launched:
  results_asym_prior.txt experiment (designed from the drift table,
  predictions pre-registered).
- 2026-08-12: results_asym_prior.txt — asymmetric contamination WIN
  (arm A 5/5 clauses, worst case 0.50x baseline; arm B 0.44x worst case
  with one clause missed 0.77 vs 0.75, logged). Zero wrong in 3,000
  runs. Production recommendation: shade transfer priors down 0.015.
- 2026-08-13: results_shade_refine.txt — prop-shade and kappa-ladder
  refinements both FAILED pre-registered clauses; flat-shade control
  reproduced its banked 0.50x exactly; zero wrong in 4,000 runs.
  Flat shade 0.015 stands. Family-wise iteration disclosed: this is
  the second (and per the frozen rule, final) iteration on the
  shade family.
- 2026-08-13: results_kelly_floor.txt — Kelly-floored lambda WIN with
  logged clause misses (qwen d 1.02 vs <=1.0; JSON parity band exceeded
  favorably; zero-wrong failed at 2/7200, localized one-per-arm at
  razor llama margins, within alpha). Pathology fix: llama-MBPP d
  2.46 -> 0.51. Promoted opt-in to src (stock class untouched for
  reproducibility); 4 new tests (106 total).
- 2026-08-13: results_chain_shaded.txt — shade-in-chain deployment win
  (every-epoch improvement, flip-epoch correct counts 1.44x/2.17x, zero
  wrong); magnitude clause missed at e3 (1.12x vs 1.5x, logged);
  extrapolated centers failed their clause (third strike). Mechanism
  thread complete: 2 wins (shade, Kelly floor), refinements and
  extrapolation all honestly lost.
- 2026-08-13: FULL REPRODUCTION SWEEP: 26/26 artifacts reproduced
  byte-identically from committed pools (./reproduce.sh all), 106 tests
  green — the exactly-reproducible claim verified end-to-end, not
  spot-checked. Severe live test resumed from journal after a host
  process restart (journal replay bit-exact by design; 10/40 reps in).
- 2026-08-14: SEVERE LIVE TEST VERDICT: FAILED (C1 982 vs [396,632];
  C2 252 vs [148,240]; C3 0.2566 vs [0.258,0.561] — by 0.0014; C4 PASS
  40/40 correct, zero wrong). Scored strictly under the frozen rule; no
  post-hoc re-scoring. Post-hoc diagnosis (labeled): live-rate
  shortfall ~2pp vs pilot — small-scale rate instability, not the
  expansion, is the binding constraint (F12 second form).
  results_severe_live.txt regenerated deterministically from the
  committed journal by scripts/summarize_severe_live.py.
- 2026-08-14: PEER RE-ANALYSIS of the severe test adopted after
  numerical verification (all three claims reproduce from the journal):
  C3 scored UNRESOLVED-BY-DESIGN alongside the frozen FAIL (bootstrap
  P(in-window) ~ 0.57 — window narrower than estimator noise); C2/C3
  dead-zone disclosed (mutually exclusive once m1 = 982; two of three
  failures geometrically forced); rate-shortfall claim softened to
  -1.3pp marginal (t ~ -2) and the pass-at-corrected-rate
  reconstruction labeled circular (assumes the structure under test).
  Verdict unchanged: FAILED as frozen. Process rule adopted: long runs
  get announced duration + milestone check-ins + immediate
  completion/crash reports.
- 2026-08-14: severity_sim.py REVISION 2 (ISEF_PLAN 1.1 blocking
  prerequisite): (a) joint-satisfiability check over the FULL stressed
  realization range of the first arm (not just the design point);
  (b) per-criterion discriminating power P(inside | d=0/1/2) with a
  0.30-gap floor. Retro-validation REFUSES the V1 design on both
  grounds and quantifies the coin: C3's d-gap was +0.02 (0.76 vs 0.84)
  — the ratio criterion could not distinguish d=0 from d=1 at 20 reps.
  run_severe2_pilot.py docstring contradictions fixed (model/count/
  path). Severe2 pilot PAUSED at 1167/3000 samples (~$0.35; journal
  resumable); no further paid sampling until the margin-sweep design
  passes the revised validator and its cost is announced.
- 2026-08-14: severity_sim dead-zone reporting fixed per second peer
  review: closed-form satisfiable window emitted directly (V1: m1 in
  [264, 930]; realized 982 — outside by 52) instead of min/max over a
  non-contiguous bad set that read as "dead everywhere." NOTE for the
  paper: commit 0e95d33's message phrased C3's gap as "0.76 vs 0.84"
  (d=0); the binding alternative is d=2 at 0.83 — the code is correct,
  do not carry the commit phrasing into Section 6.
- 2026-08-14: results_real_chain.txt — real-trajectory chains: frozen
  P1-P4 all PASS (floor saturation 1.16-1.19x cold; WSR wins totals;
  zero wrong in 2,800 runs); supplementary S1a MISSED by 0.01 (logged,
  direction-semantics caveat), S1b PASS. Warm-start scope now measured
  on real Meta/Alibaba history: close releases only. Monotonicity scope
  correction and PREREG_S1 committed at ad8cf57; lineage-d frozen at
  9a87f13 (running). Limitation 10 closed; Limitation 8 partially
  (replay on real lineages; local live arms still available free).
- 2026-08-14: results_lineage_d.txt — within-lineage boundary-premium
  test scored honestly: P1 pass (4.30 in [4,6]), differential HOLLOW
  (+0.08 vs clean sibling where rule predicts +1; formula-pass via
  censored llama3-8b fit disclosed). Rule downgraded again; Month-2
  proof target sharpened to margin-structure dependence. Margin-sweep
  freeze 3b7d709 (power ACCEPTED 0.65/0.00/0.04); replay running.
- 2026-08-14: results_margin_sweep.txt v1 — FAILED as frozen (P2 by
  0.011 nats; P4 zero-claim broken at 0.36% wrong — third vacuous
  zero). Diagnosed design bug: two-sided replay vs one-sided power
  model (selection bias the power stage could not see). v2
  pre-registered with one-sided stopping and alpha-budget P4;
  iteration disclosed.
