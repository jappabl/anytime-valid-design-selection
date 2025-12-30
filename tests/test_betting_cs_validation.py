#!/usr/bin/env python3
"""
Validation tests for one-sided Hoeffding confidence sequences.

Critical validation before running B3c:
1. Coverage under fixed-n (baseline check)
2. Coverage under decision-driven stopping (matches B3c design)
3. Comparison with intersection bounds (should be tighter)
4. Grid over p values in certification regime

Must pass before B3c results are credible.
"""

import numpy as np
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_onesided import BernoulliCSOneSided
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


def test_fixed_n_coverage(
    p_values=[0.01, 0.05, 0.10, 0.20, 0.30],
    n_values=[50, 100, 200, 500],
    alpha=0.05,
    n_reps=1000,
    seed=42
):
    """Test coverage at fixed sample sizes.

    For each (p, n):
    - Generate n_reps independent sequences of length n
    - Check if p ∈ [LCB, UCB] at n
    - Coverage should be ≥ 1-α

    Args:
        p_values: True probabilities to test
        n_values: Sample sizes to test
        alpha: Confidence level
        n_reps: Monte Carlo replications
        seed: Random seed
    """
    print("=" * 80)
    print("TEST 1: FIXED-N COVERAGE")
    print("=" * 80)
    print(f"\nAlpha: {alpha:.3f}, Expected coverage: ≥ {1-alpha:.3f}")
    print(f"Replications: {n_reps}\n")

    rng = np.random.default_rng(seed)
    all_pass = True

    for p in p_values:
        print(f"\nTrue p = {p:.3f}")
        for n in n_values:
            coverage_count = 0

            for _ in range(n_reps):
                # Generate sequence
                failures = rng.binomial(n, p)

                # Build CS state
                cs_test = BernoulliCSOneSided(alpha=alpha, n_max=n)
                for _ in range(failures):
                    cs_test.update(True)
                for _ in range(n - failures):
                    cs_test.update(False)

                # Check coverage
                lcb, ucb = cs_test.get_bounds()
                if lcb <= p <= ucb:
                    coverage_count += 1

            coverage = coverage_count / n_reps
            passed = coverage >= (1 - alpha - 0.02)  # Allow 2% slack for MC noise

            status = "✓" if passed else "✗"
            print(f"  n={n:3d}: coverage={coverage:.3f} [{status}]")

            if not passed:
                all_pass = False

    return all_pass


def test_decision_driven_coverage(
    p_values=[0.05, 0.07, 0.09, 0.31, 0.33, 0.35],
    tau=0.20,
    n_max=1000,
    n_min=50,
    alpha=0.05,
    n_reps=500,
    seed=43
):
    """Test coverage under decision-driven stopping (B3c design).

    For each p:
    - Run decision-driven stopping: stop when UCB ≤ τ or LCB > τ
    - Check if p ∈ [LCB, UCB] at stopping time
    - Coverage should be ≥ 1-α (time-uniform property)

    This is the critical test - matches B3c experimental design.

    Args:
        p_values: True probabilities (Safe and Unsafe models from B3c)
        tau: Certification threshold
        n_max: Maximum samples
        n_min: Minimum samples before stopping
        alpha: Confidence level
        n_reps: Monte Carlo replications
        seed: Random seed
    """
    print("\n" + "=" * 80)
    print("TEST 2: DECISION-DRIVEN STOPPING COVERAGE (B3c Design)")
    print("=" * 80)
    print(f"\nThreshold τ: {tau:.2f}")
    print(f"Alpha: {alpha:.3f}, Expected coverage: ≥ {1-alpha:.3f}")
    print(f"Stopping: UCB ≤ τ or LCB > τ (after n ≥ {n_min})")
    print(f"Replications: {n_reps}\n")

    rng = np.random.default_rng(seed)
    all_pass = True

    for p in p_values:
        is_safe = p < tau

        coverage_count = 0
        cert_count = 0
        n_stops = []

        for _ in range(n_reps):
            cs = BernoulliCSOneSided(alpha=alpha, n_max=n_max)
            stopped = False
            n_stop = n_max

            # Sequential simulation
            for n in range(1, n_max + 1):
                # Generate outcome
                is_failure = rng.random() < p
                cs.update(is_failure)

                # Check stopping criterion (after n_min)
                if n >= n_min:
                    lcb, ucb = cs.get_bounds()

                    if ucb <= tau or lcb > tau:
                        n_stop = n
                        stopped = True
                        cert_count += 1
                        break

            # Final bounds at stopping
            lcb, ucb = cs.get_bounds()

            # Check coverage
            if lcb <= p <= ucb:
                coverage_count += 1

            n_stops.append(n_stop)

        coverage = coverage_count / n_reps
        cert_rate = cert_count / n_reps
        mean_n_stop = np.mean(n_stops)
        median_n_stop = np.median(n_stops)

        passed = coverage >= (1 - alpha - 0.03)  # Allow 3% slack for MC + stopping

        status = "✓" if passed else "✗"
        ground_truth = "SAFE" if is_safe else "UNSAFE"

        print(f"p={p:.3f} ({ground_truth}):")
        print(f"  Coverage: {coverage:.3f} [{status}]")
        print(f"  Cert rate: {cert_rate:.1%}")
        print(f"  Mean n_stop: {mean_n_stop:.0f}")
        print(f"  Median n_stop: {median_n_stop:.0f}")

        if not passed:
            all_pass = False

    return all_pass


