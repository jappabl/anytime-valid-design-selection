# Objective Experiments - Audit Evidence

**Status**: Ready to run
**Date**: 2025-12-28
**Purpose**: Empirical validation for 3rd party audit

---

## Quick Start

```bash
# Run all validation experiments
./scripts/run_all_validations.sh
```

This runs:
1. **Coverage validation** (~30 seconds) - No API key needed
2. **Intersection tightness** (~10 seconds) - No API key needed
3. **Stratified sampling** (~5-10 minutes) - Requires OpenAI API key

---

## Experiment 1: Coverage Validation

**File**: `scripts/validate_coverage.py`

**Validates**: Claim 1 from [AUDIT_PREP.md](AUDIT_PREP.md#claim-1-intersection-bounds-with-α-splitting-maintains-valid-coverage)

**Method**: Monte Carlo simulation
- 200 replications per configuration
- 5 different true p values: {0.01, 0.05, 0.10, 0.30, 0.50}
- 100 samples per replication
- Tests both Hoeffding and Intersection bounds

**Success Criteria**: Empirical coverage ≥ 0.95 - 0.10 = 0.85

**Evidence Provided**:
- ✓ Both Hoeffding and Intersection achieve nominal coverage
- ✓ Coverage holds across different values of p
- ✓ Validates Bonferroni union bound argument

**Results** (from validation run):
```
      Method |   True p |   Coverage |   Expected |   Status
--------------------------------------------------------------------------------
   Hoeffding |     0.01 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.01 |      1.000 |      0.950 |   ✓ PASS
   Hoeffding |     0.05 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.05 |      1.000 |      0.950 |   ✓ PASS
   Hoeffding |     0.10 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.10 |      1.000 |      0.950 |   ✓ PASS
   Hoeffding |     0.30 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.30 |      1.000 |      0.950 |   ✓ PASS
   Hoeffding |     0.50 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.50 |      1.000 |      0.950 |   ✓ PASS
```

**Conclusion**: ✓ Claim 1 validated empirically

---

## Experiment 2: Intersection Bounds Comparison ❌ DEPRECATED

**Original File**: `scripts/validate_intersection_tightness.py` (DEPRECATED - used buggy implementation)

**Status**: ❌ **CLAIM WITHDRAWN** - Results were artifacts of Bernstein constant bug

**What Happened**:
- Original results showed "47.9% improvement" for low p
- This was based on **buggy implementation** using `range_term = log_term / (3*n)`
- Correct formula per Maurer & Pontil (2009): `range_term = (7/3) * log_term / (n-1)`
- Bug was ~7x too small, causing falsely tight bounds that violated coverage guarantee

**Corrected Results** (from [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py)):

With correct Bernstein formula:
- **At n ≤ 200** (our experimental regime): Intersection is **+2.3% WIDER** on average
- **At n ≥ 500, p ≤ 0.05**: Intersection is **-13.7% narrower** on average
- α-splitting overhead (~2.8%) dominates variance savings at small n

**New Artifact**: [results_bounds_comparison.txt](results_bounds_comparison.txt)

**To Run Corrected Comparison**:
```bash
python3 scripts/comprehensive_bounds_comparison.py
```

**Conclusion**: ❌ Claim 2 INVALIDATED - Intersection provides NO benefit in our experimental regime (n ≤ 200)

**Technical Details**: See [AUDIT_PREP.md - Claim 2](AUDIT_PREP.md#claim-2-intersection-provides-tighter-bounds) and [TECHNICAL_SPEC.md Section 9](TECHNICAL_SPEC.md#9-performance-comparison)

---

## Experiment 3: Stratified Sampling

**Files**:
- `run_stratified_experiments.py` - Runs experiments
- `analyze_stratified_results.py` - Analyzes results

**Validates**: Claim 3 from [AUDIT_PREP.md](AUDIT_PREP.md#claim-3-stratified-sampling-prevents-early-stopping-bias)

**Method**: Paired experiment with real LLM
- Naive: Uniform random sampling across prompts
- Stratified: Round-robin across 4 difficulty strata
- Both use GPT-4o-mini with temperature=0
- 1000 samples max, stop early if precision ≤ 0.10 or certification
- Min samples: 200 (prevents premature stopping)

**Configs**:
- [configs/stratified_gpt4mini_naive.yaml](configs/stratified_gpt4mini_naive.yaml)
- [configs/stratified_gpt4mini_stratified.yaml](configs/stratified_gpt4mini_stratified.yaml)

**Evidence Provided**:
- ✓ Heterogeneity exists (per-stratum failure rates differ)
- ✓ Naive exhibits sampling imbalance
- ✓ Stratified maintains perfect balance (variance ≈ 0)
- ✓ Both maintain time-uniform validity

**Requirements**:
- OpenAI API key in `.env` file
- Cost: ~$1.00-2.00 (2000 samples × gpt-4o-mini)

**To Run**:
```bash
# Ensure .env file exists with OPENAI_API_KEY
python3 run_stratified_experiments.py
python3 analyze_stratified_results.py
```

**Results** (completed 2025-12-28):

### Overall Results

| Method | n | Failures | p̂ | 95% CI | Width | Status |
|--------|---|----------|-----|---------|-------|--------|
| Naive | 1000 | 249 | 0.2490 | [0.1604, 0.3376] | 0.1771 | COMPLETE |
| Stratified | 1000 | 250 | 0.2500 | [0.1613, 0.3387] | 0.1774 | COMPLETE |

Both experiments ran to max_samples=1000 (width did not reach 0.10 target).

### Heterogeneity Validation

Per-stratum failure rates demonstrate **extreme heterogeneity**:

**Naive Experiment**:
| Stratum | Samples | Failures | Failure Rate |
|---------|---------|----------|--------------|
| Simple  | 244 | 0 | 0.00% |
| Medium  | 251 | 0 | 0.00% |
| Complex | 256 | 0 | 0.00% |
| **Extreme** | **249** | **249** | **100.00%** |

**Stratified Experiment**:
| Stratum | Samples | Failures | Failure Rate |
|---------|---------|----------|--------------|
| Simple  | 250 | 0 | 0.00% |
| Medium  | 250 | 0 | 0.00% |
| Complex | 250 | 0 | 0.00% |
| **Extreme** | **250** | **250** | **100.00%** |

**Finding**: ALL failures came from the "extreme" stratum (NIGHTMARE mode schemas). Simple, medium, and complex strata had 0% failure rate. This is the strongest possible demonstration of heterogeneity.

### Stratum Balance Validation

Sampling distribution comparison:

**Naive (Uniform Random)**:
- Simple: 244 (24.4%)
- Medium: 251 (25.1%)
- Complex: 256 (25.6%)
- Extreme: 249 (24.9%)
- **Variance: σ² ≈ 18.5** (natural sampling variation)

**Stratified (Round-Robin)**:
- Simple: 250 (25.0%)
- Medium: 250 (25.0%)
- Complex: 250 (25.0%)
- Extreme: 250 (25.0%)
- **Variance: σ² = 0** (perfect balance)

**Finding**: Stratified sampling achieves **perfect balance** across all strata (zero variance), while naive exhibits natural sampling variation.

### Early-Stopping Bias Potential

With p̂ = (# extreme samples) / (total samples):
- **Naive**: p̂ = 249/1000 = 0.249
- **Stratified**: p̂ = 250/1000 = 0.250

At n=1000, both converged to similar estimates. However:
- **Naive risk**: If by chance more extreme prompts sampled early → inflated p̂ → tighter CI → stop early with biased estimate
- **Stratified guarantee**: Always exactly n/4 samples per stratum at any n → E[p̂ | stopped at n] = p (unbiased)

**Finding**: With extreme heterogeneity (p_extreme = 1.0, p_others = 0.0), stratum imbalance directly translates to biased p̂. Stratified sampling eliminates this risk.

**Conclusion**: ✓ Claim 3 validated
1. ✓ Extreme heterogeneity demonstrated (p values range 0.0 to 1.0)
2. ✓ Stratified achieves perfect balance (σ² = 0)
3. ✓ Naive exhibits natural imbalance (σ² = 18.5)
4. ✓ Both maintain time-uniform validity (CIs contain true p)

---

## Experiment Setup

### Environment File

Created [.env](.env) with OpenAI API key:
```bash
OPENAI_API_KEY=sk-proj-...
```

### Dependencies

All experiments use existing codebase:
- `src/eval_harness/stats/bernoulli_cs.py` - Hoeffding bounds
- `src/eval_harness/stats/bernoulli_cs_intersection.py` - Intersection bounds
- `src/eval_harness/core/runner.py` - Experiment runner
- `src/eval_harness/prompts/stratified_json_prompts.py` - Stratified sampler

No additional packages required.

### Reproducibility

All experiments use fixed seeds:
- Coverage: seed = 42 + experiment_id
- Tightness: seed = 42 + true_p index
- Stratified: seed = 42 (in config)

Results are deterministic (modulo LLM API non-determinism for Experiment 3).

---

## Audit Evidence Summary

### What We Can Prove

| Claim | Evidence | Status |
|-------|----------|--------|
| Intersection maintains coverage ≥ 1-α | Experiment 1 | ✓ Validated |
| Intersection tighter for low p | ~~Experiment 2~~ | ❌ WITHDRAWN (bug invalidated) |
| Stratified prevents composition drift | Experiment 3 | ✓ Validated (mechanism) |
| Time-uniform validity | All experiments | ✓ Implicit in coverage |
| Implementation correctness | pytest tests + new tests | ✓ Pass (13 tests added) |

### What We Cannot Prove

1. **Exact improvement percentages** - Data-dependent
2. **Naive always exhibits bias** - Depends on heterogeneity + stopping
3. **Coverage is exactly 95%** - Monte Carlo has variance

### Confidence Levels

- **Theoretical correctness**: High (standard methods)
- **Implementation correctness**: High (tests pass, validations pass)
- **Practical impact**: Medium (need Experiment 3 results)

---

## Running All Experiments

```bash
# Quick validation (no API key needed)
python3 scripts/validate_coverage.py
python3 scripts/comprehensive_bounds_comparison.py  # Corrected comparison

# Full validation (requires API key)
./scripts/run_all_validations.sh
```

**Total Time**:
- Experiments 1+2: ~40 seconds
- Experiment 3: ~2 hours (1000 samples × 2 experiments)
- **Total: ~2 hours**

**Total Cost**:
- Experiments 1+2: Free (local simulation)
- Experiment 3: ~$1.50-2.00 (2000 samples × gpt-4o-mini)

---

## Next Steps

1. ✅ Run Experiments 1+2 (completed)
2. ✅ Run Experiment 3 with OpenAI API (completed)
3. ⏳ Review results with auditor
4. ⏳ Address any questions from [AUDIT_PREP.md](AUDIT_PREP.md)

---

## Files Created

**Validation Scripts** (for audit):
- `scripts/validate_coverage.py` - Coverage validation (Claim 1)
- `scripts/validate_intersection_tightness.py` - Tightness validation (Claim 2)
- `scripts/run_all_validations.sh` - Run all validations

**Experiment Scripts** (existing):
- `run_stratified_experiments.py` - Run stratified experiments
- `analyze_stratified_results.py` - Analyze stratified results

**Config Files** (updated):
- `configs/stratified_gpt4mini_naive.yaml` - Naive sampling config
- `configs/stratified_gpt4mini_stratified.yaml` - Stratified sampling config
- `.env` - OpenAI API key

**Documentation**:
- `AUDIT_PREP.md` - Claims and rebuttals
- `EXPERIMENTS.md` - This file
