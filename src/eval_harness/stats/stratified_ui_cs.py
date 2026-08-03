"""Union-intersection product e-process for a stratified mixture mean.

Setting: K strata with unknown failure rates p_k, target estimand
p* = sum_k w_k p_k. Each stratum stream is iid Bernoulli(p_k) and carries
a Beta(1,1)-mixture e-process

    E_k(m) = Beta-marginal(f_k, s_k) / (m^{f_k} (1-m)^{s_k}),

a nonnegative martingale when the true rate is m. Because at most one
stratum is sampled per step and the allocation is predictable, the
product  E(m_1..m_K) = prod_k E_k(m_k)  is a martingale under the true
rates for ANY data-dependent allocation across strata.

Composite certification (union-intersection): to reject H0: p* <= tau,
reject when

    inf { prod_k E_k(m_k) : sum_k w_k m_k <= tau } >= 1/alpha.

If H0 is true, the true rate vector lies in the constraint set, the inf
is dominated by the martingale at the true rates, and Ville's inequality
bounds the false-rejection probability by alpha AT EVERY TIME — with no
alpha-splitting across strata. Symmetric for H0: p* >= tau. The
confidence sequence for p* is the set of tau rejected in neither
direction.

The inner optimization is convex: -log lik_k(m) = -f_k log m
- s_k log(1-m) is convex in m, so the boundary problem reduces to a
per-stratum KKT quadratic plus bisection on one Lagrange multiplier.

This is the union-intersection construction of the risk-limiting-audit
literature (Spertus, Sridhar & Stark 2024 use ALPHA supermartingales;
here the factors are Beta-mixture e-values). Implemented for the
audit-mandated state-of-the-art comparison and as the substrate for
GROW allocation (scripts/run_ui_grow.py).
"""

import numpy as np
from scipy.special import betaln


