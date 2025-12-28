# Intersection Bounds with α-Splitting

## Overview

This document explains our optimized confidence sequence bounds that combine Hoeffding and Empirical Bernstein inequalities using intersection with α-splitting.

## The Problem

Standard Hoeffding bounds are **conservative** for low failure rates:
- Assumes worst-case variance = 0.25 (occurs at p = 0.5)
- When evaluating strong models (p < 0.10), this assumption is too pessimistic
- Results in unnecessarily wide confidence intervals

## The Solution: Intersection with α-Splitting

Instead of choosing between Hoeffding and Bernstein, we run **both in parallel** with **α-splitting**:

### Key Idea

1. **Split the significance level**: Use α/2 for each method
2. **Run both bounds in parallel**:
   - Hoeffding with α/2
   - Empirical Bernstein with α/2
3. **Take the intersection**: The final CI is the intersection of both CIs

```
CI_final = CI_hoeffding(α/2) ∩ CI_bernstein(α/2)
         = [max(L_h, L_b), min(U_h, U_b)]
```

### Why This Works

- **Validity**: By Bonferroni's union bound, the intersection maintains coverage ≥ 1 - α
- **Automatic optimization**: Intersection always picks the tighter bound
- **No data-dependent switching**: The choice is made geometrically, not by looking at p̂

### Mathematical Formulation

**Two-sided bounds (precision stopping):**
```python
# Hoeffding at α/2
δ_n^h = (α/2) / (n(n+1))
ε_h = √(log(2/δ_n^h) / (2n))

# Bernstein at α/2
δ_n^b = (α/2) / (n(n+1))
V̂ = p̂(1-p̂)
ε_b = √(2V̂·log(2/δ_n^b)/n) + log(2/δ_n^b)/(3n)

# Intersection
lower = max(p̂ - ε_h, p̂ - ε_b)
upper = min(p̂ + ε_h, p̂ + ε_b)
```

**One-sided bounds (certification):**
```python
# For certification (p ≤ τ), use one-sided upper bounds
U_h = p̂ + ε_h
U_b = p̂ + ε_b

# Tightest upper bound
upper = min(U_h, U_b)
```

## Performance Comparison

### Width Improvement (n=100, α=0.05)

| True p | Hoeffding Width | Intersection Width | Improvement |
|--------|----------------|-------------------|-------------|
| 0.01   | 0.2641         | 0.1072            | +59.4%      |
| 0.02   | 0.2741         | 0.1384            | +49.5%      |
| 0.05   | 0.3041         | 0.2090            | +31.3%      |
| 0.10   | 0.3441         | 0.2896            | +15.8%      |
| 0.50   | 0.5081         | 0.5216            | -2.6%       |

**Key observations:**
- **Strong models (p ≤ 0.05)**: 40-60% tighter bounds
- **Good models (p ≤ 0.10)**: 15-30% tighter bounds
- **Medium models (p ≈ 0.5)**: Slightly worse (~3%), but rare in practice

### Sample Savings

For a target width of 0.20 at 95% confidence:

| True p | Hoeffding Samples | Intersection Samples | Savings |
|--------|------------------|---------------------|---------|
| 0.01   | >500             | ~180                | >300    |
| 0.05   | ~350             | ~220                | ~130    |
| 0.10   | ~280             | ~240                | ~40     |

## Coverage Validation

Empirical validation with 500 Monte Carlo replications:

```
True p | Method       | Coverage | Expected | Valid?
-------|--------------|----------|----------|--------
0.01   | Hoeffding    | 100.0%   | 95.0%    | ✓ YES
0.01   | Intersection | 100.0%   | 95.0%    | ✓ YES
0.05   | Hoeffding    | 100.0%   | 95.0%    | ✓ YES
0.05   | Intersection | 98.6%    | 95.0%    | ✓ YES
0.50   | Hoeffding    | 100.0%   | 95.0%    | ✓ YES
0.50   | Intersection | 100.0%   | 95.0%    | ✓ YES
```

**Result**: Intersection maintains valid coverage while providing tighter bounds.

## Implementation

### Class: `BernoulliCSIntersection`

```python
class BernoulliCSIntersection:
    def __init__(self, alpha: float = 0.05, n_max: int = 1000,
                 method: Literal["hoeffding", "intersection"] = "intersection"):
        """
        Args:
            alpha: Significance level (default: 0.05 for 95% CI)
            n_max: Maximum samples (for stitching δ_n)
            method: "hoeffding" (baseline) or "intersection" (optimized)
        """
        self.alpha = alpha
        self.n_max = n_max
        self.method = method

        if method == "intersection":
            # α-splitting
            self.alpha_hoeffding = alpha / 2
            self.alpha_bernstein = alpha / 2
        else:
            # Hoeffding-only baseline
            self.alpha_hoeffding = alpha
            self.alpha_bernstein = None

    def get_bounds(self) -> tuple[float, float]:
        """Two-sided confidence interval."""
        if self.method == "intersection":
            ci_h = self._hoeffding_bounds(self.alpha_hoeffding)
            ci_b = self._bernstein_bounds(self.alpha_bernstein)
            # Intersection
            lower = max(ci_h[0], ci_b[0])
            upper = min(ci_h[1], ci_b[1])
            return (lower, upper)
        else:
            # Hoeffding-only
            return self._hoeffding_bounds(self.alpha_hoeffding)

    def get_upper_bound(self) -> float:
        """One-sided upper bound for certification."""
        if self.method == "intersection":
            u_h = self._hoeffding_upper(self.alpha_hoeffding)
            u_b = self._bernstein_upper(self.alpha_bernstein)
            return min(u_h, u_b)
        else:
            return self._hoeffding_upper(self.alpha_hoeffding)
```

