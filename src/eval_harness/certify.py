"""Practitioner-facing certification API.

One class wraps the validated anytime-valid machinery behind the
protocol this project's experiments established: block-gated peeking
(never decide mid-block), certification semantics (UNSAFE if the lower
confidence bound exceeds tau, SAFE if the upper bound is at or below
tau), and optional epsilon-contaminated warm-starting from a prior
epoch. Methods:

- "mixture" (default): the Beta-Bernoulli mixture UI e-process
  (StratifiedUICS); k = 1 gives the single-stream CS, k > 1 the
  stratified product. With prior_rates it becomes the joint
  eps-contaminated transfer prior (TransferPriorJointUICS semantics).
- "wsr": the stratify -> block -> bet reduction (WSRBlockCS on block
  means). Samples are buffered per stratum; a block is consumed
  whenever every stratum has a pending sample, so any arrival order
  that is balanced in the long run works.

Design-map guidance (which method to pick) is exposed as
``recommend()`` and returns a string; it encodes FINDINGS.md's
four-regime map and is advisory only.
"""

from __future__ import annotations

import numpy as np

from .stats.stratified_ui_cs import StratifiedUICS
from .stats.wsr_block_cs import WSRBlockCS

_MIN_N = 20


class _TransferPriorJointUICS(StratifiedUICS):
    """Joint eps-contaminated transfer prior (mirrors the validated
    implementation in scripts/run_warmstart_joint.py)."""

    def __init__(self, prior_rates, kappa, k, alpha, eps):
        super().__init__(k=k, alpha=alpha)
        pr = np.clip(np.asarray(prior_rates, dtype=float), 1e-3, 1 - 1e-3)
        kap = np.broadcast_to(np.asarray(kappa, dtype=float), (k,))
        self._a = np.stack([1.0 + kap * pr, np.ones(k)])
        self._b = np.stack([1.0 + kap * (1 - pr), np.ones(k)])
        self._logw = np.log(np.array([1 - eps, eps]))
        self._cf = np.zeros((2, k))
        self._cs = np.zeros((2, k))
        self._logm_total = np.zeros(2)

    def update(self, stratum, is_failure):
        i = stratum
        a = self._a[:, i] + self._cf[:, i]
        b = self._b[:, i] + self._cs[:, i]
        pred_fail = a / (a + b)
        p_obs = pred_fail if is_failure else 1 - pred_fail
        lw = self._logw + self._logm_total
        lw = lw - np.logaddexp.reduce(lw)
        mix_pred = float(np.exp(np.logaddexp.reduce(lw + np.log(p_obs))))
        self.log_pred += float(np.log(max(mix_pred, 1e-300)))
        self._logm_total += np.log(p_obs)
        if is_failure:
            self._cf[:, i] += 1
            self.f[i] += 1
        else:
            self._cs[:, i] += 1
            self.s[i] += 1


