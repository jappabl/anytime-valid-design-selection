# Response to "PARTIALLY CREDIBLE" Verdict

**Date**: 2025-12-29 Evening
**Audit**: Decision Impact Experiment (Experiment B)

---

## Verdict Summary

**Overall Assessment**: PARTIALLY CREDIBLE

The experiment runs and produces documented numbers (49.2% disagreement), but several claims in documentation overreach the evidence. Core findings are numerically correct but require caveats about coupling, heterogeneity significance, and composition drift measurement.

---

## Issues Identified and Fixed

### 1. Composition Drift Overclaim

**Issue**: Documentation claimed "Naive variance ~60×10⁻⁴ vs Stratified 0 (validated)"

**Actual Evidence**:
- Naive: ≈22×10⁻⁴ ± 22 (high het case only)
- Stratified: Not computed empirically, only assumed zero by design

**Fix Applied**:
- Replaced all "~60×10⁻⁴" with "≈22×10⁻⁴"
- Changed "validated" to "pattern observed"
- Added caveat: "stratified drift not computed but expected near zero by design"

**Files Updated**:
- [AUDIT_PREP.md](AUDIT_PREP.md): Lines 550, 559, 568
- [AUDIT_RESPONSE.md](AUDIT_RESPONSE.md): Line 178
- [DECISION_IMPACT_RESULTS.md](DECISION_IMPACT_RESULTS.md): Lines 108-111, 154

---

### 2. RNG Coupling Overclaim

**Issue**: Documentation implied "shared randomness" or "fully coupled" RNGs

**Actual Implementation**:
```python
base = BASE_SEED + model_offset + rep * 1000
seed = base + (0 if method == 'naive' else 1)
```
- Naive and stratified use **different RNG streams** per replication
- Outcome sequences are **independent**, not shared
- Coupling is **partial** (same base seed, different offsets)

**Fix Applied**:
- Replaced "identical budgets" with "same budget constraint (independent RNG streams)"
- Replaced "shared randomness" with "independent RNG streams per method"
- Added explicit note: "RNG coupling: Partial (same base seed per replication, different streams per method)"

**Files Updated**:
- [AUDIT_PREP.md](AUDIT_PREP.md): Lines 14, 555, 566, 569
- [AUDIT_RESPONSE.md](AUDIT_RESPONSE.md): Line 176
- [DECISION_IMPACT_RESULTS.md](DECISION_IMPACT_RESULTS.md): Lines 18, 70, 170

---

### 3. Heterogeneity Effect Overclaim

**Issue**: Documentation stated "High heterogeneity amplifies disagreement" or "confirmed"

**Statistical Test**:
- High: 52.5% (105/200)
- Low: 46.0% (92/200)
- Difference: 6.5 pp (13 disagreements)
- SE ≈ 0.050
- 95% CI: [-0.033, 0.163] → **includes zero**
- **NOT statistically significant** at α=0.05

**Fix Applied**:
- Changed "Heterogeneity Effect" → "Heterogeneity Trend"
- Changed "amplifies" → "shows more disagreement"
- Changed "Confirmed" → "not statistically significant (95% CI includes zero)"
- Added explicit caveat: "(not statistically significant at α=0.05)"

**Files Updated**:
- [AUDIT_PREP.md](AUDIT_PREP.md): Lines 557, 567
- [DECISION_IMPACT_RESULTS.md](DECISION_IMPACT_RESULTS.md): Lines 72, 152

---

## What Remains Verified

### ✅ Core Findings That Stand

1. **49.2% decision disagreement**: Verified for this run (197/400)
   - Evidence: [results_decision_impact.txt](results_decision_impact.txt), script lines 340-420

2. **Equal means enforced**: Both models have p = 0.1375
   - Evidence: Script lines 82-97, mean assertion at lines 100-102

3. **Design improvements implemented**:
   - Plug-in heuristic labeling (not "certification")
   - Adaptive threshold (median of pilot, not arbitrary)
   - Proper seed structure for paired comparison

4. **Reproducible**: With numpy==2.4.0, seed=42, git 0a40e8f4
   - Expected checksum: 1bb74fc56a17e49f

