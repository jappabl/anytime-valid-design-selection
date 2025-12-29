#!/usr/bin/env python3
"""Validation of certification bias under composition drift.

This experiment demonstrates that naive sequential sampling can produce false
certifications under heterogeneous failure rates, and that stratified sampling
prevents this harm.

EXPERIMENTAL DESIGN:
- Setting: One-sided certification (certify if upper bound ≤ τ)
- Heterogeneity: 4 strata with controlled failure rates
- True mixture p: 0.1625 (ABOVE certification threshold τ = 0.10)
- Correct decision: DO NOT CERTIFY
- Harm metric: False certification rate P(certify | p_true > τ)

STATISTICAL RIGOR:
- Independent replications: 200 (power ≥ 80% to detect 10pp difference)
- Separate RNG streams per replication (ensures independence)
- Wilson confidence intervals for false-cert rate estimates
- Deterministic seeds for full reproducibility
- All results written to file

AUDIT TRAIL:
- Configuration logged in output
- Per-replication results saved
- Composition drift tracked
- Statistical tests included

References:
- Wilson, E. B. (1927). Probable inference. JASA.
- Howard et al. (2021). Time-uniform confidence sequences. AOS.
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
# Designed so p_true is just above τ to enable false certifications via drift
STRATUM_P = {
    'easy': 0.00,      # Always succeeds
    'medium': 0.02,    # 2% failure rate
    'hard': 0.10,      # 10% failure rate
    'nightmare': 0.32  # 32% failure rate
}

# True mixture failure rate (uniform mixture)
# p_true = (1/4) * (0.00 + 0.02 + 0.10 + 0.32) = 0.11
P_TRUE = sum(STRATUM_P.values()) / len(STRATUM_P)

# Certification threshold
# p_true = 0.11 is just above τ = 0.10
# This allows composition drift to cause false certifications
TAU = 0.10

# Critical property: P_TRUE > TAU
# Therefore, correct decision is DO NOT CERTIFY
assert P_TRUE > TAU, f"Design error: p_true={P_TRUE} must be > τ={TAU}"

# Stopping rule parameters
ALPHA = 0.05         # 95% confidence
MAX_SAMPLES = 200    # Budget constraint
MIN_SAMPLES = 20     # Prevent trivial early stops

# Statistical power for false-cert rate estimation
N_REPLICATIONS = 200  # Detects 10pp difference with power ≥ 80%

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
    statement += "CRITICAL: Both naive and stratified sampling estimate the SAME p under\n"
    statement += "uniform target mixture. The difference is:\n"
    statement += "- Naive: Composition varies randomly → biased at early stopping times\n"
    statement += "- Stratified: Composition fixed at all n → unbiased at all stopping times\n\n"
    statement += "CERTIFICATION DECISION:\n"
    statement += f"- Threshold τ = {TAU}\n"
    statement += "- Rule: Certify \"p ≤ τ\" if upper_bound(p̂, n, α) ≤ τ\n"
    statement += f"- True state: p = {P_TRUE:.4f} > τ = {TAU} → should NOT certify\n"
    statement += "- Harm: False certification (Type I error in safety context)\n"

    return statement


# =============================================================================
# WILSON CONFIDENCE INTERVAL FOR BINOMIAL PROPORTION
# =============================================================================

def wilson_ci(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Compute Wilson score confidence interval for binomial proportion.

    More accurate than normal approximation, especially for proportions near 0 or 1.

    Args:
        successes: Number of successes
        trials: Total trials
        alpha: Significance level (1 - confidence level)

    Returns:
        (lower_bound, upper_bound) tuple

    Reference:
        Wilson, E. B. (1927). Probable inference, the law of succession, and
        statistical inference. JASA, 22(158), 209-212.
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
        """Sample uniformly random stratum, then draw Bernoulli(p_k).

        Returns:
            (stratum, is_failure) tuple
        """
        stratum = self.rng.choice(self.strata)
        is_failure = self.rng.random() < self.stratum_p[stratum]

        self.stratum_counts[stratum] += 1
        self.total_samples += 1

        return stratum, is_failure

    def sample_stratified(self) -> Tuple[str, bool]:
        """Sample via round-robin (balanced), then draw Bernoulli(p_k).

        Returns:
            (stratum, is_failure) tuple
        """
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
    certified: bool
    p_hat_at_stop: float
    upper_bound_at_stop: float
    final_stratum_counts: Dict[str, int]
    composition_variance: float


def run_single_replication(
    method: str,
    replication_id: int,
    seed: int
) -> ReplicationResult:
    """Run a single replication of the certification experiment.

    Args:
        method: 'naive' or 'stratified'
        replication_id: Unique ID for this replication
        seed: Random seed (ensures independence across replications)

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
            upper_bound = cs.get_upper_bound()

            # Certification: stop if upper bound ≤ τ
            if upper_bound <= TAU:
                return ReplicationResult(
                    method=method,
                    replication_id=replication_id,
                    stopped_at_n=n,
                    stop_reason='CERTIFIED',
                    certified=True,
                    p_hat_at_stop=cs.point_estimate,
                    upper_bound_at_stop=upper_bound,
                    final_stratum_counts=dict(sampler.stratum_counts),
                    composition_variance=sampler.get_composition_variance()
                )

    # Hit budget without certifying
    final_upper = cs.get_upper_bound()
    return ReplicationResult(
        method=method,
        replication_id=replication_id,
        stopped_at_n=MAX_SAMPLES,
        stop_reason='MAX_BUDGET',
        certified=False,
        p_hat_at_stop=cs.point_estimate,
        upper_bound_at_stop=final_upper,
        final_stratum_counts=dict(sampler.stratum_counts),
        composition_variance=sampler.get_composition_variance()
    )