class Certifier:
    """Anytime-valid failure-rate certifier with block-gated stopping.

    Parameters
    ----------
    tau : float
        Certification threshold on the (weighted) pooled failure rate.
    alpha : float
        Error budget; the SAFE/UNSAFE verdict is wrong with
        probability at most alpha under optional stopping.
    k : int
        Number of strata (1 = unstratified single stream).
    method : {"mixture", "wsr"}
    prior_rates, prior_n : array-like, optional
        Warm start ("mixture" only): per-stratum prior failure-rate
        estimates and the per-stratum sample counts behind them.
    eps : float
        Contamination weight of the uniform component in the warm
        prior (worst-case validity premium log(1/eps) nats total).
    shade : float
        Downward shift applied to the concentrated prior center.
        results_asym_prior.txt: shade=0.015 halves the worst-case
        staleness cost for a ~4% benign premium (drift asymmetry —
        overstated priors are the expensive mistake). Default 0.0
        keeps the unshaded prior; 0.015 is the recommended
        production setting.
    """

    def __init__(self, tau, alpha=0.05, k=1, method="mixture",
                 prior_rates=None, prior_n=None, eps=0.1, shade=0.0):
        if method not in ("mixture", "wsr"):
            raise ValueError(f"unknown method {method!r}")
        if method == "wsr" and k < 2:
            raise ValueError("wsr requires k >= 2 (block means)")
        if prior_rates is not None and method != "mixture":
            raise ValueError("warm start is supported for method='mixture'")
        self.tau = float(tau)
        self.alpha = float(alpha)
        self.k = int(k)
        self.method = method
        self.n = 0
        self.decision = None
        self._history = []
        if method == "mixture":
            if prior_rates is not None:
                kappa = (np.minimum(np.asarray(prior_n, dtype=float), 200.0)
                         if prior_n is not None else 200.0)
                shaded = np.asarray(prior_rates, dtype=float) - shade
                self._cs = _TransferPriorJointUICS(
                    shaded, kappa, k=k, alpha=alpha, eps=eps)
            else:
                self._cs = StratifiedUICS(
                    k=k, weights=None if k > 1 else [1.0], alpha=alpha)
        else:
            self._cs = WSRBlockCS(alpha=alpha)
            self._pending = [[] for _ in range(k)]

    def update(self, is_failure, stratum=0):
        """Feed one outcome; returns "SAFE", "UNSAFE", or "CONTINUE".

        Once a decision is returned it is sticky: further updates keep
        counting samples but the verdict never changes (the e-process
        rejection is irreversible by construction).
        """
        if not 0 <= stratum < self.k:
            raise ValueError(f"stratum {stratum} out of range")
        self.n += 1
        self._history.append((stratum, bool(is_failure)))
        if self.method == "mixture":
            self._cs.update(stratum, bool(is_failure))
            complete_block = self.n % self.k == 0
        else:
            self._pending[stratum].append(1 if is_failure else 0)
            complete_block = all(self._pending)
            if complete_block:
                block = [self._pending[i].pop(0) for i in range(self.k)]
                self._cs.update(float(np.mean(block)))
        if self.decision is None and complete_block and self.n >= _MIN_N:
            lo, hi = self.bounds()
            if lo > self.tau:
                self.decision = "UNSAFE"
            elif hi <= self.tau:
                self.decision = "SAFE"
        return self.decision or "CONTINUE"

    def bounds(self):
        """Current anytime-valid confidence bounds on the pooled rate."""
        if self.method == "mixture":
            return self._cs.get_bounds()
        return self._cs.get_bounds()

    def state(self):
        """Replayable state: feed each (stratum, is_failure) back into a
        fresh Certifier to reconstruct this one exactly."""
        return list(self._history)

    @staticmethod
    def auto_select(pilot, floor=10.0):
        """Choose a shipped design from a pilot slice.

        pilot: list of (stratum, is_failure) drawn from the target
        stream (round-robin or any balanced order). Never reuse pilot
        samples in the certification stream. Returns ("single", 1) or
        ("wsr", k): the shipped two-way dispatch on the measured
        stratum heterogeneity ratio (design-map axis; the directed and
        warm-start cells of the map need inputs this API does not take
        from a pilot alone). Shrunk ratio: (max_k p_k + h) / (min_k
        p_k + h) with h = 1/(2 n_k) guarding zero cells; ratio >=
        `floor` selects "wsr", else "single".
        """
        ks = sorted({s for s, _ in pilot})
        rates, h = [], None
        for k in ks:
            ys = [int(y) for s, y in pilot if s == k]
            h = 1.0 / (2 * max(len(ys), 1))
            rates.append(sum(ys) / max(len(ys), 1))
        ratio = (max(rates) + h) / (min(rates) + h)
        return ("wsr", len(ks)) if ratio >= floor else ("single", 1)

    @staticmethod
    def recommend(heterogeneity_ratio, margin, recurring=False):
        """Advisory design-map lookup (FINDINGS.md, fig9)."""
        if recurring:
            return ("warm-start mixture (prior from the previous epoch; "
                    "shade the prior DOWN when uncertain; expect trouble "
                    "if inter-epoch drift exceeds ~0.015 upward)")
        if heterogeneity_ratio < 10:
            return "single-stream mixture (k=1): stratification buys nothing here"
        if margin < 0.04:
            return "wsr blocks: robust at hard margins under heterogeneity"
        return ("directed/single by decision direction (see FINDINGS F5); "
                "wsr blocks are the safe default")