---

## Statistical Validity Summary

### What the Data Support

- **Decision disagreement**: 49.2% ± 2.5% (SE ≈ 0.025)
  - 95% CI: [44%, 54%]
  - Significantly different from 50% (random): p ≈ 0.75 (NOT significant)

- **Heterogeneity difference**: 6.5 pp ± 5.0 pp
  - 95% CI: [-3.3%, 16.3%]
  - NOT significant at α=0.05

- **Composition drift** (naive, high het): 22 ± 22 × 10⁻⁴
  - Stratified: Not computed empirically

### Proper Interpretation

**Claim**: Methods make opposite decisions ~49% of the time under same budget and stopping rule.

**Scope**:
- Synthetic 4-stratum heterogeneity
- Wide precision target (w=0.40)
- Small budget (n≤200)
- Plug-in heuristic (not certification)
- Independent RNG streams per method
- Adaptive threshold tuned to median

**Limitations**:
- Neither method uniformly superior
- Heterogeneity effect not statistically significant
- Composition drift not measured for stratified
- RNG coupling partial, not full
- Results specific to experimental regime

---

## Recommendations for Future Claims

### Safe Claims

✅ "Naive and stratified make opposite decisions 49% of the time (independent RNG streams, same budget)"

✅ "High heterogeneity shows trend toward more disagreement (+6.5 pp), though not statistically significant"

✅ "Naive exhibits composition drift (≈22×10⁻⁴ for high het); stratified expected near zero by design"

### Unsafe Claims (Now Fixed)

❌ ~~"Under identical budgets with shared randomness"~~ → Use specific phrasing above

❌ ~~"Composition drift validated: Naive ~60×10⁻⁴ vs Stratified 0"~~ → Use specific values and caveats

❌ ~~"Heterogeneity amplifies impact (confirmed)"~~ → Use "trend" and note lack of significance

---

## Files Modified

All overclaims corrected in:

1. ✅ [AUDIT_PREP.md](AUDIT_PREP.md)
   - Line 14: Clarified RNG coupling
   - Lines 550-552: Updated drift values
   - Lines 555, 557, 559: Fixed interpretation language
   - Lines 566-570: Updated status with accurate caveats

2. ✅ [AUDIT_RESPONSE.md](AUDIT_RESPONSE.md)
   - Lines 176-178: Fixed all three overclaims

3. ✅ [DECISION_IMPACT_RESULTS.md](DECISION_IMPACT_RESULTS.md)
   - Lines 18, 70, 72: Fixed coupling and heterogeneity language
   - Lines 108-111: Corrected drift values and caveats
   - Lines 152, 154, 170: Updated interpretation sections

4. ✅ [requirements-decision-impact.txt](requirements-decision-impact.txt)
   - Updated to numpy==2.4.0 (working version)
   - Documented reference run with checksum

5. ✅ [REPRODUCIBILITY_FIXES.md](REPRODUCIBILITY_FIXES.md)
   - Updated verification recipe for numpy 2.4.0
   - Added reference checksum

---

## Audit Trail

**Previous State**: Documentation contained three overclaims (composition drift magnitude, RNG coupling, heterogeneity significance)

**Current State**: All claims now match evidence with appropriate qualifiers

**Confidence**: Core finding (49.2% disagreement) is robust; supporting claims (heterogeneity, drift) now accurately scoped

**Readiness**: Documentation audit-safe for claims about decision-level impact in this specific experimental setup

---

## Reproducibility

**To verify these corrections**:

```bash
# 1. Check updated documentation
grep -n "22×10⁻⁴\|independent RNG\|not statistically significant" \
  AUDIT_PREP.md AUDIT_RESPONSE.md DECISION_IMPACT_RESULTS.md

# 2. Reproduce experiment
pip install -r requirements-decision-impact.txt
python3 scripts/validate_decision_impact.py

# 3. Verify checksum matches reference
# Expected: 1bb74fc56a17e49f (with numpy 2.4.0, git 0a40e8f4, seed=42)
```

**Status**: All audit issues addressed. Documentation now accurately represents evidence.
