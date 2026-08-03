"""Tests for betting-based confidence sequences (BernoulliCSBetting)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.bernoulli_cs_betting import BernoulliCSBetting


def _make_cs(n_failures: int, n_successes: int, alpha: float = 0.05) -> BernoulliCSBetting:
    cs = BernoulliCSBetting(alpha=alpha)
    for _ in range(n_failures):
        cs.update(True)
    for _ in range(n_successes):
        cs.update(False)
    return cs


class TestBoundsInvariants:
    def test_prior_bounds_are_vacuous(self):
        cs = BernoulliCSBetting(alpha=0.05)
        assert cs.get_bounds() == (0.0, 1.0)

    def test_bounds_ordered_and_in_unit_interval(self):
        for f, s in [(0, 10), (5, 5), (25, 75), (100, 0)]:
            lcb, ucb = _make_cs(f, s).get_bounds()
            assert 0.0 <= lcb <= ucb <= 1.0

    def test_bounds_contain_empirical_rate(self):
        # log E(p_hat) <= 0 < log(1/alpha), so p_hat is never rejected.
        for f, s in [(1, 99), (10, 90), (25, 75), (50, 50)]:
            cs = _make_cs(f, s)
            p_hat = f / (f + s)
            lcb, ucb = cs.get_bounds()
            assert lcb <= p_hat <= ucb

    def test_bounds_nonvacuous_at_moderate_n(self):
        # Regression: inverted binary search returned (0.0, 1.0) here.
        lcb, ucb = _make_cs(25, 75).get_bounds()
        assert lcb > 0.0
        assert ucb < 1.0
        assert ucb - lcb < 0.5

    def test_width_shrinks_with_more_data(self):
        # Same empirical rate, four times the data.
        lcb_small, ucb_small = _make_cs(10, 40).get_bounds()
        lcb_large, ucb_large = _make_cs(40, 160).get_bounds()
        assert (ucb_large - lcb_large) < (ucb_small - lcb_small)

    def test_smaller_alpha_gives_wider_bounds(self):
        lcb_5, ucb_5 = _make_cs(25, 75, alpha=0.05).get_bounds()
        lcb_1, ucb_1 = _make_cs(25, 75, alpha=0.01).get_bounds()
        assert lcb_1 <= lcb_5
        assert ucb_1 >= ucb_5

    def test_one_sided_accessors_match_two_sided(self):
        cs = _make_cs(25, 75)
        lcb, ucb = cs.get_bounds()
        assert cs.get_lcb() == pytest.approx(lcb)
        assert cs.get_ucb() == pytest.approx(ucb)

    def test_determinism(self):
        assert _make_cs(25, 75).get_bounds() == _make_cs(25, 75).get_bounds()


class TestTimeUniformCoverage:
    def test_coverage_at_all_stopping_times(self):
        # Small Monte Carlo smoke test: true p must lie inside the CS at
        # every n along each path. Ville's inequality guarantees the
        # uniform miss probability is at most alpha.
        alpha = 0.05
        n_reps = 50
        n_max = 60
        rng = np.random.default_rng(42)

        for p_true in [0.05, 0.25]:
            misses = 0
            for _ in range(n_reps):
                cs = BernoulliCSBetting(alpha=alpha)
                outcomes = rng.random(n_max) < p_true
                for outcome in outcomes:
                    cs.update(bool(outcome))
                    lcb, ucb = cs.get_bounds()
                    if not (lcb <= p_true <= ucb):
                        misses += 1
                        break
            # Allow slack for Monte Carlo noise at n_reps=50.
            assert misses / n_reps <= alpha + 0.05
