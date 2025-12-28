"""Time-uniform confidence sequences for Bernoulli parameters.

Uses finite-horizon time-uniform bounds (stitching) instead of betting CS.
This approach is:
1. Simpler to implement correctly
2. Easier to audit
3. Valid for peeking up to N_max

Based on Howard et al. (2021) finite-horizon approach.
"""

import math
import numpy as np


class BernoulliCSTimeUniform:
    """Time-uniform confidence sequence for Bernoulli failure probability.

    Uses union bound / stitching approach to provide confidence sequences
    that are valid at ALL stopping times n ≤ N_max.

    This is NOT infinite-horizon (would need betting/mixture for that),
    but for practical evaluation with a budget cap, this is sufficient
    and much simpler to implement correctly.

    Attributes:
        alpha: Significance level (e.g., 0.05 for 95% confidence)
        n_max: Maximum sample size (budget cap)
        trials: Number of samples observed so far
        failures: Number of failures observed
        successes: Number of successes observed
    """

    def __init__(self, alpha: float = 0.05, n_max: int = 1000):
        """Initialize time-uniform confidence sequence.

        Args:
            alpha: Significance level (1 - confidence level). Default 0.05 for 95% CI.
            n_max: Maximum sample size (budget cap). Default 1000.
        """
        if not 0 < alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        if n_max <= 0:
            raise ValueError(f"n_max must be positive, got {n_max}")

        self.alpha = alpha
        self.n_max = n_max
        self.trials = 0
        self.failures = 0
        self.successes = 0

    def update(self, outcome: bool) -> tuple[float, float]:
        """Update with new outcome and return current confidence bounds.

        Args:
            outcome: True if failure, False if success

        Returns:
            Tuple of (lower_bound, upper_bound) for failure probability p
        """
        if self.trials >= self.n_max:
            raise ValueError(f"Already at n_max={self.n_max}, cannot add more samples")

        self.trials += 1
        if outcome:
            self.failures += 1
        else:
            self.successes += 1

        return self.get_bounds()

    def get_bounds(self) -> tuple[float, float]:
        """Compute current time-uniform confidence bounds.

        Uses Hoeffding + union bound (stitching) to get time-uniform bounds.

        For time-uniform validity up to n_max, we use:
        delta_n = alpha / (n * (n+1))  (so sum_{n=1}^{n_max} delta_n ≤ alpha)

        Then use Hoeffding with delta_n:
        P(|p̂ - p| > epsilon_n) ≤ 2 * exp(-2 * n * epsilon_n^2) = delta_n

        Solving for epsilon_n:
        epsilon_n = sqrt(log(2/delta_n) / (2*n))
                  = sqrt(log(2*n*(n+1)/alpha) / (2*n))

        Returns:
            Tuple of (lower_bound, upper_bound) for failure probability p
        """
        if self.trials == 0:
            return (0.0, 1.0)

        n = self.trials
        p_hat = self.failures / n

        # Time-uniform bound using stitching
        # delta_n = alpha / (n * (n+1)) ensures union bound holds
        delta_n = self.alpha / (n * (n + 1))

        # Hoeffding bound with delta_n
        # epsilon_n = sqrt(log(2/delta_n) / (2*n))
        log_term = math.log(2.0 / delta_n)
        epsilon_n = math.sqrt(log_term / (2.0 * n))

        # Compute bounds
        lower = max(0.0, p_hat - epsilon_n)
        upper = min(1.0, p_hat + epsilon_n)

        return (lower, upper)

    @property
    def width(self) -> float:
        """Return current confidence interval width."""
        lower, upper = self.get_bounds()
        return upper - lower

    @property
    def point_estimate(self) -> float:
        """Return empirical failure rate."""
        if self.trials == 0:
            return 0.0
        return self.failures / self.trials

    def __repr__(self) -> str:
        lower, upper = self.get_bounds()
        return (
            f"BernoulliCSTimeUniform(n={self.trials}, failures={self.failures}, "
            f"p̂={self.point_estimate:.4f}, CI=[{lower:.4f}, {upper:.4f}], "
            f"width={self.width:.4f}, α={self.alpha}, n_max={self.n_max})"
        )


# For backward compatibility, create alias
BernoulliCS = BernoulliCSTimeUniform
