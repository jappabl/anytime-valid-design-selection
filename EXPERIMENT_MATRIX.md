# Complete Experiment Matrix: When Does Balance Matter?

**Date**: 2025-12-30
**Status**: All experiments complete and audit-safe

---

## One-Page Summary

| Exp | Objective | Decision Rule | Stopping | Bounds | Balance Helps? | Effect Size |
|-----|-----------|--------------|----------|--------|----------------|-------------|
| **A** | Estimate p̂ | None (pure estimation) | Precision | N/A | ✅ **YES** | ~50% bias reduction |
| **B2** | Accept/Reject | Plug-in: p̂ < τ | Precision | Two-sided Int | ❌ **NO** | ±2% error (noise) |
| **B3b** | Certify Safe/Unsafe | CI: UCB ≤ τ | Decision | Two-sided Int | ❌ **NO** | ±2% cert (noise) |
| **B3c** | Certify Safe/Unsafe | CI: UCB ≤ τ | Decision | One-sided | ❌ **NO** | ±1% cert (noise) |

**Pattern**: Balance helps **estimation**, not **decisions** under anytime-valid bounds.

---

## Key Findings by Experiment

### Experiment A: Conditional Bias in Estimation

**Setup**: Precision stopping (width ≤ target), report p̂
**Metrics**: Conditional bias E[p̂ - p | stopped]
**Result**: ✅ Stratified reduces bias by ~50%
**Status**: Positive result, mechanism validated

### Experiment B2: Plug-in Decisions

**Setup**: Precision stopping, threshold τ=0.13, decide via p̂ < τ
**Metrics**: False accept/reject rates
**Result**: ❌ No difference (±2%), drift eliminated but no decision improvement
**Status**: ✅ AUDIT-SAFE (checksum 9c946ec526c3bd24)

### Experiment B3b: CI-Based Certification (Conservative Bounds)

**Setup**: Decision stopping (UCB ≤ τ), two-sided intersection CS
**Metrics**: Certification rates, time-to-cert
**Result**: ❌ No difference (±2% cert, ±0-7 samples time)
**Status**: ✅ AUDIT-SAFE (checksum ea8bdd08015bf999)

### Experiment B3c: CI-Based Certification (Sharp Bounds)

**Setup**: Same as B3b, but one-sided CS (2-3% tighter)
**Metrics**: Same as B3b
**Result**: ❌ **Robust null** (±1% cert, ±0-5 samples time)
**Status**: ✅ COMPLETE (checksum ecd67702805d185f)

**Critical insight**: Null persists under sharper bounds → not a conservatism artifact.

---

## Cross-Experiment Patterns

### Drift Elimination: Confirmed Across All

| Experiment | Naive Drift (×10⁴) | Stratified Drift (×10⁴) | Reduction |
|------------|-------------------|------------------------|-----------|
| B2 | 17-26 | 0.1-0.3 | 99% |
| B3b | 3-6 | 0.01-0.03 | 99% |
| B3c | 3-7 | 0.01-0.04 | 99% |

**Conclusion**: The mechanism works (perfect balance at all n).

### Decision Benefit: Null Across All

| Experiment | Metric | Naive | Stratified | Difference |
|------------|--------|-------|------------|------------|
| B2 | Total error | 23-40% | 21-40% | ±2% |
| B3b | Cert rate (tight) | 87-95% | 85-96% | ±2% |
| B3c | Cert rate (tight) | 89-97.5% | 88-97.5% | ±1% |

**Conclusion**: Robust null across decision rules and bound types.

---

## Why the Disconnect?

**Balance eliminates drift** (99% confirmed)
**↓**
**Drift induces small bias** (~1-2% in p̂)
**↓**
**But anytime-valid bounds have large radii** (~10-15% due to peeking tax)
**↓**
**Decision boundaries dominated by radius**, not bias
**↓**
**No practical decision benefit** from eliminating drift

### Visual

```
Fixed-n bound:        p̂ ± 0.04   → Bias matters
Time-uniform bound:   p̂ ± 0.12   → Bias swamped by radius
```

**Ratio**: |bias difference| / radius ≈ 0.01 / 0.12 = 8%

---

## Robustness Checks

### B3b → B3c: Sharper Bounds

**Question**: Is null due to conservative bounds?
**Test**: Use one-sided CS (2-3% tighter)
**Result**: ❌ Null persists (even tighter: ±1% vs ±2%)
**Conclusion**: Not a bound artifact

### Across Margins (ε = 0.11, 0.13, 0.15)

**Question**: Is null specific to margin size?
**Test**: Three margins (tight/medium/wide)
**Result**: ❌ Null across all margins
**Conclusion**: Robust to margin position

### Across Heterogeneity (High vs Low)

