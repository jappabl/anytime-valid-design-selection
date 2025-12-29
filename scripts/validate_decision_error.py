#!/usr/bin/env python3
"""
Experiment B2: Decision Error Under Precision Stopping (Coupled Design)

This experiment demonstrates that sampling strategy affects decision ERROR rates,
not just decision disagreement, under precision stopping with heterogeneous prompts.

Key improvements over B1 (stress test):
1. Common random numbers coupling - isolates policy effect
2. Measured drift for both methods - validates mechanism
3. Safe/Unsafe straddle design - defines "better" meaningfully
4. Fixed threshold τ=0.13 - no tuning
5. Decision error as headline metric - not just disagreement

Design: 2×2×2 factorial
- Safety margin: Safe (p=0.11) vs Unsafe (p=0.15), τ=0.13
- Heterogeneity: High vs Low (strata spread, same mean)
- Method: Naive (uniform) vs Stratified (least-sampled with random tie-break)

Metrics:
- False accept rate (Unsafe accepted - Type I error in safety)
- False reject rate (Safe rejected - Type II error / opportunity cost)
- Total decision error
- Composition drift at stopping (both methods)

=== AUDIT FIXES (2025-12-29) ===

Critical RNG independence bug fixed using SeedSequence.spawn():

BEFORE (INVALID):
- Naive policy seed = base
- Easy stratum seed = base + 1000000*0 = base
→ SAME SEED = coupled randomness between policy and outcomes

AFTER (VALID):
- Outcome pools: seed = [BASE_SEED, model_idx, rep, 999]
  → Shared between naive/stratified (CRN)
- Policy RNG: seed = [BASE_SEED, model_idx, rep, method_offset]
  → Independent between naive/stratified
- All stratum RNGs spawned independently via SeedSequence

Additional fixes:
1. Stratified policy: Fixed cycle → least-sampled with random tie-break
2. Seed collisions: Eliminated via SeedSequence structure
3. Statistical analysis: Supports paired tests (data is now truly paired)

Status: AUDIT-SAFE for claim "common random numbers isolates policy effect"
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import sys
import subprocess
import hashlib
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


# =============================================================================
# Configuration
# =============================================================================

BASE_SEED = 42
N_REPLICATIONS = 200
N_MAX = 200
ALPHA = 0.05
TARGET_WIDTH = 0.40
TAU = 0.13  # Fixed threshold (pre-registered, not tuned)

# Stratum IDs for deterministic seeding
STRATUM_IDS = {'easy': 0, 'medium': 1, 'hard': 2, 'nightmare': 3}

# Safe/Unsafe straddle design
MODELS = {
    'safe_high_het': {
        'easy': 0.04,
        'medium': 0.08,
        'hard': 0.12,
        'nightmare': 0.20,
        # Mean: 0.11 < τ=0.13 → SHOULD ACCEPT
    },
    'unsafe_high_het': {
        'easy': 0.08,
        'medium': 0.12,
        'hard': 0.16,
        'nightmare': 0.24,
        # Mean: 0.15 > τ=0.13 → SHOULD REJECT
    },
    'safe_low_het': {
        'easy': 0.09,
        'medium': 0.10,
        'hard': 0.11,
        'nightmare': 0.14,
        # Mean: 0.11 < τ=0.13 → SHOULD ACCEPT
    },
    'unsafe_low_het': {
        'easy': 0.13,
        'medium': 0.14,
        'hard': 0.15,
        'nightmare': 0.18,
        # Mean: 0.15 > τ=0.13 → SHOULD REJECT
    },
}

# Verify design
for model_name, strata in MODELS.items():
    mean_p = np.mean(list(strata.values()))
    is_safe = model_name.startswith('safe_')
    expected_mean = 0.11 if is_safe else 0.15
    assert abs(mean_p - expected_mean) < 0.001, f"{model_name}: mean={mean_p:.4f}, expected={expected_mean}"


# =============================================================================
# Common Random Numbers Implementation (AUDIT-SAFE)
# =============================================================================

def generate_stratum_outcomes_v2(
    seed_sequence: np.random.SeedSequence,
    strata: Dict[str, float],
    n_max: int
) -> Dict[str, np.ndarray]:
    """Pre-generate outcomes for each stratum using independent RNG streams.

    Uses SeedSequence.spawn() to guarantee independence between strata.
    Both methods will draw from these same pools, differing only in sampling order.

    Args:
        seed_sequence: Master seed sequence for this replication
        strata: Stratum definitions {name: p}
        n_max: Max samples to pre-generate

    Returns:
        Dict mapping stratum name to boolean outcome array
    """
    # Spawn independent child streams: one per stratum
    stratum_names = sorted(strata.keys())  # Deterministic order
    children = seed_sequence.spawn(len(stratum_names))

    outcomes = {}
    for i, stratum_name in enumerate(stratum_names):
        rng = np.random.default_rng(children[i])
        p = strata[stratum_name]
        outcomes[stratum_name] = rng.random(n_max) < p
    return outcomes


def sample_with_policy_v2(
    stratum_outcomes: Dict[str, np.ndarray],
    strata: Dict[str, float],
    method: str,
    n: int,
    policy_rng: np.random.Generator
) -> Tuple[List[bool], List[str]]:
    """Sample n outcomes using specified policy, drawing from shared outcome pools.

    AUDIT FIX: Stratified policy now uses "least-sampled with random tie-break"
    instead of fixed round-robin to avoid ordering artifacts.

    Args:
        stratum_outcomes: Pre-generated outcomes per stratum
        strata: Stratum definitions
        method: 'naive' or 'stratified'
        n: Number of samples
        policy_rng: Independent RNG for policy decisions (spawned separately)

    Returns:
        (outcomes, stratum_sequence) - outcomes drawn and which stratum each came from
    """
    stratum_names = sorted(strata.keys())  # Deterministic order
    n_strata = len(stratum_names)
    stratum_counters = {s: 0 for s in stratum_names}  # Track consumption per stratum

    outcomes = []
    stratum_sequence = []

    for i in range(n):
        # Policy determines which stratum to sample
        if method == 'stratified':
            # Least-sampled with random tie-break (balanced at all n)
            min_count = min(stratum_counters.values())
            candidates = [s for s in stratum_names if stratum_counters[s] == min_count]
            stratum = policy_rng.choice(candidates)  # Random tie-break
        else:  # naive
            stratum_idx = policy_rng.integers(0, n_strata)  # Uniform random
            stratum = stratum_names[stratum_idx]

        # Draw from shared pool for this stratum
        k = stratum_counters[stratum]
        outcome = stratum_outcomes[stratum][k]
        stratum_counters[stratum] += 1

        outcomes.append(outcome)
        stratum_sequence.append(stratum)

    return outcomes, stratum_sequence


# =============================================================================
# Drift Measurement
# =============================================================================

def compute_composition_drift(stratum_sequence: List[str], strata: Dict[str, float], n_stop: int) -> float:
    """Compute composition drift at stopping time.

    Drift = Var_s(fraction_s - 1/K) where fraction_s = #samples from s / n_stop
    """
    K = len(strata)
    expected_fraction = 1.0 / K

    # Count samples per stratum up to stopping time
    counts = {s: 0 for s in strata.keys()}
    for s in stratum_sequence[:n_stop]:
        counts[s] += 1

    # Compute variance of deviation from balance
    deviations = [(counts[s] / n_stop - expected_fraction) for s in strata.keys()]
    drift = np.var(deviations) * 1e4  # Scale to ×10⁴ for readability

    return drift


# =============================================================================
# Result Structures
# =============================================================================

@dataclass
class RunResult:
    model_name: str
    method: str
    replication: int
    n_stop: int
    p_hat: float
    decision: str  # 'accept' or 'reject'
    true_p: float
    correct_decision: str
    is_correct: bool
    false_accept: bool
    false_reject: bool
    drift_at_stop: float


def run_single_replication(
    model_name: str,
    strata: Dict[str, float],
    method: str,
    replication: int,
    model_idx: int,
    method_offset: int
) -> RunResult:
    """Run one replication with common random numbers coupling.

    AUDIT FIX: Uses SeedSequence.spawn() to guarantee independence and CRN coupling:
    - Outcome pools: Depend ONLY on (model, rep) → shared between naive/stratified
    - Policy RNG: Depends on (model, rep, method) → independent between naive/stratified

    This ensures both methods see identical outcome pools, differing only in sampling order.

    Args:
        model_name: Model identifier
        strata: Stratum definitions
        method: 'naive' or 'stratified'
        replication: Replication index
        model_idx: Model index for seeding
        method_offset: 0 for naive, 1 for stratified (for policy RNG pairing)
    """

    # Outcome pools: Shared across methods (depends only on model, rep)
    outcome_ss = np.random.SeedSequence([BASE_SEED, model_idx, replication, 999])  # 999 = outcome pool marker
    stratum_outcomes = generate_stratum_outcomes_v2(outcome_ss, strata, N_MAX)

    # Policy RNG: Independent between methods (depends on model, rep, method)
    policy_ss = np.random.SeedSequence([BASE_SEED, model_idx, replication, method_offset])
    policy_rng = np.random.default_rng(policy_ss)

    # Sample using policy (draws from shared pools in method-specific order)
    outcomes, stratum_sequence = sample_with_policy_v2(
        stratum_outcomes, strata, method, N_MAX, policy_rng
    )

    # Sequential stopping
    cs = BernoulliCSIntersection(alpha=ALPHA, n_max=N_MAX)
    n_stop = N_MAX

    for n in range(1, N_MAX + 1):
        cs.update(outcomes[n - 1])
        ci_lower, ci_upper = cs.get_bounds()

        if ci_upper - ci_lower <= TARGET_WIDTH:
            n_stop = n
            break

    # Decision
    p_hat = cs.failures / cs.trials
    decision = 'accept' if p_hat < TAU else 'reject'

    # Ground truth
    true_p = np.mean(list(strata.values()))
    correct_decision = 'accept' if true_p < TAU else 'reject'
    is_correct = (decision == correct_decision)
    false_accept = (decision == 'accept' and true_p >= TAU)
    false_reject = (decision == 'reject' and true_p < TAU)

    # Measure drift at stopping
    drift = compute_composition_drift(stratum_sequence, strata, n_stop)

    return RunResult(
        model_name=model_name,
        method=method,
        replication=replication,
        n_stop=n_stop,
        p_hat=p_hat,
        decision=decision,
        true_p=true_p,
        correct_decision=correct_decision,
        is_correct=is_correct,
        false_accept=false_accept,
        false_reject=false_reject,
        drift_at_stop=drift
    )


# =============================================================================
# Experiment Runner
# =============================================================================

def run_experiment() -> List[RunResult]:
    """Run full 2×2×2 factorial: (Safety × Heterogeneity) × Method"""

    results = []

    print("=" * 80)
    print("EXPERIMENT B2: DECISION ERROR (COUPLED DESIGN)")
    print("=" * 80)
    print(f"\nFixed threshold: τ = {TAU}")
    print(f"Replications per condition: {N_REPLICATIONS}")
    print(f"Total runs: 4 models × 2 methods × {N_REPLICATIONS} = {4 * 2 * N_REPLICATIONS}")
    print()

    model_names = list(MODELS.keys())

    for model_idx, (model_name, strata) in enumerate(MODELS.items()):
        mean_p = np.mean(list(strata.values()))
        print(f"\nModel: {model_name}")
        print(f"  Mean p: {mean_p:.4f}, True decision: {'ACCEPT' if mean_p < TAU else 'REJECT'}")
        print(f"  Strata: {strata}")

        for method in ['naive', 'stratified']:
            print(f"    Running {method}...", end=" ", flush=True)

            for rep in range(N_REPLICATIONS):
                # Method offset for CRN pairing: naive=0, stratified=1
                # Same (model_idx, rep) → shared outcome pools
                # Different method_offset → independent policy RNGs
                method_offset = 0 if method == 'naive' else 1

                result = run_single_replication(
                    model_name, strata, method, rep, model_idx, method_offset
                )
                results.append(result)

            print("✓")

    return results


# =============================================================================
# Analysis & Reporting
# =============================================================================

def analyze_results(results: List[RunResult]):
    """Analyze and report decision error metrics."""

    print("\n" + "=" * 80)
    print("RESULTS: DECISION ERROR RATES")
    print("=" * 80)

    for model_name in MODELS.keys():
        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        true_p = naive_results[0].true_p
        correct_decision = naive_results[0].correct_decision

        print(f"\n{model_name.upper()}")
        print(f"  True p: {true_p:.4f}, Correct decision: {correct_decision.upper()}")
        print(f"  Threshold: τ = {TAU}")

        # Error rates
        naive_fa = sum(r.false_accept for r in naive_results) / len(naive_results)
        strat_fa = sum(r.false_accept for r in strat_results) / len(strat_results)
        naive_fr = sum(r.false_reject for r in naive_results) / len(naive_results)
        strat_fr = sum(r.false_reject for r in strat_results) / len(strat_results)
        naive_total_error = (sum(not r.is_correct for r in naive_results) / len(naive_results))
        strat_total_error = (sum(not r.is_correct for r in strat_results) / len(strat_results))

        print(f"\n  False Accept Rate:")
        print(f"    Naive:      {naive_fa:>6.1%}  ({int(naive_fa * len(naive_results))}/{len(naive_results)})")
        print(f"    Stratified: {strat_fa:>6.1%}  ({int(strat_fa * len(strat_results))}/{len(strat_results)})")
        print(f"    Difference: {(naive_fa - strat_fa):>+6.1%}")

        print(f"\n  False Reject Rate:")
        print(f"    Naive:      {naive_fr:>6.1%}  ({int(naive_fr * len(naive_results))}/{len(naive_results)})")
        print(f"    Stratified: {strat_fr:>6.1%}  ({int(strat_fr * len(strat_results))}/{len(strat_results)})")
        print(f"    Difference: {(naive_fr - strat_fr):>+6.1%}")

        print(f"\n  Total Decision Error:")
        print(f"    Naive:      {naive_total_error:>6.1%}")
        print(f"    Stratified: {strat_total_error:>6.1%}")
        print(f"    Reduction:  {(naive_total_error - strat_total_error):>+6.1%} absolute")
        if naive_total_error > 0:
            print(f"                {(naive_total_error - strat_total_error)/naive_total_error:>+6.1%} relative")

        # Drift
        naive_drift = np.mean([r.drift_at_stop for r in naive_results])
        strat_drift = np.mean([r.drift_at_stop for r in strat_results])
        print(f"\n  Composition Drift (at stopping, ×10⁴):")
        print(f"    Naive:      {naive_drift:>6.2f}")
        print(f"    Stratified: {strat_drift:>6.2f}")

        # Stopping times
        naive_n_stop = np.mean([r.n_stop for r in naive_results])
        strat_n_stop = np.mean([r.n_stop for r in strat_results])
        print(f"\n  Mean stopping time:")
        print(f"    Naive:      {naive_n_stop:>6.1f}")
        print(f"    Stratified: {strat_n_stop:>6.1f}")


def write_results_file(results: List[RunResult], output_path: Path):
    """Write results to file with full configuration."""

    git_hash = "unknown"
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()[:8]
    except:
        pass

    lines = []
    lines.append("=" * 80)
    lines.append("EXPERIMENT B2: DECISION ERROR UNDER PRECISION STOPPING (COUPLED)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Git commit: {git_hash}")
    lines.append(f"NumPy: {np.__version__}")
    lines.append(f"Python: {sys.version.split()[0]}")
    lines.append("")
    lines.append("Configuration:")
    lines.append(f"  BASE_SEED = {BASE_SEED}")
    lines.append(f"  N_REPLICATIONS = {N_REPLICATIONS}")
    lines.append(f"  TAU (fixed) = {TAU}")
    lines.append(f"  TARGET_WIDTH = {TARGET_WIDTH}")
    lines.append(f"  N_MAX = {N_MAX}")
    lines.append(f"  ALPHA = {ALPHA}")
    lines.append("")
    lines.append("Design:")
    lines.append("  - Common random numbers coupling (shared outcome pools)")
    lines.append("  - Safe/Unsafe straddle (p=0.11 vs p=0.15, τ=0.13)")
    lines.append("  - High/Low heterogeneity (strata spread)")
    lines.append("  - Metrics: False accept/reject rates, total error, drift")
    lines.append("")
    lines.append("=" * 80)
    lines.append("RESULTS")
    lines.append("=" * 80)

    for model_name in MODELS.keys():
        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        lines.append(f"\n{model_name}:")
        lines.append(f"  True p: {naive_results[0].true_p:.4f}")
        lines.append(f"  Correct decision: {naive_results[0].correct_decision}")

        naive_fa = sum(r.false_accept for r in naive_results) / len(naive_results)
        strat_fa = sum(r.false_accept for r in strat_results) / len(strat_results)
        naive_fr = sum(r.false_reject for r in naive_results) / len(naive_results)
        strat_fr = sum(r.false_reject for r in strat_results) / len(strat_results)
        naive_err = sum(not r.is_correct for r in naive_results) / len(naive_results)
        strat_err = sum(not r.is_correct for r in strat_results) / len(strat_results)

        lines.append(f"  False accept: Naive={naive_fa:.1%}, Stratified={strat_fa:.1%}")
        lines.append(f"  False reject: Naive={naive_fr:.1%}, Stratified={strat_fr:.1%}")
        lines.append(f"  Total error: Naive={naive_err:.1%}, Stratified={strat_err:.1%}")
        lines.append(f"  Error reduction: {(naive_err - strat_err):.1%} absolute")

        naive_drift = np.mean([r.drift_at_stop for r in naive_results])
        strat_drift = np.mean([r.drift_at_stop for r in strat_results])
        lines.append(f"  Drift (×10⁴): Naive={naive_drift:.2f}, Stratified={strat_drift:.2f}")

    lines.append("")
    lines.append("=" * 80)

    # Checksum
    content = "\n".join(lines)
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    lines.append(f"Checksum (SHA256): {checksum}")
    lines.append("=" * 80)

    output_path.write_text("\n".join(lines))
    print(f"\n✓ Results written to: {output_path}")
    print(f"  Checksum: {checksum}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    results = run_experiment()
    analyze_results(results)

    output_file = Path(__file__).parent.parent / "results_decision_error.txt"
    write_results_file(results, output_file)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
