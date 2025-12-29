"""Time-uniform confidence sequences using intersection with α-splitting.

Maintains multiple valid bounds in parallel and takes the intersection,
avoiding data-dependent switching while still adapting to variance.

Based on the principle:
- If CI_A covers with prob ≥ 1 - α/2
- And CI_B covers with prob ≥ 1 - α/2
- Then CI_A ∩ CI_B covers with prob ≥ 1 - α

This is SAFE (no data-dependent switching) and ADAPTIVE (automatically
uses tighter bound when variance is low).
"""

import math
from typing import Literal


class BernoulliCSIntersection:
    """Time-uniform CS using intersection of Hoeffding + Bernstein.

    Maintains two bounds in parallel with α-splitting:
    1. Hoeffding (conservative, works everywhere)
    2. Empirical Bernstein (adaptive, tighter for low variance)

    The reported CI is the INTERSECTION, which:
    - Maintains validity (both bounds are valid)
    - Automatically picks tighter when variance is low
    - Avoids data-dependent switching bugs
    """

    def __init__(
        self,
        alpha: float = 0.05,
        n_max: int = 1000,
        method: Literal["hoeffding", "intersection"] = "intersection",
    ):
        """Initialize intersection-based confidence sequence.

        Args:
            alpha: Significance level (1 - confidence level)
            n_max: Maximum sample size (budget cap)
            method:
                - "hoeffding": Use only Hoeffding (baseline)
                - "intersection": Use Hoeffding ∩ Bernstein (optimized)
        """
        if not 0 < alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        if n_max <= 0:
            raise ValueError(f"n_max must be positive, got {n_max}")

        self.alpha = alpha
        self.n_max = n_max
        self.method = method
        self.trials = 0
        self.failures = 0
        self.successes = 0

        # Alpha-splitting for intersection
        if method == "intersection":
            self.alpha_hoeffding = alpha / 2
            self.alpha_bernstein = alpha / 2
        else:
            self.alpha_hoeffding = alpha
            self.alpha_bernstein = alpha  # Unused

    def update(self, outcome: bool) -> tuple[float, float]:
        """Update with new outcome and return current bounds.

        Args:
            outcome: True if failure, False if success

        Returns:
            Tuple of (lower_bound, upper_bound) for failure probability p
        """
        if self.trials >= self.n_max:
            raise ValueError(f"Already at n_max={self.n_max}")

        self.trials += 1
        if outcome:
            self.failures += 1
        else:
            self.successes += 1

        return self.get_bounds()

    def get_bounds(self) -> tuple[float, float]:
        """Get current two-sided confidence bounds.

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if self.trials == 0:
            return (0.0, 1.0)

        if self.method == "hoeffding":
            return self._hoeffding_bounds(self.alpha_hoeffding)
        else:  # intersection
            # Get both bounds with α/2 each
            ci_h = self._hoeffding_bounds(self.alpha_hoeffding)
            ci_b = self._bernstein_bounds(self.alpha_bernstein)

            # INTERSECTION (automatically picks tighter)
            lower = max(ci_h[0], ci_b[0])
            upper = min(ci_h[1], ci_b[1])

            return (lower, upper)

    def get_upper_bound(self) -> float:
        """Get one-sided upper bound (for certification).

        More efficient than two-sided when only certifying p ≤ threshold.

        Returns:
            Upper bound on failure probability p
        """
        if self.trials == 0:
            return 1.0

        if self.method == "hoeffding":
            return self._hoeffding_upper(self.alpha_hoeffding)
        else:  # intersection
            # Get both one-sided uppers with α/2 each
            u_h = self._hoeffding_upper(self.alpha_hoeffding)
            u_b = self._bernstein_upper(self.alpha_bernstein)

            # Take minimum (tighter)
            return min(u_h, u_b)

    def _hoeffding_bounds(self, alpha: float) -> tuple[float, float]:
        """Two-sided Hoeffding bounds with stitching.

        Args:
            alpha: Significance level for this bound

        Returns:
            Tuple of (lower, upper)
        """
        n = self.trials
        p_hat = self.failures / n

        # Stitching allocation
        delta_n = alpha / (n * (n + 1))

        # Hoeffding radius
        log_term = math.log(2.0 / delta_n)
        epsilon = math.sqrt(log_term / (2.0 * n))

        lower = max(0.0, p_hat - epsilon)
        upper = min(1.0, p_hat + epsilon)

        return (lower, upper)

    def _hoeffding_upper(self, alpha: float) -> float:
        """One-sided Hoeffding upper bound with stitching.

        Args:
            alpha: Significance level for this bound

        Returns:
            Upper bound on p
        """
        n = self.trials
        p_hat = self.failures / n

        # Stitching allocation
        delta_n = alpha / (n * (n + 1))

        # One-sided Hoeffding (no factor of 2 in exp)
        log_term = math.log(1.0 / delta_n)  # Note: 1/δ not 2/δ
        epsilon = math.sqrt(log_term / (2.0 * n))

        upper = min(1.0, p_hat + epsilon)

        return upper

    def _bernstein_bounds(self, alpha: float) -> tuple[float, float]:
        """Two-sided empirical Bernstein bounds with stitching.

        Uses actual variance V̂ = p̂(1-p̂) to get tighter bounds
        when variance is low (p near 0 or 1).

        Args:
            alpha: Significance level for this bound

        Returns:
            Tuple of (lower, upper)
        """
        n = self.trials
        p_hat = self.failures / n
        var_hat = p_hat * (1 - p_hat)

        # Stitching allocation
        delta_n = alpha / (n * (n + 1))

        # Empirical Bernstein radius (per Maurer & Pontil 2009)
        log_term = math.log(2.0 / delta_n)

        # Two terms: variance term + range term
        # Range term uses (7/3) constant and (n-1) denominator
        var_term = math.sqrt(2 * var_hat * log_term / n)
        range_term = (7/3) * log_term / (n - 1) if n > 1 else log_term
        epsilon = var_term + range_term

        lower = max(0.0, p_hat - epsilon)
        upper = min(1.0, p_hat + epsilon)

        return (lower, upper)

    def _bernstein_upper(self, alpha: float) -> float:
        """One-sided empirical Bernstein upper bound with stitching.

        Args:
            alpha: Significance level for this bound

        Returns:
            Upper bound on p
        """
        n = self.trials
        p_hat = self.failures / n
        var_hat = p_hat * (1 - p_hat)

        # Stitching allocation
        delta_n = alpha / (n * (n + 1))

        # One-sided Bernstein (per Maurer & Pontil 2009)
        log_term = math.log(1.0 / delta_n)  # Note: 1/δ not 2/δ

        # Two terms: variance term + range term
        # Range term uses (7/3) constant and (n-1) denominator
        var_term = math.sqrt(2 * var_hat * log_term / n)
        range_term = (7/3) * log_term / (n - 1) if n > 1 else log_term
        epsilon = var_term + range_term

        upper = min(1.0, p_hat + epsilon)

        return upper

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
            f"BernoulliCSIntersection(n={self.trials}, failures={self.failures}, "
            f"p̂={self.point_estimate:.4f}, CI=[{lower:.4f}, {upper:.4f}], "
            f"width={self.width:.4f}, method={self.method}, α={self.alpha})"
        )


# Alias for backward compatibility
BernoulliCS = BernoulliCSIntersection