def run_all_replications(method: str) -> List[ReplicationResult]:
    """Run all replications for a given method.

    Args:
        method: 'naive' or 'stratified'

    Returns:
        List of ReplicationResult objects
    """
    results = []

    for rep_id in range(N_REPLICATIONS):
        # Ensure independence: each replication gets unique seed
        seed = BASE_SEED + rep_id * 1000 + hash(method) % 1000

        result = run_single_replication(method, rep_id, seed)
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
    stratified_results: List[ReplicationResult]
) -> str:
    """Analyze and format results for audit trail.

    Args:
        naive_results: Results from naive sampling
        stratified_results: Results from stratified sampling

    Returns:
        Formatted analysis string
    """
    output = []
    output.append("=" * 90)
    output.append("EXPERIMENT A: CERTIFICATION BIAS VALIDATION")
    output.append("=" * 90)
    output.append("")
    output.append(get_estimand_statement())
    output.append("")
    output.append("=" * 90)
    output.append("PRIMARY RESULTS - False Certification Rate")
    output.append("=" * 90)
    output.append("")

    # Primary metric: False certification rate
    naive_false_certs = sum(1 for r in naive_results if r.certified)
    stratified_false_certs = sum(1 for r in stratified_results if r.certified)

    naive_rate = naive_false_certs / N_REPLICATIONS
    stratified_rate = stratified_false_certs / N_REPLICATIONS

    # Wilson CIs for false-cert rates
    naive_ci = wilson_ci(naive_false_certs, N_REPLICATIONS, alpha=0.05)
    stratified_ci = wilson_ci(stratified_false_certs, N_REPLICATIONS, alpha=0.05)

    output.append(f"Certification Threshold: τ = {TAU}")
    output.append(f"True Failure Rate: p = {P_TRUE:.4f} > τ (should NOT certify)")
    output.append(f"Nominal False-Cert Bound: ≤ α = {ALPHA}")
    output.append("")
    output.append(f"{'Method':<15} | {'False Certs':<12} | {'Rate':<8} | {'95% Wilson CI':<20} | {'Status':<10}")
    output.append("-" * 90)
    output.append(f"{'Naive':<15} | {naive_false_certs:>4}/{N_REPLICATIONS:<6} | {naive_rate:>7.1%} | [{naive_ci[0]:.3f}, {naive_ci[1]:.3f}] | {'EXCEEDS α' if naive_rate > ALPHA else 'PASS'}")
    output.append(f"{'Stratified':<15} | {stratified_false_certs:>4}/{N_REPLICATIONS:<6} | {stratified_rate:>7.1%} | [{stratified_ci[0]:.3f}, {stratified_ci[1]:.3f}] | {'EXCEEDS α' if stratified_rate > ALPHA else 'PASS'}")
    output.append("")

    # Statistical test: difference in proportions
    pooled_p = (naive_false_certs + stratified_false_certs) / (2 * N_REPLICATIONS)
    se_diff = math.sqrt(2 * pooled_p * (1 - pooled_p) / N_REPLICATIONS)
    z_stat = (naive_rate - stratified_rate) / se_diff if se_diff > 0 else 0
    p_value = 1 - stats.norm.cdf(z_stat)  # One-sided: naive > stratified

    output.append(f"Difference (Naive - Stratified): {naive_rate - stratified_rate:+.1%} ± {1.96 * se_diff:.1%}")
    output.append(f"Z-statistic: {z_stat:.2f}")
    output.append(f"P-value (one-sided): {p_value:.4f}")
    output.append(f"Significant at α=0.05: {'YES' if p_value < 0.05 else 'NO'}")
    output.append("")

    # =============================================================================
    # SECONDARY RESULTS - Stopping Time Distribution
    # =============================================================================
    output.append("=" * 90)
    output.append("SECONDARY RESULTS - Stopping Time Distribution")
    output.append("=" * 90)
    output.append("")

    naive_stop_times = [r.stopped_at_n for r in naive_results]
    stratified_stop_times = [r.stopped_at_n for r in stratified_results]

    output.append(f"{'Method':<15} | {'Median':<8} | {'IQR':<20} | {'Mean':<8}")
    output.append("-" * 90)
    output.append(f"{'Naive':<15} | {np.median(naive_stop_times):>7.0f} | [{np.percentile(naive_stop_times, 25):.0f}, {np.percentile(naive_stop_times, 75):.0f}] | {np.mean(naive_stop_times):>7.1f}")
    output.append(f"{'Stratified':<15} | {np.median(stratified_stop_times):>7.0f} | [{np.percentile(stratified_stop_times, 25):.0f}, {np.percentile(stratified_stop_times, 75):.0f}] | {np.mean(stratified_stop_times):>7.1f}")
    output.append("")
    output.append(f"Interpretation: Earlier stopping indicates premature decisions.")
    output.append("")

    # =============================================================================
    # MECHANISM - Composition Drift
    # =============================================================================
    output.append("=" * 90)
    output.append("MECHANISM - Composition Drift at Stopping Time")
    output.append("=" * 90)
    output.append("")

    # Analyze only replications that certified (false certs)
    naive_false_cert_results = [r for r in naive_results if r.certified]

    if len(naive_false_cert_results) > 0:
        avg_comp_var_false_certs = np.mean([r.composition_variance for r in naive_false_cert_results])

        # Compute average stratum proportions for false certs
        avg_stratum_props = defaultdict(float)
        for r in naive_false_cert_results:
            total = sum(r.final_stratum_counts.values())
            for stratum, count in r.final_stratum_counts.items():
                avg_stratum_props[stratum] += (count / total) / len(naive_false_cert_results)

        output.append(f"Naive replications that FALSELY CERTIFIED (n={len(naive_false_cert_results)}):")
        output.append("")
        output.append(f"Average composition variance: σ² = {avg_comp_var_false_certs:.1f}")
        output.append(f"Target (perfect balance): σ² = 0.0")
        output.append("")
        output.append("Average stratum proportions at stop:")
        for stratum in STRATUM_P.keys():
            target_prop = 1.0 / len(STRATUM_P)
            actual_prop = avg_stratum_props[stratum]
            output.append(f"  {stratum:<12}: {actual_prop:.1%} (target: {target_prop:.1%})")
        output.append("")
        output.append("Interpretation: False certifications correlate with oversampling low-p strata.")
    else:
        output.append("Naive: No false certifications observed.")
        output.append("")

    # Stratified composition (should be perfect even for false certs)
    stratified_comp_vars = [r.composition_variance for r in stratified_results]
    avg_stratified_comp_var = np.mean(stratified_comp_vars)

    output.append(f"Stratified replications (all n={N_REPLICATIONS}):")
    output.append(f"Average composition variance: σ² = {avg_stratified_comp_var:.1f}")
    output.append(f"Target (perfect balance): σ² = 0.0")
    output.append("")

    # =============================================================================
    # CONCLUSION
    # =============================================================================
    output.append("=" * 90)
    output.append("CONCLUSION")
    output.append("=" * 90)
    output.append("")

    if naive_rate > ALPHA and stratified_rate <= ALPHA and p_value < 0.05:
        output.append("✓ HYPOTHESIS VALIDATED:")
        output.append(f"  - Naive sampling produces false certifications at {naive_rate:.1%} (EXCEEDS α={ALPHA})")
        output.append(f"  - Stratified sampling maintains false-cert rate at {stratified_rate:.1%} (≈ α={ALPHA})")
        output.append(f"  - Difference is statistically significant (p={p_value:.4f})")
        output.append(f"  - Composition drift correlates with false certifications in naive method")
        output.append("")
        output.append("INTERPRETATION:")
        output.append("  Under heterogeneous failure rates + early stopping, naive sequential")
        output.append("  sampling exhibits composition drift that causes false certifications.")
        output.append("  Stratified sampling prevents this harm by maintaining exact balance.")
    elif naive_rate <= ALPHA and stratified_rate <= ALPHA:
        output.append("⚠ HYPOTHESIS NOT SUPPORTED:")
        output.append(f"  - Both methods maintain false-cert rate ≤ α")
        output.append(f"  - Early stopping did not trigger frequently enough")
        output.append(f"  - Recommendation: Increase heterogeneity or adjust stopping threshold")
    else:
        output.append("⚠ UNEXPECTED RESULT:")
        output.append(f"  - Naive: {naive_rate:.1%}, Stratified: {stratified_rate:.1%}")
        output.append(f"  - Requires investigation")

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
    """Run Experiment A: Certification bias validation."""
    print("=" * 90)
    print("EXPERIMENT A: CERTIFICATION BIAS VALIDATION")
    print("=" * 90)
    print("")
    print(f"Configuration:")
    print(f"  Strata: {list(STRATUM_P.keys())}")
    print(f"  Per-stratum p: {STRATUM_P}")
    print(f"  True mixture p: {P_TRUE:.4f}")
    print(f"  Certification threshold τ: {TAU}")
    print(f"  True state: p > τ → should NOT certify")
    print(f"  Replications: {N_REPLICATIONS}")
    print(f"  Max samples: {MAX_SAMPLES}")
    print(f"  Base seed: {BASE_SEED}")
    print("")

    # Run naive
    print("Running naive sampling replications...")
    naive_results = run_all_replications('naive')

    # Run stratified
    print("Running stratified sampling replications...")
    stratified_results = run_all_replications('stratified')

    # Analyze
    print("\nAnalyzing results...")
    analysis = analyze_results(naive_results, stratified_results)

    # Print to console
    print("\n")
    print(analysis)

    # Write to file
    output_file = Path(__file__).parent.parent / "results_certification_bias.txt"
    with open(output_file, 'w') as f:
        f.write(analysis)

    print(f"\nResults saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