def test_vs_intersection_bounds(
    p_values=[0.05, 0.10, 0.20, 0.30],
    n_values=[100, 200, 500],
    alpha=0.05,
    seed=44
):
    """Compare one-sided CS width vs intersection CS width.

    One-sided CS should be tighter (no α/2 split overhead), but check for:
    - Consistently tighter than intersection (validation of improvement)
    - Expected improvement: ~√2 factor (α vs α/2)

    Args:
        p_values: True probabilities to test
        n_values: Sample sizes to test
        alpha: Confidence level
        seed: Random seed
    """
    print("\n" + "=" * 80)
    print("TEST 3: COMPARISON WITH INTERSECTION BOUNDS")
    print("=" * 80)
    print(f"\nExpected: One-sided CS should be tighter than Intersection CS\n")

    rng = np.random.default_rng(seed)
    all_reasonable = True

    for p in p_values:
        print(f"\nTrue p = {p:.3f}")

        for n in n_values:
            # Generate one sequence
            failures = rng.binomial(n, p)

            # One-sided CS
            cs_onesided = BernoulliCSOneSided(alpha=alpha, n_max=n)
            for _ in range(failures):
                cs_onesided.update(True)
            for _ in range(n - failures):
                cs_onesided.update(False)
            lcb_one, ucb_one = cs_onesided.get_bounds()
            width_one = ucb_one - lcb_one

            # Intersection CS
            cs_int = BernoulliCSIntersection(alpha=alpha, n_max=n)
            for _ in range(failures):
                cs_int.update(True)
            for _ in range(n - failures):
                cs_int.update(False)
            lcb_int, ucb_int = cs_int.get_bounds()
            width_int = ucb_int - lcb_int

            # Comparison
            ratio = width_one / width_int if width_int > 0 else 1.0
            tighter = width_one < width_int

            # Should be tighter (ratio < 1)
            reasonable = tighter

            status = "✓" if tighter else "✗"

            print(f"  n={n:3d}: OneSided={width_one:.3f}, Intersection={width_int:.3f}, "
                  f"Ratio={ratio:.2f}x [{status}]")

            if not reasonable:
                all_reasonable = False

    return all_reasonable


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "=" * 80)
    print("ONE-SIDED HOEFFDING CS VALIDATION SUITE")
    print("=" * 80)
    print("\nThese tests must pass before B3c results are credible.\n")

    results = {}

    # Test 1: Fixed-n coverage
    results['fixed_n'] = test_fixed_n_coverage()

    # Test 2: Decision-driven coverage (most critical)
    results['decision_driven'] = test_decision_driven_coverage()

    # Test 3: Comparison with intersection
    results['vs_intersection'] = test_vs_intersection_bounds()

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20s}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED - READY FOR B3c")
    else:
        print("✗ SOME TESTS FAILED - DO NOT RUN B3c")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
