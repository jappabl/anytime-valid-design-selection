"""Sequential stopping rules for anytime-valid inference."""

from dataclasses import dataclass
from typing import Optional

from eval_harness.stats.bernoulli_cs import BernoulliCS


@dataclass
class StoppingDecision:
    """Result of evaluating stopping criteria."""

    should_stop: bool
    reason: Optional[str] = None
    achieved_precision: Optional[float] = None
    upper_bound: Optional[float] = None


class SequentialStopper:
    """Manages multiple stopping criteria for sequential experiments.

    Supports:
    - Precision-based stopping: Stop when CI width <= target
    - Certification stopping: Stop when upper bound <= threshold
    - Budget cap: Stop when max samples reached
    - Minimum sample requirement: Prevent premature stopping
    """

    def __init__(
        self,
        precision_target: Optional[float] = None,
        certification_threshold: Optional[float] = None,
        min_samples: int = 30,
        max_samples: int = 2000,
    ):
        """Initialize stopping rule manager.

        Args:
            precision_target: Stop when CI width <= this value (e.g., 0.01)
            certification_threshold: Stop when upper bound <= this value (e.g., 0.01)
            min_samples: Minimum samples before allowing any stopping
            max_samples: Hard budget cap
        """
        self.precision_target = precision_target
        self.certification_threshold = certification_threshold
        self.min_samples = min_samples
        self.max_samples = max_samples

        if precision_target is not None and precision_target <= 0:
            raise ValueError(f"precision_target must be > 0, got {precision_target}")
        if certification_threshold is not None and not (0 < certification_threshold < 1):
            raise ValueError(
                f"certification_threshold must be in (0, 1), got {certification_threshold}"
            )
        if min_samples < 1:
            raise ValueError(f"min_samples must be >= 1, got {min_samples}")
        if max_samples < min_samples:
            raise ValueError(
                f"max_samples ({max_samples}) must be >= min_samples ({min_samples})"
            )

    def check(self, cs: BernoulliCS) -> StoppingDecision:
        """Evaluate all stopping criteria.

        Args:
            cs: Current BernoulliCS state

        Returns:
            StoppingDecision with stop flag and reason
        """
        # Check budget cap first
        if cs.trials >= self.max_samples:
            return StoppingDecision(
                should_stop=True,
                reason=f"budget_cap_n={cs.trials}",
                achieved_precision=cs.width,
            )

        # Require minimum samples
        if cs.trials < self.min_samples:
            return StoppingDecision(should_stop=False)

        lower, upper = cs.get_bounds()

        # Check certification threshold
        if self.certification_threshold is not None:
            if upper <= self.certification_threshold:
                return StoppingDecision(
                    should_stop=True,
                    reason=f"certified_p<={self.certification_threshold:.4f}_at_upper={upper:.4f}",
                    upper_bound=upper,
                    achieved_precision=cs.width,
                )

        # Check precision target
        if self.precision_target is not None:
            if cs.width <= self.precision_target:
                return StoppingDecision(
                    should_stop=True,
                    reason=f"precision_met_width={cs.width:.4f}<={self.precision_target:.4f}",
                    achieved_precision=cs.width,
                )

        return StoppingDecision(should_stop=False)

    def __repr__(self) -> str:
        parts = [f"min_n={self.min_samples}", f"max_n={self.max_samples}"]
        if self.precision_target is not None:
            parts.append(f"precision<={self.precision_target}")
        if self.certification_threshold is not None:
            parts.append(f"certify_p<={self.certification_threshold}")
        return f"SequentialStopper({', '.join(parts)})"
