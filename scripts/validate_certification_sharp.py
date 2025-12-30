#!/usr/bin/env python3
"""
Experiment B3c: CI-Based Certification with SHARPER One-Sided Bounds

Tests whether the null result from B3b persists under sharper confidence bounds.

Key difference from B3b:
- Uses ONE-SIDED Hoeffding CS (no α-splitting overhead)
- Expected improvement: ~2% tighter bounds than two-sided intersection
- Tests if null result is artifact of conservative bounds or genuine finding

Design: Identical to B3b
- Same 3×2×2 factorial (margin × heterogeneity × method)
- Same decision-driven stopping (UCB ≤ τ or LCB > τ)
- Same CRN coupling (audit-safe SeedSequence.spawn())
- Same metrics (cert rates, time-to-decision, errors, drift)

Research question: Does balance help under sharper bounds?
- If YES → "Sharp CS reveals balance benefit" (positive finding)
- If NO → "Robust null even with sharp bounds" (strong negative result)

RNG Coupling: Audit-safe SeedSequence.spawn() for CRN
- Outcome pools: shared between naive/stratified (depends only on model, rep)
- Policy RNG: independent between methods (depends on model, rep, method)
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

from eval_harness.stats.bernoulli_cs_onesided import BernoulliCSOneSided


# =============================================================================
# Configuration
# =============================================================================

BASE_SEED = 42
N_REPLICATIONS = 200
N_MAX = 1000  # Budget for certification attempts
N_MIN = 50  # Minimum samples before allowing certification (avoid early noise)
ALPHA = 0.05
TAU = 0.20  # Fixed threshold

# =============================================================================
# Model Definitions (Margin Sweep)
# =============================================================================

# Margin levels: ε controls distance from threshold
# Safe: p = τ - ε, Unsafe: p = τ + ε

MARGIN_LEVELS = {
    'wide': {
        'epsilon': 0.15,
        'safe_p': 0.05,   # 0.20 - 0.15
        'unsafe_p': 0.35, # 0.20 + 0.15
    },
    'medium': {
        'epsilon': 0.13,
        'safe_p': 0.07,   # 0.20 - 0.13
        'unsafe_p': 0.33, # 0.20 + 0.13
    },
    'tight': {
        'epsilon': 0.11,
        'safe_p': 0.09,   # 0.20 - 0.11
        'unsafe_p': 0.31, # 0.20 + 0.11
    },
}

def generate_models():
    """Generate all model configurations for margin × heterogeneity sweep"""
    models = {}

    for margin_name, margin_spec in MARGIN_LEVELS.items():
        safe_p = margin_spec['safe_p']
        unsafe_p = margin_spec['unsafe_p']

        # High heterogeneity: wide strata spread (symmetric around mean)
        models[f'safe_{margin_name}_high_het'] = {
            'easy': max(0.0, safe_p - 0.05),
            'medium': safe_p - 0.01,
            'hard': safe_p + 0.01,
            'nightmare': safe_p + 0.05,
        }
        models[f'unsafe_{margin_name}_high_het'] = {
            'easy': unsafe_p - 0.05,
            'medium': unsafe_p - 0.01,
            'hard': unsafe_p + 0.01,
            'nightmare': unsafe_p + 0.05,
        }

        # Low heterogeneity: tight strata spread (symmetric around mean)
        models[f'safe_{margin_name}_low_het'] = {
            'easy': safe_p - 0.02,
            'medium': safe_p - 0.01,
            'hard': safe_p + 0.01,
            'nightmare': safe_p + 0.02,
        }
        models[f'unsafe_{margin_name}_low_het'] = {
            'easy': unsafe_p - 0.02,
            'medium': unsafe_p - 0.01,
            'hard': unsafe_p + 0.01,
            'nightmare': unsafe_p + 0.02,
        }

    # Verify means
    for model_name, strata in models.items():
        mean_p = np.mean(list(strata.values()))

        # Extract safety and margin from model name
        # Format: {safe|unsafe}_{margin}_{het_level}
        parts = model_name.split('_')
        is_safe = parts[0] == 'safe'
        margin_name = parts[1]  # wide, medium, or tight

        expected = MARGIN_LEVELS[margin_name]['safe_p' if is_safe else 'unsafe_p']

        assert abs(mean_p - expected) < 0.001, \
            f"{model_name}: mean={mean_p:.4f}, expected={expected:.4f}"

    return models

MODELS = generate_models()


# =============================================================================
# Reproducibility Utilities
# =============================================================================

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
    return {
        'python': sys.version.split()[0],
        'numpy': np.__version__,
    }

def compute_checksum(data: str) -> str:
    """Compute SHA256 checksum of results"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# =============================================================================
# Feasibility Pre-Check
# =============================================================================

