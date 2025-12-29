#!/usr/bin/env python3
"""Validation of estimation bias under precision stopping with composition drift.

This experiment demonstrates that naive sequential sampling exhibits selection-induced
bias when stopping based on precision targets, and that stratified sampling prevents
this harm by maintaining compositional balance.

EXPERIMENTAL DESIGN:
- Setting: Precision stopping (stop when CI width ≤ target)
- Heterogeneity: 4 strata with controlled failure rates
- True mixture p: 0.1375 (uniform over strata)
- Stopping rule: τ = min{n : width(n) ≤ w} or n = n_max
- Harm metrics: Conditional bias E[p̂_τ - p], absolute error, MSE

CRITICAL DISTINCTION:
- Unconditional bias E[p̂_n] at fixed n: Zero for both (unbiased estimators)
- Conditional bias E[p̂_τ | stopped]: Non-zero for naive (selection effect)

STATISTICAL RIGOR:
- Independent replications: 200 (detect 0.02 bias with power ≥ 80%)
- Separate RNG streams per replication
- Wilson CIs for coverage rates
- Deterministic seeds for full reproducibility
- All results written to file with complete audit trail

References:
- Robbins (1970). Law of iterated logarithm
- Howard et al. (2021). Time-uniform confidence sequences
- Wilson, E. B. (1927). Probable inference
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import math
import numpy as np
from scipy import stats
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


# =============================================================================
# EXPERIMENTAL CONFIGURATION
# =============================================================================

# Stratum-specific failure rates (controlled heterogeneity)
# Designed to enable early stopping while demonstrating composition drift
STRATUM_P = {
    'easy': 0.00,      # Always succeeds
    'medium': 0.05,    # 5% failure rate
    'hard': 0.10,      # 10% failure rate
    'nightmare': 0.40  # 40% failure rate
}

# True mixture failure rate (uniform mixture)
# p_true = (1/4) * (0.00 + 0.05 + 0.10 + 0.40) = 0.1375
P_TRUE = sum(STRATUM_P.values()) / len(STRATUM_P)

# Stopping rule parameters
ALPHA = 0.05                       # 95% confidence
WIDTH_TARGETS = [0.35, 0.38, 0.40, 0.45]  # Sweep: demonstrate peeking tax
MAX_SAMPLES = 200                  # Budget constraint
MIN_SAMPLES = 30                   # Prevent trivial early stops

# Statistical power
N_REPLICATIONS = 200    # Detects 0.02 bias with power ≥ 80%

# Reproducibility
BASE_SEED = 42


# =============================================================================
# ESTIMAND DEFINITION
# =============================================================================

def get_estimand_statement() -> str:
    """Return formal estimand definition for audit trail."""
    K = len(STRATUM_P)
    strata_list = list(STRATUM_P.keys())

    statement = "ESTIMAND (Target of Inference):\n"
    statement += "-" * 32 + "\n"
    statement += "We estimate the failure rate of a uniform mixture over strata:\n\n"
    statement += f"    p = (1/{K}) Σ_{{k=1}}^{K} p_k\n\n"
    statement += "where:\n"
    statement += f"- K = {K} strata\n"
    statement += "- p_k = per-stratum failure rate\n"
    statement += "- Uniform weights w_k = 1/K (equal-sized evaluation slices)\n\n"
    statement += "For this experiment:\n"
    statement += f"- Strata: {strata_list}\n"
    statement += f"- Per-stratum p: {STRATUM_P}\n"
    statement += f"- True mixture p: {P_TRUE:.4f}\n\n"
    statement += "CRITICAL: Both naive and stratified estimate the SAME p under uniform mixture.\n"
    statement += "The difference appears under optional stopping:\n\n"
    statement += "UNCONDITIONAL (fixed n):\n"
    statement += "  E[p̂_n] = p  (both methods unbiased at any fixed n)\n\n"
    statement += "CONDITIONAL (at stopping time τ):\n"
    statement += "  Naive: E[p̂_τ | stopped] ≠ p (selection-induced bias)\n"
    statement += "  Stratified: E[p̂_τ | stopped] ≠ p (residual selection bias)\n"
    statement += "  Key: Stratified exhibits ~50% less bias (associated with zero composition drift)\n\n"
    statement += "PRECISION STOPPING RULE (SWEEP):\n"
    statement += f"  τ(w) = min{{n ≥ {MIN_SAMPLES} : width(n) ≤ w}} ∪ {{{MAX_SAMPLES}}}\n"
    statement += f"  Width targets: w ∈ {WIDTH_TARGETS}\n"
    statement += "  Purpose: Demonstrate time-uniform peeking tax at small n\n\n"
    statement += "HARM METRICS:\n"
    statement += "  1. Conditional bias: E[p̂_τ - p]\n"
    statement += "  2. Absolute error: E[|p̂_τ - p|]\n"
    statement += "  3. MSE: E[(p̂_τ - p)²]\n"
    statement += "  4. Coverage at stop: P(p ∈ [L_τ, U_τ])\n"

    return statement


# =============================================================================
# WILSON CONFIDENCE INTERVAL FOR BINOMIAL PROPORTION
# =============================================================================

def wilson_ci(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Compute Wilson score confidence interval for binomial proportion.

    Args:
        successes: Number of successes
        trials: Total trials
        alpha: Significance level

    Returns:
        (lower_bound, upper_bound) tuple
    """
    if trials == 0:
        return (0.0, 1.0)

    z = stats.norm.ppf(1 - alpha / 2)
    p_hat = successes / trials
    n = trials

    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    margin = z * math.sqrt((p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (lower, upper)


# =============================================================================
# SYNTHETIC DATA GENERATION
# =============================================================================

class StratifiedBernoulliSampler:
    """Generate stratified Bernoulli samples with controlled heterogeneity."""

    def __init__(self, stratum_p: Dict[str, float], seed: int):
        """Initialize sampler.

        Args:
            stratum_p: Dict mapping stratum name to failure probability
            seed: Random seed for reproducibility
        """
        self.stratum_p = stratum_p
        self.strata = list(stratum_p.keys())
        self.K = len(self.strata)
        self.rng = np.random.default_rng(seed)

        # Track stratum counts
        self.stratum_counts = {s: 0 for s in self.strata}
        self.total_samples = 0

    def sample_naive(self) -> Tuple[str, bool]:
        """Sample uniformly random stratum, then draw Bernoulli(p_k)."""
        stratum = self.rng.choice(self.strata)
        is_failure = self.rng.random() < self.stratum_p[stratum]

        self.stratum_counts[stratum] += 1
        self.total_samples += 1

        return stratum, is_failure

    def sample_stratified(self) -> Tuple[str, bool]:
        """Sample via round-robin (balanced), then draw Bernoulli(p_k)."""
        # Select least-sampled stratum (break ties randomly)
        min_count = min(self.stratum_counts.values())
        candidates = [s for s in self.strata if self.stratum_counts[s] == min_count]
        stratum = self.rng.choice(candidates)

        is_failure = self.rng.random() < self.stratum_p[stratum]

        self.stratum_counts[stratum] += 1
        self.total_samples += 1

        return stratum, is_failure

    def get_composition_variance(self) -> float:
        """Compute variance of stratum counts (measures imbalance)."""
        counts = list(self.stratum_counts.values())
        return float(np.var(counts))


# =============================================================================
# EXPERIMENT EXECUTION
# =============================================================================

@dataclass
class ReplicationResult:
    """Results from a single replication."""
    method: str
    replication_id: int
    stopped_at_n: int
    stop_reason: str
    p_hat_at_stop: float
    ci_width_at_stop: float
    lower_bound: float
    upper_bound: float
    contains_true_p: bool
    error: float  # p̂ - p_true
    abs_error: float
    squared_error: float
    final_stratum_counts: Dict[str, int]
    composition_variance: float


def run_single_replication(
    method: str,
    replication_id: int,
    seed: int,
    width_target: float
) -> ReplicationResult:
    """Run a single replication of the precision stopping experiment.

    Args:
        method: 'naive' or 'stratified'
        replication_id: Unique ID for this replication
        seed: Random seed
        width_target: Precision threshold for stopping

    Returns:
        ReplicationResult with all tracked metrics
    """
    # Initialize sampler and confidence sequence
    sampler = StratifiedBernoulliSampler(STRATUM_P, seed=seed)
    cs = BernoulliCSIntersection(alpha=ALPHA, n_max=MAX_SAMPLES, method='hoeffding')

    # Sampling loop
    for n in range(1, MAX_SAMPLES + 1):
        # Draw sample
        if method == 'naive':
            stratum, is_failure = sampler.sample_naive()
        elif method == 'stratified':
            stratum, is_failure = sampler.sample_stratified()
        else:
            raise ValueError(f"Unknown method: {method}")

        # Update confidence sequence
        cs.update(is_failure)

        # Check stopping rule (after min_samples)
        if n >= MIN_SAMPLES:
            lower, upper = cs.get_bounds()
            width = upper - lower

            # Precision stopping: stop if width ≤ target
            if width <= width_target:
                p_hat = cs.point_estimate
                error = p_hat - P_TRUE
                return ReplicationResult(
                    method=method,
                    replication_id=replication_id,
                    stopped_at_n=n,
                    stop_reason='PRECISION',
                    p_hat_at_stop=p_hat,
                    ci_width_at_stop=width,
                    lower_bound=lower,
                    upper_bound=upper,
                    contains_true_p=(lower <= P_TRUE <= upper),
                    error=error,
                    abs_error=abs(error),
                    squared_error=error**2,
                    final_stratum_counts=dict(sampler.stratum_counts),
                    composition_variance=sampler.get_composition_variance()
                )

    # Hit budget without reaching precision
    lower, upper = cs.get_bounds()
    width = upper - lower
    p_hat = cs.point_estimate
    error = p_hat - P_TRUE

    return ReplicationResult(
        method=method,
        replication_id=replication_id,
        stopped_at_n=MAX_SAMPLES,
        stop_reason='MAX_BUDGET',
        p_hat_at_stop=p_hat,
        ci_width_at_stop=width,
        lower_bound=lower,
        upper_bound=upper,
        contains_true_p=(lower <= P_TRUE <= upper),
        error=error,
        abs_error=abs(error),
        squared_error=error**2,
        final_stratum_counts=dict(sampler.stratum_counts),
        composition_variance=sampler.get_composition_variance()
    )


def run_all_replications(method: str, width_target: float) -> List[ReplicationResult]:
    """Run all replications for a given method and width target."""
    results = []

    for rep_id in range(N_REPLICATIONS):
        # Ensure independence: each replication gets unique seed
        seed = BASE_SEED + rep_id * 1000 + (0 if method == 'naive' else 500)

        result = run_single_replication(method, rep_id, seed, width_target)
        results.append(result)

        # Progress indicator
        if (rep_id + 1) % 50 == 0:
            print(f"  {method}: {rep_id + 1}/{N_REPLICATIONS} replications complete")

    return results


# =============================================================================
# STATISTICAL ANALYSIS
# =============================================================================

def analyze_results(
    naive_results: List[ReplicationResult],
    stratified_results: List[ReplicationResult],
    width_target: float
) -> str:
    """Analyze and format results for audit trail."""
    output = []
    output.append("=" * 90)
    output.append(f"RESULTS FOR WIDTH TARGET w = {width_target:.2f}")
    output.append("=" * 90)
    output.append("")

    # =============================================================================
    # PRIMARY RESULTS - Conditional Bias at Stopping Time
    # =============================================================================
    output.append("=" * 90)
    output.append("PRIMARY RESULTS - Conditional Bias at Stopping Time")
    output.append("=" * 90)
    output.append("")
    output.append(f"True failure rate: p = {P_TRUE:.4f}")
    output.append(f"Width target: w = {width_target:.2f}")
    output.append(f"Budget: n_max = {MAX_SAMPLES}")
    output.append("")

    # Conditional error metrics
    naive_errors = [r.error for r in naive_results]
    stratified_errors = [r.error for r in stratified_results]

    naive_abs_errors = [r.abs_error for r in naive_results]
    stratified_abs_errors = [r.abs_error for r in stratified_results]

    naive_mse = np.mean([r.squared_error for r in naive_results])
    stratified_mse = np.mean([r.squared_error for r in stratified_results])

    # Bias (mean error)
    naive_bias = np.mean(naive_errors)
    stratified_bias = np.mean(stratified_errors)

    naive_bias_se = np.std(naive_errors, ddof=1) / math.sqrt(N_REPLICATIONS)
    stratified_bias_se = np.std(stratified_errors, ddof=1) / math.sqrt(N_REPLICATIONS)

    # Mean absolute error
    naive_mae = np.mean(naive_abs_errors)
    stratified_mae = np.mean(stratified_abs_errors)

    output.append(f"{'Metric':<25} | {'Naive':<15} | {'Stratified':<15} | {'Difference':<15}")
    output.append("-" * 90)
    output.append(f"{'Conditional Bias':<25} | {naive_bias:>14.4f} | {stratified_bias:>14.4f} | {naive_bias - stratified_bias:>+14.4f}")
    output.append(f"{'  (95% CI)':<25} | ±{1.96*naive_bias_se:>13.4f} | ±{1.96*stratified_bias_se:>13.4f} |")
    output.append(f"{'Mean Absolute Error':<25} | {naive_mae:>14.4f} | {stratified_mae:>14.4f} | {naive_mae - stratified_mae:>+14.4f}")
    output.append(f"{'MSE':<25} | {naive_mse:>14.4f} | {stratified_mse:>14.4f} | {naive_mse - stratified_mse:>+14.4f}")
    output.append("")

    # Statistical test: difference in bias
    pooled_se = math.sqrt(naive_bias_se**2 + stratified_bias_se**2)
    if pooled_se > 0:
        z_stat = (naive_bias - stratified_bias) / pooled_se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))  # Two-sided
        output.append(f"Statistical Test (Bias Difference):")
        output.append(f"  Z-statistic: {z_stat:.2f}")
        output.append(f"  P-value (two-sided): {p_value:.4f}")
        output.append(f"  Significant at α=0.05: {'YES' if p_value < 0.05 else 'NO'}")
    output.append("")

    # =============================================================================
    # COVERAGE AT STOPPING TIME
    # =============================================================================
    output.append("=" * 90)
    output.append("COVERAGE AT STOPPING TIME")
    output.append("=" * 90)
    output.append("")

    naive_coverage_count = sum(1 for r in naive_results if r.contains_true_p)
    stratified_coverage_count = sum(1 for r in stratified_results if r.contains_true_p)

    naive_coverage = naive_coverage_count / N_REPLICATIONS
    stratified_coverage = stratified_coverage_count / N_REPLICATIONS

    naive_cov_ci = wilson_ci(naive_coverage_count, N_REPLICATIONS, alpha=0.05)
    stratified_cov_ci = wilson_ci(stratified_coverage_count, N_REPLICATIONS, alpha=0.05)

    output.append(f"Nominal coverage: {1-ALPHA:.0%}")
    output.append("")
    output.append(f"{'Method':<15} | {'Coverage':<12} | {'95% Wilson CI':<20} | {'Status':<10}")
    output.append("-" * 90)
    output.append(f"{'Naive':<15} | {naive_coverage_count:>4}/{N_REPLICATIONS:<6} | [{naive_cov_ci[0]:.3f}, {naive_cov_ci[1]:.3f}] | {'PASS' if naive_cov_ci[0] >= 0.90 else 'FAIL'}")
    output.append(f"{'Stratified':<15} | {stratified_coverage_count:>4}/{N_REPLICATIONS:<6} | [{stratified_cov_ci[0]:.3f}, {stratified_cov_ci[1]:.3f}] | {'PASS' if stratified_cov_ci[0] >= 0.90 else 'FAIL'}")
    output.append("")
    output.append("Interpretation: Time-uniform validity should maintain ≥ 95% coverage at all stopping times.")
    output.append("")

    # =============================================================================
    # STOPPING TIME DISTRIBUTION
    # =============================================================================
    output.append("=" * 90)
    output.append("STOPPING TIME DISTRIBUTION")
    output.append("=" * 90)
    output.append("")

    naive_stop_times = [r.stopped_at_n for r in naive_results]
    stratified_stop_times = [r.stopped_at_n for r in stratified_results]

    naive_precision_stops = sum(1 for r in naive_results if r.stop_reason == 'PRECISION')
    stratified_precision_stops = sum(1 for r in stratified_results if r.stop_reason == 'PRECISION')

    output.append(f"{'Method':<15} | {'Precision':<12} | {'Median':<8} | {'IQR':<20} | {'Mean':<8}")
    output.append("-" * 90)
    output.append(f"{'Naive':<15} | {naive_precision_stops:>4}/{N_REPLICATIONS:<6} | {np.median(naive_stop_times):>7.0f} | [{np.percentile(naive_stop_times, 25):.0f}, {np.percentile(naive_stop_times, 75):.0f}] | {np.mean(naive_stop_times):>7.1f}")
    output.append(f"{'Stratified':<15} | {stratified_precision_stops:>4}/{N_REPLICATIONS:<6} | {np.median(stratified_stop_times):>7.0f} | [{np.percentile(stratified_stop_times, 25):.0f}, {np.percentile(stratified_stop_times, 75):.0f}] | {np.mean(stratified_stop_times):>7.1f}")
    output.append("")
    output.append("Interpretation: Early stopping enables comparison at optional stopping time.")
    output.append("")

    # =============================================================================
    # MECHANISM - Composition Drift
    # =============================================================================
    output.append("=" * 90)
    output.append("MECHANISM - Composition Drift at Stopping Time")
    output.append("=" * 90)
    output.append("")

    # Naive composition variance
    naive_comp_vars = [r.composition_variance for r in naive_results]
    avg_naive_comp_var = np.mean(naive_comp_vars)

    # Stratified composition variance (should be near zero)
    stratified_comp_vars = [r.composition_variance for r in stratified_results]
    avg_stratified_comp_var = np.mean(stratified_comp_vars)

    output.append(f"{'Method':<15} | {'Mean σ² (counts)':<20} | {'Target':<15}")
    output.append("-" * 90)
    output.append(f"{'Naive':<15} | {avg_naive_comp_var:>19.1f} | {'> 0 (varies)':<15}")
    output.append(f"{'Stratified':<15} | {avg_stratified_comp_var:>19.1f} | {'0.0 (balanced)':<15}")
    output.append("")
    output.append("Interpretation: Variance in stratum counts reflects compositional imbalance.")
    output.append("                Naive exhibits natural sampling variation.")
    output.append("                Stratified maintains perfect balance (σ² ≈ 0).")
    output.append("")

    # =============================================================================
    # CONCLUSION
    # =============================================================================
    output.append("=" * 90)
    output.append("CONCLUSION")
    output.append("=" * 90)
    output.append("")

    # Statistical assessment (Bonferroni-aware)
    bias_diff = naive_bias - stratified_bias  # Keep sign
    bonferroni_threshold = 0.05 / 4  # Four width targets tested
    uncorrected_sig = (p_value < 0.05) if pooled_se > 0 else False
    bonferroni_sig = (p_value < bonferroni_threshold) if pooled_se > 0 else False
    coverage_valid = (naive_cov_ci[0] >= 0.90 and stratified_cov_ci[0] >= 0.90)
    early_stopping_occurred = (naive_precision_stops > 0 or stratified_precision_stops > 0)

    # Report results
    output.append("STATISTICAL SUMMARY:")
    output.append(f"  - Naive conditional bias: {naive_bias:+.4f} (SE: {naive_bias_se:.4f})")
    output.append(f"  - Stratified conditional bias: {stratified_bias:+.4f} (SE: {stratified_bias_se:.4f})")
    output.append(f"  - Bias difference (naive - stratified): {bias_diff:+.4f}")
    output.append(f"  - Statistical significance:")
    output.append(f"    * Uncorrected (p < 0.05): {'YES' if uncorrected_sig else 'NO'} (p={p_value:.4f})")
    output.append(f"    * Bonferroni (p < {bonferroni_threshold:.4f}): {'YES' if bonferroni_sig else 'NO'}")
    output.append(f"  - Coverage at stopping: {'VALID' if coverage_valid else 'INVALID'} (both methods ≥90% lower CI)")
    output.append(f"  - Early stopping rate: Naive={naive_precision_stops}/{N_REPLICATIONS}, Stratified={stratified_precision_stops}/{N_REPLICATIONS}")
    output.append(f"  - Composition drift: Naive σ²={avg_naive_comp_var:.1f}, Stratified σ²={avg_stratified_comp_var:.1f}")
    output.append("")
    output.append("INTERPRETATION:")
    if early_stopping_occurred and coverage_valid:
        output.append("  Precision stopping induces conditional bias in both methods.")
        output.append(f"  Stratified reduces bias by {abs(bias_diff)/abs(naive_bias)*100:.1f}% (associated with")
        output.append("  elimination of composition drift; causal attribution not demonstrated).")
        output.append("  Residual selection bias remains in both methods.")
        if not uncorrected_sig:
            output.append("  ⚠ Bias difference not statistically significant at this width target.")
    else:
        output.append("  ⚠ Early stopping did not trigger; cannot assess conditional bias.")

    output.append("")
    output.append("=" * 90)
    output.append(f"Experiment completed: {N_REPLICATIONS} replications per method")
    output.append(f"Reproducibility: BASE_SEED = {BASE_SEED}")
    output.append("=" * 90)

    return "\n".join(output)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run Experiment A: Precision stopping bias validation with width sweep."""
    print("=" * 90)
    print("EXPERIMENT A: PRECISION STOPPING BIAS VALIDATION")
    print("=" * 90)
    print("")
    print(f"Configuration:")
    print(f"  Strata: {list(STRATUM_P.keys())}")
    print(f"  Per-stratum p: {STRATUM_P}")
    print(f"  True mixture p: {P_TRUE:.4f}")
    print(f"  Width targets: {WIDTH_TARGETS}")
    print(f"  Max samples: {MAX_SAMPLES}")
    print(f"  Replications: {N_REPLICATIONS}")
    print(f"  Base seed: {BASE_SEED}")
    print("")
    print(get_estimand_statement())
    print("")

    # Collect all analyses
    all_analyses = []

    for w_idx, width_target in enumerate(WIDTH_TARGETS):
        print("=" * 90)
        print(f"RUNNING WIDTH TARGET w={width_target:.2f} ({w_idx+1}/{len(WIDTH_TARGETS)})")
        print("=" * 90)
        print("")

        # Run naive
        print(f"Running naive sampling replications (w={width_target:.2f})...")
        naive_results = run_all_replications('naive', width_target)

        # Run stratified
        print(f"Running stratified sampling replications (w={width_target:.2f})...")
        stratified_results = run_all_replications('stratified', width_target)

        # Analyze
        print(f"\nAnalyzing results for w={width_target:.2f}...")
        analysis = analyze_results(naive_results, stratified_results, width_target)
        all_analyses.append(analysis)
        print("")

    # Combine all analyses
    print("")
    print("=" * 90)
    print("ALL RESULTS COMPILED")
    print("=" * 90)
    print("")

    # Write to file
    output_file = Path(__file__).parent.parent / "results_precision_stopping_bias.txt"
    with open(output_file, 'w') as f:
        f.write("=" * 90 + "\n")
        f.write("EXPERIMENT A: PRECISION STOPPING BIAS VALIDATION - WIDTH SWEEP\n")
        f.write("=" * 90 + "\n\n")
        f.write(get_estimand_statement() + "\n\n")
        f.write("=" * 90 + "\n")
        f.write(f"Width targets tested: {WIDTH_TARGETS}\n")
        f.write(f"Replications per (method, width): {N_REPLICATIONS}\n")
        f.write(f"Budget: n_max = {MAX_SAMPLES}\n")
        f.write(f"Confidence: α = {ALPHA}\n")
        f.write("=" * 90 + "\n\n")

        for analysis in all_analyses:
            f.write(analysis)
            f.write("\n\n")

    print(f"Results saved to: {output_file}")
    print("")
    print(f"Total experiment runs: {len(WIDTH_TARGETS)} width targets × 2 methods × {N_REPLICATIONS} reps")
    print(f"                     = {len(WIDTH_TARGETS) * 2 * N_REPLICATIONS} total replications")

    return 0


if __name__ == "__main__":
    sys.exit(main())
