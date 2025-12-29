# Technical Specification - Confidence Sequence Implementation

**Date**: 2025-12-28
**Purpose**: Audit-grade specification of implemented confidence sequences

---

## 1. Time-Uniform Stitching

**Schedule**: Robbins (1970) stitching
```
δ_n = α / (n * (n + 1))
```

**Property**: Σ_{n=1}^∞ δ_n = α (exact)

**Reference**: Robbins, H. (1970). Statistical methods related to the law of the iterated logarithm. Ann. Math. Statist.

---

## 2. Two-Sided Hoeffding

**Inequality**: Hoeffding's inequality for bounded random variables

**Implementation**:
```python
delta_n = alpha / (n * (n + 1))
log_term = log(2.0 / delta_n)  # Factor of 2 for two tails
epsilon = sqrt(log_term / (2 * n))
CI = [max(0, p_hat - epsilon), min(1, p_hat + epsilon)]
```

**Guarantee**: P(p ∈ CI_n for all n ≤ n_max) ≥ 1 - α

**File**: [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L130-L152)

---

## 3. One-Sided Hoeffding Upper Bound

**Implementation**:
```python
delta_n = alpha / (n * (n + 1))
log_term = log(1.0 / delta_n)  # Note: 1/δ not 2/δ (single tail)
epsilon = sqrt(log_term / (2 * n))
upper = min(1, p_hat + epsilon)
```

**Guarantee**: P(p ≤ upper_n for all n ≤ n_max) ≥ 1 - α

**File**: [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L154-L175)

**Note**: log(1/δ) vs log(2/δ) difference accounts for ~2% tighter bound

---

## 4. Two-Sided Empirical Bernstein

**Inequality**: Maurer & Pontil (2009) empirical Bernstein inequality for bounded random variables

**Reference**: Maurer, A., & Pontil, M. (2009). Empirical Bernstein bounds and sample variance penalization. COLT.

**Implementation**:
```python
delta_n = alpha / (n * (n + 1))
log_term = log(2.0 / delta_n)

# Empirical variance
var_hat = p_hat * (1 - p_hat)

# Two terms per Maurer & Pontil Theorem 6
var_term = sqrt(2 * var_hat * log_term / n)
range_term = (7/3) * log_term / (n - 1)  # if n > 1

epsilon = var_term + range_term
CI = [max(0, p_hat - epsilon), min(1, p_hat + epsilon)]
```

**Guarantee**: P(p ∈ CI_n for all n ≤ n_max) ≥ 1 - α

**Constants**:
- Variance term coefficient: 2 (from concentration inequality)
- Range term coefficient: 7/3 (from Maurer & Pontil Theorem 6)
- Range term denominator: (n - 1) (from Theorem 6)

**Edge case**: At n=1, use range_term = log_term (avoid division by zero)

**File**: [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L177-L208)

---

## 5. One-Sided Empirical Bernstein Upper Bound

**Implementation**:
```python
delta_n = alpha / (n * (n + 1))
log_term = log(1.0 / delta_n)  # One-sided: 1/δ not 2/δ

var_hat = p_hat * (1 - p_hat)
var_term = sqrt(2 * var_hat * log_term / n)
range_term = (7/3) * log_term / (n - 1)  # if n > 1

epsilon = var_term + range_term
upper = min(1, p_hat + epsilon)
```

**Guarantee**: P(p ≤ upper_n for all n ≤ n_max) ≥ 1 - α

**File**: [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L210-L235)

---

## 6. Intersection with α-Splitting

**Method**: Bonferroni union bound

**Implementation**:
```python
# Split α across components (NOT across tails)
alpha_hoeffding = alpha / 2
alpha_bernstein = alpha / 2

# Compute both bounds independently
CI_h = hoeffding_two_sided(alpha_hoeffding)
CI_b = bernstein_two_sided(alpha_bernstein)

# Intersection (tightest valid bound)
lower = max(CI_h[0], CI_b[0])
upper = min(CI_h[1], CI_b[1])
```

**Guarantee**: P(p ∈ [lower, upper]_n for all n ≤ n_max) ≥ 1 - α

**Derivation**:
```
P(p ∉ CI_h ∪ p ∉ CI_b) ≤ P(p ∉ CI_h) + P(p ∉ CI_b)  [union bound]
                        ≤ α/2 + α/2 = α

Therefore: P(p ∈ CI_h ∩ CI_b) ≥ 1 - α
```

