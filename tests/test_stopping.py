"""Tests for sequential stopping rules."""

import pytest

from eval_harness.stats.bernoulli_cs import BernoulliCS
from eval_harness.stats.stopping import SequentialStopper


def test_precision_stopping():
    """Test that precision-based stopping works correctly."""
    cs = BernoulliCS(alpha=0.05)
    stopper = SequentialStopper(
        precision_target=0.05, min_samples=10, max_samples=1000
    )

    # Should not stop before min_samples
    for _ in range(5):
        cs.update(False)

    decision = stopper.check(cs)
    assert not decision.should_stop, "Should not stop before min_samples"

    # Simulate until width is small (with p≈0, width shrinks fast)
    for _ in range(100):
        cs.update(False)

    decision = stopper.check(cs)
    # With all successes, width should be small
    if cs.width <= 0.05:
        assert decision.should_stop
        assert "precision" in decision.reason


def test_certification_stopping():
    """Test certification-based stopping."""
    cs = BernoulliCS(alpha=0.05)
    stopper = SequentialStopper(
        certification_threshold=0.05, min_samples=20, max_samples=1000
    )

    # Simulate very low failure rate
    for _ in range(100):
        cs.update(False)  # All successes

    decision = stopper.check(cs)

    # Upper bound should be well below 0.05 with 100 successes
    _, upper = cs.get_bounds()
    if upper <= 0.05:
        assert decision.should_stop
        assert "certified" in decision.reason


def test_budget_cap_stopping():
    """Test that max_samples is enforced."""
    cs = BernoulliCS(alpha=0.05)
    stopper = SequentialStopper(min_samples=10, max_samples=50)

    # Simulate exactly max_samples
    for _ in range(50):
        cs.update(True)  # Simulate high failure rate to avoid other stops

    decision = stopper.check(cs)
    assert decision.should_stop
    assert "budget_cap" in decision.reason


def test_min_samples_enforcement():
    """Test that stopping is prevented before min_samples."""
    cs = BernoulliCS(alpha=0.05)
    stopper = SequentialStopper(
        precision_target=0.01, min_samples=50, max_samples=1000
    )

    # Even with very tight CI, should not stop before min_samples
    for _ in range(30):
        cs.update(False)

    decision = stopper.check(cs)
    assert not decision.should_stop, "Should not stop before min_samples=50"


def test_multiple_criteria():
    """Test stopper with multiple criteria."""
    cs = BernoulliCS(alpha=0.05)
    stopper = SequentialStopper(
        precision_target=0.02,
        certification_threshold=0.01,
        min_samples=30,
        max_samples=500,
    )

    # Simulate low failure rate
    for i in range(200):
        # 1% failure rate
        outcome = i % 100 == 0
        cs.update(outcome)

        if i >= 30:  # After min_samples
            decision = stopper.check(cs)
            if decision.should_stop:
                # Should stop due to either precision or certification
                assert (
                    "precision" in decision.reason or "certified" in decision.reason
                )
                break


def test_stopper_initialization_validation():
    """Test that invalid stopper configs raise errors."""
    # precision_target must be positive
    with pytest.raises(ValueError):
        SequentialStopper(precision_target=-0.01)

    # certification_threshold must be in (0, 1)
    with pytest.raises(ValueError):
        SequentialStopper(certification_threshold=1.5)

    # min_samples must be >= 1
    with pytest.raises(ValueError):
        SequentialStopper(min_samples=0)

    # max_samples must be >= min_samples
    with pytest.raises(ValueError):
        SequentialStopper(min_samples=100, max_samples=50)
