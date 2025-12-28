"""Statistical validity tests using toy model.

These tests verify that our confidence sequences achieve nominal coverage.
"""

import numpy as np
import pytest

from eval_harness.stats.bernoulli_cs import BernoulliCS


def test_cs_coverage_simple():
    """Test that CS achieves nominal coverage on simple case."""
    true_p = 0.1
    n_trials = 50
    n_experiments = 100
    alpha = 0.05

    coverage_count = 0

    for trial in range(n_experiments):
        cs = BernoulliCS(alpha=alpha)
        rng = np.random.default_rng(trial)

        # Collect n_trials samples
        for _ in range(n_trials):
            outcome = rng.random() < true_p
            cs.update(outcome)

        lower, upper = cs.get_bounds()

        if lower <= true_p <= upper:
            coverage_count += 1

    coverage_rate = coverage_count / n_experiments
    expected_coverage = 1 - alpha

    # Allow 10% slack due to randomness
    assert coverage_rate >= expected_coverage - 0.10, (
        f"Coverage {coverage_rate:.3f} below expected {expected_coverage:.3f}"
    )


def test_cs_coverage_multiple_p():
    """Test coverage across different true probabilities."""
    true_ps = [0.01, 0.05, 0.1, 0.3, 0.5]
    n_trials = 100
    n_experiments = 50
    alpha = 0.05

    for true_p in true_ps:
        coverage_count = 0

        for trial in range(n_experiments):
            cs = BernoulliCS(alpha=alpha)
            rng = np.random.default_rng(trial * 1000 + int(true_p * 100))

            for _ in range(n_trials):
                outcome = rng.random() < true_p
                cs.update(outcome)

            lower, upper = cs.get_bounds()

            if lower <= true_p <= upper:
                coverage_count += 1

        coverage_rate = coverage_count / n_experiments
        expected_coverage = 1 - alpha

        # More lenient threshold for extreme probabilities
        slack = 0.15 if true_p < 0.05 or true_p > 0.9 else 0.10

        assert coverage_rate >= expected_coverage - slack, (
            f"Coverage {coverage_rate:.3f} for p={true_p} "
            f"below expected {expected_coverage:.3f}"
        )


def test_cs_width_decreases():
    """Test that confidence interval width decreases with more samples."""
    true_p = 0.1
    cs = BernoulliCS(alpha=0.05)
    rng = np.random.default_rng(42)

    widths = []

    for i in range(1, 201):
        outcome = rng.random() < true_p
        cs.update(outcome)

        if i in [10, 50, 100, 200]:
            widths.append(cs.width)

    # Check that width is decreasing
    for i in range(len(widths) - 1):
        assert widths[i] > widths[i + 1], (
            f"Width at n={[10, 50, 100, 200][i]} ({widths[i]:.4f}) "
            f"not greater than at n={[10, 50, 100, 200][i+1]} ({widths[i+1]:.4f})"
        )


def test_cs_point_estimate_convergence():
    """Test that point estimate converges to true probability."""
    true_p = 0.15
    n_samples = 1000
    cs = BernoulliCS(alpha=0.05)
    rng = np.random.default_rng(42)

    for _ in range(n_samples):
        outcome = rng.random() < true_p
        cs.update(outcome)

    # With 1000 samples, point estimate should be close to true_p
    assert abs(cs.point_estimate - true_p) < 0.03, (
        f"Point estimate {cs.point_estimate:.4f} far from true p={true_p}"
    )


def test_cs_bounds_always_valid():
    """Test that bounds are always in [0, 1] and lower <= upper."""
    true_p = 0.2
    cs = BernoulliCS(alpha=0.05)
    rng = np.random.default_rng(42)

    for i in range(100):
        outcome = rng.random() < true_p
        lower, upper = cs.update(outcome)

        assert 0 <= lower <= 1, f"Lower bound {lower} out of [0, 1] at sample {i}"
        assert 0 <= upper <= 1, f"Upper bound {upper} out of [0, 1] at sample {i}"
        assert lower <= upper, f"Lower {lower} > upper {upper} at sample {i}"


def test_cs_with_all_successes():
    """Test CS behavior when all outcomes are successes (p=0)."""
    cs = BernoulliCS(alpha=0.05)

    for _ in range(50):
        cs.update(False)  # All successes

    lower, upper = cs.get_bounds()

    assert lower == 0.0, f"Lower bound should be 0 with all successes, got {lower}"
    assert upper > 0, f"Upper bound should be > 0, got {upper}"
    assert cs.point_estimate == 0.0


def test_cs_with_all_failures():
    """Test CS behavior when all outcomes are failures (p=1)."""
    cs = BernoulliCS(alpha=0.05)

    for _ in range(50):
        cs.update(True)  # All failures

    lower, upper = cs.get_bounds()

    assert lower < 1.0, f"Lower bound should be < 1, got {lower}"
    assert upper == 1.0, f"Upper bound should be 1 with all failures, got {upper}"
    assert cs.point_estimate == 1.0