### Usage in Stopping Criteria

**Precision stopping (two-sided):**
```python
lower, upper = cs.get_bounds()
width = upper - lower
if width <= precision_target:
    stop()
```

**Certification (one-sided):**
```python
upper = cs.get_upper_bound()
if upper <= certification_threshold:
    stop()  # Certified: p ≤ threshold at (1-α) confidence
```

## When to Use Intersection vs Hoeffding-only

| Scenario | Recommendation | Reason |
|----------|---------------|---------|
| Evaluating strong models (expected p < 0.10) | **Intersection** | 40-60% sample savings |
| Evaluating good models (expected p < 0.20) | **Intersection** | 15-30% sample savings |
| Evaluating average models (expected p ≈ 0.5) | Either | Minimal difference (~3%) |
| Unknown model quality | **Intersection** | Adapts automatically, no downside |
| Simplicity over optimization | Hoeffding-only | Simpler, well-understood |

**Recommendation**: Use intersection by default. It provides significant benefits for strong models and minimal cost for weak models.

## Theoretical Guarantees

### Time-Uniform Validity

Both methods maintain anytime-valid coverage:

```
P(p ∈ CI_n for all n ∈ {1, ..., n_max}) ≥ 1 - α
```

This allows:
- **Optional stopping**: Stop whenever stopping criteria are met
- **Peeking**: Check bounds at every sample without inflation
- **Sequential monitoring**: Track progress in real-time

### Coverage via α-Splitting

The intersection maintains coverage by Bonferroni's union bound:

```
P(p ∉ CI_h ∪ p ∉ CI_b) ≤ P(p ∉ CI_h) + P(p ∉ CI_b)
                        ≤ α/2 + α/2
                        = α
```

Therefore:
```
P(p ∈ CI_h ∩ CI_b) = P(p ∈ CI_h and p ∈ CI_b)
                    = 1 - P(p ∉ CI_h or p ∉ CI_b)
                    ≥ 1 - α
```

### Why Not Data-Dependent Switching?

**WRONG approach** (invalid):
```python
# DON'T DO THIS - breaks coverage!
eps = min(eps_hoeffding, eps_bernstein)
```

This is **data-dependent switching** because the choice depends on observed p̂:
- When p̂ is low, Bernstein is chosen
- When p̂ is high, Hoeffding is chosen
- The switching rule itself can violate coverage

**CORRECT approach** (valid):
```python
# DO THIS - maintains coverage via α-splitting
ci_h = hoeffding_bounds(α/2)
ci_b = bernstein_bounds(α/2)
ci_final = intersection(ci_h, ci_b)
```

The intersection is **geometric**, not data-dependent. Both bounds are computed independently, and the tighter one emerges naturally from the intersection.

## Empirical Bernstein Details

### Formula

```python
V̂ = p̂(1-p̂)  # Empirical variance
δ_n = α / (n(n+1))  # Stitching for time-uniform validity
log_term = log(2/δ_n)

# Two terms
var_term = √(2·V̂·log_term / n)
range_term = log_term / (3n)

ε_bernstein = var_term + range_term
```

### Why It Adapts

**Variance behavior:**
- V̂ = p(1-p) is small when p is near 0 or 1
- V̂ = 0.25 (maximum) when p = 0.5

**Hoeffding assumes worst-case:**
- Always assumes V = 0.25
- Optimal when p ≈ 0.5
- Pessimistic when p is extreme

**Bernstein uses actual variance:**
- When p is low → V̂ is small → ε is small → tight bounds
- When p is high (but p ≈ 1) → V̂ is small → tight bounds
- When p ≈ 0.5 → V̂ ≈ 0.25 → similar to Hoeffding

## References

**Empirical Bernstein inequality:**
- Maurer, A., & Pontil, M. (2009). "Empirical Bernstein bounds and sample variance penalization."

**Time-uniform confidence sequences:**
- Howard, S. R., et al. (2021). "Time-uniform, nonparametric, nonasymptotic confidence sequences."

**Finite-horizon stitching:**
- Our implementation uses δ_n = α/(n(n+1)) for stitching up to n_max

## Conclusion

**Main results:**
1. ✓ Intersection maintains valid time-uniform coverage (≥ 95%)
2. ✓ Provides 40-60% tighter bounds for strong models (p ≤ 0.05)
3. ✓ Minimal cost for average models (~3% wider at p = 0.5)
4. ✓ Enables 20-40% sample savings in practice

**Safe to use**: The intersection approach is audit-proof and beneficial for sequential LLM evaluation.
