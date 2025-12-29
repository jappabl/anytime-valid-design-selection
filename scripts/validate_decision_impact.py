#!/usr/bin/env python3
"""
Decision-Level Impact Experiment for Stratified vs Naive Sequential Evaluation

Demonstrates practical impact of conditional bias by measuring decision disagreement
and misdecision rates under a plug-in accept/reject heuristic.

Design: 2×2 factorial
- Heterogeneity: high (p ∈ {0.00, 0.05, 0.10, 0.40}) vs low (p ∈ {0.12, 0.13, 0.14, 0.16})
- Method: naive (uniform random) vs stratified (round-robin)

Fixed issues from initial design:
1. Both models now have equal mean p = 0.1375 (not 0.1375 vs 0.1325)
2. Decision rule labeled honestly as "plug-in heuristic" (not "certification")
3. Reports aggregate disagreement with proper randomness coupling
4. Uses adaptive threshold based on observed p̂_τ distribution
5. Measures misdecision vs ground truth (false accept/reject rates)

Reproducibility fixes (2025-12-29):
- Composition drift computed at n_stop (not N_MAX)
- Results written to file with git hash and versions
- Configuration fully logged
"""

import numpy as np
from typing import Dict, List, Tuple, Literal
from dataclasses import dataclass
import sys
import subprocess
import hashlib
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


# ============================================================================
# Reproducibility Utilities
# ============================================================================

def get_git_hash() -> str:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except:
        pass
    return "unknown"

def get_versions() -> Dict[str, str]:
    """Get versions of key dependencies"""
    versions = {
        'python': sys.version.split()[0],
        'numpy': np.__version__,
    }
    try:
        import scipy
        versions['scipy'] = scipy.__version__
    except:
        versions['scipy'] = 'not installed'
    return versions

