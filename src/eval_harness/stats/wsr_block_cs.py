"""Hedged betting confidence sequence for iid bounded [0,1] observations.

Follows Waudby-Smith & Ramdas (2023), "Estimating means of bounded random
variables by betting". For each mean-candidate m on a grid, two capital
processes are maintained:

    K+_t(m) = prod_{i<=t} (1 + lam_i(m) * (X_i - m))
    K-_t(m) = prod_{i<=t} (1 - lam_i(m) * (X_i - m))

with a predictable bet size lam_i (a function of past observations only),
truncated so capitals stay positive. Under the true mean, each capital is a
nonnegative martingale, so by Ville's inequality the hedged capital
(K+ + K-)/2 exceeds 1/alpha with probability at most alpha at ANY time.
The confidence sequence is the set of m not yet rejected.

Intended use in this project: the per-BLOCK means of a round-robin
stratified stream (one draw per stratum per block) are iid bounded
variables with mean p*, so this CS gives PROVABLE anytime-validity for the
mixture failure rate under stratified sampling — and adapts to the small
between-block variance that stratification creates.
"""

import numpy as np


class WSRBlockCS:
    """Anytime-valid CS for the mean of iid observations in [0, 1]."""

    def __init__(self, alpha: float = 0.05, c: float = 0.75,
                 grid_size: int = 1000):
        self.alpha = alpha
        self.c = c
        self.grid = np.linspace(0.0005, 0.9995, grid_size)
        self.t = 0
        self.mean = 0.5       # running mean (prior guess 1/2)
        self.sq = 0.25        # running sum of squared deviations (prior 1/4)
        self.log_kp = np.zeros_like(self.grid)
        self.log_km = np.zeros_like(self.grid)

    def update(self, x: float):
        """Update with one observation x in [0, 1]."""
        if not 0.0 <= x <= 1.0:
            raise ValueError(f"observation {x} outside [0, 1]")
        self.t += 1
        sigma2 = self.sq / self.t
        lam = np.sqrt(2 * np.log(2 / self.alpha)
                      / (sigma2 * self.t * np.log(self.t + 1) + 1e-12))
        lam_p = np.minimum(lam, self.c / np.maximum(self.grid, 1e-6))
        lam_m = np.minimum(lam, self.c / np.maximum(1 - self.grid, 1e-6))
        self.log_kp += np.log1p(lam_p * (x - self.grid))
        self.log_km += np.log1p(-lam_m * (x - self.grid))
        # Running stats update AFTER betting keeps lambda predictable.
        self.sq += (x - self.mean) ** 2
        self.mean += (x - self.mean) / (self.t + 1)

    def get_bounds(self) -> tuple:
        """Current confidence interval (lower, upper)."""
        if self.t == 0:
            return 0.0, 1.0
        thresh = np.log(1 / self.alpha)
        hedged = np.logaddexp(self.log_kp, self.log_km) - np.log(2)
        alive = self.grid[hedged < thresh]
        if len(alive) == 0:
            return 0.0, 1.0
        # When the alive set touches a grid edge, extend the bound to the
        # true endpoint: means outside the grid range (e.g. exactly 0 for
        # an all-zeros stream) must not be silently excluded.
        lo = 0.0 if alive[0] == self.grid[0] else float(alive[0])
        hi = 1.0 if alive[-1] == self.grid[-1] else float(alive[-1])
        return lo, hi