class StratifiedUICS:
    """Union-intersection e-process CS for p* = sum w_k p_k."""

    def __init__(self, k: int = 4, weights=None, alpha: float = 0.05,
                 prior_mode: str = "laplace", warmup: int = 10,
                 kappa: float = 16.0):
        """prior_mode='laplace': fixed Beta(1,1) mixture (default; the
        accumulated predictive product equals the closed-form Beta
        marginal). prior_mode='sharp': after `warmup` observations in a
        stratum, the prior recenters PREDICTABLY on the running estimate
        with `kappa` pseudo-counts — each bet still depends only on the
        past, so the product stays a valid e-process; the recentering
        only changes tightness (reduces mixture overhead)."""
        self.k = k
        self.w = np.full(k, 1.0 / k) if weights is None else np.asarray(weights)
        self.alpha = alpha
        self.log_thresh = np.log(1.0 / alpha)
        self.f = np.zeros(k, dtype=int)
        self.s = np.zeros(k, dtype=int)
        self.prior_mode = prior_mode
        self.warmup = warmup
        self.kappa = kappa
        # Predictable-predictive accumulator (all strata summed) and
        # per-stratum prior state: pseudo-counts + counts since prior set.
        self.log_pred = 0.0
        self._pa = np.ones(k)
        self._pb = np.ones(k)
        self._cf = np.zeros(k, dtype=int)
        self._cs = np.zeros(k, dtype=int)

    def update(self, stratum: int, is_failure: bool):
        i = stratum
        denom = self._pa[i] + self._pb[i] + self._cf[i] + self._cs[i]
        pred_fail = (self._pa[i] + self._cf[i]) / denom
        self.log_pred += float(np.log(pred_fail if is_failure
                                      else 1.0 - pred_fail))
        if is_failure:
            self.f[i] += 1
            self._cf[i] += 1
        else:
            self.s[i] += 1
            self._cs[i] += 1
        if (self.prior_mode == "sharp"
                and self.f[i] + self.s[i] == self.warmup):
            p_hat = (self.f[i] + 0.5) / (self.f[i] + self.s[i] + 1.0)
            self._pa[i] = 1.0 + self.kappa * p_hat
            self._pb[i] = 1.0 + self.kappa * (1.0 - p_hat)
            self._cf[i] = 0
            self._cs[i] = 0

    # ------------------------------------------------------------------
    # e-value machinery
    # ------------------------------------------------------------------

    def _log_marginal(self) -> float:
        """Sum over strata of the log predictive product. In laplace
        mode this equals the closed-form Beta(1,1) marginal (tested);
        the accumulator is authoritative in both modes."""
        return self.log_pred

    def log_e_at(self, m: np.ndarray) -> float:
        """log prod_k E_k(m_k)."""
        m = np.clip(np.asarray(m, dtype=float), 1e-12, 1 - 1e-12)
        loglik = float(np.sum(self.f * np.log(m) + self.s * np.log(1 - m)))
        return self._log_marginal() - loglik

    def _m_of_lambda(self, lam: float) -> np.ndarray:
        """Per-stratum minimizer of -f log m - s log(1-m) + lam*w*m.

        Stationarity: -f/m + s/(1-m) + lam*w = 0. Multiplying by m(1-m):
        a*m^2 - (f + s + a)*m + f = 0  with a = lam*w
        (take the root in [0,1]). Larger lam pushes m down.
        """
        f = self.f.astype(float)
        s = self.s.astype(float)
        n = f + s
        a = lam * self.w
        with np.errstate(divide="ignore", invalid="ignore"):
            mle = np.where(n > 0, f / np.maximum(n, 1), 0.5)
            b = f + s + a
            disc = np.maximum(b * b - 4 * a * f, 0.0)
            sq = np.sqrt(disc)
            r1 = (b - sq) / (2 * a)
            r2 = (b + sq) / (2 * a)
        in1 = (r1 >= 0.0) & (r1 <= 1.0)
        root = np.where(in1, r1, r2)
        m = np.where(np.abs(a) < 1e-12, mle, root)
        return np.clip(m, 1e-12, 1 - 1e-12)

    def _boundary_log_e(self, tau: float) -> float:
        """min log E over {sum w_k m_k = tau}, by bisection on lambda."""
        lo, hi = -1e7, 1e7
        for _ in range(80):
            lam = 0.5 * (lo + hi)
            mix = float(np.sum(self.w * self._m_of_lambda(lam)))
            if mix > tau:
                lo = lam
            else:
                hi = lam
            if hi - lo < 1e-9 * (1 + abs(lam)):
                break
        return self.log_e_at(self._m_of_lambda(0.5 * (lo + hi)))

    def least_favorable(self, tau: float, side: str) -> np.ndarray:
        """The minimizing null vector m* for H0 (used by GROW allocation).

        If the MLE vector lies inside H0 the inf is attained there;
        otherwise m* lies on the boundary {sum w_k m_k = tau}.
        """
        n = self.f + self.s
        p_hat = np.where(n > 0, self.f / np.maximum(n, 1), 0.5)
        mix_hat = float(np.sum(self.w * p_hat))
        inside = mix_hat <= tau if side == "le" else mix_hat >= tau
        if inside:
            return np.clip(p_hat, 1e-12, 1 - 1e-12)
        lo, hi = -1e7, 1e7
        for _ in range(80):
            lam = 0.5 * (lo + hi)
            mix = float(np.sum(self.w * self._m_of_lambda(lam)))
            if mix > tau:
                lo = lam
            else:
                hi = lam
            if hi - lo < 1e-9 * (1 + abs(lam)):
                break
        return self._m_of_lambda(0.5 * (lo + hi))

    def min_log_e(self, tau: float, side: str) -> float:
        """min over H0 of log E; side='le' -> H0={p*<=tau}, 'ge' -> {p*>=tau}.

        The unconstrained minimizer of -log lik is the MLE vector; if it
        lies inside H0 the inf is there (and is <= 0 <= log(1/alpha), so
        no rejection); otherwise the inf is on the boundary.
        """
        n = self.f + self.s
        p_hat = np.where(n > 0, self.f / np.maximum(n, 1), 0.5)
        mix_hat = float(np.sum(self.w * p_hat))
        inside = mix_hat <= tau if side == "le" else mix_hat >= tau
        if inside:
            return self.log_e_at(p_hat)
        return self._boundary_log_e(tau)

    # ------------------------------------------------------------------
    # Decisions and bounds
    # ------------------------------------------------------------------

    def rejects_le(self, tau: float) -> bool:
        """Reject H0: p* <= tau (evidence p* > tau: certify UNSAFE)."""
        return self.min_log_e(tau, "le") >= self.log_thresh

    def rejects_ge(self, tau: float) -> bool:
        """Reject H0: p* >= tau (evidence p* < tau: certify SAFE)."""
        return self.min_log_e(tau, "ge") >= self.log_thresh

    def get_bounds(self, grid_size: int = 400) -> tuple:
        """CS for p*: the taus rejected in neither direction.

        min_log_e(tau,'le') is nonincreasing in tau and min_log_e(tau,'ge')
        nondecreasing, so both rejection regions are half-lines and binary
        search suffices.
        """
        # LCB = sup{tau: rejects_le(tau)} (0 if none rejected)
        lo, hi = 0.0, 1.0
        if not self.rejects_le(0.0):
            lcb = 0.0
        else:
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if self.rejects_le(mid):
                    lo = mid
                else:
                    hi = mid
            lcb = lo
        lo, hi = 0.0, 1.0
        if not self.rejects_ge(1.0):
            ucb = 1.0
        else:
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if self.rejects_ge(mid):
                    hi = mid
                else:
                    lo = mid
            ucb = hi
        return lcb, ucb
