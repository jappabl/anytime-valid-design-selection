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
- 2026-08-14: results_margin_sweep.txt v2 FINAL — FAILED as frozen
  (P2 by 0.008 nats; P1 pass 12/16; P4 honest form 0/8200). d=0/d=2
  excluded; deviation -0.26 nats = measured o(1) terms; no v3 by
  policy. Meta: severe-test outcomes track disclosed severities.
  Task 41 closed. Month-2 formalization inherits the o(1) bound
  target.
- 2026-08-14 (correction): commit 4565f93's message claimed "ledger
  current" — FALSE at commit time: the paper's miss ledger (presented
  as complete) was missing six scored failures from the last day,
  including both ISEF_PLAN 1.1 centerpieces. Caught by peer review;
  fixed now (six rows added; margin-sweep failed-twice sequence given
  emphasis; o(1)/overshoot localization and the rho protocol effect
  added to paper Section 5.2). The doc-sync rule was violated between
  f016a02 and this commit; recorded per the rule itself.
- 2026-08-14: PEER QUEUE (4 items + 1 minor), all re-derived before
  adoption: (1) raw-residual structure recorded (-1.144 mean, all 17
  negative, t=-13.9, slope ~-1.4/unit p*) — Month-2 target now a
  falsifiable curve; "constant-in-tau" phrasing corrected to p*.
  (2) severity "calibrated" meta-claim WITHDRAWN (expected 2.18
  passes, observed 1, P(<=1)=0.17 — no-evidence-of-miscalibration at
  n=3 is all that survives). (3) severity_sim revision-3 rules:
  procedure identity (powered model must share the executed stopping
  rule) + gate-every-clause. (4) results_lineage_d.txt did not print
  verdicts (house-standard violation); scoring corrected 3-of-4 ->
  2-of-4 as frozen (P4 all-three fails); verdict block added and
  artifact regenerating. (5) 34f0e01 note: real-chain P1/P3 passes
  near-vacuous (shaded arm byte-identical to unshaded at these
  drifts); two load-bearing passes (P2, P4), not four — do not carry
  "all pass" into the paper.
- 2026-08-14: results_portfolio.txt — Target 2 verdict: P1 PASS, P2
  FAIL as frozen (mechanism confirmed, cap mis-set at tiny n), P3
  HEADLINE LOST to fixed WSR (8,718 vs 10,224). Reported as the loss
  it is. results_lineage_d.txt regenerated with printed verdicts
  (2-of-4 as frozen, P3 hollow disclosed). Certifier O(n)-per-update
  defect (peer-found, 900x) fixed + regression-tested; auto-select
  relaunched on the fixed wrapper.
- 2026-08-14: peer rev-2 profiling correction adopted: the defect was
  a ~6-9ms per-block exact Lagrange decision, not O(n) growth. Fixed
  with a cached-feasible-boundary-point gate (sound upper bound on the
  min-statistic; skipping evaluations is validity-free). k=4 mixture:
  ~2ms -> 21.2us/sample amortized (~1,300x across both wrapper fixes);
  2,000-sample wall-clock regression test replaces the flat-in-n form
  that would not have caught the original defect. auto-select
  relaunched on the gated wrapper (decision semantics identical across
  wrapper versions). Target 1 sweep unblocked.
- 2026-08-15: host machine died mid-runs; recovery per design (all
  work committed; partial files resumed; zero loss). results_auto_select.txt
  scored: P1 FAIL by one cell (11/16), P2/P3 PASS (mean regret +8.3%).
  mistral-7b pool complete; gemma2 resumed at 735/1000; phi3.5 and
  deepseek queued. Auto-select ran on the gated wrapper (~12 min vs the
  29h quadratic-era estimate).
- 2026-08-15: results_overshoot.txt — fourth term derived (residual
  -(1/2)log(2 pi p q); slope collapse -1.398 -> -0.255 zero-fit; C4
  decomposition closes within 0.125; C3 marginal fail std 0.286 vs
  0.25 disclosed; two in-artifact corrections disclosed). Phase curve
  passes 1-3 self-refused honestly (8bbccb2); pass 4 with the
  four-term expansion is the derivation's blind test. Peer reordering
  (Target 3 blocks Target 1) adopted.
- 2026-08-15: RELATION GATE built from the peer's 16-defect census
  (local objects correct; relations unchecked). First run:
  results_relation_gate.txt — A2 confirmed non-discriminating
  mechanically, 18 R4 flags (pre-standard artifacts lacking printed
  verdicts), 11 R5 flags (n-of-m claims without adjacent
  enumeration). Retrofit queued as a systematic task rather than
  rushed. Gate policy: runs before freezes and verdict commits.
- 2026-08-15 (corrections via peer running the gate on the gate):
  (1) R4 rev 2 — flag only verdict-asserting citations (the first
  implementation object-checked artifacts, the exact generator defect;
  27 flags contained false positives like measurement-only tables).
  (2) dc020b2's message said "18 R4" where the artifact printed 27 —
  an R5 violation inside the R5 commit; correct count recorded here.
  (3) d392c74 unit mix fixed: corr collapse is -0.616 -> -0.133
  per-point (slope -1.398 -> -0.255); -0.900 was the 6-group-mean
  statistic. Overshoot artifact regenerated on one unit.
- 2026-08-15: A1 BLIND TEST PASSED under four-term derived single-arm
  constants (+ one disclosed measured renewal scalar): single 832 vs
  WSR 835/908/945 across the whole envelope band, matching the
  measured cell direction. Phase-curve pass 4 (full curve regeneration
  + gate + freeze) queued. Absolute-median caveat recorded (~10-20%
  low both arms; WSR o(1) treatment open).
- 2026-08-15: results_phase_test.txt — phase curve FAILED as frozen
  (P1 0/2, P2 7/7, P3 1/4400). WSR region derivation-verified; single
  region misses diagnosed as c_short(R) dependence (constant treated
  as object, not relation — the generator again). c_short(R)
  derivation queued as its own frozen artifact; no same-day patching.
- 2026-08-15: v1 phase verdict restated (single region untested at
  resolution, one corner wrong — not curve-refuted); v2 frozen with
  inverted allocation (R8-compliant, 77% novel-region); c_short(R)
  derivation held pending v2's diagnostic pattern.
- 2026-08-15: results_phase_test.txt v2b — PHASE CURVE CONFIRMED with
  the honest instrument (7/13 ties, peer prediction confirmed; 3/3
  resolving below-band -> single; 3/3 sanity -> WSR; 0/6000 wrong).
  c_short(R) dissolved (v1 misses were unpaired-median noise). Target 1
  complete; the below-boundary indifference zone is the final form.
- 2026-08-15: v2b independently verified by peer; emphasis corrected
  (strong-arm-first: 10/10 above-band; 3/3-resolving + 7 ties below);
  three-region final form adopted. Hao's scope decision relayed:
  restructure the paper around the general derivable-selection thesis,
  then LLM-safety domain, then RLA bridge (Spertus already
  implemented). Restructure launched before any domain work.
