"""Tests for the union-intersection product e-process CS."""

import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.fast_bounds import betting_bounds
from eval_harness.stats.stratified_ui_cs import StratifiedUICS


def _load_bench():
    """Load the benchmark script's game-solver functions (script-local)."""
    path = Path(__file__).parent.parent / "scripts" / "run_ui_grow.py"
    src = open(path).read().split("if __name__")[0]
    mod = types.ModuleType("bench")
    mod.__dict__["__file__"] = str(path)
    exec(src, mod.__dict__)
    return mod


class TestUICS:
    def test_k1_reduces_to_plain_betting_cs(self):
        # With one stratum the UI construction IS the betting CS.
        for f, n in [(25, 100), (2, 50), (0, 30)]:
            cs = StratifiedUICS(k=1, weights=[1.0])
            for i in range(n):
                cs.update(0, i < f)
            lo_u, hi_u = cs.get_bounds()
            lo_b, hi_b = betting_bounds(f, n - f, 0.05)
            assert lo_u == pytest.approx(lo_b, abs=2e-3)
            assert hi_u == pytest.approx(hi_b, abs=2e-3)

    def test_bounds_ordered_and_contain_mle_mixture(self):
        rng = np.random.default_rng(0)
        cs = StratifiedUICS(k=4)
        rates = [0.0, 0.05, 0.1, 0.7]
        for step in range(200):
            k = step % 4
            cs.update(k, bool(rng.random() < rates[k]))
        lo, hi = cs.get_bounds()
        n = cs.f + cs.s
        mix_hat = float(np.sum(cs.w * (cs.f / n)))
        assert 0.0 <= lo <= mix_hat <= hi <= 1.0

    def test_min_log_e_monotone_in_tau(self):
        rng = np.random.default_rng(1)
        cs = StratifiedUICS(k=4)
        for step in range(120):
            cs.update(step % 4, bool(rng.random() < 0.2))
        taus = np.linspace(0.01, 0.6, 15)
        le = [cs.min_log_e(t, "le") for t in taus]
        ge = [cs.min_log_e(t, "ge") for t in taus]
        assert all(le[i] >= le[i + 1] - 1e-6 for i in range(len(taus) - 1))
        assert all(ge[i] <= ge[i + 1] + 1e-6 for i in range(len(taus) - 1))

    def test_least_favorable_respects_boundary(self):
        rng = np.random.default_rng(2)
        cs = StratifiedUICS(k=4)
        for step in range(160):
            cs.update(step % 4, bool(rng.random() < [0.0, 0.0, 0.1, 0.7][step % 4]))
        tau = 0.1  # MLE mixture (~0.2) is outside H0: p* <= 0.1
        m = cs.least_favorable(tau, "le")
        assert float(np.sum(cs.w * m)) == pytest.approx(tau, abs=1e-4)

    def test_no_rejection_at_mle(self):
        # log E at the MLE vector is <= 0, so tau at the MLE mixture is
        # never rejected in either direction.
        rng = np.random.default_rng(3)
        cs = StratifiedUICS(k=4)
        for step in range(100):
            cs.update(step % 4, bool(rng.random() < 0.3))
        n = cs.f + cs.s
        mix_hat = float(np.sum(cs.w * (cs.f / n)))
        assert not cs.rejects_le(mix_hat)
        assert not cs.rejects_ge(mix_hat)

    def test_uniform_coverage_smoke(self):
        # Miss = true p* rejected in either direction at ANY check.
        rates = [0.0, 0.05, 0.1, 0.45]
        p_star = float(np.mean(rates))
        rng = np.random.default_rng(42)
        misses = 0
        n_reps = 40
        for _ in range(n_reps):
            cs = StratifiedUICS(k=4)
            missed = False
            for step in range(120):
                cs.update(step % 4, bool(rng.random() < rates[step % 4]))
                if step >= 8 and step % 8 == 0:
                    if (cs.min_log_e(p_star, "le") >= cs.log_thresh
                            or cs.min_log_e(p_star, "ge") >= cs.log_thresh):
                        missed = True
                        break
            misses += missed
        assert misses / n_reps <= 0.05 + 0.08  # MC slack at 40 reps


class TestGameSolver:
    def test_lambda_on_simplex_and_value_beats_uniform(self):
        mod = _load_bench()
        p = np.array([0.004, 0.0, 0.068, 0.736])
        w = np.full(4, 0.25)
        lam, val = mod.game_allocation(p, w, 0.15)
        assert lam.shape == (4,)
        assert float(np.sum(lam)) == pytest.approx(1.0, abs=1e-9)
        assert np.all(lam >= -1e-12)
        # Value at the optimized lam must be >= value at uniform lam
        m_u = mod._inner_min(w.copy(), p, w, 0.15)
        val_uniform = float(np.sum(w * [mod.kl_bern(p[i], m_u[i])
                                        for i in range(4)]))
        assert val >= val_uniform - 1e-6

    def test_inner_min_respects_constraint(self):
        mod = _load_bench()
        p = np.array([0.1, 0.2, 0.3, 0.4])
        w = np.full(4, 0.25)
        lam = np.array([0.4, 0.3, 0.2, 0.1])
        m = mod._inner_min(lam, p, w, 0.15)
        assert float(np.sum(w * m)) == pytest.approx(0.15, abs=1e-4)


class TestInfimumIsAnInfimum:
    """min_log_e must not exceed log E at any point of its own null set."""

    @pytest.mark.parametrize("side,tau", [("le", 0.5), ("ge", 0.5)])
    def test_boundary_inf_bounded_by_feasible_points(self, side, tau):
        # Unequal weights and saturated strata (s = 0 / f = 0) put the
        # constrained optimum exactly on an endpoint of [0, 1].
        sizes = np.array([518384, 408240, 382901, 366539, 134606, 135609,
                          110717, 126286, 117050, 97136, 90050, 84914,
                          2363055], dtype=float)
        w = sizes / sizes.sum()
        f = np.array([4, 5, 3, 3, 1, 3, 1, 0, 0, 0, 1, 0, 2])
        s = np.array([3, 1, 2, 0, 1, 2, 0, 0, 0, 0, 0, 0, 10])
        cs = StratifiedUICS(k=13, weights=w, alpha=0.1)
        for i in range(13):
            for _ in range(int(f[i])):
                cs.update(i, True)
            for _ in range(int(s[i])):
                cs.update(i, False)
        inf_val = cs.min_log_e(tau, side)
        for m_const in (0.5, 0.6, 0.75, 0.9):
            m = np.full(13, m_const)
            mix = float(np.sum(w * m))
            feasible = mix <= tau if side == "le" else mix >= tau
            if feasible:
                assert inf_val <= cs.log_e_at(m) + 1e-9
