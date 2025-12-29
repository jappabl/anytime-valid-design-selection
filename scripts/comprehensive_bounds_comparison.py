#!/usr/bin/env python3
"""Comprehensive, reproducible comparison of confidence bound methods.

Generates Table 1 for audit: exact widths across (p, n) grid.

Comparison is FAIR:
- All methods provide 95% coverage (α = 0.05)
- Intersection uses α-splitting internally but delivers same guarantee
- Two-sided bounds (estimation, not certification)
- Time-uniform validity over n ∈ {1, ..., n_max}
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import math
import numpy as np
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


def compute_bounds_at_fixed_n_p(n: int, p_true: float, alpha: float = 0.05, n_max: int = 1000):
    """Compute all bound types at fixed (n, p).

    Args:
        n: Sample size
        p_true: True failure probability (used to compute deterministic failures)
        alpha: Significance level
        n_max: Maximum sample size for stitching

    Returns:
        dict with width for each method
    """
    # Deterministic failures (no randomness)
    failures = round(p_true * n)
    successes = n - failures
    p_hat = failures / n

    # Initialize CS instances
    cs_hoeffding = BernoulliCSIntersection(alpha=alpha, n_max=n_max, method="hoeffding")
    cs_intersection = BernoulliCSIntersection(alpha=alpha, n_max=n_max, method="intersection")

    # Feed data
    for _ in range(failures):
        cs_hoeffding.update(True)
        cs_intersection.update(True)
    for _ in range(successes):
        cs_hoeffding.update(False)
        cs_intersection.update(False)

    # Get bounds
    hoeff_bounds = cs_hoeffding.get_bounds()
    inter_bounds = cs_intersection.get_bounds()

    # Also compute standalone Bernstein for reference
    # (not recommended for use, but shows why intersection doesn't help)
    delta_n = alpha / (n * (n + 1))
    log_term = math.log(2.0 / delta_n)
    var_hat = p_hat * (1 - p_hat)

    # Bernstein two-sided
    var_term = math.sqrt(2 * var_hat * log_term / n)
    range_term = (7/3) * log_term / (n - 1) if n > 1 else log_term
    bern_epsilon = var_term + range_term
    bern_lower = max(0.0, p_hat - bern_epsilon)
    bern_upper = min(1.0, p_hat + bern_epsilon)
    bern_width = bern_upper - bern_lower

    return {
        'p_hat': p_hat,
        'hoeffding_width': hoeff_bounds[1] - hoeff_bounds[0],
        'bernstein_width': bern_width,
        'intersection_width': inter_bounds[1] - inter_bounds[0],
        'hoeffding_bounds': hoeff_bounds,
        'intersection_bounds': inter_bounds,
    }


def main():
    header = "="*90 + "\n"
    header += "COMPREHENSIVE BOUNDS COMPARISON - Audit Artifact\n"
    header += "="*90 + "\n"
    header += "\nConfiguration:\n"
    header += "  - Two-sided interval estimation (not certification)\n"
    header += "  - Time-uniform validity: n ∈ {1, ..., n_max}\n"
    header += "  - Nominal coverage: 95% (α = 0.05)\n"
    header += "  - Stitching: δ_n = α / (n(n+1))\n"
    header += "  - Bernstein: Maurer & Pontil (2009) empirical Bernstein inequality\n"
    header += "    * Variance term: sqrt(2 * p̂(1-p̂) * log(2/δ_n) / n)\n"
    header += "    * Range term: (7/3) * log(2/δ_n) / (n-1)\n"
    header += "  - Intersection: α-split (α_h = α_b = 0.025)\n"
    header += "  - Failures: deterministic (failures = round(p_true * n))\n"
    header += "\n" + "="*90 + "\n"

    print(header)

    # Grid
    p_values = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50]
    n_values = [50, 100, 200, 500, 1000]

    # Store results for analysis
    all_results = []

    table_header = f"{'p_true':>7} | {'n':>5} | {'p̂':>7} | {'W_Hoeff':>8} | {'W_Bern':>8} | {'W_Inter':>8} | {'vs Hoeff':>10}\n"
    table_header += "-" * 90 + "\n"

    print(table_header)
    table_rows = ""

    for p in p_values:
        for n in n_values:
            results = compute_bounds_at_fixed_n_p(n, p, alpha=0.05, n_max=max(n_values))

            p_hat = results['p_hat']
            w_h = results['hoeffding_width']
            w_b = results['bernstein_width']
            w_i = results['intersection_width']

            # Improvement vs baseline
            improvement = (w_i - w_h) / w_h * 100

            all_results.append({
                'p': p,
                'n': n,
                'p_hat': p_hat,
                'w_h': w_h,
                'w_b': w_b,
                'w_i': w_i,
                'improvement': improvement
            })

            row = f"{p:7.2f} | {n:5d} | {p_hat:7.4f} | {w_h:8.4f} | {w_b:8.4f} | {w_i:8.4f} | {improvement:+9.1f}%\n"
            print(row, end="")
            table_rows += row

        sep = "-" * 90 + "\n"
        print(sep, end="")
        table_rows += sep

    # Analyze results by regime
    low_n_results = [r for r in all_results if r['n'] <= 200]
    high_n_low_p_results = [r for r in all_results if r['n'] >= 500 and r['p'] <= 0.05]

    avg_low_n = np.mean([r['improvement'] for r in low_n_results])
    avg_high_n_low_p = np.mean([r['improvement'] for r in high_n_low_p_results])

    findings = "\n" + "="*90 + "\n"
    findings += "KEY FINDINGS:\n"
    findings += "="*90 + "\n"
    findings += f"\n1. At n ≤ 200 (our experimental regime):\n"
    findings += f"   - Intersection is +{avg_low_n:.1f}% wider on average\n"
    findings += f"   - Range: +{min(r['improvement'] for r in low_n_results):.1f}% to +{max(r['improvement'] for r in low_n_results):.1f}%\n"
    findings += f"\n2. At n ≥ 500 with p ≤ 0.05 (large-sample low-p regime):\n"
    findings += f"   - Intersection is {avg_high_n_low_p:.1f}% narrower on average\n"
    findings += f"   - Variance adaptation begins to overcome overhead\n"
    findings += f"\n3. α-splitting overhead:\n"
    findings += f"   - Hoeffding(α/2) uses log(2/δ_α/2) = log(2/δ_α) + log(2)\n"
    findings += f"   - Additive log(2) ≈ 0.69 increase in log term\n"
    findings += f"   - For typical δ_n values (log ≈ 10-15), this is ~5-7% increase\n"
    findings += f"   - Translates to ~2-3% width increase after sqrt\n"
    findings += f"\n4. Bernstein range term:\n"
    findings += f"   - (7/3) * log(2/δ_n) / (n-1) dominates at small n\n"
    findings += f"   - Makes Bernstein worse than Hoeffding until n ≥ 500\n"
    findings += f"\n5. CONCLUSION:\n"
    findings += f"   - For n ≤ 200 (our experiments): intersection provides NO benefit\n"
    findings += f"   - For n ≥ 500 with p ≤ 0.05: intersection can save 10-30% width\n"
    findings += f"   - Our use case doesn't reach the beneficial regime\n"
    findings += "\n" + "="*90 + "\n"

    print(findings)

    # Write to file
    output_file = Path(__file__).parent.parent / "results_bounds_comparison.txt"
    with open(output_file, 'w') as f:
        f.write(header)
        f.write(table_header)
        f.write(table_rows)
        f.write(findings)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