def compute_feasibility_bounds():
    """Compute minimum UCB at p̂=0 across all n to verify certification is possible"""
    print("=" * 80)
    print("FEASIBILITY PRE-CHECK")
    print("=" * 80)
    print(f"\nConfiguration: n_max={N_MAX}, α={ALPHA}, τ={TAU}")
    print("\nComputing minimum UCB at p̂=0 across n ∈ [1, n_max]...")

    cs = BernoulliCSOneSided(alpha=ALPHA, n_max=N_MAX)

    min_ucb = float('inf')
    min_ucb_n = None
    first_feasible_n = None

    # Simulate all successes (p̂=0)
    for n in range(1, N_MAX + 1):
        cs.update(False)  # Success
        _, ucb = cs.get_bounds()

        if ucb < min_ucb:
            min_ucb = ucb
            min_ucb_n = n

        if first_feasible_n is None and ucb <= TAU:
            first_feasible_n = n

    print(f"\nMinimum UCB: {min_ucb:.4f} at n={min_ucb_n}")
    print(f"Threshold τ: {TAU:.4f}")

    if min_ucb <= TAU:
        print(f"✓ Certification IS feasible (UCB can reach ≤ τ)")
        print(f"  First feasible n: {first_feasible_n}")

        # Compute implied maximum certifiable p̂
        max_certifiable_phat = TAU - min_ucb
        print(f"  Maximum certifiable p̂ ≈ {max_certifiable_phat:.4f}")
    else:
        print(f"✗ Certification NOT feasible (UCB never reaches τ)")
        print(f"  Gap: {min_ucb - TAU:.4f}")
        print(f"  To make feasible: increase n_max or raise τ")

    print()
    return min_ucb, min_ucb_n, first_feasible_n


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
    """
    stratum_names = sorted(strata.keys())
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

    Stratified policy: least-sampled with random tie-break (balanced at all n)
    Naive policy: uniform random stratum selection
    """
    stratum_names = sorted(strata.keys())
    n_strata = len(stratum_names)
    stratum_counters = {s: 0 for s in stratum_names}

    outcomes = []
    stratum_sequence = []

    for i in range(n):
        if method == 'stratified':
            # Least-sampled with random tie-break
            min_count = min(stratum_counters.values())
            candidates = [s for s in stratum_names if stratum_counters[s] == min_count]
            stratum = policy_rng.choice(candidates)
        else:  # naive
            stratum_idx = policy_rng.integers(0, n_strata)
            stratum = stratum_names[stratum_idx]

        # Draw from shared pool
        k = stratum_counters[stratum]
        outcome = stratum_outcomes[stratum][k]
        stratum_counters[stratum] += 1

        outcomes.append(outcome)
        stratum_sequence.append(stratum)

    return outcomes, stratum_sequence


# =============================================================================
# Sequential Stopping & Certification
# =============================================================================

@dataclass
class CertificationResult:
    model_name: str
    method: str
    replication: int
    n_stop: int
    p_hat: float
    ci_lower: float
    ci_upper: float
    ci_width: float
    decision: str  # 'certified_safe', 'certified_unsafe', 'not_certified'
    true_p: float
    is_safe_model: bool  # Ground truth
    false_reject: bool  # Safe model but rejected/not_certified
    false_accept: bool  # Unsafe model but certified safe
    drift_at_stop: float


def run_single_replication(
    model_name: str,
    strata: Dict[str, float],
    method: str,
    replication: int,
    model_idx: int,
    method_offset: int
) -> CertificationResult:
    """Run one replication with decision-driven stopping for certification.

    Stopping rules (applied after n >= N_MIN):
    - Stop and certify safe if UCB ≤ τ
    - Stop and certify unsafe if LCB > τ
    - Otherwise continue to n_max, then abstain (not certified)
    """

    # Outcome pools: Shared across methods (depends only on model, rep)
    outcome_ss = np.random.SeedSequence([BASE_SEED, model_idx, replication, 999])
    stratum_outcomes = generate_stratum_outcomes_v2(outcome_ss, strata, N_MAX)

    # Policy RNG: Independent between methods
    policy_ss = np.random.SeedSequence([BASE_SEED, model_idx, replication, method_offset])
    policy_rng = np.random.default_rng(policy_ss)

    # Sample using policy
    outcomes, stratum_sequence = sample_with_policy_v2(
        stratum_outcomes, strata, method, N_MAX, policy_rng
    )

    # Decision-driven sequential stopping for certification
    cs = BernoulliCSOneSided(alpha=ALPHA, n_max=N_MAX)
    n_stop = N_MAX
    decision = 'not_certified'  # Default if we reach n_max without certifying

    for n in range(1, N_MAX + 1):
        cs.update(outcomes[n - 1])
        ci_lower, ci_upper = cs.get_bounds()

        # Only attempt certification after minimum samples
        if n >= N_MIN:
            if ci_upper <= TAU:
                decision = 'certified_safe'
                n_stop = n
                break
            elif ci_lower > TAU:
                decision = 'certified_unsafe'
                n_stop = n
                break

    # Final state at stopping
    p_hat = cs.failures / cs.trials if cs.trials > 0 else 0.0
    ci_lower, ci_upper = cs.get_bounds()
    ci_width = ci_upper - ci_lower

    # Ground truth
    true_p = np.mean(list(strata.values()))
    is_safe_model = true_p < TAU

    # Error flags
    false_reject = is_safe_model and (decision != 'certified_safe')
    false_accept = (not is_safe_model) and (decision == 'certified_safe')

    # Composition drift at stopping
    n_strata = len(strata)
    stratum_counts = {s: stratum_sequence[:n_stop].count(s) for s in strata.keys()}
    fractions = np.array([stratum_counts[s] / n_stop for s in sorted(strata.keys())])
    drift = np.var(fractions - 1.0 / n_strata) * 10000

    return CertificationResult(
        model_name=model_name,
        method=method,
        replication=replication,
        n_stop=n_stop,
        p_hat=p_hat,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_width=ci_width,
        decision=decision,
        true_p=true_p,
        is_safe_model=is_safe_model,
        false_reject=false_reject,
        false_accept=false_accept,
        drift_at_stop=drift
    )


