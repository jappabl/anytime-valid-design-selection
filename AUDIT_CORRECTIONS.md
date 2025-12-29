# Audit Corrections - 2025-12-28

**Summary**: This document tracks corrections made in response to adversarial audit findings.

---

## Critical Corrections Made

### 1. **Removed False "Unbiasedness" Claims**

**Issue**: Claimed "E[p̂_τ | stopped] = p for stratified" when empirical data shows stratified bias ≠ 0.

**Evidence**: Stratified bias ranges from -0.0057 to -0.0106 (SE: 0.0019-0.0027), statistically distinguishable from zero.

**Correction**:
- **Before**: "Stratified: E[p̂_τ | stopped] = p (balance prevents bias)"
- **After**: "Stratified: E[p̂_τ | stopped] ≠ p (residual selection bias remains); ~50% less bias than naive"

**Files modified**:
- `scripts/validate_precision_stopping_bias.py` lines 102-105
- `AUDIT_PREP.md` lines 46-52, 215-216, 477-478

---

### 2. **Fixed Backwards Mechanism Explanation**

**Issue**: Claimed "tighter precision → larger composition drift → larger bias" when data shows OPPOSITE pattern.

**Evidence**:
- w=0.45 (early stop, n≈56): σ²=10.2, bias_diff=0.0117
- w=0.35 (late stop, n≈140): σ²=26.3, bias_diff=0.0066

Pattern: Earlier stopping → LESS drift, but LARGER bias.

**Correction**:
- **Before**: "Tighter precision requires earlier stopping → larger composition drift → larger bias"
- **After**: "Tighter precision applies stronger selection filter; bias arises from filter strength, with drift as secondary amplifier"

**Files modified**:
- `AUDIT_PREP.md` lines 480-492

---

### 3. **Reported Full Range, Not Just Maximum**

**Issue**: Headline claimed "1.17% bias" without noting this is maximum from 4-target sweep.

**Correction**:
- **Before**: "Harm quantified (1.17% bias difference at w=0.45)"
- **After**: "Bias reduction: 0.66%-1.17% across w∈{0.35,0.45}"

**Files modified**:
- `AUDIT_PREP.md` lines 62-64, 459-475

---

### 4. **Added Bonferroni-Corrected Significance Reporting**

**Issue**: Reported p<0.05 for all targets without multiple-testing correction.

**Truth**: Only w∈{0.40,0.45} survive Bonferroni (p<0.0125).

**Correction**: Added full table with both uncorrected and Bonferroni columns.

**Files modified**:
- `AUDIT_PREP.md` lines 466-471
- `scripts/validate_precision_stopping_bias.py` lines 480-508

---

### 5. **Removed Arbitrary 0.01 "Validation" Threshold**

**Issue**: Code used post-hoc 0.01 cutoff to label results "validated" vs "inconclusive".

**Correction**: Removed threshold logic; replaced with statistical significance reporting (uncorrected + Bonferroni).

**Files modified**:
- `scripts/validate_precision_stopping_bias.py` lines 480-508 (complete rewrite of conclusion section)

---

### 6. **Downgraded Confidence Level Statement**

**Issue**: Claimed "HIGH" impact based on single maximum value.

**Correction**:
- **Before**: "Practical impact of bias: HIGH (1.17% bias at w=0.45, p<0.01)"
- **After**: "Bias reduction effect: MODERATE-HIGH (0.66%-1.17%; p<0.0125 for 2/4 targets under Bonferroni; ≈5%-8.5% relative to base rate)"

**Files modified**:
- `AUDIT_PREP.md` line 420

---

### 7. **Acknowledged Both Methods Are Biased**

**Issue**: Interpretation implied only naive was biased.

**Correction**: Explicitly stated both methods exhibit conditional bias; stratified reduces it by ~50%.

**Files modified**:
- `AUDIT_PREP.md` lines 477-478
- `scripts/validate_precision_stopping_bias.py` lines 500-508

---

### 8. **Added Mechanism Isolation as Future Work**

**Issue**: Causal link between composition drift and bias not cleanly isolated (could be driven by stopping-time differences).

**Correction**: Added Future Work section proposing controlled ablation with matched stopping times.

**Files modified**:
- `AUDIT_PREP.md` lines 500-510

---

## What Remains Valid

✓ Stratified maintains perfect balance (σ² ≈ 0)
✓ Naive exhibits 48%-52% more conditional bias than stratified
✓ Difference is statistically significant (p<0.05 all targets; p<0.0125 for 2/4 under Bonferroni)
✓ Both methods maintain valid coverage (100% empirical, reflects conservative bounds)
✓ Time-uniform bounds impose width floor ~0.35-0.40 at n=200

---

## What Cannot Be Claimed

✗ "Stratified yields unbiased estimates at stopping" (FALSE: both are biased)
✗ "Composition drift increases with tighter stopping" (FALSE: pattern is reversed)
✗ "1.17% bias" without context (INCOMPLETE: ranges 0.66%-1.17%)
✗ "HIGH impact" (SUBJECTIVE: 0.66%-1.17% on 13.75% base = moderate effect size)
✗ "Validated" based on 0.01 threshold (ARBITRARY: post-hoc cutoff)

---

## Audit-Safe Summary Statement

**Core contribution**:
Stratified sequential evaluation reduces conditional bias under precision stopping by approximately 50% (from 1.23%-2.23% to 0.57%-1.06% across tested precision targets) by maintaining compositional balance and eliminating the composition-drift component of selection bias. Residual selection bias from the precision-stopping mechanism itself remains in both methods. Effect is statistically significant (p<0.05 uncorrected for all targets; p<0.0125 for aggressive targets w∈{0.40,0.45} under Bonferroni correction). Magnitude represents 5%-8.5% relative error on base rate p=0.1375 under extreme synthetic heterogeneity (p∈{0.00,0.40}).

---

## Final Round: Causal Language Corrections (2025-12-28)

**Issue**: Despite acknowledging mechanism not isolated in Future Work, several locations still used causal language ("through elimination," "by eliminating") that contradicts our stated limitations.

**Correction**: Replaced all causal verbs with associative language throughout:

**Changes made**:
- `AUDIT_PREP.md` line 11: "by eliminating" → "associated with elimination of" + explicit caveat
- `AUDIT_PREP.md` line 215: "eliminates component" → "zero composition variance at all n" + caveat
- `AUDIT_PREP.md` line 478: "through elimination" → "associated with elimination" + reference to Future Work
- `AUDIT_PREP.md` lines 495-498: Separated "balance mechanism" from "causal pathway" in status summary
- `validate_precision_stopping_bias.py` line 105: "by eliminating" → "associated with zero"
- `validate_precision_stopping_bias.py` lines 503-505: "through elimination" → "associated with" + explicit caveat

**Rationale**: We observe (1) stratified maintains zero composition drift, and (2) stratified exhibits ~50% less bias. These are associated, but causal attribution requires the ablation study proposed in Future Work to rule out confounds from later stopping times.

---

**Files Modified (Complete List)**:
1. `scripts/validate_precision_stopping_bias.py` - estimand statement (line 105) + conclusion logic (lines 477-508)
2. `AUDIT_PREP.md` - executive summary (line 11), stratified explanation (lines 164-216), key results interpretation (line 478), status section (lines 495-498)
3. `AUDIT_CORRECTIONS.md` - this file (new)

**Reproducibility**: All changes are deterministic; re-running experiments will produce identical numeric results with corrected interpretations.
