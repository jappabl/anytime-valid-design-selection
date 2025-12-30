#!/usr/bin/env python3
"""
Real-LLM Validation: Experiment A Replication

Replicates Experiment A's estimation bias findings on actual LLM evaluation.

Design:
- Task: JSON schema generation (complexity-stratified prompts)
- Model: GPT-4o-mini (temperature=0 for reproducibility)
- Strata: 4 complexity levels (simple/moderate/complex/extreme)
- Methods: Naive (uniform) vs Stratified (balanced)
- Stopping: Precision (CI width ≤ 0.20)
- Budget: n_max=100 per run
- Replications: 30 runs per method

Objectives:
1. Show heterogeneity exists (stratum failure rates differ)
2. Show naive exhibits conditional bias at stopping
3. Show stratified reduces bias (even if smaller than synthetic)

Expected cost: ~6,000 API calls ≈ $3-5 with GPT-4o-mini

This validates that the phenomenon is REAL, not just synthetic.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import hashlib

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection
from eval_harness.prompts.stratified_json_prompts import (
    StratifiedJSONSchemaDataset,
    StratifiedSampler,
    NaiveSampler
)
from eval_harness.sampling.openai_sampler import OpenAISampler
from eval_harness.validators.json_schema import JSONSchemaValidator
from eval_harness.core.types import DecodingConfig


# =============================================================================
# Configuration
# =============================================================================

BASE_SEED = 42
N_REPLICATIONS = 30  # Per method (modest for cost control)
N_MAX = 100  # Budget per run
TARGET_WIDTH = 0.20  # Precision target
ALPHA = 0.05

# Model config
MODEL_ID = "gpt-4o-mini"
TEMPERATURE = 0.0  # Deterministic for reproducibility

# Check API key
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Set it with: export OPENAI_API_KEY='your-key'")
    sys.exit(1)


# =============================================================================
# Result Types
# =============================================================================

@dataclass
class ReplicationResult:
    """Results from one replication."""
    method: str
    replication: int
    n_stop: int
    p_hat: float
    ci_lower: float
    ci_upper: float
    ci_width: float
    stratum_counts: Dict[str, int]  # How many from each stratum
    stratum_failures: Dict[str, int]  # Failures per stratum
    drift_at_stop: float  # Composition drift


# =============================================================================
# Experiment Logic
# =============================================================================

def run_single_replication(
    method: str,
    replication: int,
    prompts_per_stratum: int = 25
) -> ReplicationResult:
    """Run one replication with real LLM calls.

    Args:
        method: 'naive' or 'stratified'
        replication: Replication index for seeding
        prompts_per_stratum: How many prompts per stratum to generate

    Returns:
        ReplicationResult with outcomes
    """

    # Create stratified prompt dataset
    seed = BASE_SEED + replication
    dataset = StratifiedJSONSchemaDataset(
        prompts_per_stratum=prompts_per_stratum,
        seed=seed
    )

    # Create sampler based on method
    if method == 'stratified':
        sampler = StratifiedSampler(dataset, seed=seed)
    else:  # naive
        sampler = NaiveSampler(dataset, seed=seed)

    # Create LLM sampler and validator
    llm_sampler = OpenAISampler(
        model_id=MODEL_ID,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    validator = JSONSchemaValidator()

    # Decoding config
    decoding = DecodingConfig(
        temperature=TEMPERATURE,
        max_tokens=500,
        top_p=1.0
    )

    # Sequential evaluation with precision stopping
    cs = BernoulliCSIntersection(alpha=ALPHA, n_max=N_MAX)

    stratum_counts = {'simple': 0, 'moderate': 0, 'complex': 0, 'extreme': 0}
    stratum_failures = {'simple': 0, 'moderate': 0, 'complex': 0, 'extreme': 0}

    n_stop = N_MAX

    for n in range(1, N_MAX + 1):
        # Sample next prompt
        stratum, prompt = sampler.sample_next()
        stratum_counts[stratum] += 1

        # Query LLM
        generation = llm_sampler.sample(prompt, decoding)

        # Validate
        result = validator.validate(
            generation,
            sample_id=f"{method}_rep{replication}_n{n}",
            schema=prompt.metadata.get('schema')
        )

        is_failure = not result.passed
        if is_failure:
            stratum_failures[stratum] += 1

        # Update CS
        cs.update(is_failure)

        # Check stopping criterion (precision)
        if n >= 20:  # Min samples
            ci_lower, ci_upper = cs.get_bounds()
            ci_width = ci_upper - ci_lower

            if ci_width <= TARGET_WIDTH:
                n_stop = n
                break

    # Final state
    p_hat = cs.failures / cs.trials if cs.trials > 0 else 0.0
    ci_lower, ci_upper = cs.get_bounds()
    ci_width = ci_upper - ci_lower

    # Compute drift
    n_strata = 4
    fractions = np.array([stratum_counts[s] / n_stop for s in sorted(stratum_counts.keys())])
    drift = np.var(fractions - 1.0 / n_strata) * 10000

    return ReplicationResult(
        method=method,
        replication=replication,
        n_stop=n_stop,
        p_hat=p_hat,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_width=ci_width,
        stratum_counts=stratum_counts,
        stratum_failures=stratum_failures,
        drift_at_stop=drift
    )


def run_experiment() -> List[ReplicationResult]:
    """Run full experiment (both methods)."""

    print("=" * 80)
    print("REAL-LLM EXPERIMENT A REPLICATION")
    print("=" * 80)
    print(f"\nModel: {MODEL_ID} (temperature={TEMPERATURE})")
    print(f"Task: JSON schema generation")
    print(f"Strata: 4 complexity levels")
    print(f"Stopping: Precision (width ≤ {TARGET_WIDTH})")
    print(f"Budget: n_max={N_MAX}")
    print(f"Replications: {N_REPLICATIONS} per method")
    print(f"\nTotal API calls: ~{N_REPLICATIONS * 2 * N_MAX} (max)")
    print()

    results = []

    for method in ['naive', 'stratified']:
        print(f"\n{'='*80}")
        print(f"METHOD: {method.upper()}")
        print(f"{'='*80}\n")

        for rep in range(N_REPLICATIONS):
            print(f"Replication {rep+1}/{N_REPLICATIONS}...", end=" ", flush=True)

            try:
                result = run_single_replication(method, rep)
                results.append(result)
                print(f"✓ (n={result.n_stop}, p̂={result.p_hat:.3f}, drift={result.drift_at_stop:.2f})")
            except Exception as e:
                print(f"✗ ERROR: {e}")
                continue

    return results


# =============================================================================
# Analysis
# =============================================================================

def analyze_results(results: List[ReplicationResult]):
    """Analyze heterogeneity, bias, and drift."""

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Group by method
    naive_results = [r for r in results if r.method == 'naive']
    strat_results = [r for r in results if r.method == 'stratified']

    print(f"\n1. DATA COLLECTION")
    print(f"   Naive: {len(naive_results)} replications")
    print(f"   Stratified: {len(strat_results)} replications")

    # Heterogeneity: per-stratum failure rates
    print(f"\n2. HETEROGENEITY (Per-Stratum Failure Rates)")

    all_stratum_rates = {'simple': [], 'moderate': [], 'complex': [], 'extreme': []}

    for result in results:
        for stratum in all_stratum_rates.keys():
            count = result.stratum_counts[stratum]
            failures = result.stratum_failures[stratum]
            if count > 0:
                all_stratum_rates[stratum].append(failures / count)

    print("\n   Stratum | Mean Rate | Std | Min | Max")
    print("   " + "-" * 50)
    for stratum in ['simple', 'moderate', 'complex', 'extreme']:
        rates = all_stratum_rates[stratum]
        if rates:
            mean_rate = np.mean(rates)
            std_rate = np.std(rates)
            min_rate = np.min(rates)
            max_rate = np.max(rates)
            print(f"   {stratum:8s} | {mean_rate:9.3f} | {std_rate:.3f} | {min_rate:.3f} | {max_rate:.3f}")

    # Bias analysis (simplified: mean p̂ vs estimated true p from all data)
    print(f"\n3. CONDITIONAL BIAS AT STOPPING")

    # Estimate true p from all samples
    all_failures = sum(r.n_stop * r.p_hat for r in results)
    all_samples = sum(r.n_stop for r in results)
    estimated_true_p = all_failures / all_samples if all_samples > 0 else 0.0

    naive_mean_phat = np.mean([r.p_hat for r in naive_results])
    strat_mean_phat = np.mean([r.p_hat for r in strat_results])

    naive_bias = naive_mean_phat - estimated_true_p
    strat_bias = strat_mean_phat - estimated_true_p

    bias_reduction = abs(naive_bias) - abs(strat_bias)
    bias_reduction_pct = 100 * bias_reduction / abs(naive_bias) if naive_bias != 0 else 0

    print(f"\n   Estimated true p (from all data): {estimated_true_p:.4f}")
    print(f"\n   Naive:")
    print(f"     Mean p̂ at stop: {naive_mean_phat:.4f}")
    print(f"     Bias: {naive_bias:+.4f}")
    print(f"\n   Stratified:")
    print(f"     Mean p̂ at stop: {strat_mean_phat:.4f}")
    print(f"     Bias: {strat_bias:+.4f}")
    print(f"\n   Bias reduction: {bias_reduction:.4f} ({bias_reduction_pct:+.1f}%)")

    # Drift
    print(f"\n4. COMPOSITION DRIFT AT STOPPING")

    naive_mean_drift = np.mean([r.drift_at_stop for r in naive_results])
    strat_mean_drift = np.mean([r.drift_at_stop for r in strat_results])

    drift_reduction = 100 * (1 - strat_mean_drift / naive_mean_drift) if naive_mean_drift > 0 else 0

    print(f"\n   Naive: {naive_mean_drift:.2f} ×10⁴")
    print(f"   Stratified: {strat_mean_drift:.2f} ×10⁴")
    print(f"   Reduction: {drift_reduction:.1f}%")

    # Stopping behavior
    print(f"\n5. STOPPING BEHAVIOR")

    naive_mean_n = np.mean([r.n_stop for r in naive_results])
    strat_mean_n = np.mean([r.n_stop for r in strat_results])

    print(f"\n   Naive: mean n_stop = {naive_mean_n:.1f}")
    print(f"   Stratified: mean n_stop = {strat_mean_n:.1f}")


def write_results_file(results: List[ReplicationResult], output_path: Path):
    """Write results to file."""

    lines = []
    lines.append("=" * 80)
    lines.append("REAL-LLM EXPERIMENT A REPLICATION")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Model: {MODEL_ID}")
    lines.append(f"Temperature: {TEMPERATURE}")
    lines.append(f"Task: JSON schema generation")
    lines.append(f"Replications: {N_REPLICATIONS} per method")
    lines.append(f"Budget: n_max={N_MAX}")
    lines.append(f"Precision target: width ≤ {TARGET_WIDTH}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Compute summary stats
    naive_results = [r for r in results if r.method == 'naive']
    strat_results = [r for r in results if r.method == 'stratified']

    # True p estimate
    all_failures = sum(r.n_stop * r.p_hat for r in results)
    all_samples = sum(r.n_stop for r in results)
    estimated_true_p = all_failures / all_samples

    lines.append(f"Estimated true p (from all data): {estimated_true_p:.4f}")
    lines.append("")

    for method_name, method_results in [('Naive', naive_results), ('Stratified', strat_results)]:
        mean_phat = np.mean([r.p_hat for r in method_results])
        bias = mean_phat - estimated_true_p
        mean_drift = np.mean([r.drift_at_stop for r in method_results])
        mean_n = np.mean([r.n_stop for r in method_results])

        lines.append(f"{method_name}:")
        lines.append(f"  Mean p̂: {mean_phat:.4f}")
        lines.append(f"  Bias: {bias:+.4f}")
        lines.append(f"  Mean drift (×10⁴): {mean_drift:.2f}")
        lines.append(f"  Mean n_stop: {mean_n:.1f}")
        lines.append("")

    # Bias reduction
    naive_bias = np.mean([r.p_hat for r in naive_results]) - estimated_true_p
    strat_bias = np.mean([r.p_hat for r in strat_results]) - estimated_true_p
    bias_reduction = abs(naive_bias) - abs(strat_bias)
    bias_reduction_pct = 100 * bias_reduction / abs(naive_bias) if naive_bias != 0 else 0

    lines.append(f"Bias reduction: {bias_reduction:.4f} ({bias_reduction_pct:+.1f}%)")
    lines.append("")

    # Compute checksum
    content = "\n".join(lines)
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    lines.append("=" * 80)
    lines.append(f"Checksum (SHA256): {checksum}")
    lines.append("=" * 80)

    output_path.write_text("\n".join(lines))
    print(f"\n✓ Results written to: {output_path}")
    print(f"  Checksum: {checksum}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("REAL-LLM VALIDATION: EXPERIMENT A REPLICATION")
    print("=" * 80)
    print("\nThis will make API calls to OpenAI (GPT-4o-mini)")
    print(f"Estimated cost: ~$3-5 for {N_REPLICATIONS * 2} replications")
    print()

    response = input("Proceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)

    # Run experiment
    results = run_experiment()

    # Analyze
    analyze_results(results)

    # Write results
    output_file = Path(__file__).parent.parent / "results_llm_validation.txt"
    write_results_file(results, output_file)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
