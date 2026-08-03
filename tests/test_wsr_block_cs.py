"""Tests for the WSR hedged betting CS on bounded observations."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS


class TestInvariants:
    def test_prior_bounds_are_vacuous(self):
        cs = WSRBlockCS()
        assert cs.get_bounds() == (0.0, 1.0)

    def test_bounds_ordered_and_in_unit_interval(self):
        cs = WSRBlockCS()
        rng = np.random.default_rng(0)
        for x in rng.random(100):
            cs.update(float(x))
            lo, hi = cs.get_bounds()
            assert 0.0 <= lo <= hi <= 1.0

    def test_rejects_out_of_range_observation(self):
        cs = WSRBlockCS()
        with pytest.raises(ValueError):
            cs.update(1.5)
        with pytest.raises(ValueError):
            cs.update(-0.1)

    def test_interval_shrinks_with_data(self):
        cs = WSRBlockCS()
        rng = np.random.default_rng(1)
        for x in (rng.random(30) < 0.2).astype(float):
            cs.update(float(x))
        w30 = np.subtract(*cs.get_bounds()[::-1])
        for x in (rng.random(170) < 0.2).astype(float):
            cs.update(float(x))
        w200 = np.subtract(*cs.get_bounds()[::-1])
        assert w200 < w30

    def test_low_variance_stream_gives_tight_interval(self):
        # Constant observations: interval should collapse around the value.
        cs = WSRBlockCS()
        for _ in range(200):
            cs.update(0.25)
        lo, hi = cs.get_bounds()
        assert lo <= 0.25 <= hi
        assert hi - lo < 0.10

    def test_degenerate_streams_keep_true_endpoint_mean(self):
        # Regression: the grid spans [0.0005, 0.9995]; a true mean of
        # exactly 0 or 1 must not be silently excluded at the edges.
        cs0 = WSRBlockCS()
        cs1 = WSRBlockCS()
        for _ in range(300):
            cs0.update(0.0)
            cs1.update(1.0)
        lo0, hi0 = cs0.get_bounds()
        lo1, hi1 = cs1.get_bounds()
        assert lo0 == 0.0 and hi0 < 0.05
        assert hi1 == 1.0 and lo1 > 0.95

    def test_deterministic(self):
        def run():
            cs = WSRBlockCS()
            rng = np.random.default_rng(2)
            for x in rng.random(50):
                cs.update(float(x))
            return cs.get_bounds()

        assert run() == run()


class TestTimeUniformCoverage:
    def test_coverage_on_iid_block_means(self):
        # Block means of 4 Bernoulli draws with heterogeneous rates:
        # iid across blocks with mean p* = mean(rates).
        rates = np.array([0.0, 0.05, 0.1, 0.4])
        p_star = float(rates.mean())
        alpha = 0.05
        n_reps, n_blocks = 60, 80
        rng = np.random.default_rng(42)
        misses = 0
        for _ in range(n_reps):
            cs = WSRBlockCS(alpha=alpha)
            missed = False
            for _ in range(n_blocks):
                block_mean = float(np.mean(rng.random(4) < rates))
                cs.update(block_mean)
                lo, hi = cs.get_bounds()
                if not (lo <= p_star <= hi):
                    missed = True
                    break
            misses += missed
        assert misses / n_reps <= alpha + 0.05
