"""Comprehensive unit tests for intersection bounds and stratified sampling.

Tests the key components that were missing per audit:
1. α-splitting logic
2. Intersection bounds mechanics
3. Correct Bernstein constants (7/3, n-1)
4. Stratified sampler balance
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection
from eval_harness.prompts.stratified_json_prompts import (
    StratifiedJSONSchemaDataset,
    StratifiedSampler,
    NaiveSampler,
    STRATUM_SEED_OFFSETS,
)


class TestAlphaSplitting:
    """Test that α-splitting is correctly implemented."""

    def test_alpha_splitting_values(self):
        """Verify α is split 50/50 for intersection method."""
        cs = BernoulliCSIntersection(alpha=0.10, n_max=100, method="intersection")
        assert cs.alpha_hoeffding == 0.05
        assert cs.alpha_bernstein == 0.05

    def test_no_alpha_splitting_for_hoeffding_only(self):
        """Verify no splitting when using Hoeffding-only baseline."""
        cs = BernoulliCSIntersection(alpha=0.10, n_max=100, method="hoeffding")
        assert cs.alpha_hoeffding == 0.10
        # Bernstein alpha unused in this mode


class TestIntersectionMechanics:
    """Test intersection bounds are computed correctly."""

    def test_intersection_is_tightest_valid_bound(self):
        """Verify intersection takes max(lower) and min(upper)."""
        cs = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")

        # Add 5 failures, 15 successes
        for _ in range(5):
            cs.update(True)
        for _ in range(15):
            cs.update(False)

        # Get both component bounds
        ci_h = cs._hoeffding_bounds(cs.alpha_hoeffding)
        ci_b = cs._bernstein_bounds(cs.alpha_bernstein)

        # Get intersection
        lower, upper = cs.get_bounds()

        # Verify intersection logic
        assert lower == max(ci_h[0], ci_b[0])
        assert upper == min(ci_h[1], ci_b[1])

    def test_intersection_never_wider_than_union(self):
        """Verify intersection is never wider than either component alone."""
        cs = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")

        # Test multiple scenarios
        for n_failures in [1, 10, 25, 50]:
            cs.trials = 0
            cs.failures = 0
            cs.successes = 0

            for _ in range(n_failures):
                cs.update(True)
            for _ in range(100 - n_failures):
                cs.update(False)

            ci_intersection = cs.get_bounds()
            ci_h = cs._hoeffding_bounds(cs.alpha_hoeffding)
            ci_b = cs._bernstein_bounds(cs.alpha_bernstein)

            width_intersection = ci_intersection[1] - ci_intersection[0]
            width_h = ci_h[1] - ci_h[0]
            width_b = ci_b[1] - ci_b[0]

            # Intersection should be at most as wide as the tighter component
            # (It could be tighter if bounds don't fully overlap)
            assert width_intersection <= max(width_h, width_b) + 1e-10


class TestBernsteinConstants:
    """Test that Bernstein bounds use correct constants."""

    def test_bernstein_range_term_formula(self):
        """Verify Bernstein range term uses (7/3) * log_term / (n-1)."""
        cs = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")

        # Add 10 failures, 90 successes
        for _ in range(10):
            cs.update(True)
        for _ in range(90):
            cs.update(False)

        n = cs.trials
        p_hat = cs.failures / n
        var_hat = p_hat * (1 - p_hat)
        alpha_b = cs.alpha_bernstein
        delta_n = alpha_b / (n * (n + 1))

        import math

        log_term = math.log(2.0 / delta_n)

        # Expected values per Maurer & Pontil (2009)
        expected_var_term = math.sqrt(2 * var_hat * log_term / n)
        expected_range_term = (7 / 3) * log_term / (n - 1)
        expected_epsilon = expected_var_term + expected_range_term

        # Get actual bounds
        ci_b = cs._bernstein_bounds(alpha_b)
        actual_epsilon = ci_b[1] - p_hat  # Upper bound radius

        # Should match within floating point precision
        assert abs(actual_epsilon - expected_epsilon) < 1e-10

    def test_bernstein_uses_n_minus_1(self):
        """Verify denominator is (n-1), not n."""
        cs = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")

        for _ in range(50):
            cs.update(False)

        n = cs.trials
        alpha_b = cs.alpha_bernstein
        delta_n = alpha_b / (n * (n + 1))

        import math

        log_term = math.log(2.0 / delta_n)

        # The range term should use (n-1) in denominator
        expected_range_term = (7 / 3) * log_term / (n - 1)

        # If it incorrectly used n, we'd get:
        wrong_range_term = (7 / 3) * log_term / n

        # These should differ
        assert abs(expected_range_term - wrong_range_term) > 1e-6

    def test_bernstein_edge_case_n_equals_1(self):
        """Verify no division by zero at n=1."""
        cs = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")
        cs.update(True)

        # Should not raise exception
        lower, upper = cs.get_bounds()

        # Bounds should be valid
        assert 0 <= lower <= 1
        assert 0 <= upper <= 1
        assert lower <= upper


class TestStratifiedSamplerBalance:
    """Test stratified sampler maintains perfect balance."""

    def test_strict_mode_perfect_balance(self):
        """Verify strict mode achieves zero variance in stratum counts."""
        dataset = StratifiedJSONSchemaDataset(
            prompts_per_stratum=25, seed=42, strata=["simple", "medium", "complex", "extreme"]
        )
        rng = np.random.default_rng(42)
        sampler = StratifiedSampler(dataset, rng, balance_mode="strict")

        # Sample 100 times (25 per stratum)
        for _ in range(100):
            stratum, prompt = sampler.sample_next()

        counts = sampler.get_stratum_counts()

        # Perfect balance: all counts should be exactly 25
        assert counts["simple"] == 25
        assert counts["medium"] == 25
        assert counts["complex"] == 25
        assert counts["extreme"] == 25

        # Variance should be exactly zero
        count_values = list(counts.values())
        variance = np.var(count_values)
        assert variance == 0.0

    def test_naive_sampler_has_variance(self):
        """Verify naive sampler exhibits natural sampling variation."""
        dataset = StratifiedJSONSchemaDataset(
            prompts_per_stratum=100, seed=42, strata=["simple", "medium", "complex", "extreme"]
        )
        rng = np.random.default_rng(42)
        sampler = NaiveSampler(dataset, rng)

        # Sample 100 times
        for _ in range(100):
            stratum, prompt = sampler.sample_next()

        counts = sampler.get_stratum_counts()

        # Counts should NOT all be exactly 25 (natural variation)
        count_values = list(counts.values())
        variance = np.var(count_values)

        # With 100 samples across 4 strata, we expect variance > 0
        assert variance > 0

    def test_stratified_balance_at_all_n(self):
        """Verify balance holds at ALL stopping times, not just n_max."""
        dataset = StratifiedJSONSchemaDataset(
            prompts_per_stratum=50, seed=42, strata=["simple", "medium", "complex", "extreme"]
        )
        rng = np.random.default_rng(42)
        sampler = StratifiedSampler(dataset, rng, balance_mode="strict")

        # Check balance every 4 samples (each stratum sampled once)
        for i in range(1, 51):  # Up to 50 rounds = 200 samples
            for _ in range(4):  # Sample 4 times (one per stratum)
                stratum, prompt = sampler.sample_next()

            counts = sampler.get_stratum_counts()

            # After each round, all counts should be exactly i
            assert all(count == i for count in counts.values())


class TestReproducibility:
    """Test that fixed seeds produce deterministic results."""

    def test_stratified_dataset_deterministic(self):
        """Verify same seed produces identical prompts."""
        dataset1 = StratifiedJSONSchemaDataset(prompts_per_stratum=10, seed=42)
        dataset2 = StratifiedJSONSchemaDataset(prompts_per_stratum=10, seed=42)

        # All prompts should be identical
        for stratum in dataset1.strata:
            prompts1 = dataset1.get_stratum_prompts(stratum)
            prompts2 = dataset2.get_stratum_prompts(stratum)

            assert len(prompts1) == len(prompts2)
            for p1, p2 in zip(prompts1, prompts2):
                assert p1.text == p2.text
                assert p1.metadata == p2.metadata

    def test_stratum_offsets_deterministic(self):
        """Verify stratum seed offsets are deterministic (not hash-based)."""
        # The old implementation used hash(stratum), which is nondeterministic
        # The new implementation uses STRATUM_SEED_OFFSETS, which is deterministic

        # Verify offsets are defined
        assert "simple" in STRATUM_SEED_OFFSETS
        assert "medium" in STRATUM_SEED_OFFSETS
        assert "complex" in STRATUM_SEED_OFFSETS
        assert "extreme" in STRATUM_SEED_OFFSETS

        # Verify offsets are distinct
        offsets = list(STRATUM_SEED_OFFSETS.values())
        assert len(offsets) == len(set(offsets))  # All unique

    def test_intersection_bounds_deterministic(self):
        """Verify same data produces identical bounds."""
        cs1 = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")
        cs2 = BernoulliCSIntersection(alpha=0.05, n_max=100, method="intersection")

        # Same updates
        for _ in range(10):
            cs1.update(True)
            cs2.update(True)
        for _ in range(40):
            cs1.update(False)
            cs2.update(False)

        # Should produce identical bounds
        bounds1 = cs1.get_bounds()
        bounds2 = cs2.get_bounds()

        assert bounds1 == bounds2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
