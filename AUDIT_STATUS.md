# Audit Status - Documentation Cleanup Complete

**Date**: 2025-12-28
**Status**: All critical bugs fixed, documentation aligned with corrected code

---

## Summary of Changes

### 1. Documentation Consistency ✅

**Problem**: EXPERIMENTS.md contradicted AUDIT_PREP.md about Claim 2

**Fixed**:
- [EXPERIMENTS.md](EXPERIMENTS.md#experiment-2-intersection-bounds-comparison) - Updated to mark Experiment 2 as DEPRECATED
- [scripts/validate_intersection_tightness.py](scripts/validate_intersection_tightness.py) - Added deprecation warning
- Audit Evidence Summary table updated to show Claim 2 as WITHDRAWN

**Result**: All documentation now consistently reflects that Claim 2 is invalidated

### 2. Corrected Artifacts ✅

**Old (Buggy)**:
- `validate_intersection_tightness.py` - Used buggy Bernstein formula
- Reported "47.9% improvement" for low p
- Stochastic comparison (not reproducible)

**New (Correct)**:
- [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py) - Uses correct Maurer & Pontil formula
- Reports "+2.3% wider at n≤200" (accurate)
- Fully deterministic comparison
- Writes results to [results_bounds_comparison.txt](results_bounds_comparison.txt)

### 3. Known Limitations Documented ✅

Added to [AUDIT_PREP.md](AUDIT_PREP.md#known-limitations-and-future-work):

**Experiment Reproducibility**:
- Current experiment DBs used pre-fix `hash(stratum)` seeding
- Results valid but not reproducible with new deterministic code
- Recommendation: Rerun with corrected implementation

**Early Stopping**:
- Experiments hit budget cap, didn't actually stop early
- Balance mechanism proven ✅
- Bias outcome not empirically demonstrated
- Recommendation: Design experiment with lower max_samples

---

## Claim-by-Claim Status

### Claim 1: Intersection Maintains Coverage ✅

**Status**: VALIDATED

**Evidence**:
- [scripts/validate_coverage.py](scripts/validate_coverage.py) - 200/200 coverage with Wilson CIs
- [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) - α-splitting tests (lines 28-42)
- [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) - Intersection mechanics tests (lines 44-94)

**Remaining Gaps**:
- Validation checks final n only (not supremum over all n)
- Could add time-series coverage validation

**Severity**: Low - coverage at final n implies coverage at all n for valid CS

### Claim 2: Intersection Provides Tighter Bounds ❌

**Status**: WITHDRAWN

**Evidence**:
- [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py) - Deterministic comparison
- [results_bounds_comparison.txt](results_bounds_comparison.txt) - Audit trail showing +2.3% wider

**Documentation**:
- [AUDIT_PREP.md](AUDIT_PREP.md#claim-2-intersection-provides-tighter-bounds) - Claim explicitly withdrawn
- [EXPERIMENTS.md](EXPERIMENTS.md#experiment-2-intersection-bounds-comparison) - Marked as DEPRECATED
- [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md#9-performance-comparison) - Regime analysis

**Severity**: N/A - claim withdrawn, no further work needed

### Claim 3: Stratified Prevents Composition Drift ✅

**Status**: VALIDATED (mechanism)

**Evidence**:
- [tests/test_intersection_and_stratified.py](tests/test_intersection_and_stratified.py) - Balance tests (lines 169-235)
- [EXPERIMENTS.md](EXPERIMENTS.md#stratum-balance-validation) - Empirical σ²=0 demonstrated
- [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py) - Deterministic seeds (lines 22-27)

**Remaining Gaps**:
1. **Experiment databases from pre-fix code**
   - Used `hash(stratum)` (nondeterministic)
   - Results valid but not reproducible with new code
   - Fix: Rerun experiments with current implementation

2. **Early stopping not demonstrated**
   - Both experiments hit max_samples=1000
   - Balance proven, bias prevention not empirically shown
   - Fix: Design experiment with realistic stopping (e.g., max=200, width≤0.15)

**Severity**: Medium - mechanism validated, outcome demonstration desirable but not critical

---

## Reproducibility Status

### Fully Reproducible ✅

1. **Coverage validation**: `python3 scripts/validate_coverage.py`
   - Seed: 42 + replication_id
   - Output: Deterministic with Wilson CIs

2. **Bounds comparison**: `python3 scripts/comprehensive_bounds_comparison.py`
   - Failures: round(p_true * n) (no randomness)
   - Output: Deterministic, written to file

3. **Unit tests**: `python3 tests/test_intersection_and_stratified.py`
   - All 13 tests deterministic
   - STRATUM_SEED_OFFSETS ensure reproducibility

### Partially Reproducible ⚠️

4. **Stratified experiments**: `python3 run_stratified_experiments.py`
   - Current DBs: Generated with pre-fix code (hash-based seeds)
   - With new code: Will produce different prompts (but same balance properties)
   - To match current results: Use old code
   - To verify new code: Rerun and update EXPERIMENTS.md

---

## Next Steps (Optional)

### High Priority (For Full Reproducibility)

1. **Rerun stratified experiments with corrected code**
   ```bash
   # Delete old results
   rm -rf experiments/results/stratified_gpt4mini_*

   # Rerun with new deterministic seeds
   python3 run_stratified_experiments.py

   # Update EXPERIMENTS.md with new results
   python3 analyze_stratified_results.py
   ```

   **Expected**: Same balance (σ²=0), same heterogeneity, but different exact prompts

### Medium Priority (For Stronger Evidence)

2. **Design early-stopping experiment**

   Create new configs with:
   - `max_samples: 200` (instead of 1000)
   - `precision_target: 0.15` (achievable with ~150 samples)
   - `min_samples: 50`

   **Expected**: Naive and stratified stop at different n, demonstrating bias in practice

### Low Priority (For Completeness)

3. **Time-series coverage validation**

   Modify `validate_coverage.py` to check coverage at multiple n, not just final

   **Expected**: Coverage ≥ 95% at all checkpoints (confirms time-uniform property)

---

## Files Modified (2025-12-28)

### Core Implementation (Bug Fixes)
1. `src/eval_harness/stats/bernoulli_cs_intersection.py` - Fixed Bernstein constant
2. `src/eval_harness/prompts/stratified_json_prompts.py` - Fixed hash nondeterminism

### Tests (Added)
3. `tests/test_intersection_and_stratified.py` - 13 comprehensive unit tests

### Validation Scripts (Corrected)
4. `scripts/validate_coverage.py` - Added Wilson CIs
5. `scripts/comprehensive_bounds_comparison.py` - Made deterministic, writes to file
6. `scripts/validate_intersection_tightness.py` - Deprecated with warning

### Documentation (Updated)
7. `AUDIT_PREP.md` - Complete rewrite with all fixes, withdrawn claims, limitations
8. `EXPERIMENTS.md` - Updated Experiment 2 to DEPRECATED, aligned with AUDIT_PREP.md
9. `TECHNICAL_SPEC.md` - Created complete mathematical specification
10. `AUDIT_FIXES_SUMMARY.md` - Summary of all changes
11. `AUDIT_STATUS.md` - This file (current status)

### Generated Artifacts
12. `results_bounds_comparison.txt` - Deterministic bounds comparison results

---

## Auditor Checklist

- [x] All critical bugs fixed and validated
- [x] Documentation internally consistent
- [x] Claim 2 explicitly withdrawn in all docs
- [x] Test coverage comprehensive (13 new tests)
- [x] Reproducibility protocol documented
- [x] Known limitations acknowledged
- [x] All artifacts deterministic and falsifiable
- [ ] Experiments rerun with corrected code (optional, recommended)
- [ ] Early stopping demonstrated empirically (optional, desirable)

---

## Summary

**Implementation**: ✅ Correct and validated
**Main Contribution**: Stratified sequential evaluation (Claim 3) - mechanism proven
**Secondary Contribution**: ~~Intersection bounds~~ (withdrawn)
**Documentation**: ✅ Consistent across all files
**Reproducibility**: ✅ Core validation scripts, ⚠️ Experiment DBs from pre-fix code
**Test Coverage**: ✅ Comprehensive (13 new tests, all passing)

**Confidence Levels**:
- Implementation correctness: **HIGH** (all tests pass, correct formulas)
- Stratified balance: **HIGH** (σ²=0 proven algorithmically and empirically)
- Documentation accuracy: **HIGH** (all contradictions resolved)
- Experiment reproducibility with new code: **MEDIUM** (requires rerun)
- Practical bias prevention: **MEDIUM** (mechanism proven, outcome not demonstrated)

**Recommendation**: Current state is audit-ready. Optional rerun of experiments would strengthen reproducibility claims but is not critical for validating the core contribution.
