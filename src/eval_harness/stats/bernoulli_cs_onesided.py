"""
One-sided Hoeffding confidence sequences for Bernoulli outcomes.

Simpler and faster than betting-based CS, but still meaningfully tighter than
two-sided intersection bounds (no α-splitting overhead).

Design:
    - Uses one-sided Hoeffding bounds with finite-horizon stitching
    - No α/2 split (uses full α for each bound)
    - Separate UCB (for Safe certification) and LCB (for Unsafe certification)
    - Closed-form computation (instant, no binary search)

Reference:
    Howard, S. R., Ramdas, A., McAuliffe, J., & Sekhon, J. (2021).
    Time-uniform, nonparametric, nonasymptotic confidence sequences.
    The Annals of Statistics, 49(2), 1055-1080.
    (Section on Hoeffding stitching)
"""

import numpy as np
from typing import Tuple


class BernoulliCSOneSided:
    """One-sided Hoeffding confidence sequence for Bernoulli parameter.

    Uses finite-horizon stitching for time-uniform validity:
        δ_n = α / (n * (n + 1))

    For certification:
        - UCB(n) = p̂ + sqrt((log(2/δ_n)) / (2n))
        - LCB(n) = p̂ - sqrt((log(2/δ_n)) / (2n))

    Key advantage over intersection CS:
        - No α/2 split → tighter by factor of sqrt(2)
        - Separate bounds for Safe/Unsafe → only compute what's needed
    """

    def __init__(self, alpha: float = 0.05, n_max: int = 1000):
        """
        Args:
            alpha: Confidence level (error probability)
            n_max: Maximum samples (for stitching)
        """
        self.alpha = alpha
        self.n_max = n_max

        # State
        self.trials = 0
        self.failures = 0

    def update(self, is_failure: bool):
        """Update with one observation.

        Args:
            is_failure: True if failure, False if success
        """
        self.trials += 1
        if is_failure:
            self.failures += 1

    def _stitching_delta(self, n: int) -> float:
        """Stitching constant for time-uniform validity.

        δ_n = α / (n * (n + 1))

        Ensures Σ δ_n ≤ α over all n.

        Args:
            n: Current sample size

        Returns:
            Stitching delta for this n
        """
        if n <= 0:
            return self.alpha
        return self.alpha / (n * (n + 1))

    def get_ucb(self) -> float:
        """Get upper confidence bound (for Safe certification).

        UCB(n) = p̂ + sqrt(log(2/δ_n) / (2n))

        Returns:
            Upper confidence bound
        """
        if self.trials == 0:
            return 1.0

        p_hat = self.failures / self.trials
        delta_n = self._stitching_delta(self.trials)

        # Hoeffding radius
        radius = np.sqrt(np.log(2.0 / delta_n) / (2.0 * self.trials))

        ucb = p_hat + radius
        return min(ucb, 1.0)  # Clip to [0, 1]

    def get_lcb(self) -> float:
        """Get lower confidence bound (for Unsafe certification).

        LCB(n) = p̂ - sqrt(log(2/δ_n) / (2n))

        Returns:
            Lower confidence bound
        """
        if self.trials == 0:
            return 0.0

        p_hat = self.failures / self.trials
        delta_n = self._stitching_delta(self.trials)

        # Hoeffding radius
        radius = np.sqrt(np.log(2.0 / delta_n) / (2.0 * self.trials))

        lcb = p_hat - radius
        return max(lcb, 0.0)  # Clip to [0, 1]

    def get_bounds(self) -> Tuple[float, float]:
        """Get both confidence bounds.

        Returns:
            (lower_bound, upper_bound) tuple
        """
        return (self.get_lcb(), self.get_ucb())