**Question**: Is null due to insufficient heterogeneity?
**Test**: Two levels (high: 0.05 spread, low: 0.02 spread)
**Result**: ❌ Null for both
**Conclusion**: Robust to heterogeneity level (within tested range)

---

## Scientific Claims (Audit-Safe)

### ✅ Can Claim

1. **Drift is real and measurable**: 17-26 ×10⁻⁴ for naive vs 0.01-0.3 ×10⁻⁴ for stratified
2. **Stratified eliminates drift**: 99% reduction across all experiments
3. **Balance helps estimation**: ~50% conditional bias reduction under precision stopping
4. **Balance doesn't help decisions**: ±1-2% differences (within noise) across B2/B3b/B3c
5. **Robust across bounds**: Null holds for conservative (intersection) and sharp (one-sided)
6. **Mechanism explanation**: Peeking tax dominates small bias differences

### ❌ Cannot Claim

1. **"Balance never matters for decisions"**: Only tested moderate heterogeneity, time-uniform stitching
2. **"One-sided bounds are always better"**: Only 2-3% improvement in our regime
3. **"Drift has no effect"**: It has measurable statistical effect, just not decision-relevant magnitude

---

## Scope and Limitations

### What Results Apply To

✅ Synthetic Bernoulli models with known heterogeneity
✅ Moderate heterogeneity (4 strata, p ∈ {0.05, 0.35})
✅ Time-uniform stitching-based CS
✅ Moderate budgets (n ≤ 1000)
✅ Anytime-valid inference

### What Results Do NOT Apply To

❌ Real LLM evaluation (needs validation)
❌ Extreme heterogeneity (10+ strata, 0.01-0.90 range)
❌ Fixed-n analysis (no peeking tax)
❌ Likelihood-ratio methods (SPRT, mSPRT)
❌ Large-scale evaluation (n > 10,000)

---

## Next Steps for Workshop Submission

### Completed ✅

1. Experiment A: Estimation bias reduction (positive result)
2. Experiment B2: Plug-in decisions (null)
3. Experiment B3b: CI certification with conservative bounds (null)
4. Experiment B3c: CI certification with sharp bounds (robust null)
5. Full audit-safe RNG coupling (SeedSequence.spawn())
6. Comprehensive documentation

### Required for Acceptance ⏳

1. **Real-LLM validation**: Replicate Experiment A on actual model/task
   - Show heterogeneity exists
   - Show naive exhibits bias
   - Show stratified reduces it (even if smaller effect)
   - Minimum: 20-30 reps, temperature=0, JSON schema task

2. **"When Balance Matters" figure**: Two-row visual summary
   - Row 1: Estimation → stratified helps
   - Row 2: Decisions → stratified doesn't help

### Optional (Nice to Have)

3. Phase diagram: Sweep heterogeneity strength × budget × CS type
4. Real-LLM decision experiment (lower priority if #1 done)

---

## Files

### Experiment Scripts
- [scripts/validate_decision_error.py](scripts/validate_decision_error.py) - B2
- [scripts/validate_certification.py](scripts/validate_certification.py) - B3b
- [scripts/validate_certification_sharp.py](scripts/validate_certification_sharp.py) - B3c

### Statistical Implementations
- [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py) - Two-sided
- [src/eval_harness/stats/bernoulli_cs_onesided.py](src/eval_harness/stats/bernoulli_cs_onesided.py) - One-sided

### Documentation
- [DECISION_ERROR_RESULTS.md](DECISION_ERROR_RESULTS.md) - B2 full doc
- [CERTIFICATION_RESULTS.md](CERTIFICATION_RESULTS.md) - B3b full doc
- [B3C_SHARP_BOUNDS.md](B3C_SHARP_BOUNDS.md) - B3c full doc
- [BALANCE_SYNTHESIS.md](BALANCE_SYNTHESIS.md) - Three-experiment synthesis
- [RNG_AUDIT_FIXES.md](RNG_AUDIT_FIXES.md) - Audit response

### Results
- [results_decision_error.txt](results_decision_error.txt) - B2 (checksum 9c946ec526c3bd24)
- [results_certification.txt](results_certification.txt) - B3b (checksum ea8bdd08015bf999)
- [results_certification_sharp.txt](results_certification_sharp.txt) - B3c (checksum ecd67702805d185f)

---

## Checksums for Reproducibility

| Experiment | Git Commit | NumPy | Checksum |
|------------|-----------|-------|----------|
| B2 | a6969c85 | 2.0.2 | 9c946ec526c3bd24 |
| B3b | 2c323817 | 2.0.2 | ea8bdd08015bf999 |
| B3c | 05709f0f | 2.0.2 | ecd67702805d185f |