- 2026-08-15: paper/DRAFT.md v4 — spine changed from the four-regime
  empirical map to the DERIVABLE DESIGN BOUNDARY (three pre-observable
  quantities: stratum heterogeneity ratio, decision direction, margin;
  §1.1 discloses that the derivation covers ratio+margin and that
  direction is empirically mapped, not derived). §1.1 now claims the
  boundary derivation, its verification, and the fourth term as
  ORIGINAL while every classical-priority disclaimer (WSR, UI,
  mixtures, Pollak-Siegmund-era expansion) is kept verbatim. §4 = THE
  BOUNDARY: 4.1 four-regime map retained as the empirical origin, 4.2
  derived curve (four passes, three self-refusing per 8bbccb2/f75eb8d;
  two discriminating anchors; A2 unscored per R1), 4.3 v1/v2/v2b saga
  told with both frozen failures, 4.4 three-region final form
  strong-arm-first. §5.3 = fourth term derived, centerpiece after the
  zero-fit table (C1-C4 with the C3 std FAIL disclosed; per-point units
  kept separate from the -0.900 group statistic; blind A1 test). §6.2 =
  relation gate (16-defect census, R1-R8 incl. R1b, four generator
  instances in the phase work alone). Miss ledger 21 -> 27 rows (all 21
  v3 rows kept verbatim; six added): phase v1 (FAILED-restated), v2
  (instrument-limited), v2b (CONFIRMED), portfolio P2/P3, auto-select
  P1, overshoot C3. Test-suite count
  refreshed 106 -> 110 (verified). Gate run against the new draft: 4 R4
  flags repo-wide; R5 flags rise 4 -> 33 on the draft because R5 only
  recognizes artifact-side enumeration while v4 enumerates its
  verification points in-paper — disclosed inside §6.2 as an open
  methodology item (R5 needs the object->relation fix R4 already got),
  NOT waived. Untracked-artifact note: results_auto_select.txt is cited
  by §4.4/§6.3 and is not yet committed. Follow-up flagged: the gate's
  own r1_anchors() still evaluates A1 under the PASS-3 fitted constants
  (it prints "central DISAGREES" for A1), which contradicts the frozen
  pass-4 curve in results_phase_curve.txt — the gate's anchor copy needs
  syncing to the derived constants before the next freeze.
- 2026-08-15 (retrofit close): R4 CLEAN — every verdict-cited artifact
  now self-scores (six batches; two silent patch no-ops caught and
  redone; the batch-5 && chain break diagnosed and replaced with
  per-step logged runs). Residual gate state, disclosed: R1's A2 flag
  is permanent and correct (non-evidence, unscored everywhere); R5's
  seven flags are the heuristic's artifact-side-only limitation
  (claims hand-verified; open methodology item per paper 6.2).
  110 tests green.
- 2026-08-16: threshold cycle recorded as project method (THEORY);
  handoff doc rewritten (ISEF_PLAN.md, resumable). c_ren cycle:
  median-vs-mean CLOSED zero-fit (results_cren.txt); overshoot
  literature-pass done — classical average-excess framework
  (Lorden/Siegmund) identified but naive non-lattice constant refuted
  2x by the periodic every-4-check boundary (exact Lotov-type
  correction OPEN, cited not fudged); selection untouched.
- 2026-08-16: SELECTION correction (peer-originated, self-corrected;
  re-verified 60k reps): Bregman identity exact; first-order term
  exactly zero => selection = E[N D(p_hat||p*)] exact form; repo C4
  value +0.681 REJECTED as noise-high (true ~0.639, z=-12.6);
  c_ren SCHEDULE-DEPENDENT (carries check period d), gap magnitude
  DISPUTED (my +0.011 vs peer +0.086, not adopted). Decomposition no
  longer closes with corrected number (~-1.06 vs -1.105) -- disclosed,
  not fudged. results_overshoot.txt C4 flagged STALE. No constant
  fitted (per request). results_selection.txt is authoritative.
- 2026-08-16: OVERSHOOT asymptotic constant CLOSED (peer Spitzer
  derivation, re-verified two ways across 3 points to <0.0003;
  rho_1=0.0942, rho_4=0.1703 matching exact enumeration). It is the
  block-skeleton ladder height (rho_d = E[H_d^2]/(2E[H_d])), NOT a
  lattice span — my earlier 2x diagnosis was wrong. rho_4/rho_1=1.81
  PROVES the schedule dependence. Asymptotic 0.170 kept distinct from
  finite-L measured 0.228; the gap is the single remaining obstruction
  (shared with selection). Citations recorded (Kim & Woodroofe
  math/0611695). Nothing fitted. results_overshoot_closed.txt.
- 2026-08-16: c_ren EXACT (absorption recursion, re-verified 7
  decimals): -1.1700824 not -1.105 (MC noise, off 0.065); a full
  function c_ren(p*,tau,alpha,d,n0), not scalar/universal. Old C4
  decomposition SUPERSEDED (its closure was two noise errors
  cancelling). R6 propagation: phase-boundary single arm -> exact
  recursion (anchors still PASS 820/1240; partition UI-dominated 0/84
  holds; both curves regenerated); BOUNDARY_THEOREM/DRAFT/THEORY/
  ISEF_PLAN carry -1.1700824 + (d,n0) + discrete-median convention.
  results_overshoot.txt C4 and results_cren.txt are superseded
  (kept for history). Nothing fitted.
- 2026-08-16: results_partition_test.txt -- three-arm verification:
  UI-dominated claim VERIFIED (0/10 outright wins incl. UI's best case,
  medians 1.6-3x; 0/3000 wrong); single|WSR resolving cells match the
  derived partition, ties = boundary region. Two-region partition now
  derived AND verified. Task: partition verification done.
- 2026-08-16: results_optimal_k.txt — optimal stratification inverse
  problem. Pre-registered finite-interior-K* FAILED for the mixture
  (K*=1, tax dominates); the failure mechanistically explains
  UI-domination (F13/F14). Arm-specific: mixture K*=1, flat/WSR large.
  Estimand fixed as population mean. Synthetic-population scope stated;
  reported as the failed-prediction-yielding-mechanism it is.
- 2026-08-16 (rev 2 of F14, peer-triggered): quoted-gain check on the
  real pools OVERTURNED the universal mixture-K*=1 claim — census
  K*=1:4, K*=2:4, K*=4:2 across ten pools; gains 1.06-4.31x (both
  synthetic figures unrepresentative); finite-interior-K* prediction
  CONFIRMED on 4 pools after rev 1 declared it failed; "K*=1 explains
  UI-domination" RETRACTED (WSR is why UI loses). The generalization-
  from-one-synthetic-population error is recorded as such.
  results_gain.txt is authoritative; derive_optimal_k.py kept as the
  well-posedness construction, superseded-in-part note added.
- 2026-08-16 (BOUNDARY_THEOREM adversarial audit, gpt-5.6-sol lineage,
  all three findings verified here before adoption): (1) proof line
  claiming O(log n/n) residual was O(log n) — Eq. (2) survived only by
  downstream cancellation; proof REPAIRED with A_n = 1-(n+3/2)log(1+1/n)
  displayed and the wrong line disclosed in-document. (2) remainder
  coefficient corrected -1 -> -13 (verified exactly at n=1e4:
  -7.500e-05 both) and the untestable O(1/n) tail replaced by the
  rigorous interval. (3) C1 rev 1 was an ad hoc threshold (x1.5 at the
  wrong grid point) that PASSED while the error exceeded the displayed
  bound — rewritten to test the rigorous interval pointwise (0/12
  violations, float64 allowance only); gate rule R4b added (named-
  quantity thresholds must be computed from theory; mechanical scan
  clean). (4) Eq. (3) restated as a DEFINITION of c_ren with the
  dropped theta*M_N + N*D(p_hat||p*) identified (Wald + selection).
  Conclusion unaffected; proof, bound, and check were the defects.