# =============================================================================
# Experiment Runner
# =============================================================================

def run_experiment() -> List[CertificationResult]:
    """Run full 3×2×2 factorial experiment"""
    results = []

    print("=" * 80)
    print("EXPERIMENT B3c: CI-BASED CERTIFICATION (SHARP BOUNDS)")
    print("=" * 80)
    print(f"\nFixed threshold: τ = {TAU}")
    print(f"Replications per condition: {N_REPLICATIONS}")

    n_models = len(MODELS)
    total_runs = n_models * 2 * N_REPLICATIONS
    print(f"Total runs: {n_models} models × 2 methods × {N_REPLICATIONS} = {total_runs}")
    print()

    for model_idx, (model_name, strata) in enumerate(MODELS.items()):
        mean_p = np.mean(list(strata.values()))
        is_safe = 'safe' in model_name

        print(f"\nModel: {model_name}")
        print(f"  Mean p: {mean_p:.4f}, Ground truth: {'SAFE' if is_safe else 'UNSAFE'}")
        print(f"  Strata: {strata}")

        for method in ['naive', 'stratified']:
            print(f"    Running {method}...", end=" ", flush=True)

            for rep in range(N_REPLICATIONS):
                method_offset = 0 if method == 'naive' else 1

                result = run_single_replication(
                    model_name, strata, method, rep, model_idx, method_offset
                )
                results.append(result)

            print("✓")

    return results


# =============================================================================
# Analysis & Results
# =============================================================================

def analyze_results(results: List[CertificationResult]):
    """Analyze certification outcomes and decision errors"""
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    # Group by model
    models_list = sorted(set(r.model_name for r in results))

    for model_name in models_list:
        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        print(f"\n{model_name}:")
        print(f"  True p: {naive_results[0].true_p:.4f}")
        print(f"  Ground truth: {'SAFE' if naive_results[0].is_safe_model else 'UNSAFE'}")

        for method, method_results in [('Naive', naive_results), ('Stratified', strat_results)]:
            n_certified_safe = sum(1 for r in method_results if r.decision == 'certified_safe')
            n_certified_unsafe = sum(1 for r in method_results if r.decision == 'certified_unsafe')
            n_not_certified = sum(1 for r in method_results if r.decision == 'not_certified')

            cert_safe_rate = 100 * n_certified_safe / len(method_results)
            cert_unsafe_rate = 100 * n_certified_unsafe / len(method_results)
            abstain_rate = 100 * n_not_certified / len(method_results)

            false_reject_count = sum(1 for r in method_results if r.false_reject)
            false_accept_count = sum(1 for r in method_results if r.false_accept)

            mean_n_stop = np.mean([r.n_stop for r in method_results])
            mean_drift = np.mean([r.drift_at_stop for r in method_results])

            # Time-to-decision for certified outcomes only
            certified_results = [r for r in method_results if r.decision != 'not_certified']
            if certified_results:
                median_time_to_cert = np.median([r.n_stop for r in certified_results])
                mean_time_to_cert = np.mean([r.n_stop for r in certified_results])
            else:
                median_time_to_cert = None
                mean_time_to_cert = None

            print(f"  {method}:")
            print(f"    Certified safe: {cert_safe_rate:.1f}%")
            print(f"    Certified unsafe: {cert_unsafe_rate:.1f}%")
            print(f"    Not certified: {abstain_rate:.1f}%")
            print(f"    False reject: {false_reject_count} ({100*false_reject_count/len(method_results):.1f}%)")
            print(f"    False accept: {false_accept_count} ({100*false_accept_count/len(method_results):.1f}%)")
            print(f"    Mean n_stop (all): {mean_n_stop:.1f}")
            if median_time_to_cert is not None:
                print(f"    Time-to-cert (median): {median_time_to_cert:.0f}")
                print(f"    Time-to-cert (mean): {mean_time_to_cert:.1f}")
            print(f"    Drift (×10⁴): {mean_drift:.2f}")


