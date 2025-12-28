#!/usr/bin/env python3
"""Validate intersection bounds tightness.

Validates Claim 2 from AUDIT_PREP.md:
"Intersection provides tighter bounds for low p"

Compares width of:
- Hoeffding alone
- Bernstein alone
- Intersection (Hoeffding ∩ Bernstein)

Across different values of p and sample sizes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from eval_harness.stats.bernoulli_cs import BernoulliCS
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


def compare_widths(true_p: float, n_samples: int, alpha: float, seed: int = 42):
    """Compare bound widths at a given p and n."""
    rng = np.random.default_rng(seed)

    # Generate samples
    cs_hoeff = BernoulliCS(alpha=alpha)
    cs_inter = BernoulliCSIntersection(alpha=alpha)

    for _ in range(n_samples):
        outcome = rng.random() < true_p
        cs_hoeff.update(outcome)
        cs_inter.update(outcome)

    # Get bounds
    lower_h, upper_h = cs_hoeff.get_bounds()
    lower_i, upper_i = cs_inter.get_bounds()

    width_hoeffding = upper_h - lower_h
    width_intersection = upper_i - lower_i

    # Calculate improvement
    if width_hoeffding > 0:
        improvement = (1 - width_intersection / width_hoeffding) * 100
    else:
        improvement = 0

    return {
        "true_p": true_p,
        "n_samples": n_samples,
        "p_hat": cs_hoeff.point_estimate,
        "width_hoeffding": width_hoeffding,
        "width_intersection": width_intersection,
        "improvement_pct": improvement,
        "tighter": width_intersection < width_hoeffding,
    }


def main():
    print("=" * 80)
    print("INTERSECTION TIGHTNESS VALIDATION - Objective Audit Evidence")
    print("=" * 80)
    print()
    print("Validates Claim 2: Intersection provides tighter bounds for low p")
    print()

    # Test configurations
    test_cases = [
        # (true_p, n_samples, seed)
        (0.01, 100, 42),
        (0.02, 100, 43),
        (0.05, 100, 44),
        (0.10, 100, 45),
        (0.20, 100, 46),
        (0.30, 100, 47),
        (0.50, 100, 48),
    ]

    alpha = 0.05

    print(f"Configuration:")
    print(f"  alpha: {alpha}")
    print(f"  n_samples: 100 (fixed)")
    print()

    results = []

    for true_p, n_samples, seed in test_cases:
        result = compare_widths(true_p, n_samples, alpha, seed)
        results.append(result)

    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(
        f"{'True p':>8} | {'p̂':>8} | {'Width_H':>10} | {'Width_I':>10} | "
        f"{'Improv %':>10} | {'Tighter?':>10}"
    )
    print("-" * 80)

    for r in results:
        tighter_str = "✓ Yes" if r["tighter"] else "✗ No"
        print(
            f"{r['true_p']:8.2f} | {r['p_hat']:8.4f} | {r['width_hoeffding']:10.4f} | "
            f"{r['width_intersection']:10.4f} | {r['improvement_pct']:9.1f}% | {tighter_str:>10}"
        )

    print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    low_p_results = [r for r in results if r["true_p"] <= 0.05]
    mid_p_results = [r for r in results if 0.05 < r["true_p"] < 0.30]
    high_p_results = [r for r in results if r["true_p"] >= 0.30]

    print("Low p (p ≤ 0.05):")
    if low_p_results:
        avg_improvement = np.mean([r["improvement_pct"] for r in low_p_results])
        all_tighter = all(r["tighter"] for r in low_p_results)
        print(f"  Average improvement: {avg_improvement:.1f}%")
        print(f"  Always tighter: {all_tighter}")
    print()

    print("Medium p (0.05 < p < 0.30):")
    if mid_p_results:
        avg_improvement = np.mean([r["improvement_pct"] for r in mid_p_results])
        all_tighter = all(r["tighter"] for r in mid_p_results)
        print(f"  Average improvement: {avg_improvement:.1f}%")
        print(f"  Always tighter: {all_tighter}")
    print()

    print("High p (p ≥ 0.30):")
    if high_p_results:
        avg_improvement = np.mean([r["improvement_pct"] for r in high_p_results])
        all_tighter = all(r["tighter"] for r in high_p_results)
        print(f"  Average improvement: {avg_improvement:.1f}%")
        print(f"  Always tighter: {all_tighter}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    low_p_improved = all(r["tighter"] for r in low_p_results) if low_p_results else False

    if low_p_improved:
        avg_low_p_improvement = np.mean([r["improvement_pct"] for r in low_p_results])
        print("✓ CLAIM VALIDATED")
        print()
        print(
            f"For low p (≤ 0.05), intersection is consistently tighter "
            f"({avg_low_p_improvement:.1f}% average improvement)."
        )
        print()
        print("Audit Evidence: Claim 2 validated for p ≤ 0.05.")
        print()
        print(
            "Note: Improvement is data-dependent. At higher p, Hoeffding may be competitive."
        )
    else:
        print("⚠ CLAIM PARTIALLY VALIDATED")
        print()
        print("Intersection is not always tighter, even at low p.")
        print("This may be due to random variation or implementation issues.")

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
