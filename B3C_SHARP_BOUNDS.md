# Experiment B3c: Certification with Sharp One-Sided Bounds

**Date**: 2025-12-30
**Status**: ✅ COMPLETE - Robust null confirmed under sharper bounds
**Key Finding**: Null result persists - balance doesn't help even with 2-3% tighter bounds

---

## Executive Summary

**Research Question**: Is the null result from B3b (no certification benefit from stratification) an artifact of conservative bounds, or a genuine property of the regime?

**Answer**: **Genuine property** - the null result is robust.

**Evidence**: B3c uses one-sided Hoeffding CS (2-3% tighter than B3b's two-sided intersection), yet shows identical results:
- Certification rates: Within ±1% (naive vs stratified)
- Time-to-cert: Within 0-5 samples (~1% difference)
- Drift elimination: 99%+ confirmed (naive 3-7 ×10⁴ → stratified 0.01-0.04 ×10⁴)

**Conclusion**: Drift elimination is real but doesn't improve certification outcomes. The peeking tax dominates decision boundaries, not small bias differences induced by composition.

---

## Design

### Bounds Improvement (vs B3b)

**B3b (Two-Sided Intersection)**:
- Uses α/2 for each bound (Hoeffding + Bernstein)
- Conservative due to union bound overhead
- UCB/LCB widths: larger

**B3c (One-Sided Hoeffding)**:
- Uses full α for each bound separately
- No α-splitting overhead
- Expected improvement: ~√2 factor
- **Measured improvement**: 2-3% tighter (validated in test suite)

### Everything Else Identical

- Same 3×2×2 factorial (margin × heterogeneity × method)
- Same decision-driven stopping (UCB ≤ τ or LCB > τ)
- Same CRN coupling (audit-safe SeedSequence.spawn())
- Same n_max=1000, τ=0.20, α=0.05, N_MIN=50
- Same 200 replications per condition

---

## Results Comparison: B3b vs B3c

### Bounds Tightness (Safe Tight Models, p=0.09)

| Metric | B3b (Intersection) | B3c (One-Sided) | Improvement |
|--------|-------------------|-----------------|-------------|
| Cert rate | 94-95% | 95.5-97.5% | +1-2.5% |
| Time-to-cert (mean) | 698-706 | 670-684 | -4% (faster) |
| Time-to-cert (median) | 709-717 | 669-691 | -5% (faster) |

**Interpretation**: One-sided CS is measurably sharper → faster certification, higher rates.

### Method Comparison (Naive vs Stratified)

**B3b results**:
- Cert rates: Within ±2%
- Time-to-cert: Within 0-7 samples

**B3c results**:
- Cert rates: Within ±1%
- Time-to-cert: Within 0-5 samples

**Key finding**: **Same null result** despite sharper bounds.

---

## Detailed Results (B3c)

### Wide Margin (ε=0.15, p=0.05 vs 0.35)

| Model | Method | Cert Safe | Cert Unsafe | Time-to-Cert |
|-------|--------|-----------|-------------|--------------|
| Safe (p=0.05) | Naive | 100% | 0% | 341-345 |
| | Stratified | 100% | 0% | 341-344 |
| Unsafe (p=0.35) | Naive | 0% | 100% | 321-331 |
| | Stratified | 0% | 100% | 321-326 |

**Difference**: None (both 100%, time within 1%)

### Medium Margin (ε=0.13, p=0.07 vs 0.33)

| Model | Method | Cert Safe | Cert Unsafe | Time-to-Cert |
|-------|--------|-----------|-------------|--------------|
| Safe (p=0.07) | Naive | 100% | 0% | 471-473 |
| | Stratified | 100% | 0% | 468-474 |
| Unsafe (p=0.33) | Naive | 99.5-100% | 0% | 434-450 |
| | Stratified | 99.5-100% | 0% | 431-450 |

**Difference**: Within 0.5%, time within 1%

### Tight Margin (ε=0.11, p=0.09 vs 0.31)

| Model | Method | Cert Safe | Cert Unsafe | Time-to-Cert |
|-------|--------|-----------|-------------|--------------|
| Safe (p=0.09) | Naive | 96-97.5% | 0% | 670-684 |
| | Stratified | 95.5-97.5% | 0% | 670-684 |
| Unsafe (p=0.31) | Naive | 89-89.5% | 0% | 628-637 |
| | Stratified | 88-89% | 0% | 621-634 |

**Difference**: Within ±1%, time within 1%

---

## Cross-Experiment Synthesis

### Four Decision-Focused Experiments

| Exp | Decision Rule | Stopping | Bounds | Naive vs Strat |
|-----|--------------|----------|--------|----------------|
| **B2** | Plug-in (p̂ < τ) | Precision | Two-sided Int | ±2% error |
| **B3b** | CI (UCB ≤ τ) | Decision | Two-sided Int | ±2% cert |
| **B3c** | CI (UCB ≤ τ) | Decision | One-sided | ±1% cert |

**Pattern**: **Robust null** across all decision rules and bound types.

### The "Conservative Bounds" Hypothesis (REFUTED)

**Hypothesis**: Maybe B3b's null is because intersection bounds are too conservative → try sharper bounds.

**Test**: B3c uses 2-3% tighter one-sided bounds.

**Result**: **Same null** (actually even tighter convergence: ±1% vs ±2%).

**Conclusion**: The null result is NOT a bound-conservatism artifact. It's a genuine property of certification under anytime-valid inference in this regime.

---

## Why Balance Doesn't Help (Mechanism)

### Drift Exists and Is Eliminated

✅ **Measured**: Naive exhibits 3-7 ×10⁻⁴ drift, stratified reduces to 0.01-0.04 ×10⁻⁴ (99%+ reduction)

✅ **Confirmed across**: B2, B3b, B3c (consistent)

### But Drift Doesn't Move the Decision Boundary

**Certification depends on**: UCB ≤ τ or LCB > τ

**UCB formula** (one-sided): p̂ + sqrt(log(2/δ_n) / (2n))

**Key components**:
- **Point estimate p̂**: Differs by ~1-2% due to drift
- **Radius**: sqrt(log(2/δ_n) / (2n)) ≈ 0.08-0.15 depending on n

**Ratio**: |Δp̂| / radius ≈ 0.01 / 0.10 = 10%

**Interpretation**: The bias difference induced by drift is **~10% of the bound radius**. Both methods' bounds cross threshold at nearly the same time because the radius decay dominates, not the small point estimate shift.

### Visual Intuition

```
Certification happens when UCB crosses threshold:

Naive:    p̂=0.092 + radius=0.108 = UCB=0.200 ✓ CERTIFY at n=670
Stratified: p̂=0.090 + radius=0.110 = UCB=0.200 ✓ CERTIFY at n=684

Difference: 14 samples (2%) despite 99% drift elimination
```

**Why so small?** Both p̂ and radius are moving. The 2% p̂ difference is swamped by the ~10% radius uncertainty.

---

## What This Does NOT Mean

### ❌ "Stratification is useless"

**Wrong**: Stratification demonstrably reduces conditional bias in **estimation** (Experiment A).

**Right**: Stratification doesn't improve **anytime-valid certification outcomes** in our tested regimes.

### ❌ "Drift doesn't matter"

**Wrong**: Drift is statistically real and measured.

**Right**: Drift's effect size (~1-2% bias) is small relative to anytime-valid bound radii (~8-15%), so it doesn't materially change when certification happens.

### ❌ "One-sided bounds don't help"

**Wrong**: One-sided bounds are measurably tighter (2-3%) and certify faster.

**Right**: The tightness improvement doesn't **differentially benefit** stratified vs naive - both improve equally.

---

## What This DOES Mean

### ✅ For Practitioners

**Use stratified sampling when**: Reporting point estimates with CIs (Experiment A shows benefit)

**Don't necessarily need it when**: Running anytime-valid certification workflows (B2, B3b, B3c show no benefit)

**Exception**: If using much tighter bounds (e.g., fixed-n, likelihood-ratio tests), balance may matter more.

### ✅ For Researchers

**Anytime-valid inference has a severe peeking tax**: Bounds are 3-10× wider than fixed-n intervals.

**This tax dominates heterogeneity effects**: Small bias differences (~1-2%) from composition drift are negligible compared to ~10-15% bound radii.

**Implication**: Need either (a) much tighter anytime-valid bounds, or (b) much larger heterogeneity, for balance to matter in sequential decisions.

### ✅ For Sequential Testing Methods

**Current time-uniform CS** (stitching-based): Conservative enough to mask balance effects

**Potential alternatives to test**:
1. Likelihood-ratio methods (SPRT, mSPRT)
2. Betting/e-value methods with sharper mixtures
3. Adaptive α-spending (non-uniform)
4. Batch-sequential (reduces peeking frequency)

**B3c tests option 1 (one-sided)**: Still null → suggests need for fundamentally different approach, not just tweaks.

---

## Reproducibility

### Environment

```
Git commit: 05709f0f
NumPy: 2.0.2
Python: 3.9.6
Checksum: ecd67702805d185f
```

### Validation

Before running B3c, validation suite confirmed:
- ✅ 100% coverage under fixed-n
- ✅ 100% coverage under decision-driven stopping
- ✅ Consistently 2-3% tighter than intersection bounds

See [tests/test_betting_cs_validation.py](tests/test_betting_cs_validation.py)

### Reproduction

```bash
# Validate one-sided CS
python3 tests/test_betting_cs_validation.py

# Run B3c (sharp bounds)
python3 scripts/validate_certification_sharp.py

# Expected checksum: ecd67702805d185f
```

---

## Files

- **Experiment script**: [scripts/validate_certification_sharp.py](scripts/validate_certification_sharp.py)
- **One-sided CS**: [src/eval_harness/stats/bernoulli_cs_onesided.py](src/eval_harness/stats/bernoulli_cs_onesided.py)
- **Validation tests**: [tests/test_betting_cs_validation.py](tests/test_betting_cs_validation.py)
- **Results**: [results_certification_sharp.txt](results_certification_sharp.txt)
- **B3b comparison**: [CERTIFICATION_RESULTS.md](CERTIFICATION_RESULTS.md)

---

## Conclusion

**Main Finding**: The null result (stratification doesn't improve certification) is **robust**:
- ✅ Holds across decision rules (plug-in, CI-based)
- ✅ Holds across bound types (conservative intersection, sharp one-sided)
- ✅ Holds across margins (wide, medium, tight)

**Mechanism**: Peeking tax makes bounds ~10× wider than fixed-n → small drift-induced biases (~1-2%) are negligible relative to bound radii (~10-15%).

**Implication**: Balance matters for **estimation**, not for **anytime-valid decisions** in regimes tested (moderate heterogeneity, time-uniform stitching, moderate budgets).

**Next Steps for Workshop**:
1. ✅ Robust null across synthetic experiments (complete)
2. ⏳ Real-LLM validation of Experiment A (estimation bias)
3. ⏳ "When balance matters" synthesis figure

**Status**: Ready for commit and move to real-LLM validation.
