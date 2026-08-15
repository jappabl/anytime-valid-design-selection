"""Tests for the practitioner Certifier wrapper.

The underlying statistics are validated elsewhere; these tests cover
the wrapper contract: equivalence with direct class usage, block
gating, verdict semantics, stickiness, and replayability.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.certify import Certifier
from eval_harness.stats.stratified_ui_cs import StratifiedUICS
from eval_harness.stats.wsr_block_cs import WSRBlockCS


def _stream(seed, n, p=0.3, k=4):
    rng = np.random.default_rng(seed)
    return [((i % k), bool(rng.random() < p)) for i in range(n)]


def test_mixture_bounds_match_direct_class():
    c = Certifier(tau=0.2, alpha=0.05, k=4)
    ref = StratifiedUICS(k=4, alpha=0.05)
    for s, y in _stream(0, 200):
        c.update(y, stratum=s)
        ref.update(s, y)
    assert c.bounds() == ref.get_bounds()


def test_wsr_bounds_match_direct_class():
    c = Certifier(tau=0.2, alpha=0.05, k=4, method="wsr")
    ref = WSRBlockCS(alpha=0.05)
    outcomes = _stream(1, 200)
    for s, y in outcomes:
        c.update(y, stratum=s)
    for b in range(len(outcomes) // 4):
        block = [int(outcomes[4 * b + i][1]) for i in range(4)]
        ref.update(float(np.mean(block)))
    assert c.bounds() == ref.get_bounds()


def test_no_decision_before_min_samples_or_mid_block():
    c = Certifier(tau=0.5, alpha=0.05, k=4)
    for i, (s, _) in enumerate(_stream(2, 19)):
        assert c.update(True, stratum=s) == "CONTINUE"


def test_unsafe_verdict_on_all_failures():
    c = Certifier(tau=0.2, alpha=0.05, k=1)
    verdicts = [c.update(True) for _ in range(60)]
    assert verdicts[-1] == "UNSAFE"


def test_safe_verdict_on_all_passes():
    c = Certifier(tau=0.2, alpha=0.05, k=1)
    verdicts = [c.update(False) for _ in range(400)]
    assert verdicts[-1] == "SAFE"


def test_decision_is_sticky():
    c = Certifier(tau=0.2, alpha=0.05, k=1)
    while c.update(True) != "UNSAFE":
        pass
    for _ in range(50):
        assert c.update(False) == "UNSAFE"


def test_replay_reconstructs_state():
    c1 = Certifier(tau=0.25, alpha=0.05, k=4)
    for s, y in _stream(3, 300):
        c1.update(y, stratum=s)
    c2 = Certifier(tau=0.25, alpha=0.05, k=4)
    for s, y in c1.state():
        c2.update(y, stratum=s)
    assert c1.bounds() == c2.bounds()
    assert c1.decision == c2.decision
    assert c1.n == c2.n


def test_warmstart_matches_cold_when_uninformative():
    cold = Certifier(tau=0.2, alpha=0.05, k=4)
    warm = Certifier(tau=0.2, alpha=0.05, k=4,
                     prior_rates=[0.3, 0.3, 0.3, 0.3], prior_n=[200] * 4)
    for s, y in _stream(4, 400, p=0.3):
        cold.update(y, stratum=s)
        warm.update(y, stratum=s)
    lo_c, hi_c = cold.bounds()
    lo_w, hi_w = warm.bounds()
    # A well-centered strong prior can only be informative: interval no
    # wider than cold's beyond numerical slack.
    assert (hi_w - lo_w) <= (hi_c - lo_c) + 1e-9


def test_wsr_requires_multiple_strata():
    with pytest.raises(ValueError):
        Certifier(tau=0.2, k=1, method="wsr")


def test_warmstart_requires_mixture():
    with pytest.raises(ValueError):
        Certifier(tau=0.2, k=4, method="wsr", prior_rates=[0.1] * 4)


def test_stratum_out_of_range():
    c = Certifier(tau=0.2, k=2)
    with pytest.raises(ValueError):
        c.update(True, stratum=2)


def test_recommend_covers_regimes():
    assert "single-stream" in Certifier.recommend(2.0, 0.05)
    assert "wsr" in Certifier.recommend(200.0, 0.02)
    assert "warm-start" in Certifier.recommend(200.0, 0.02, recurring=True)


def test_auto_select_dispatch():
    hot = [(i % 4, (i % 4 == 3) and (i % 8 == 3)) for i in range(80)]
    mild = [(i % 4, i % 5 == 0) for i in range(160)]
    assert Certifier.auto_select(hot)[0] == "wsr"
    assert Certifier.auto_select(mild)[0] == "single"


def test_auto_select_zero_stratum_guarded():
    pilot = [(i % 4, i % 4 == 3) for i in range(80)]
    kind, k = Certifier.auto_select(pilot)
    assert kind == "wsr" and k == 4


def test_update_cost_flat_in_history_length():
    import time
    c = Certifier(tau=0.9, alpha=0.05, k=1)
    xs = list(np.random.default_rng(9).random(2400) < 0.3)
    for y in xs[:200]:
        c.update(bool(y))
    t0 = time.perf_counter()
    for y in xs[200:400]:
        c.update(bool(y))
    early = time.perf_counter() - t0
    for y in xs[400:2200]:
        c.update(bool(y))
    t0 = time.perf_counter()
    for y in xs[2200:2400]:
        c.update(bool(y))
    late = time.perf_counter() - t0
    assert late < 3 * early + 0.05
    assert late / 200 < 0.002


def test_fixed_wrapper_decisions_match_direct_class():
    from eval_harness.stats.stratified_ui_cs import StratifiedUICS as S
    rng = np.random.default_rng(12)
    xs = [bool(r < 0.35) for r in rng.random(400)]
    c = Certifier(tau=0.2, alpha=0.05, k=1)
    ref = S(k=1, weights=[1.0], alpha=0.05)
    ref_decision = None
    for n, y in enumerate(xs, 1):
        v = c.update(y)
        ref.update(0, y)
        if ref_decision is None and n >= 20 and n % 1 == 0:
            if ref.rejects_le(0.2):
                ref_decision = "UNSAFE"
            elif ref.rejects_ge(0.2):
                ref_decision = "SAFE"
        assert v == (ref_decision or "CONTINUE")
