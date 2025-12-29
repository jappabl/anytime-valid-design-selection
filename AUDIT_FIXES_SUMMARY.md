# Audit Fixes Summary - 2025-12-28

## Overview

A third-party audit identified **5 critical issues** in the LLM evaluation framework. All have been addressed.

---

## Issues Fixed

### ✅ Issue 1: Bernstein Constant Bug (CRITICAL)

**Problem**: Empirical Bernstein bound used incorrect formula
```python
# OLD (WRONG - caused undercoverage)
range_term = log_term / (3 * n)

# NEW (CORRECT per Maurer & Pontil 2009)
range_term = (7/3) * log_term / (n - 1)
```

**Impact**:
- ~7x difference in range term magnitude
- Old formula gave falsely tight bounds that violated 95% coverage guarantee
- All previous "tightness" results were artifacts of this bug

**Files Modified**:
- [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L196-L203)
- [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L226-L233)

**Validation**: Re-ran coverage validation - maintains 100% empirical coverage ✅

**Critical Consequence**: **Claim 2 INVALIDATED**
- Old claim: "40-60% improvement for low p"
- New reality: Intersection is 2-3% WIDER than Hoeffding
- The "improvement" was due to the bug, not a real methodological advance

---

### ✅ Issue 2: Hash Nondeterminism

**Problem**: Used `hash(stratum)` for seed derivation, which is randomized by PYTHONHASHSEED
```python
# OLD (WRONG - nondeterministic)
seed=self.seed + hash(stratum) % 1000

# NEW (CORRECT - deterministic)
seed=self.seed + STRATUM_SEED_OFFSETS[stratum]
```

**Impact**: Experiments not reproducible across Python sessions

