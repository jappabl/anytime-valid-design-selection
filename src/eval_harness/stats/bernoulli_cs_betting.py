"""
Betting-based one-sided confidence sequences for Bernoulli outcomes.

Implements anytime-valid one-sided confidence bounds via e-value inversion,
following Ville's inequality for sequential hypothesis testing.

Reference:
    Howard, S. R., Ramdas, A., Ramd as, A., McAuliffe, J., & Sekhon, J. (2021).
    Time-uniform, nonparametric, nonasymptotic confidence sequences.
    The Annals of Statistics, 49(2), 1055-1080.

Design:
    - Uses conjugate Beta priors for predictable betting
    - Constructs e-value (wealth process) via sequential likelihood ratios
    - Inverts e-value to get confidence bounds
    - Time-uniform via Ville's inequality (no stitching needed)
    - All computations in log-space for numerical stability

Key properties:
    - One-sided bounds (UCB for certification p < τ, LCB for p > τ)
    - Tighter than Hoeffding+stitching (no union bound overhead)
    - Anytime-valid at all stopping times
"""

import numpy as np
from typing import Tuple


class BernoulliCSBetting:
    """One-sided betting-based confidence sequence for Bernoulli parameter.

    Uses conjugate Beta(1,1) prior (uniform) for simplicity and audit-safety.
    Constructs e-value via predictive likelihood ratio, inverts to get bounds.

    For certification stopping:
        - UCB: Test H₀: p ≥ p₀, certify safe when UCB ≤ τ
        - LCB: Test H₀: p ≤ p₀, certify unsafe when LCB > τ
    """

    def __init__(self, alpha: float = 0.05, n_max: int = 1000):
        """
        Args:
            alpha: Confidence level (error probability)
            n_max: Maximum samples (for bound computation grid)
        """
        self.alpha = alpha
        self.n_max = n_max

        # State
        self.trials = 0
        self.failures = 0  # Number of failures (bad outcomes)

        # Beta prior parameters (conjugate for Bernoulli)
        self.prior_alpha = 1.0  # Uniform Beta(1,1)
        self.prior_beta = 1.0

        # Log threshold for e-value comparisons (log(1/α))
        self.log_threshold = np.log(1.0 / alpha)

    def update(self, is_failure: bool):
        """Update with one observation.

        Args:
            is_failure: True if failure, False if success
        """
        self.trials += 1
        if is_failure:
            self.failures += 1

    def _log_e_value_upper(self, p_null: float) -> float:
        """Compute log e-value for testing H₀: p ≥ p_null (upper bound test).

        Uses Beta-Bernoulli conjugate predictive probabilities.
        Working in log-space avoids numerical overflow.

        Args:
            p_null: Null hypothesis value

        Returns:
            Log e-value under H₀: p ≥ p_null
        """
        if self.trials == 0:
            return 0.0  # log(1) = 0

        # Bound p_null away from 0 and 1 for numerical stability
        p_null = np.clip(p_null, 1e-10, 1 - 1e-10)

        log_e_value = 0.0
        a = self.prior_alpha
        b = self.prior_beta

        # Reconstruct sequence (order doesn't matter for product)
        failures_so_far = 0
        successes_so_far = 0

        for t in range(self.trials):
            post_a = a + failures_so_far
            post_b = b + successes_so_far
            normalizer = post_a + post_b

            pred_fail = post_a / normalizer
            pred_success = post_b / normalizer

            # Actual outcome
            if failures_so_far < self.failures:
                # Failure observed
                log_likelihood_ratio = np.log(pred_fail) - np.log(p_null)
                failures_so_far += 1
            else:
                # Success observed
                log_likelihood_ratio = np.log(pred_success) - np.log(1 - p_null)
                successes_so_far += 1

            log_e_value += log_likelihood_ratio

        return log_e_value

    def _log_e_value_lower(self, p_null: float) -> float:
        """Compute log e-value for testing H₀: p ≤ p_null (lower bound test).

        Uses inverted outcomes (successes instead of failures).

        Args:
            p_null: Null hypothesis value

        Returns:
            Log e-value under H₀: p ≤ p_null
        """
        if self.trials == 0:
            return 0.0

        # Bound p_null
        p_null = np.clip(p_null, 1e-10, 1 - 1e-10)

        successes = self.trials - self.failures

        log_e_value = 0.0
        a = self.prior_alpha
        b = self.prior_beta

        successes_so_far = 0
        failures_so_far = 0

        for t in range(self.trials):
            post_a = a + failures_so_far
            post_b = b + successes_so_far
            normalizer = post_a + post_b

            pred_fail = post_a / normalizer
            pred_success = post_b / normalizer

            # Successes first (for lower bound test)
            if successes_so_far < successes:
                # Success observed
                log_likelihood_ratio = np.log(pred_success) - np.log(1 - p_null)
                successes_so_far += 1
            else:
                # Failure observed
                log_likelihood_ratio = np.log(pred_fail) - np.log(p_null)
                failures_so_far += 1

            log_e_value += log_likelihood_ratio

        return log_e_value

    def _find_ucb(self) -> float:
        """Find upper confidence bound via e-value inversion.

        UCB(α) = inf{p: log E(p) < log(1/α)}

        Returns:
            Upper confidence bound
        """
        if self.trials == 0:
            return 1.0

        p_hat = self.failures / self.trials

        # Special cases
        if p_hat >= 0.9999:
            return 1.0

        # Check if we can reject at p close to 1
        if self._log_e_value_upper(0.9999) < self.log_threshold:
            return 1.0

        # Binary search: e-value is increasing in p_null on [p_hat, 1],
        # so the rejected region is [ucb, 1]. Invariant: low not rejected,
        # high rejected; both converge to the crossing point.
        low, high = p_hat, 1.0

        for _ in range(100):
            mid = (low + high) / 2
            log_e_val = self._log_e_value_upper(mid)

            if log_e_val >= self.log_threshold:
                # Can reject H₀: p ≥ mid → UCB is below mid
                high = mid
            else:
                # Cannot reject → UCB is above mid
                low = mid

            if high - low < 1e-6:
                break

        return high

    def _find_lcb(self) -> float:
        """Find lower confidence bound via e-value inversion.

        LCB(α) = sup{p: log E(p) < log(1/α)}

        Returns:
            Lower confidence bound
        """
        if self.trials == 0:
            return 0.0

        p_hat = self.failures / self.trials

        # Special cases
        if p_hat <= 0.0001:
            return 0.0

        # Check if we can reject at p close to 0
        if self._log_e_value_lower(0.0001) < self.log_threshold:
            return 0.0

        # Binary search: e-value is decreasing in p_null on [0, p_hat],
        # so the rejected region is [0, lcb]. Invariant: low rejected,
        # high not rejected; both converge to the crossing point.
        low, high = 0.0, p_hat

        for _ in range(100):
            mid = (low + high) / 2
            log_e_val = self._log_e_value_lower(mid)

            if log_e_val >= self.log_threshold:
                # Can reject H₀: p ≤ mid → LCB is above mid
                low = mid
            else:
                # Cannot reject → LCB is below mid
                high = mid

            if high - low < 1e-6:
                break

        return low

    def get_bounds(self) -> Tuple[float, float]:
        """Get current confidence bounds.

        Returns:
            (lower_bound, upper_bound) tuple
        """
        lcb = self._find_lcb()
        ucb = self._find_ucb()
        return (lcb, ucb)

    def get_ucb(self) -> float:
        """Get upper confidence bound only (for Safe certification).

        Returns:
            Upper confidence bound
        """
        return self._find_ucb()

    def get_lcb(self) -> float:
        """Get lower confidence bound only (for Unsafe certification).

        Returns:
            Lower confidence bound
        """
        return self._find_lcb()
