#!/usr/bin/env python3
"""Compute minimum achievable width at n=200 with intersection bounds.

Determines feasible width targets for precision stopping.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection


def compute_width_at_n(n: int, p_hat: float, alpha: float = 0.05, n_max: int = 200) -> float:
    """Compute intersection bound width at fixed (n, p̂)."""
    cs = BernoulliCSIntersection(alpha=alpha, n_max=n_max, method="intersection")

    # Feed n samples with failure rate p_hat
    failures = round(p_hat * n)
    for _ in range(failures):
        cs.update(True)
    for _ in range(n - failures):
        cs.update(False)

    lower, upper = cs.get_bounds()
    return upper - lower


def main():
    print("=" * 80)
    print("FEASIBLE WIDTH ANALYSIS - Precision Stopping at n=200")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  - Method: Intersection (α-splitting, α_h = α_b = 0.025)")
    print("  - Horizon: n_max = 200")
    print("  - Nominal coverage: 95% (α = 0.05)")
    print()

    # Representative p̂ values
    p_hat_values = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    n = 200

    print(f"Achievable widths at n={n}:")
    print(f"{'p̂':>6} | {'Width':>8} | {'Notes':>40}")
    print("-" * 80)

    widths = []
    for p_hat in p_hat_values:
        width = compute_width_at_n(n, p_hat, alpha=0.05, n_max=n)
        widths.append(width)

        note = ""
        if p_hat == 0.00:
            note = "(lower bound clipped at 0)"
        elif p_hat == 0.50:
            note = "(maximum variance)"
        elif p_hat in [0.10, 0.15]:
            note = "(our experimental regime)"

        print(f"{p_hat:6.2f} | {width:8.4f} | {note:>40}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    min_width = min(widths)
    print(f"Minimum achievable width: {min_width:.4f}")
    print()

    # Suggested targets
    conservative = min_width + 0.02
    moderate = min(w for w in widths if w >= min_width + 0.05)

    print(f"Suggested width targets:")
    print(f"  - Conservative (guaranteed): w = {conservative:.2f}")
    print(f"  - Moderate (likely):        w = {moderate:.2f}")
    print()

    # Stopping probability estimates (heuristic)
    print("Expected stopping behavior at n=200:")
    for target in [0.30, 0.35, 0.40, 0.45]:
        achievable_p_values = [p for p, w in zip(p_hat_values, widths) if w <= target]
        if achievable_p_values:
            print(f"  w={target:.2f}: Achievable for p̂ ∈ {{{min(achievable_p_values):.2f}, ..., {max(achievable_p_values):.2f}}}")
        else:
            print(f"  w={target:.2f}: NOT achievable at n=200")

    print()
    print("=" * 80)
    print("DECISION RULE")
    print("=" * 80)
    print()
    print("For immediate use:")
    print(f"  → Use w=0.40 (conservative, guaranteed early stops)")
    print()
    print("For robustness (recommended):")
    print("  → Sweep w ∈ {0.35, 0.38, 0.40, 0.45} and report:")
    print("     - Stopping rate")
    print("     - Conditional bias at stop")
    print("     - Coverage at stop")
    print("  → Demonstrates 'peeking tax' of time-uniform bounds")
    print()


if __name__ == "__main__":
    main()