**Files Modified**:
- [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py#L22-L27)
- [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py#L65-L75)

**Validation**: Added reproducibility tests - same seed → identical prompts ✅

---

### ✅ Issue 3: Incomplete Test Coverage

**Problem**: Tests only covered Hoeffding baseline, missing:
- α-splitting logic
- Intersection bounds mechanics
- Correct Bernstein constants (7/3, n-1)
- Stratified sampler balance

**Fix**: Created comprehensive test suite with 13 tests covering all missing areas

**Files Created**:
- [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py)

**Test Results**: All 13 tests passing ✅
```
TestAlphaSplitting: 2 tests
TestIntersectionMechanics: 2 tests
TestBernsteinConstants: 3 tests
TestStratifiedSamplerBalance: 3 tests
TestReproducibility: 3 tests
```

---

### ✅ Issue 4: "499 Failures" Wording Clarification

**Problem**: "ALL 499 failures" sounded like one experiment, but was 249 + 250 across two

**Fix**: Clarified in documentation:
- Naive experiment: 249 failures (all from extreme stratum)
- Stratified experiment: 250 failures (all from extreme stratum)

**Files Modified**:
- [AUDIT_PREP.md](AUDIT_PREP.md#L73-L75)

---

### ⚠️ Issue 5: Early Stopping Not Demonstrated

**Problem**: Both experiments hit max_samples=1000 (budget cap), never stopped early
- Proved perfect balance ✅
- Did NOT demonstrate the bias that balance prevents ❌

**Status**: Acknowledged in documentation
- Claim 3 reframed: "Eliminates a SOURCE of bias"
- Bias only manifests when actually stopping early
- Would need new experiment with lower max_samples and realistic stopping criteria

**Files Modified**:
- [AUDIT_PREP.md](AUDIT_PREP.md#L45-L48)

---

## Impact on Research Claims

### Claim 1: Intersection Maintains Coverage ✅
**Status**: ✅ **VALIDATED**
- Coverage maintained after bug fix (100% empirical coverage)
- α-splitting logic correct
- Bonferroni union bound argument sound

### Claim 2: Intersection Provides Tighter Bounds ❌
**Status**: ❌ **INVALIDATED**
- Was based on buggy implementation
- With correct formula: intersection is 2-3% WIDER, not tighter
- No longer a contribution of this work

### Claim 3: Stratified Sampling Prevents Bias ✅
**Status**: ✅ **VALIDATED** (with caveat)
- Perfect balance demonstrated (σ² = 0 vs σ² = 18.5)
- Extreme heterogeneity confirmed (p_extreme = 1.0, p_others = 0.0)
- Caveat: Didn't actually demonstrate bias because didn't stop early
- Claim holds theoretically and balance is proven empirically

---

## Revised Research Contribution

### Before Audit
**Primary**: Stratified sequential evaluation
**Secondary**: Intersection bounds (40-60% improvement)

### After Audit
**Primary**: Stratified sequential evaluation ← **ONLY CONTRIBUTION**
**Secondary**: ~~Intersection bounds~~ (bug invalidated this)

**New Focus**: The work is now solely about stratified sampling for sequential evaluation, not about bound tightness.

---

## Files Modified

### Core Implementation
1. [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py)
   - Fixed Bernstein constant (lines 196-203, 226-233)

2. [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py)
   - Fixed hash nondeterminism (lines 22-27, 69)

### Tests
3. [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) ← NEW
   - 13 comprehensive unit tests
   - All passing

### Documentation
4. [AUDIT_PREP.md](AUDIT_PREP.md)
   - Added critical update section
   - Invalidated Claim 2
   - Clarified "499 failures"
   - Updated bottom line

5. [AUDIT_FIXES_SUMMARY.md](AUDIT_FIXES_SUMMARY.md) ← THIS FILE
   - Summary of all fixes

---

## Validation Results

### Coverage Validation (Experiment 1)
```
      Method |   True p |   Coverage |   Expected |   Status
--------------------------------------------------------------------------------
   Hoeffding |     0.01 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.01 |      1.000 |      0.950 |   ✓ PASS
   Hoeffding |     0.05 |      1.000 |      0.950 |   ✓ PASS
Intersection |     0.05 |      1.000 |      0.950 |   ✓ PASS
   ... (all passing)
```

### Tightness Validation (Experiment 2)
```
  True p |       p̂ |    Width_H |    Width_I |   Improv % |   Tighter?
--------------------------------------------------------------------------------
    0.01 |   0.0100 |     0.2641 |     0.2708 |      -2.5% |       ✗ No
    0.02 |   0.0300 |     0.2841 |     0.2908 |      -2.4% |       ✗ No
    0.05 |   0.0300 |     0.2841 |     0.2908 |      -2.4% |       ✗ No
    ... (intersection consistently WIDER)
```

### Stratified Balance (Experiment 3)
```
Naive:       σ² = 18.5 (natural sampling variation)
Stratified:  σ² = 0.0  (perfect balance)

Result: Stratified achieves perfect balance as designed ✅
```

### Unit Tests
```
13 tests in test_intersection_and_stratified.py - ALL PASSING ✅
```

---

## Lessons Learned

1. **Always validate against exact published formulas**
   - Don't rely on intuition or simplified versions
   - Small constant differences can have huge impact (1/3 vs 7/3)

2. **Beware of hash() for reproducibility**
   - Python's hash() is randomized by default
   - Use deterministic seed derivation

3. **Coverage validation is essential**
   - "Tightness" means nothing if coverage is broken
   - Always check empirical coverage before claiming improvements

4. **Test the right thing**
   - We tested Hoeffding baseline but not the intersection logic
   - Need tests for every claimed contribution

5. **Early stopping must actually happen**
   - Can't claim to prevent early-stopping bias without demonstrating it
   - Need experiments that actually stop early to show the effect

---

## Next Steps

1. ✅ **All critical bugs fixed**
2. ✅ **All tests passing**
3. ✅ **Documentation updated**
4. ⏳ **Consider**: Run new Experiment 3 with actual early stopping
   - Lower max_samples (e.g., 200)
   - Realistic precision target (e.g., width ≤ 0.15)
   - Should observe: naive stops at different n than stratified
5. ⏳ **Revise paper**: Focus solely on stratified sequential evaluation
   - Remove intersection bounds as contribution
   - Intersection can stay as implementation choice (valid but not tighter)

---

## Current Status

**Implementation**: ✅ Correct and validated
**Main Contribution**: Stratified sequential evaluation (Claim 3)
**Secondary Contribution**: ~~Intersection bounds~~ (invalidated)
**Test Coverage**: ✅ Comprehensive (13 new tests)
**Reproducibility**: ✅ Fixed (deterministic seeds)
**Documentation**: ✅ Updated to reflect reality

**Ready for**: Continued development, paper revision, or additional validation experiments