**File**: [src/eval_harness/stats/bernoulli_cs_intersection.py](src/eval_harness/stats/bernoulli_cs_intersection.py#L87-L107)

**Critical property**: NO data-dependent switching - intersection is geometric, not conditional

---

## 7. α-Splitting Overhead Analysis

**Question**: How much does α-splitting inflate Hoeffding?

**Answer**: It's an additive increase in log space, not multiplicative √2.

**Derivation**:
```
Hoeffding(α):   epsilon = sqrt(log(2/δ_α) / (2n))
Hoeffding(α/2): epsilon = sqrt(log(2/δ_α/2) / (2n))

Ratio = sqrt(log(2/δ_α/2) / log(2/δ_α))
      = sqrt((log(2/δ_α) + log(2)) / log(2/δ_α))
      = sqrt(1 + log(2) / log(2/δ_α))
```

**With stitching**: δ_n = α/(n(n+1)), so log(2/δ_n) ≈ 10-15 for n=50-200

**Numerical effect**:
```
log(2) = 0.693
log(2/δ_n) ≈ 12 (at n=100, α=0.05)

Ratio = sqrt(1 + 0.693/12) = sqrt(1.058) ≈ 1.028

This is a ~2.8% increase, NOT ~41% (which √2 would give)
```

**Conclusion**: α-splitting adds 2-3% overhead, consistent with empirical observations

---

## 8. Coverage Validation Protocol

**Method**: Monte Carlo simulation

**Parameters**:
- Replications per (p, n) condition: 200
- Sample size: n = 100
- Significance level: α = 0.05
- True p values tested: {0.01, 0.05, 0.10, 0.30, 0.50}
- Random seed: deterministic (42 + replication_id)

**Coverage event**: true_p ∈ [L, U] at final n = 100

**Success criterion**:
- Empirical coverage rate ≥ 0.95 (nominal target)
- 95% Wilson CI lower bound ≥ 0.90 (accounting for Monte Carlo variance)

**Results**: All conditions achieved 200/200 coverage (100%), with Wilson CI [0.981, 1.000]

**Interpretation**: 100% coverage indicates conservative bounds (as expected for Hoeffding). The Wilson CI confirms this is statistically consistent with the 95% target, not a validation artifact.

**File**: [scripts/validate_coverage.py](scripts/validate_coverage.py)

---

## 9. Performance Comparison

**Objective**: Two-sided interval estimation under time-uniform validity

**Regime**: n ∈ {50, 100, 200, 500, 1000}, p ∈ {0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50}

**Metric**: Interval width at fixed (n, p)

**Methods**:
- Baseline: Hoeffding(α=0.05)
- Comparison: Intersection with α_h = α_b = 0.025

**Findings**:
1. **At n ≤ 200** (our experimental regime):
   - Intersection is +2.3% wider on average
   - Range: +1.5% to +3.0%
   - Reason: α-splitting overhead dominates variance savings

2. **At n ≥ 500 with p ≤ 0.05** (large-sample low-p regime):
   - Intersection is -13.7% narrower on average
   - Reason: Variance adaptation overcomes overhead

**File**: [scripts/comprehensive_bounds_comparison.py](scripts/comprehensive_bounds_comparison.py)

**Artifact**: [results_bounds_comparison.txt](results_bounds_comparison.txt)

---

## 10. Stratified Sampling

**Objective**: Prevent composition drift under sequential stopping with heterogeneous strata

**Algorithm**: Round-robin balanced sampling

**Implementation**:
```python
# Maintain counts per stratum
samples_per_stratum = {s: 0 for s in strata}

def sample_next():
    # Select least-sampled stratum (break ties randomly)
    min_count = min(samples_per_stratum.values())
    candidates = [s for s in strata if samples_per_stratum[s] == min_count]
    stratum = rng.choice(candidates)

    # Sample prompt from stratum
    prompt = sample_from_stratum(stratum)
    samples_per_stratum[stratum] += 1

    return stratum, prompt
```

**Guarantee**: At any n divisible by |strata|, all strata have exactly n/|strata| samples

**Property**: E[p̂_stratified | stopped at n] = (1/K) Σ_k p_k (unbiased for uniform target)

**File**: [src/eval_harness/prompts/stratified_json_prompts.py](src/eval_harness/prompts/stratified_json_prompts.py#L128-L169)

**Deterministic seeds**: Uses fixed offset mapping (not hash()) to avoid PYTHONHASHSEED nondeterminism

---

## 11. Known Limitations

1. **Intersection not beneficial at small n**: Requires n ≥ 500 to overcome α-splitting overhead

2. **Conservative bounds**: Hoeffding and Bernstein both use worst-case range assumptions; tighter methods exist (e.g., betting-based CS)

3. **Estimand assumption**: Stratified sampling assumes uniform target mixture; non-uniform targets require weighting

4. **Early stopping not demonstrated**: Experiments hit budget cap (n=1000), didn't actually stop early

---

## 12. Reproducibility

**All results are deterministic**:
- Coverage validation: seed = 42 + replication_id
- Bounds comparison: failures = round(p_true * n) (no randomness)
- Stratified sampling: deterministic stratum offsets

**Environment**: Python 3.9+, numpy, scipy

**Execution**:
```bash
# Coverage validation (~30 seconds)
python3 scripts/validate_coverage.py

# Bounds comparison (~5 seconds)
python3 scripts/comprehensive_bounds_comparison.py

# Full test suite (~1 second)
python3 tests/test_intersection_and_stratified.py
```

---

## 13. References

1. Robbins, H. (1970). Statistical methods related to the law of the iterated logarithm. Ann. Math. Statist., 41(5), 1397-1409.

2. Maurer, A., & Pontil, M. (2009). Empirical Bernstein bounds and sample variance penalization. COLT 2009.

3. Howard, S. R., Ramdas, A., McAuliffe, J., & Sekhon, J. (2021). Time-uniform, nonparametric, nonasymptotic confidence sequences. Ann. Statist., 49(2), 1055-1080.

4. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. J. Amer. Statist. Assoc., 22(158), 209-212.