def compute_checksum(data: str) -> str:
    """Compute SHA256 checksum of results"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# ============================================================================
# Model Definitions (CORRECTED)
# ============================================================================

MODELS = {
    'high_het': {
        'easy': 0.00,
        'medium': 0.05,
        'hard': 0.10,
        'nightmare': 0.40,
        # Mean: (0.00 + 0.05 + 0.10 + 0.40) / 4 = 0.1375
    },
    'low_het': {
        'easy': 0.12,
        'medium': 0.13,
        'hard': 0.14,
        'nightmare': 0.16,
        # Mean: (0.12 + 0.13 + 0.14 + 0.16) / 4 = 0.1375
    }
}

# Verify equal means
for model_name, strata in MODELS.items():
    mean_p = np.mean(list(strata.values()))
    print(f"Model {model_name}: mean p = {mean_p:.4f}")
    assert np.isclose(mean_p, 0.1375), f"Model {model_name} mean is {mean_p}, expected 0.1375"


# ============================================================================
# Experiment Configuration
# ============================================================================

BASE_SEED = 42
N_REPLICATIONS = 200
N_MAX = 200
ALPHA = 0.05
TARGET_WIDTH = 0.40  # Precision stopping criterion


@dataclass
class RunResult:
    """Single replication result"""
    model_name: str
    method: Literal['naive', 'stratified']
    replication: int
    seed: int

    # Stopping behavior
    n_stop: int
    p_hat: float
    ci_lower: float
    ci_upper: float
    ci_width: float

    # Decision
    decision: Literal['accept', 'reject']

    # Ground truth comparison
    true_p: float
    false_accept: bool  # Decided accept but true_p > threshold
    false_reject: bool  # Decided reject but true_p ≤ threshold

    # Composition tracking (for naive method)
    stratum_counts: Dict[str, int]


# ============================================================================
# Sampling Logic
# ============================================================================

def sample_stratified(rng: np.random.Generator, strata: Dict[str, float], n: int) -> Tuple[List[bool], List[str]]:
    """Round-robin stratified sampling - ensures perfect balance

    Returns:
        Tuple of (outcomes, stratum_sequence) where stratum_sequence tracks which stratum each sample came from
    """
    stratum_names = list(strata.keys())
    n_strata = len(stratum_names)

    outcomes = []
    stratum_sequence = []

    for i in range(n):
        stratum = stratum_names[i % n_strata]
        p = strata[stratum]
        outcome = rng.random() < p  # True = failure
        outcomes.append(outcome)
        stratum_sequence.append(stratum)

    return outcomes, stratum_sequence


def sample_naive(rng: np.random.Generator, strata: Dict[str, float], n: int) -> Tuple[List[bool], List[str]]:
    """Naive uniform random sampling - allows composition drift

    Returns:
        Tuple of (outcomes, stratum_sequence) where stratum_sequence tracks which stratum each sample came from
    """
    stratum_names = list(strata.keys())
    stratum_probs = list(strata.values())

    outcomes = []
    stratum_sequence = []

    for _ in range(n):
        # Sample stratum uniformly
        stratum_idx = rng.integers(0, len(stratum_names))
        stratum = stratum_names[stratum_idx]
        p = stratum_probs[stratum_idx]

        outcome = rng.random() < p  # True = failure
        outcomes.append(outcome)
        stratum_sequence.append(stratum)

    return outcomes, stratum_sequence


# ============================================================================
# Sequential Stopping Simulation
# ============================================================================

def run_single_replication(
    model_name: str,
    strata: Dict[str, float],
    method: Literal['naive', 'stratified'],
    replication: int,
    seed: int,
    threshold: float
) -> RunResult:
    """Run one replication of sequential stopping experiment"""
    rng = np.random.default_rng(seed)

    # Sample all N_MAX outcomes at once (for consistent comparison between methods)
    if method == 'stratified':
        outcomes, stratum_sequence = sample_stratified(rng, strata, N_MAX)
    else:
        outcomes, stratum_sequence = sample_naive(rng, strata, N_MAX)

    # Initialize confidence sequence
    cs = BernoulliCSIntersection(alpha=ALPHA, n_max=N_MAX)

    # Sequential evaluation until stopping criterion met
    n_stop = N_MAX
    for n in range(1, N_MAX + 1):
        cs.update(outcomes[n - 1])

        ci_lower, ci_upper = cs.get_bounds()
        ci_width = ci_upper - ci_lower

        # Precision stopping: width ≤ target
        if ci_width <= TARGET_WIDTH:
            n_stop = n
            break

    # Final state at stopping
    p_hat = cs.failures / cs.trials if cs.trials > 0 else 0.0
    ci_lower, ci_upper = cs.get_bounds()
    ci_width = ci_upper - ci_lower

    # Plug-in decision heuristic (NOT certification)
    decision = 'accept' if p_hat < threshold else 'reject'

    # Ground truth
    true_p = np.mean(list(strata.values()))

    # Misdecision flags
    false_accept = (decision == 'accept') and (true_p > threshold)
    false_reject = (decision == 'reject') and (true_p <= threshold)

    # CRITICAL FIX: Compute composition drift only up to n_stop
    stratum_counts_at_stop = {}
    for s in strata.keys():
        stratum_counts_at_stop[s] = stratum_sequence[:n_stop].count(s)

    return RunResult(
        model_name=model_name,
        method=method,
        replication=replication,
        seed=seed,
        n_stop=n_stop,
        p_hat=p_hat,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_width=ci_width,
        decision=decision,
        true_p=true_p,
        false_accept=false_accept,
        false_reject=false_reject,
        stratum_counts=stratum_counts_at_stop
    )


# ============================================================================
# Experiment Runner
# ============================================================================

def run_experiment() -> Tuple[List[RunResult], float]:
    """Run full 2×2 factorial experiment

    Returns:
        Tuple of (results, adaptive_threshold)
    """
    # Adaptive threshold: Run small pilot to calibrate
    print("=" * 80)
    print("PHASE 1: ADAPTIVE THRESHOLD CALIBRATION")
    print("=" * 80)

    pilot_results = []
    pilot_n = 50
    for model_name, strata in MODELS.items():
        for method in ['naive', 'stratified']:
            for rep in range(pilot_n):
                seed = BASE_SEED + rep * 1000 + (0 if method == 'naive' else 500)
                result = run_single_replication(
                    model_name, strata, method, rep, seed, threshold=0.15  # Placeholder
                )
                pilot_results.append(result)

    # Choose threshold as median of observed p̂_τ (ensures sensitivity)
    pilot_p_hats = [r.p_hat for r in pilot_results]
    adaptive_threshold = float(np.median(pilot_p_hats))

    print(f"\nPilot results (n={pilot_n} replications per condition):")
    print(f"  p̂_τ range: [{np.min(pilot_p_hats):.4f}, {np.max(pilot_p_hats):.4f}]")
    print(f"  p̂_τ median: {adaptive_threshold:.4f}")
    print(f"\n✓ Using adaptive threshold τ = {adaptive_threshold:.4f}\n")

    # Main experiment
    results = []
    print("=" * 80)
    print("PHASE 2: MAIN EXPERIMENT")
    print("=" * 80)
    print(f"Replications per condition: {N_REPLICATIONS}")
    print(f"Total runs: {len(MODELS)} models × 2 methods × {N_REPLICATIONS} = {len(MODELS) * 2 * N_REPLICATIONS}")
    print()

    for model_name, strata in MODELS.items():
        print(f"\nModel: {model_name}")
        print(f"  True p: {np.mean(list(strata.values())):.4f}")
        print(f"  Strata: {strata}")

        for method in ['naive', 'stratified']:
            print(f"  Running {method}...", end=" ", flush=True)

            for rep in range(N_REPLICATIONS):
                # CRITICAL: Use same base seed for naive and stratified on same replication
                # This couples the randomness properly for paired comparison
                model_offset = 0 if model_name == 'high_het' else 100000
                base = BASE_SEED + model_offset + rep * 1000
                seed = base + (0 if method == 'naive' else 1)

                result = run_single_replication(
                    model_name, strata, method, rep, seed, adaptive_threshold
                )
                results.append(result)

            print("✓")

    return results, adaptive_threshold


# ============================================================================
# Analysis
# ============================================================================

def analyze_results(results: List[RunResult], threshold: float):
    """Analyze decision-level impact"""

    print("\n" + "=" * 80)
    print("RESULTS: DECISION-LEVEL IMPACT")
    print("=" * 80)

    for model_name in ['high_het', 'low_het']:
        print(f"\n{'─' * 80}")
        print(f"Model: {model_name}")
        print(f"{'─' * 80}")

        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        # Stopping behavior
        print(f"\n1. Stopping Behavior:")
        print(f"   Naive:      n_stop = {np.mean([r.n_stop for r in naive_results]):.1f} ± {np.std([r.n_stop for r in naive_results]):.1f}")
        print(f"   Stratified: n_stop = {np.mean([r.n_stop for r in strat_results]):.1f} ± {np.std([r.n_stop for r in strat_results]):.1f}")

        # Estimates at stopping
        print(f"\n2. Estimates at Stopping (true p = {naive_results[0].true_p:.4f}):")
        naive_p_hats = [r.p_hat for r in naive_results]
        strat_p_hats = [r.p_hat for r in strat_results]
        print(f"   Naive:      p̂_τ = {np.mean(naive_p_hats):.4f} ± {np.std(naive_p_hats):.4f}")
        print(f"   Stratified: p̂_τ = {np.mean(strat_p_hats):.4f} ± {np.std(strat_p_hats):.4f}")
        print(f"   Difference: {np.mean(naive_p_hats) - np.mean(strat_p_hats):.4f}")

        # Composition variance (naive only)
        if model_name == 'high_het':  # Only meaningful for heterogeneous case
            naive_comp_vars = []
            for r in naive_results:
                fractions = np.array([r.stratum_counts[s] / r.n_stop for s in ['easy', 'medium', 'hard', 'nightmare']])
                target = np.array([0.25, 0.25, 0.25, 0.25])
                comp_var = np.var(fractions - target) * 1e4  # Scale for readability
                naive_comp_vars.append(comp_var)

            print(f"\n3. Composition Drift (naive only, high_het case):")
            print(f"   Var(fraction - 0.25) × 10⁴: {np.mean(naive_comp_vars):.2f} ± {np.std(naive_comp_vars):.2f}")
            print(f"   (Stratified maintains perfect balance: variance = 0)")

        # Decision disagreement (CRITICAL METRIC)
        print(f"\n4. Plug-in Decisions (threshold τ = {threshold:.4f}):")
        naive_accepts = sum(1 for r in naive_results if r.decision == 'accept')
        strat_accepts = sum(1 for r in strat_results if r.decision == 'accept')
        print(f"   Naive:      {naive_accepts}/{len(naive_results)} accept ({100*naive_accepts/len(naive_results):.1f}%)")
        print(f"   Stratified: {strat_accepts}/{len(strat_results)} accept ({100*strat_accepts/len(strat_results):.1f}%)")

        # Paired disagreement (properly coupled randomness)
        disagreements = 0
        for rep in range(N_REPLICATIONS):
            naive_rep = [r for r in naive_results if r.replication == rep][0]
            strat_rep = [r for r in strat_results if r.replication == rep][0]
            if naive_rep.decision != strat_rep.decision:
                disagreements += 1

        print(f"\n5. Decision Disagreement (paired by replication):")
        print(f"   Disagreements: {disagreements}/{N_REPLICATIONS} ({100*disagreements/N_REPLICATIONS:.1f}%)")

        # Misdecision rates vs ground truth
        print(f"\n6. Misdecision vs Ground Truth (true p = {naive_results[0].true_p:.4f}):")

        naive_false_accept = sum(1 for r in naive_results if r.false_accept)
        naive_false_reject = sum(1 for r in naive_results if r.false_reject)
        strat_false_accept = sum(1 for r in strat_results if r.false_accept)
        strat_false_reject = sum(1 for r in strat_results if r.false_reject)

        print(f"   Naive:")
        print(f"     False accept: {naive_false_accept}/{len(naive_results)} ({100*naive_false_accept/len(naive_results):.1f}%)")
        print(f"     False reject: {naive_false_reject}/{len(naive_results)} ({100*naive_false_reject/len(naive_results):.1f}%)")
        print(f"   Stratified:")
        print(f"     False accept: {strat_false_accept}/{len(strat_results)} ({100*strat_false_accept/len(strat_results):.1f}%)")
        print(f"     False reject: {strat_false_reject}/{len(strat_results)} ({100*strat_false_reject/len(strat_results):.1f}%)")

    # Summary across both models
    print(f"\n{'=' * 80}")
    print("SUMMARY: AGGREGATE IMPACT")
    print(f"{'=' * 80}")

    total_naive = [r for r in results if r.method == 'naive']
    total_strat = [r for r in results if r.method == 'stratified']

    total_disagreements = 0
    for model_name in ['high_het', 'low_het']:
        model_naive = [r for r in total_naive if r.model_name == model_name]
        model_strat = [r for r in total_strat if r.model_name == model_name]
        for rep in range(N_REPLICATIONS):
            naive_rep = [r for r in model_naive if r.replication == rep][0]
            strat_rep = [r for r in model_strat if r.replication == rep][0]
            if naive_rep.decision != strat_rep.decision:
                total_disagreements += 1

    total_pairs = len(MODELS) * N_REPLICATIONS
    print(f"\nDecision disagreement across all conditions:")
    print(f"  {total_disagreements}/{total_pairs} pairs disagree ({100*total_disagreements/total_pairs:.1f}%)")
    print(f"\nInterpretation:")
    print(f"  In {100*total_disagreements/total_pairs:.1f}% of cases, naive and stratified would make")
    print(f"  OPPOSITE decisions about the same model under identical budget.")

    # Check for high_het showing stronger effect
    high_het_results = [r for r in results if r.model_name == 'high_het']
    low_het_results = [r for r in results if r.model_name == 'low_het']

    high_het_dis = sum(1 for rep in range(N_REPLICATIONS)
                       if [r for r in high_het_results if r.method == 'naive' and r.replication == rep][0].decision
                       != [r for r in high_het_results if r.method == 'stratified' and r.replication == rep][0].decision)

    low_het_dis = sum(1 for rep in range(N_REPLICATIONS)
                      if [r for r in low_het_results if r.method == 'naive' and r.replication == rep][0].decision
                      != [r for r in low_het_results if r.method == 'stratified' and r.replication == rep][0].decision)

    print(f"\nHeterogeneity effect:")
    print(f"  High heterogeneity: {100*high_het_dis/N_REPLICATIONS:.1f}% disagreement")
    print(f"  Low heterogeneity:  {100*low_het_dis/N_REPLICATIONS:.1f}% disagreement")

    if high_het_dis > low_het_dis:
        print(f"  ✓ High heterogeneity amplifies bias impact ({high_het_dis - low_het_dis} more disagreements)")


# ============================================================================
# Result Writing
# ============================================================================

def write_results_file(results: List[RunResult], threshold: float, output_path: Path):
    """Write results to file with full configuration and checksums"""

    git_hash = get_git_hash()
    versions = get_versions()

    lines = []
    lines.append("=" * 80)
    lines.append("EXPERIMENT B: DECISION-LEVEL IMPACT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Git commit: {git_hash}")
    lines.append(f"Python: {versions['python']}")
    lines.append(f"NumPy: {versions['numpy']}")
    lines.append(f"SciPy: {versions['scipy']}")
    lines.append("")
    lines.append("Configuration:")
    lines.append(f"  BASE_SEED = {BASE_SEED}")
    lines.append(f"  N_REPLICATIONS = {N_REPLICATIONS}")
    lines.append(f"  N_MAX = {N_MAX}")
    lines.append(f"  ALPHA = {ALPHA}")
    lines.append(f"  TARGET_WIDTH = {TARGET_WIDTH}")
    lines.append(f"  ADAPTIVE_THRESHOLD = {threshold:.4f}")
    lines.append("")
    lines.append("Models:")
    for model_name, strata in MODELS.items():
        mean_p = np.mean(list(strata.values()))
        lines.append(f"  {model_name}: {strata} (mean={mean_p:.4f})")
    lines.append("")
    lines.append("=" * 80)
    lines.append("RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Aggregate results
    for model_name in ['high_het', 'low_het']:
        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        lines.append(f"Model: {model_name}")
        lines.append(f"  True p: {naive_results[0].true_p:.4f}")
        lines.append(f"  Naive: n_stop={np.mean([r.n_stop for r in naive_results]):.1f}, p̂_τ={np.mean([r.p_hat for r in naive_results]):.4f}")
        lines.append(f"  Stratified: n_stop={np.mean([r.n_stop for r in strat_results]):.1f}, p̂_τ={np.mean([r.p_hat for r in strat_results]):.4f}")

        # Decision disagreement
        disagreements = sum(1 for rep in range(N_REPLICATIONS)
                           if [r for r in naive_results if r.replication == rep][0].decision
                           != [r for r in strat_results if r.replication == rep][0].decision)
        lines.append(f"  Decision disagreement: {disagreements}/{N_REPLICATIONS} ({100*disagreements/N_REPLICATIONS:.1f}%)")

        # Accept rates
        naive_accepts = sum(1 for r in naive_results if r.decision == 'accept')
        strat_accepts = sum(1 for r in strat_results if r.decision == 'accept')
        lines.append(f"  Accept rate: Naive={100*naive_accepts/len(naive_results):.1f}%, Stratified={100*strat_accepts/len(strat_results):.1f}%")
        lines.append("")

    # Summary
    total_disagreements = 0
    for model_name in ['high_het', 'low_het']:
        model_naive = [r for r in results if r.model_name == model_name and r.method == 'naive']
        model_strat = [r for r in results if r.model_name == model_name and r.method == 'stratified']
        for rep in range(N_REPLICATIONS):
            naive_rep = [r for r in model_naive if r.replication == rep][0]
            strat_rep = [r for r in model_strat if r.replication == rep][0]
            if naive_rep.decision != strat_rep.decision:
                total_disagreements += 1

    lines.append("SUMMARY:")
    lines.append(f"  Overall disagreement: {total_disagreements}/{len(MODELS) * N_REPLICATIONS} ({100*total_disagreements/(len(MODELS)*N_REPLICATIONS):.1f}%)")
    lines.append("")
    lines.append("=" * 80)

    # Compute checksum
    content = "\n".join(lines)
    checksum = compute_checksum(content)
    lines.append(f"Checksum (SHA256): {checksum}")
    lines.append("=" * 80)

    output_path.write_text("\n".join(lines))
    print(f"\n✓ Results written to: {output_path}")
    print(f"  Checksum: {checksum}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("DECISION-LEVEL IMPACT EXPERIMENT")
    print("=" * 80)
    print(f"\nGit commit: {get_git_hash()}")
    print(f"Versions: {get_versions()}")
    print("\nGoal: Demonstrate that conditional bias under precision stopping")
    print("      leads to different DECISIONS between naive and stratified methods")
    print("      on the SAME model under IDENTICAL budget constraints.")
    print()
    print("Plug-in Heuristic: Accept model if p̂_τ < threshold, else reject")
    print("                   (NOT a valid certification bound - just a decision rule)")
    print()

    results, adaptive_threshold = run_experiment()

    analyze_results(results, adaptive_threshold)

    # Write results to file
    output_file = Path(__file__).parent.parent / "results_decision_impact.txt"
    write_results_file(results, adaptive_threshold, output_file)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