def write_results_file(results: List[CertificationResult], output_path: Path):
    """Write results to file with full configuration and checksums"""
    git_hash = get_git_hash()
    versions = get_versions()

    lines = []
    lines.append("=" * 80)
    lines.append("EXPERIMENT B3c: CI-BASED CERTIFICATION (SHARP BOUNDS)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Git commit: {git_hash}")
    lines.append(f"NumPy: {versions['numpy']}")
    lines.append(f"Python: {versions['python']}")
    lines.append("")
    lines.append("Configuration:")
    lines.append(f"  BASE_SEED = {BASE_SEED}")
    lines.append(f"  N_REPLICATIONS = {N_REPLICATIONS}")
    lines.append(f"  N_MAX = {N_MAX}")
    lines.append(f"  N_MIN = {N_MIN}")
    lines.append(f"  ALPHA = {ALPHA}")
    lines.append(f"  TAU (fixed) = {TAU}")
    lines.append("")
    lines.append("Stopping rule: Decision-driven (certification stopping)")
    lines.append("  - Stop and certify safe if UCB ≤ τ (after n ≥ N_MIN)")
    lines.append("  - Stop and certify unsafe if LCB > τ (after n ≥ N_MIN)")
    lines.append("  - Otherwise continue to n_max, then abstain")
    lines.append("")
    lines.append("=" * 80)
    lines.append("RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Aggregate results by model
    models_list = sorted(set(r.model_name for r in results))

    for model_name in models_list:
        model_results = [r for r in results if r.model_name == model_name]
        naive_results = [r for r in model_results if r.method == 'naive']
        strat_results = [r for r in model_results if r.method == 'stratified']

        lines.append(f"{model_name}:")
        lines.append(f"  True p: {naive_results[0].true_p:.4f}")
        lines.append(f"  Ground truth: {'SAFE' if naive_results[0].is_safe_model else 'UNSAFE'}")

        for method, method_results in [('Naive', naive_results), ('Stratified', strat_results)]:
            n_cert_safe = sum(1 for r in method_results if r.decision == 'certified_safe')
            n_cert_unsafe = sum(1 for r in method_results if r.decision == 'certified_unsafe')
            n_not_cert = sum(1 for r in method_results if r.decision == 'not_certified')

            false_reject = sum(1 for r in method_results if r.false_reject)
            false_accept = sum(1 for r in method_results if r.false_accept)

            mean_n = np.mean([r.n_stop for r in method_results])
            mean_drift = np.mean([r.drift_at_stop for r in method_results])

            # Time-to-cert for certified outcomes only
            certified = [r for r in method_results if r.decision != 'not_certified']
            if certified:
                median_cert_n = np.median([r.n_stop for r in certified])
                mean_cert_n = np.mean([r.n_stop for r in certified])
            else:
                median_cert_n = None
                mean_cert_n = None

            lines.append(f"  {method}:")
            lines.append(f"    Certified safe: {100*n_cert_safe/len(method_results):.1f}%")
            lines.append(f"    Certified unsafe: {100*n_cert_unsafe/len(method_results):.1f}%")
            lines.append(f"    Not certified: {100*n_not_cert/len(method_results):.1f}%")
            lines.append(f"    False reject: {false_reject}/{len(method_results)} ({100*false_reject/len(method_results):.1f}%)")
            lines.append(f"    False accept: {false_accept}/{len(method_results)} ({100*false_accept/len(method_results):.1f}%)")
            lines.append(f"    Mean n_stop (all): {mean_n:.1f}")
            if median_cert_n is not None:
                lines.append(f"    Time-to-cert (median): {median_cert_n:.0f}")
                lines.append(f"    Time-to-cert (mean): {mean_cert_n:.1f}")
            lines.append(f"    Drift (×10⁴): {mean_drift:.2f}")

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


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"\nGit commit: {get_git_hash()}")
    print(f"Versions: {get_versions()}\n")

    # Feasibility pre-check
    min_ucb, min_ucb_n, first_feasible_n = compute_feasibility_bounds()

    # Run experiment
    results = run_experiment()

    # Analyze
    analyze_results(results)

    # Write results
    output_file = Path(__file__).parent.parent / "results_certification_sharp.txt"
    write_results_file(results, output_file)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