- 2026-08-16 (ordering miss + WSR verdict): 805ae03 absorbed the
  external stock-no-expansion claim while its frozen test was pending;
  the test scored P1 FAIL (1.23x vs 1.5x on the SHIPPED classes; the
  peer's 1.80x was a reimplementation, withdrawn). Claim downgraded to
  hypothesis everywhere; derive-WSR-fourth-term route REOPENED; miss
  ledger +1; gate rule R9 (no absorption while a frozen test pends).
  P3 SURVIVES (within-implementation): Kelly-floored arm is regular
  (drift 1.2% vs stock 22.9%), expansion exists there, d=+1.27
  measured — the live theorem route. P2 criterion disambiguated
  (max-dev-from-mean, 6.1% pass) and the artifact regenerated.
- 2026-08-16 (floored-d intercept): external audit found the WSR grid
  bias (tau always mid-cell, fixed 0.0005 offset, grows 1.4->5.6% of
  margin at deep rungs — verified here) making measured d=1.27
  ill-determined (d=1 indistinguishable); idealized floored arm gives
  d_regular=1 (same as single-stream), shipped class misses the
  optimizer condition by a quantified kappa gap (external, NOT fully
  blinded — disclosed). Derivation agent redirected mid-flight: grid-
  corrected re-measurement + frozen d=1 test + independent derivation
  + kappa-gap quantification. No absorption into docs until the
  frozen test scores (R9).
- 2026-08-16 (measurement threshold resolved): peer power analysis at
  20k paired reps CONFIRMS the below-band ties are real (not
  instrument): four real-but-underpowered median effects (11-33%
  power at 200 reps), one ~zero, one unresolved, one favoring WSR.
  Peer self-corrected their own premise (CRN pairing was already
  preserved; corr 0.77-0.79). One scored defect: the lattice median
  bootstrap was CONSERVATIVE (1.8-2.6% vs nominal 5%) — v2c frozen
  with calibrated Harrell-Davis (4.4-5.2%), same estimand; expected
  4/4 resolving + 6 ties. RMST rejected for validation (different
  estimand; may appear later as a labelled practitioner metric).
  Power table queued for Section 4 at consolidation.
- 2026-08-17 (floored-d, frozen verdict): grid-corrected floored-arm
  d = +1.65 +/- 0.38 (bootstrap); grid defect CONFIRMED but the
  external direction claim REFUTED (correction moves d AWAY from 1);
  stock arm still irregular (+4.50) under the same correction. Both
  pre-registered windows (idealization d=1 [0.15,1.85]; warmup-
  corrected derivation [0.64,2.42]) contain the measurement ->
  UNRESOLVED: ladder precision cannot discriminate. Windows not
  widened; attribution sum matches regression (1.5301). 4.3 stays
  "derivable on the idealization, unresolved at measurement
  precision on the shipped arm" — discrimination needs more reps
  (future run). results_floor_d.txt authoritative.
- 2026-08-17 (final floored-d + v2c): floor_d artifact updated (3x
  reps: d = 1.3614 +/- 0.2006; committed 1.27 was biased LOW by the
  grid defect, not high; external 1.12 traced to invalid arithmetic;
  kappa gap not load-bearing ~0.01). d_regular = 1 DERIVED and
  verified once the floor binds; warmup adds +0.507 (pred_shipped
  1.53). STRUCTURAL headline: warmup decays as 1/log t_c, so the
  shipped floored arm has NO fixed d either — a slowly drifting
  effective d, milder than stock; {1, 1.12, 1.27, 1.53} mutually
  indistinguishable at any feasible rep budget on this ladder. 4.3
  final form: derivable (d=1) on the post-warmup idealization;
  drifting on the literal class; discriminating experiment does not
  exist at this budget. v2c (Harrell-Davis): below-band 4/4 resolving
  + 6 ties, curve CONFIRMED under correct sizing — the calibration
  fix resolved exactly the predicted extra point.
- 2026-08-19 (safety domain #50 SCORED; frozen-prediction discipline;
  miss ledger +1): results_safety.txt (checksum a369e454bc5450fd) —
  the derived single-vs-WSR boundary ported OUT-OF-FAMILY to
  StrongREJECT harmful-compliance (8 local-model pools, 313 prompts, 6
  CATEGORY strata, deterministic refusal-string proxy grader). FRAMING
  (locked): per-model numbers are POOL PARAMETERS (p*, R), NOT safety
  rankings; MILD regime (five ratios 1.16-5.40 + one outlier 17.0; p*
  0.019-0.857 across models); mechanism = between-MODEL variance
  dominates between-stratum. Margin m=0.045, tau=mu-m, direction
  rejects_le per pool (all six scored pools certify p*>tau). FREEZE
  (committed BEFORE results at 8aa3e7e, machinery-derived: single_
  fourterm + wsr_crossing K=4 envelope + v_kelly_block generalized to
  K=6/64-atom): mistral-7b & qwen2-7b SINGLE, four scored pools TIE,
  WSR outright NOWHERE; llama3-8b (p*0.019) & gemma2-9b (p*0.035)
  boundary-regime (tau<0, exact-zero strata, NOT scored). CERTIFY (v2c
  Harrell-Davis paired bootstrap, 150 reps/arm, CRN, n_max 12000):
  single-arm predictor PORTS (measured single medians within ~5% of
  single_fourterm on 6/6); the reused K=4 WSR envelope does NOT —
  WSR certifies 19-37% faster than predicted on the four mid/high-p*
  pools (the K=6 block gives more variance reduction than the K=4
  overhead encodes), so WSR is fastest on 4/6, single only on lowest-
  p* qwen2-7b, qwen2.5 measured TIE (frozen TIE CONFIRMED). P1 FAIL
  (1/2 resolving HIT: qwen2-7b HIT, mistral-7b MISS — predicted
  single, WSR won; REPORTED, NOT tuned). P2 PASS (UI dominated 0/6,
  min UI-to-faster-arm median gap 945 >> 24 poll). P3 PASS (wrong
  SAFE-dir certs 4/2700 = 0.0015 <= 0.05). Discrimination/severity
  gate ok (2 resolving predictions, 2/2 flip under a wrong-theory
  single arm — not trivially satisfiable). Relation gate --anchors
  --allocation UNCHANGED (only the known-permanent A2 non-evidence
  flag; derive_phase_boundary/run_phase_test untouched). The MISS
  localizes to the WSR overhead envelope's stratum-count (K=4->K=6)
  portability, NOT the boundary structure or the single-arm predictor
  — re-derive the WSR overhead for K=6 is the fix. LABEL-NOISE
  (results_safety_noise.txt, checksum 923a301bde114ced): string grader
  vs gemma2:9b judge on a 60-prompt llama3.2:3b regeneration disagree
  43.3% (26/60); direction = grader OVER-counts compliance (26/28 of
  its "complied" calls the judge reads as refusals — a head-prefix-vs-
  whole-response construct gap), 0 missed real compliances. Disclosed
  like Section 3.3's temp-0 flip rate; it caps how well the labels
  track true harmful-compliance (so p* is pool-graded, not a safety
  measurement) but does NOT enter the exact alpha guarantee, and the
  design-selection verdict is invariant to label meaning. No raw
  generations stored. Two commits: freeze (8aa3e7e) then results+docs.
  NEXT per sequence: the RLA bridge (Spertus already implemented).
- 2026-08-19 (the safety miss's ONE constant MEASURED; K-dependence):
  results_wsr_k.txt (checksum f6aea65aa754d0d8) — the WSR overhead
  envelope re-measured at K in {2,4,6,8} on one frozen grid (iid
  Bernoulli p in {0.20,0.35,0.50} x 5 margins, K=4 medians ~220-17000,
  the SHIPPED WSRBlockCS polled every block, CRN across K — every K
  consumes the same underlying Bernoulli stream regrouped — reps
  300/300/300/200/150 tapered and disclosed; 60/60 rungs certified
  >= 97%). V = exact Binomial(K,p)/K block-mean Kelly rate, which agrees
  with the shipped 2**K enumeration at K=4 to 1.7e-17. RESULT: the
  envelope IS K-dependent and its constants are LINEAR IN K (OBSERVED
  REGULARITY, explicitly not derived): d_K = 4.1407 - 0.4267 K
  (max|resid| 0.115 = 5% of range), c_K = 0.9638 K - 8.9801 (0.226 =
  4%). Larger blocks -> smaller effective dimension and less overhead at
  the horizons the boundary uses. Two-regime check: a short-horizon
  plateau appears at K=4/6/8 but NOT at K=2 (SSE cut 9.7% < the 20%
  criterion), so the pre-registered uniform selection rule reported the
  single-regime pair; the triple is printed UNSCORED (c_short NOT
  monotone 3.099/1.521/1.291/1.299; d_long 3.707->1.386 and c_long
  -8.389->-3.579 both monotone). P1 FAIL — pre-stated as expected, with
  the reason committed BEFORE the run: this grid is R=1 while c_short=2.3
  was calibrated on extreme-heterogeneity pools, i.e. the already-recorded
  c_short(R) offset (THEORY.md 2026-08-15), NOT a K result. Measured K=4
  triple (1.521, 2.809, -7.395) sits outside the committed corner band
  and the committed central envelope is worst +27.6% on the K=4 rungs.
  P2 PASS (both reported constants strictly monotone in K; direction was
  not pre-committed). P3 PASS (0/60 rungs excluded; hard guard unused).
  POST-HOC DIAGNOSTIC (labeled as such; does NOT re-score #50):
  run_safety_cert's prediction path reused verbatim — its load_pool, mu,
  tau=round(mu-0.045,3), single_fourterm, 64-atom v_kelly_block_K at K=6,
  +/-5% tie band — with ONLY the WSR overhead swapped, and the COMMITTED
  column asserted to reproduce the frozen table exactly (it does).
  INDEPENDENT CONFIRMATION of the miss's size from the envelope side: the
  committed K=4 envelope over-predicts n_wsr by +19.3% to +37.2% on the
  four mid/high-p* pools — the same +19-37% the certification measured,
  reached by a different route. Transporting the measured K=4->K=6
  DIFFERENCE onto the committed envelope (function-level transport;
  additive separability of the R-offset from K is ASSERTED, not proved)
  cuts that to [-0.9%, +14.5%]. ANSWER: PARTIALLY. mistral-7b moves
  SINGLE -> TIE (n_w 844 -> 735 against n_s 764), so a K-aware boundary
  would not have made the wrong RESOLVING call — but it does not flip to
  WSR, and the qwen2-7b HIT collapses to TIE as well, leaving the domain
  with ZERO resolving predictions, which the discrimination gate would
  have REFUSED as vacuous. Block size accounts for most of the MAGNITUDE
  and none of the RESOLUTION. The #50 MISS STANDS AS SCORED; miss ledger
  unchanged (33 rows). Scope disclosed in-artifact: homogeneous R=1 grid;
  stock WSR has no fixed (d,c) asymptotically (results_wsr_expansion.txt)
  so every envelope here is an EFFECTIVE LOCAL fit over the measured
  range, not an expansion claim; tau held on the 0.001 lattice (mid-cell
  on the shipped CS grid, the identical convention to run_safety_cert)
  across all K so grid quantization (0.5-3.8% of margin) cannot
  masquerade as K-dependence. Honest next clause: the envelope needs a
  JOINT c(R, K), not a K-only patch. Freeze convention for this artifact:
  the protocol is a measurement grid, not a prediction test, so the
  docstring is committed WITH the results — P1-P3 still print PASS/FAIL.
- 2026-08-19 (the JOINT (R, K) surface measured; the outstanding
  "envelope needs a joint c(R,K)" clause CLOSED WITH A NULL ON R):
  results_wsr_rk.txt (checksum 202b167276d05415) — the WSR overhead
  envelope measured on a designed 12-cell grid, K in {2,4,6} x R in
  {1,3,10,30}, at p* in {0.20,0.35} x 4 margins (96 rungs). Pools are
  two-level K-stratum profiles (half the strata at p_lo, half at p_hi,
  p_hi/p_lo = R, mean exactly p*); a block is one draw per stratum
  (round-robin) fed to the SHIPPED WSRBlockCS polled every block;
  certify UNSAFE at tau = p* - delta. The tau ladder is solved per
  (p*, R) at K=4 to a COMMON median window {250,800,2500,8000} and then
  shared by every K — deliberate, because an effective LOCAL fit depends
  on the range it is taken over, so unequal per-cell n-ranges would
  masquerade as R-dependence. Reps 250/250/180/120 tapered and
  disclosed; CRN = one uniform stream per (p*, rung, rep) SHARED by all
  twelve (K,R) arms, mapped to strata by position mod K, so K and R
  change the mapping and thresholds, never the randomness; 96/96 rungs
  certified >= 0.99. V = exact per-sample Kelly rate of the block mean
  computed by Poisson-binomial DP convolution in O(K^2) (the block mean
  is a sum of INDEPENDENT NON-IDENTICAL Bernoullis, so the K artifact's
  Binomial form does not apply); it agrees with the shipped 2**K
  enumeration at K=4 to 1.39e-17, both at (K=4,R=1) and over the WHOLE
  K=4 sub-grid. Per (K,R) cell the two p* ladders are POOLED (8 rungs)
  and O = (d/2) log n + c is fit by OLS with standard errors printed.
  12-CELL RESULT (d/c): K=2 3.566/-7.282, 2.722/-4.428, 3.324/-6.994,
  3.525/-7.919; K=4 2.084/-4.174, 2.319/-5.052, 2.194/-4.923,
  1.990/-4.326; K=6 1.562/-3.235, 1.393/-2.723, 1.515/-3.354,
  1.267/-2.601 (columns R=1,3,10,30).
  P1 FAIL (regression anchor) — but 2 of its 3 sub-checks PASS: at K=2
  (d +0.180, c -0.360) and K=6 (d +0.097, c -0.097) the R=1 column
  reproduces results_wsr_k.txt inside the pre-registered +/-0.25 / +/-0.6;
  K=4 misses on both (d -0.259, c +1.177). POST-HOC ARITHMETIC (labeled,
  computed from the two artifacts' own printed constants, scores
  nothing): the two independently measured envelopes agree at FUNCTION
  level within 0.494 / 0.446 / 0.335 nats across each cell's measured
  n-range at K=2/4/6, i.e. ~7% in n — the K=4 pairwise failure is the
  d<->c trade-off of a two-parameter local fit (that cell's own OLS SEs
  are 0.239 in d and 0.886 in c), not an envelope disagreement. The
  anchor's identity was re-verified in-artifact (checksum recomputed AND
  its (d_K,c_K) table parsed and asserted against the values scored).
  P2 FAIL — AND THAT IS THE RESULT. c is NOT monotone in R at any K, and
  the R=1 -> R=30 endpoint change is -0.637 / -0.152 / +0.634 nats at
  K=2/4/6: inconsistent in SIGN and each at most 0.37 of its own
  standard error. d is likewise non-monotone. The long-hypothesized
  c_short(R) offset (THEORY.md 2026-08-15, ~0.7-1.0 nats) is NOT PRESENT
  over R in [1,30] on these profiles; this is the first time R was swept
  at fixed p* on a designed grid rather than inferred across pools.
  P3 PASS (0/96 rungs excluded; hard guard unused).
  SURFACE (observed regularity, not derived): d = 4.1707 - 0.4625 K
  - 0.0190 log R and c = -8.2446 + 0.9194 K - 0.1081 log R. Over the
  whole R sweep the log R terms move d by -0.065 (3.5% of the K effect)
  and c by -0.368 (10.0%), against max|residual| 0.503 (22% of range)
  and 2.096 (39%) — so the pre-registered rule REJECTS log R as a
  carrier, and the reason is that the R effect is NULL, not that some
  other R-carrier is wanted; nothing else was fitted to force it and the
  full 12-cell residual table is printed. The K coefficients reproduce
  the K artifact's linear laws (-0.4625 vs -0.4267 in d, +0.9194 vs
  +0.9638 in c) on an entirely new grid with a different profile family
  — an INDEPENDENT confirmation of the K law.
  POST-HOC DIAGNOSTIC (labeled; does NOT re-score #50): run_safety_cert's
  prediction path reused verbatim (load_pool, mu, tau=round(mu-0.045,3),
  single_fourterm, 64-atom v_kelly_block_K at K=6, +/-5% tie band), only
  the WSR overhead swapped, COMMITTED column asserted to reproduce the
  frozen table (it does). The joint envelope at (K=6, R_pool) gives 3
  RESOLVING calls (vs the frozen 2) but matches the measured winners 1
  HIT / 1 MISS / 1 unconfirmed = 1/2 — the SAME rate as the frozen call.
  ANSWER: PARTIAL (Q1 >= 2 resolving YES; Q2 better than 1/2 NO). Errors
  COMMITTED [-11.8%,+37.2%] -> JOINT-S [-35.2%,+31.2%]: better on the
  mid/high-p* pools (+37.2 -> +31.2, +19.3 -> +13.5, +36.1 -> +28.0),
  worse on the low-p* ones. mistral-7b again moves SINGLE -> TIE and
  never to WSR; llama3.2-3b TIE -> WSR (matching measurement); and
  qwen2-7b's HIT is LOST (SINGLE -> WSR, a new miss). The #50 MISS
  STANDS AS SCORED; miss ledger unchanged (33 rows).
  RESIDUAL OBSERVATION (labeled, six points, explicitly NOT a claim):
  the JOINT-S error orders with pool p* (corr +0.75) and anti-orders
  with log R (corr -0.71) — but p* and log R are CONFOUNDED at -0.87
  across these six pools, so the pool set cannot separate them. What the
  DESIGNED grid settles is the R side: with p* held fixed and R swept
  1 -> 30, c moves by less than 0.4 SE. The residual over-prediction is
  therefore NOT heterogeneity; p* (or the profile shape, or the
  short-horizon plateau the K artifact saw at K=4/6/8) is the open
  candidate and is NOT established here.
  SCOPE, disclosed in-artifact: the grid's R is a two-level half-half
  ratio while a real pool's R is max/min over six category rates
  (asserted equivalent, not proved); the surface carries no p* term and
  extrapolates to pool p* up to 0.857; stock WSR has no fixed (d,c)
  asymptotically (results_wsr_expansion.txt), so every envelope here is
  an EFFECTIVE LOCAL fit over the measured range, not an expansion
  claim; tau's 0.001-lattice mid-cell offset (0.6-3.1% of margin) is
  held FIXED across all twelve cells so it cannot masquerade as R- or
  K-dependence. DISCLOSED DEVIATION from the requested protocol: four
  margins per cell span ~32x in n, not ~8x — two free parameters fit
  from eight points need leverage in log n and ~8x cannot reach the
  requested 200-15000 window; the operative constraint is met (measured
  medians 222-13158). Freeze convention as for the K artifact: a
  measurement grid, docstring committed WITH the results, P1-P3 print
  PASS/FAIL. Next clause: the envelope's missing argument is block size
  alone as far as this grid can see — R is ruled out, p* is open.
- 2026-08-19 (DIRECTION and p* disentangled; the safety miss's
  RESOLUTION recovered in a labeled diagnostic — the #50 MISS STILL
  STANDS AS SCORED): results_wsr_pdir.txt (checksum eb8f5f8d7eb4efad)
  — the WSR overhead envelope measured on a designed 6-cell grid,
  p* in {0.20, 0.50, 0.80} x direction in {UNSAFE, SAFE} at FIXED
  K=6 and R=1.2, five margins per cell (30 rungs). MOTIVATION: every
  envelope in this arc (results_wsr_k.txt, results_wsr_rk.txt, the
  original K=4 calibration) is UNSAFE-direction (certify p > tau, CS
  LOWER bound clears tau), and in the safety pools high p* and the
  favourable direction arrive together, so the residual left open by
  the R null could be p*, direction, or both. UNSAFE certifies
  p > tau at tau = p* - delta with lo > tau; SAFE certifies p < tau at
  tau = p* + delta with hi <= tau — the two SHIPPED tests of
  run_safety_cert.run_arm, on the SHIPPED WSRBlockCS polled every
  block. CRN: one uniform stream per (p*, rung, rep) SHARED by both
  direction arms; since the profile depends only on (p*, R) and R is
  fixed, the two arms consume the IDENTICAL Bernoulli sequence block
  for block and only tau and the tested bound differ — the tightest
  pairing available. Ladder solved PER CELL by an independent pilot
  (seed block 909000, 60 reps, three fixed-point steps on n ~ delta^-2)
  to a COMMON window {250,700,2000,5000,12000}; reps 250/250/200/150/
  120 tapered and disclosed; 30/30 rungs certified 1.00.
  V IS DIRECTION-ASYMMETRIC, ANALYTICALLY, AND IS PRINTED BEFORE ANY
  SIMULATION: UNSAFE V = sup_lam E log(1+lam(M-tau))/K over lam in
  (0,1/tau); SAFE V = sup_lam E log(1+lam(tau-M))/K over lam in
  (0,1/(1-tau)). At delta=0.09 the ratio V_SAFE/V_UNSAFE is 0.506 at
  p*=0.20 and 1.994 at p*=0.80, narrowing to 0.904/1.102 at
  delta=0.02 (Gaussian limit). At p*=0.50 it is EXACTLY 1: the
  two-level profile has p_lo + p_hi = 2p* = 1, so the rate multiset is
  closed under p -> 1-p, the block-mean law is symmetric about 0.5 and
  V_UNSAFE(0.5-d) = V_SAFE(0.5+d) identically (checked to 2.1e-17).
  BOTH V branches are validated against SHIPPED code (64-atom
  v_kelly_block_K at K=6): UNSAFE directly to 1.2e-17, SAFE via the
  exact complement identity V_SAFE(rates,tau) = V_UNSAFE(1-rates,1-tau)
  to 3.5e-17. Because O(n) := n*V - log(1/alpha) divides by each
  direction's OWN V, this entire analytic asymmetry is absorbed BEFORE
  the fit: any direction effect surviving in (d, c) belongs to the
  confidence sequence, not to the information rate.
  6-CELL RESULT (d/c, columns p*=0.20/0.50/0.80): UNSAFE
  1.142/-1.693, 1.257/-2.773, 0.152/+0.582; SAFE 0.250/+0.458,
  1.518/-3.855, 1.043/-0.966.
  P1 FAIL — the (p*=0.20, UNSAFE) cell vs results_wsr_rk.txt's K=6,
  R=1 cell: d 1.142 vs 1.562 (diff -0.420, tol +/-0.35), c -1.693 vs
  -3.235 (diff +1.542, tol +/-0.9). The tolerance had ALREADY been
  widened from the (R,K) grid's +/-0.25/+/-0.6 in advance and with the
  reason stated (that cell is R=1 vs this grid's R=1.2 AND it pooled
  p* in {0.20,0.35} vs this cell's p*=0.20 alone — two design
  differences, not one), and it still fails. POST-HOC ARITHMETIC
  (labeled, from the two artifacts' own printed constants, scores
  nothing): over the two fits' overlapping range n in [261, 7392] the
  envelopes differ at FUNCTION level by at most 0.373 nats (~5% in n),
  the same d<->c trade-off of a two-parameter local fit the (R,K) grid
  reported at ITS K=4 P1 failure (0.446 nats). Anchor identity
  re-verified in-artifact (checksum recomputed AND the 12-cell table
  parsed and asserted against the values scored). Read with P2, the P1
  failure is not an anomaly: a p*-pooled anchor cannot equal a
  single-p* cell once p* is shown to move the constants.
  P2 (the discrimination; ONLY the comparison was pre-committed, no
  winner) — RAW (d, c), the scored metric: DIRECTION axis max |dd|
  0.892 / max |dc| 2.151; p* axis max |dd| 1.269 / max |dc| 4.314.
  Both constants name p*, by 1.42x in d and 2.01x in c: P2 VERDICT
  p*. Reported NOT scored, because raw gaps are not scale-free and d
  and c trade off: in mean-OLS-SE units direction is 2.90/1.82 SE vs
  p* 4.13/3.66 SE (same ordering); at FUNCTION level over the common
  window n in [285, 11415] the ordering REVERSES to direction 2.612
  nats vs p* 2.349 nats, a 1.11x margin, i.e. a wash. SCALE REFERENCE
  (labeled, computed from results_wsr_rk.txt's own printed K=6 cells,
  scores nothing): the REFUTED R axis measured the identical
  function-level way spans 0.658 nats across R = 1..30, so BOTH axes
  here are 3.6-4.0x the axis this same instrument called null. The
  honest reading: p* wins the pre-registered comparison, but DIRECTION
  IS NOT A SECOND NULL — the two are comparable at function level and
  both are real, unlike R. The envelope is DIRECTION-DEPENDENT and
  every envelope in this arc was measured one-sided.
  P3 PASS (0/30 rungs excluded; hard guard unused).
  POST-HOC DIAGNOSTIC (labeled; does NOT re-score #50):
  run_safety_cert's prediction path reused verbatim (load_pool, mu,
  tau=round(mu-0.045,3), single_fourterm, 64-atom v_kelly_block_K at
  K=6, +/-5% tie band), only the WSR overhead swapped, COMMITTED
  column asserted to reproduce the frozen table (it does). All six
  scored pools certify UNSAFE (asserted in-artifact), so the matched
  cells are the three UNSAFE ones at the nearest p*. THIS IS THE FIRST
  ENVELOPE IN THE ARC THAT RECOVERS THE MISS'S RESOLUTION: PDIR-N
  gives 6 RESOLVING calls, 4 HIT / 1 MISS / 1 unconfirmed = matched
  4/5, against the frozen 1/2 and the (R,K) surface's 1/2. Q1 YES,
  Q2 YES -> ANSWER "YES on both". Errors COMMITTED [-11.8%, +37.2%]
  -> PDIR-N [-23.7%, +18.1%]. mistral-7b — the pool that produced the
  scored MISS — moves SINGLE -> WSR and now MATCHES the measured WSR
  (n_wsr 844 -> 649 vs measured 678, err +24.5% -> -4.3%);
  llama3.1-8b +19.3% -> +2.8% and qwen2.5-7b +9.2% -> +0.3%. The one
  new MISS is qwen2-7b (lowest p*, 0.107; predicted WSR, measured
  SINGLE, err -11.8% -> -23.7%), so the residual has moved from the
  high-p* pools to the low-p* one. PDIR-I (linear-in-p* interpolation)
  agrees call-for-call. DIR-SWAP (SENSITIVITY ONLY, never a
  prediction): using the p*-matched SAFE cell instead moves n_wsr by
  -37% to +37% (mistral 649 -> 888, qwen2.5 515 -> 446), which is the
  diagnostic-side statement of the same direction-dependence P2
  measured. THE #50 MISS STANDS AS SCORED — the diagnostic is
  post-hoc, uses constants fitted after the miss was recorded, and
  scores nothing; miss ledger unchanged (33 rows).
  SCOPE, disclosed in-artifact: R is held at 1.2 for every cell while
  the pools run R = 1.16-17.0, licensed ONLY by the R null of
  results_wsr_rk.txt, which is a failure to detect over [1,30], not a
  proof of R-independence; the two-level profile stands in for six
  category rates; p* = 0.857 extrapolates 0.057 past the top cell (the
  (R,K) grid extrapolated 0.507 past ITS top p*, so this is a strict
  improvement, not a fix); stock WSR has no fixed (d,c) asymptotically
  (results_wsr_expansion.txt) so every envelope here is an EFFECTIVE
  LOCAL fit; tau's 0.001-lattice offset is DIRECTION-SYMMETRIC by
  construction (UNSAFE lo > tau effectively certifies at tau + 0.0005,
  SAFE hi <= tau at tau - 0.0005, so both lose exactly 0.0005 of
  margin) and so cannot masquerade as a direction effect — its size
  (0.5-4.5% of margin) is printed per rung. DISCLOSED DEVIATION: five
  margins per cell span 48x in n, not the (R,K) grid's 32x, because
  the requested 250-12000 window is itself 48x. Freeze convention as
  for the two previous grids: a measurement grid, docstring committed
  WITH the results, P1-P3 print PASS/FAIL. Next clause: the envelope's
  arguments are block size K, p*, and DECISION DIRECTION; R remains
  ruled out; the residual now sits at LOW p* rather than high.
- 2026-08-19 (#51 RLA BRIDGE, second and final domain extension, SCORED;
  miss ledger unchanged at 33 rows -- this frozen set produced no miss):
  results_rla.txt (checksum 1eefa5b579a1b395). Freeze committed BEFORE
  results in its own commit (5b831fb, script + docstring table + the src
  fix below); results and docs in the follow-up commit. Pool: Georgia
  2020 presidential, 12 county strata + one aggregate remainder from
  approximate-official certified totals (source URL in the docstring),
  size-proportional weights (F14 population-mean estimand verbatim),
  p* = 0.501193, margin 0.239%, R = 3.22, N = 4,935,487. Threshold
  tau = 0.5, direction rejects_le (UNSAFE branch) on every cell, stated
  before the run. FROZEN: SINGLE at the real margin (both alphas),
  TIE at 2%, WSR at 5% (both alphas); 2 resolving, 2/2 flip under a
  wrong-theory single arm -> DISCRIMINATING. WSR constants =
  results_wsr_pdir.txt cell (K=6, p*=0.50, UNSAFE), chosen as nearest in
  ALL THREE known envelope arguments; this is the FIRST PROSPECTIVE test
  of those constants (their 4/5 safety recovery was labelled post-hoc).
  MEASURED (150 CRN-paired reps/arm/cell, v2c HD bootstrap, identical
  ballot sequence across arms): P1 1/1 HIT (WSR at 5%/alpha=0.05, 4,032
  vs 4,914 ballots); 5%/alpha=0.10 measured TIE = unconfirmed, NOT a
  miss; frozen TIE at 2% measured TIE. P2 PASS -- UI never certifies at
  all within n_max on any cell (censored 150,000 / 12,000). P3 = the
  risk limit in RLA terms, on a NULL pool shifted to p* = 0.5 exactly:
  1/450 audits ever certified "winner leads" = 0.0022 <= 0.05; the
  wrong-direction counts on the true pools are each inside their own
  alpha (1/450, 14/450, 29/450 at alpha=0.10). Single-arm predictor
  error 0.0% / -2.6% / +7.1%; WSR envelope error -11.6% / +9.8% / +5.0%
  (BOTH SIGNS -- no longer the one-sided +19-37% of the K=4 constants).
  BALLOTS: design choice worth 882 (1.22x) at 5% and 3,096 (1.09x) at
  2%; >=3-4x against UI; within +-12% of a fixed-n binomial audit at the
  same power and 4,137 ballots CHEAPER at 2% (early stopping repays the
  mixture overhead) while buying validity under peeking/escalation. At
  the real 0.239% margin every design needs a MAJORITY of the ballots
  cast (3.19M / 3.40M / 2.77M fixed-n vs 4.94M), so no ballot-polling
  audit beats a full hand count -- which is what Georgia did; the margin
  axis reproduces that decision unprompted.
  SCOPE/DISCLOSURES, all in-artifact: the GA-official rows are
  PREDICTED-ONLY (3.2M ballots/rep is three orders beyond the simulation
  budget) and unscored, and use the four-term closed form, which is
  validated against the exact recursion at both simulated margins
  (-1.7% to -3.4%, the schedule term); the 2% and 5% cells are
  SYNTHETIC-MARGIN pools (one common additive shift of every county
  share, R 3.22 -> 3.15/3.04), disclosed as constructed, not elections;
  the single/UI check period D is a compute choice (D*KL <= 0.06 nats,
  <=1.0% of the crossing, below the tie band) and is carried in the
  predictor too, so powered model and executed replay share one stopping
  rule (severity_sim rev 3 rule (c)); R is inert for the single/WSR
  arms under uniform statewide draws, licensed ONLY by the R null of
  results_wsr_rk.txt, which is a failure to detect, never a proof.
  NON-CLAIM, mandatory in any write-up: nothing here improves SHANGRLA /
  BRAVO / ALPHA / UI-TS and no procedure here is proposed for a real
  election; county totals fix pool parameters only.
- 2026-08-19 (DEFECT, found by #51 and fixed before its results):
  StratifiedUICS._m_of_lambda selected the wrong root of the KKT
  quadratic when a stratum is saturated (s = 0 or f = 0). There the
  quadratic factors as (m-1)(a m - f) (resp. m (a m - (s+a))), so the
  admissible root IS an endpoint of [0,1] and can land one ulp outside
  it; `in1 = (r1 >= 0) & (r1 <= 1)` then rejected it and the code took
  the other root, which lies outside [0,1] and is clipped to the
  OPPOSITE endpoint. Consequence: min_log_e returned values exceeding
  log E at feasible points of its own null set by up to 100 nats ->
  spurious `ge`-direction rejections at n = 42 ballots (measured:
  wrong-direction certifications in a majority of reps on the UI arm).
  Fixed with an endpoint tolerance; regression test asserts the
  mathematical invariant (an infimum cannot exceed a feasible point) on
  the real Georgia weights and FAILS on the old code. 110 -> 112 tests.
  Scope of impact, checked: the defect lives in the k>1 constrained
  optimizer only, so it can move UI-arm results and wrong-direction
  counts and cannot move any frozen prediction, the single arm, or the
  WSR arm. Prior artifacts using UI (results_partition_test.txt,
  results_safety.txt) reported UI as DOMINATED and their P3 wrong-cert
  counts were small (4/2700 in #50), so no prior verdict flips; not
  regenerated, and the exposure is recorded here rather than assumed
  away. Generator: an object correct in every configuration it had been
  run in, wrong in the first configuration it had not -- the relation
  gate's own thesis, this time caught by a domain port instead of a
  census.
- 2026-08-19 (PAPER v4.2 CONSOLIDATION; one contradiction in THIS file
  found and resolved): paper/DRAFT.md v4.1 -> v4.2, consolidation only
  (v4.1 section skeleton preserved; every addition is a new subsection
  or an in-place sync). Folded in: NEW 4.8 "Export: two out-of-family
  domains" (4.8.1 safety #50 with the frozen table, the mandatory
  pool-parameters-not-rankings non-claim printed adjacent to that table,
  the scored P1 1/2 MISS, P2 0/6, P3 4/2700, and the 43.3% label-noise
  disclosure; 4.8.2 the RLA bridge #51 with the frozen margin-axis
  table, P1 1/1 HIT, TIE confirmed at 2%, P3 1/450 = 0.0022 on the
  null pool, the ballots-saved table, the real-margin majority result,
  and the mandatory SHANGRLA/BRAVO/ALPHA/UI-TS non-claim); 5.5 extended
  with the three envelope grids (K linear laws, the R refutation
  recorded as a scored P2 FAIL that IS the finding, direction+p* with
  V's asymmetry divided out before the fit, and the standing statement
  that the envelope is a measured (K, p*, direction) surface with R
  null); 6.2 instance 9 (StratifiedUICS KKT root defect, 110 -> 112
  tests); 6.3 ledger + 1 row; 7 items 21-22 and item 13 synced; 8 new
  "Risk-limiting audits" paragraph (Stark 2020 SHANGRLA, Stark 2023
  ALPHA added to References); 1.2 two mandatory non-claims added; 9
  test count, six new checksums, and the safety raw-generation storage
  exception that README already cited to paper 9. Abstract updated
  minimally (one domain-export paragraph naming the miss first, 112
  tests, 34-row ledger).
  CONTRADICTION FOUND AND RESOLVED -- MISS LEDGER COUNT. This file's
  #50 entry says "miss ledger +1" against a v4.1 baseline of 33 rows
  (commit 9fa5758, "ledger 33 rows"), which makes the post-#50 count
  34. The four entries that follow it (wsr_k, wsr_rk, wsr_pdir, #51)
  each say "miss ledger unchanged (33 rows)". Both cannot be true.
  RESOLUTION: the "+1" is authoritative on the DELTA -- v4.1's table
  demonstrably lacked any safety row and was counted at 33 -- and the
  four "(33 rows)" parentheticals are a stale count copied forward;
  their load-bearing content is "unchanged BY THIS ARTIFACT", which is
  correct in every case (all four are measurement grids that added no
  miss). THE LEDGER IS 34 ROWS as of the safety P1 row, and v4.2 prints
  34. The four stale parentheticals are left in place as the record
  rather than back-edited; this entry is the correction.
  Also recorded, both disclosed in-draft rather than silently fixed:
  (a) v4.1's 1.2 said "the boundary work adds four more" above five
  bullets -- an off-by-one predating this pass, corrected to seven with
  the two new non-claims and the miscount named; (b) the relation gate
  was last run against v4.1 and the v4.2 additions have NOT been
  re-scanned -- 6.2 says so, and says the new per-cell tables would ADD
  to the R5 count rather than reduce it. No verdict, no artifact and no
  number was changed by this pass; nothing was re-run except the test
  suite (112 passed). publish_sync.sh untouched and not run.
- 2026-08-19 (post-v4.2 gate rescan): relation gate re-run over v4.2 —
  no new flag classes; same disclosed set (A2 permanent non-evidence,
  results_cren_exact R4, R5 prose-heuristic hits incl. two new n-of-m
  phrases from v4.2 text). The in-draft 6.2 note about the un-rescanned
  additions is now discharged.
- 2026-08-20 (Task A, joint attack): WSR ENVELOPE LAW DERIVED ZERO-FIT
  by the gpt-5.6-sol lineage (explicit max effort, on record) and
  INDEPENDENTLY VERIFIED here: fresh end-to-end rerun reproduces every
  substantive prediction block byte-identically (only the created_unix
  timestamp differs; the hash covers it, explaining the hash delta);
  freeze structure sound (predict() upstream of any artifact read);
  measured column matches the committed grids. The law closes as a
  FINITE-WINDOW PROJECTION of the cumulative stock-schedule drift (no
  fixed-d asymptotic, consistent with the divergence result): d slope
  pred -0.4453 vs meas -0.4267 (4.4%), d intercept 4.206 vs 4.141
  (1.6%), c slope 1.056 vs 0.964 (9.5%), c intercept -9.107 vs -8.980
  (1.4%); per-K rows within the same envelope. DIRECTION EFFECT
  confirmed CS-side (asymmetric lambda caps 0.75/m vs 0.75/(1-m)):
  predicted within 2.3-4.8%, exact SAFE/UNSAFE symmetry at p*=0.5
  (|Delta O| < 2.4e-14). NOT CLOSED, as prominent as the wins: p*
  carrier underpredicted (14% d / 19% c); R null closes at FUNCTION
  level (0.667 vs 0.658 nats) but NOT in fitted-coordinate signs —
  "near-null in effect, not exact invariance"; c slope loosest at
  9.5%. Clock-conversion negative: n=KT alone cannot move d.
  Artifacts adopted at scripts/external/ (derive_wsr_envelope.py +
  predictions.json + verification.json; imports the shipped class).
- 2026-08-20 (freeze-design fix, R4b-adjacent, broker-flagged): the
  Task-A prediction hash covered created_unix, so it certified tamper-
  evidence, NOT rerun-reproducibility (the actual freeze guarantee) —
  reproducibility was established here by the byte-identical rerun,
  not the hash. Fixed in the adopted copy: provenance now sits outside
  the hashed object; stable hash 80e2e8e86f99... verified identical
  across two fresh reruns; predictions.json regenerated (substantive
  content unchanged). Rule for future frozen artifacts: hash the
  prediction payload only. Also adopted: the corrected worker-CPU
  diagnostic (codex parent sits at ~0:00.01 forever; check the WORKER's
  cumulative CPU advancing over ~60s — instantaneous %CPU is ~0 for
  healthy API-bound max-effort runs).
- 2026-08-20 (Task A, SECOND LINEAGE, independent of the entry above):
  the same WSR envelope law derived by a DIFFERENT route and scored
  4/4 HIT plus three mechanism predicates.
  scripts/derive_wsr_envelope.py -> results_wsr_envelope.txt (checksum
  c052f57840f4f670). NAMING WARNING: this is NOT
  scripts/external/derive_wsr_envelope.py, the gpt-5.6-sol artifact
  adopted in the entry immediately above -- same basename, different
  directory, different derivation, different output file.
  INDEPENDENCE: this script's FROZEN docstring constants were written
  and its run launched BEFORE that entry existed in this file; no
  number was taken from it. The two lineages agree to 1-4%, which is
  itself the cross-check (see the CONVERGENCE paragraph below).
  MECHANISM (this lineage's route). The stock bet is a decaying Kelly
  FRACTION. lam_t = sqrt(2 log(2/alpha)/(sq_t log(t+1))) with
  E[sq_t] ~ mu2 (t + t0 - 1), mu2 = p(1-p)/K the block variance and
  t0 = (1/4)/mu2 = K/(4 p(1-p)) -- the SHIPPED PRIOR sq_0 = 1/4
  divided by that variance -- so the Kelly fraction is
  r_t := lam_t/lam* = sqrt(L2/(V* (t+t0-1) log(t+1))) and the
  per-block growth is the quadratic Kelly loss V*(2 r_t - r_t^2).
  Summing: W(T) = 2 sqrt(L2 V*) G1(T) - L2 G2(T), a sqrt(T/log T)
  gross gain minus a LOGLOG Kelly deficit. Implicit differentiation of
  the crossing W(T) = L2 against the ordinate nV = T V* gives
  d_eff = 2 rho T V* [1 - 2 T w_T / A], A = Lambda + L2 G2(T; t0).
  K ENTERS ONLY THROUGH G2, and BOTH of its loglog limits are
  K-driven: upper T = n/K (fewer blocks per sample budget), lower
  t0 = K/(4pq) (longer warm-up, in blocks). Hence
  dA/dK = -(L2/K)[1/log T + 1/log t0]. THE MEASURED K-LINEARITY IS A
  CHORD, NOT THE LAW: the 1/K prefactor makes d(K) convex, and
  results_wsr_k.txt's own linear-fit residual signs (+,-,-,+) are that
  convexity's signature -- scored as P4, PASS.
  EVALUATION, and the methodological step past derive_floor_d.py. The
  ladder is solved WITHOUT the quadratic reduction: the exact
  (K+1)-atom increment law is pushed through an exact grid-convolution
  first-passage operator absorbing at log(2/alpha), which returns the
  MEDIAN crossing block directly. Overshoot, the median-vs-mean shift
  and the strongly non-homogeneous early variance are therefore carried
  exactly and NO renewal level convention (derive_floor_d's homogeneous
  kappa = s^2/2nu) is assumed. Validated in-artifact against a DIRECT
  simulation of the shipped WSRBlockCS on five probe rungs with this
  script's own seeds: derived/shipped in [0.974, 1.038] at 500 reps,
  against a ~3% median sampling error.
  FROZEN then SCORED. Window = sum of three variant spreads + 2
  SE_meas, the rule fixed before any derived constant was evaluated;
  the coarser G1/G2 closed form is deliberately NOT a window term
  (including a strictly worse approximation would only widen the
  window, i.e. weaken the test).
    d slope   -0.4542 vs measured -0.4267  (W 0.174)  HIT
    d int     +4.3004 vs measured +4.1405  (W 1.230)  HIT
    c slope   +1.0455 vs measured +0.9638  (W 0.351)  HIT
    c int     -9.4935 vs measured -8.9805  (W 2.780)  HIT
  All four also HIT on the "tight" window that drops the most
  conservative variant. On 2 SE_meas ALONE only 3/4 would hit (c int
  0.513 vs 0.468 would miss) -- that is the honest resolution limit and
  it is printed.
  DIRECTION x p* (results_wsr_pdir.txt). T1 is a THEOREM about the
  shipped class, verified to machine precision here: WSRBlockCS is
  equivariant under x -> 1-x (its grid 0.0005+0.001k is symmetric, its
  priors 1/2 and 1/4 are symmetric, sq_t is invariant, the two arms and
  their truncations c/m and c/(1-m) swap, the hedge (K+ + K-)/2 is
  symmetric), so lo(x) = 1 - hi(1-x) at EVERY poll (1.1e-16) and SAFE
  certification of pool P at tau is PATHWISE IDENTICAL to UNSAFE
  certification of pool 1-P at 1-tau (crossing times bit-identical).
  DIRECTION IS THEREFORE NOT AN INDEPENDENT ENVELOPE ARGUMENT. The
  6-cell table must collapse across its anti-diagonal, and it does:
  6/6 pairs agree within pooled OLS SE (P5 PASS; worst 0.727 nats on c
  against SE 1.482), whereas the same-p* direction contrast that
  artifact reported runs 2.2-2.3 SE. The entire "direction effect" is
  predicted from that artifact's own UNSAFE row with zero free
  parameters: dd(p*) = d_U(1-p*) - d_U(p*) gives -0.990 / 0 / +0.990
  against measured -0.892 / +0.261 / +0.891. T2, the p* carrier itself,
  is the BLOCK SKEWNESS: eps = (2/3) r^3 g mu3/mu2^2 with
  mu3/mu2^2 = (1-2p)/(p(1-p)) EXACTLY, so K cancels, it vanishes at
  p* = 1/2 (matching that artifact's exact V-symmetry there) and is odd
  in (p* - 1/2); its four sign predicates all HIT (P6 PASS).
  CONVERGENCE AND THE RESIDUAL THAT NEITHER LINEAGE CLOSED. Against the
  gpt-5.6-sol numbers in the entry above, the two independent routes
  agree to 2.0% (d slope), 2.2% (d int), 1.0% (c slope) and 4.2%
  (c int). But BOTH overshoot the measurement on ALL FOUR constants, in
  the same direction: a shared systematic of order 2-6% survives two
  independent derivations and is NOT explained by either. Stated as an
  open item, not as agreement.
  ASSUMPTIONS CARRIED, all disclosed in-artifact, none proved: (a) the
  increment LAW uses the deterministic lam-bar path, the schedule's own
  randomness entering only as a mean correction delta_t plus a
  barrier-displacement probe of the dispersion channel; (b) the minus
  arm is dropped from the barrier (measured leak displaces it 3e-5
  nats); (c) identifying a reflected SAFE cell with the MEASURED cell
  at 1-p* leans on the R null of results_wsr_rk.txt, which is a failure
  to detect and not a proof -- reflecting an R=1.2 pool gives R = 1.047
  and 2.142, not 1.2, and only at p* = 0.50 is the reflected pool the
  measured pool exactly; (d) the ASYMPTOTIC closed form overstates the
  exact implicit slope by up to ~2x at K=8 and is kept only because it
  exhibits the mechanism -- the scored prediction never uses it.
  POST-HOC, labelled and NOT scored (no predicate was pre-registered on
  the derived cell VALUES): 12/12 derived pdir cell constants land
  within one OLS SE of measurement.
  Miss ledger unchanged BY THIS ARTIFACT. Nothing committed; the
  working tree is left for the main session under the cross-lineage
  adoption rules, and no file other than this one and the two new
  artifacts was touched.
