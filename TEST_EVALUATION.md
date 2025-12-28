# Test Effectiveness Evaluation

## Summary

**Current state**: Tests violate CLAUDE.md rules extensively. Most are demonstration scripts disguised as tests, not actual regression tests.

**Recommendation**: Delete 5/7 test files. Keep only 2 that test actual invariants.

---

## Test-by-Test Analysis

### ❌ FAIL: `test_intersection_coverage.py`

**Violations**:
- NOT a pytest test (manual script execution)
- Extensive print statements throughout (lines 12-250)
- Tests "improvements" and "performance" (line 96, 168-171, 174-177)
- Hard-coded numeric expectations (line 78: `coverage >= expected - 0.02`)
- Demonstration/banner output (lines 84-90, 123-127, 242-249)

**What it claims to test**: Coverage validation via Monte Carlo

**What it actually is**: Exploratory analysis script with demonstration output

**Should be**: Deleted. If coverage validation is needed, write proper pytest that:
- Uses `@pytest.mark.parametrize` for different p values
- Has ZERO print statements
- Tests only the invariant: `coverage >= 1 - alpha - tolerance`
- No banners, no "observations", no explanations

---

### ❌ FAIL: `test_intersection_integration.py`

**Violations**:
- NOT a pytest test (manual script execution with `if __name__`)
- Excessive print statements (lines 12-56, 61-106, 111-157, 165-175)
- Tests "improvements" (line 96, 98, 102)
- Banners and conclusions (lines 165-175)
- Commentary output (lines 169-174)

**What it claims to test**: Interface compatibility

**What it actually is**: Interactive demonstration script

**Should be**: Delete the prints, convert to actual pytest, or delete entirely. Tests like "assert cs.trials == 0" are trivial and don't catch real bugs.

---

### ❌ FAIL: `test_stratified_sampling.py`

**Violations**:
- NOT a pytest test (manual script execution)
- Print statements throughout (lines 18-40, 46-72, 76-104, 108-156, 159-170)
- Tests probabilistic properties ("approximately", line 44)
- Banners and explanations (lines 18-21, 159-170)
- Outputs "Expected: ~25%" (lines 70, 102) - heuristic, not invariant

**What it claims to test**: Stratified sampling

**What it actually is**: Demonstration script showing sampling works

**Should be**: Deleted. If testing is needed:
- Test ONLY: "stratified sampler produces exactly n/k samples per stratum"
- Test ONLY: "naive sampler produces ≥1 sample per stratum after n samples"
- No variance calculations, no "approximately" assertions

---

### ⚠️ BORDERLINE: `tests/test_stopping.py`

**Violations**:
- None! Actually a proper pytest test

**Strengths**:
- Silent execution (no prints)
- Tests invariants only (stopping criteria logic)
- Deterministic outcomes
- Proper pytest structure

**Weaknesses**:
- Line 28-31: Conditional assertion based on observed width
  - Should be: Always test the logic, not the outcome
  - Better: Mock the CS to return specific width, then test stopper decision

**Verdict**: KEEP but needs minor fix. Remove conditional assertions.

---

### ⚠️ BORDERLINE: `tests/test_toy_model.py`

**Violations**:
- Tests coverage with tolerance (lines 38-41, 69-76)
- Hard-coded slack values (line 71: `slack = 0.15 if...`)
- Tests convergence with tolerance (line 114: `abs(...) < 0.03`)

**Strengths**:
- Actual pytest tests
- Silent execution
- Tests important invariants

**Weaknesses**:
- Probabilistic tests with arbitrary tolerances
- Will flake occasionally (probabilistic nature)
- Doesn't test deterministic properties

**Verdict**: KEEP but acknowledge it's probabilistic. Better approach would be:
- Test ONLY deterministic invariants: `0 <= lower <= upper <= 1`
- Test ONLY: `width decreases monotonically`
- Delete coverage tests (move to dedicated validation script if needed)

---

### ✅ PASS: `tests/test_validators.py`

**Violations**: None

**Strengths**:
- Proper pytest structure
- Silent execution
- Tests deterministic validation logic
- No hard-coded numeric expectations
- Tests edge cases properly

**Verdict**: KEEP. This is what all tests should look like.

---

### ❌ FAIL: `tests/test_statistical_validation.py`

**Violations**:
- Extensive print statements (lines 42-91, throughout)
- Tests probabilistic properties with arbitrary thresholds (line 100: `>= 18`)
- Runs full experiments in tests (lines 48-93)
- 412 lines of integration testing disguised as unit tests
- Banner output (lines 42-45)

**What it claims to test**: Statistical validity via full experiments

**What it actually is**: Expensive integration test script

**Problems**:
- Too slow for regular test suite
- Probabilistic (will occasionally fail randomly)
- Tests implementation, not interface
- Belongs in `scripts/validate_coverage.py`, not `tests/`

**Should be**: Deleted from `tests/`. If validation is needed, move to `scripts/` as a separate validation script.

---

## Recommended Actions

### DELETE (5 files):
1. `test_intersection_coverage.py` - Demonstration script
2. `test_intersection_integration.py` - Demonstration script
3. `test_stratified_sampling.py` - Demonstration script
4. `tests/test_statistical_validation.py` - Belongs in scripts/, not tests/

### KEEP (2 files):
1. `tests/test_validators.py` - Proper unit tests ✅
2. `tests/test_toy_model.py` - Acceptable with caveats ⚠️

### FIX (1 file):
1. `tests/test_stopping.py` - Remove conditional assertions

---

## What Good Tests Look Like

From `tests/test_validators.py` (the only good test file):

```python
def test_pass_validation(self):
    validator = ToyValidator()
    result = validator.validate("PASS", "sample_1")

    assert result.passed
    assert not result.failed
    assert result.failure_mode is None
```

**Properties**:
- ✅ Silent (no prints)
- ✅ Deterministic
- ✅ Tests interface contract
- ✅ Fast
- ✅ Will only fail on real regression

**Contrast with `test_intersection_coverage.py`**:

```python
print("="*70)
print("COVERAGE VALIDATION: Intersection with α-Splitting")
print("="*70)
...
if eps_correct < hoeff_eps:
    improvement = (1 - eps_correct/hoeff_eps) * 100
    print(f"  ✓ BETTER! Improvement: {improvement:.1f}% narrower")
```

This is a demonstration script, not a test.

---

## Impact on Development

**Current state**:
- Running `pytest` executes slow, probabilistic, chatty "tests"
- No confidence that tests catch real regressions
- Tests fail randomly due to Monte Carlo noise
- Test suite takes too long

**After cleanup**:
- `pytest tests/` runs in <1 second
- Tests only fail on real bugs
- Clear signal when something breaks
- Developers can trust the test suite

---

## Conclusion

**5/7 test files are scripts, not tests**. They violate every rule in CLAUDE.md:
- Print output during execution
- Test performance/improvements (not guaranteed properties)
- Hard-code arbitrary numeric thresholds
- Require manual inspection of output

**Only `test_validators.py` is a proper test.**

Delete the bad tests. If statistical validation is needed, create `scripts/validate_statistical_properties.py` for that purpose.
