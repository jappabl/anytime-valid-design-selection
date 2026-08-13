"""Tests for the Kelly-floored WSR variant (wrapper contract only;
validity is by construction and checked by the artifact's null MC)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.stats.wsr_block_cs import WSRBlockCS
from eval_harness.stats.wsr_kelly_floor import KellyFloorWSR


def _stream(seed, n, p=0.3):
    rng = np.random.default_rng(seed)
    return [float(np.mean(rng.random(4) < p)) for _ in range(n)]


def test_matches_stock_during_warmup():
    a, b = WSRBlockCS(), KellyFloorWSR()
    for x in _stream(0, 10):
        a.update(x)
        b.update(x)
    assert a.get_bounds() == b.get_bounds()


def test_bounds_contain_truth_on_typical_stream():
    cs = KellyFloorWSR()
    for x in _stream(1, 800, p=0.3):
        cs.update(x)
    lo, hi = cs.get_bounds()
    assert lo <= 0.3 <= hi


def test_deterministic_replay():
    xs = _stream(2, 300)
    a, b = KellyFloorWSR(), KellyFloorWSR()
    for x in xs:
        a.update(x)
    for x in xs:
        b.update(x)
    assert a.get_bounds() == b.get_bounds()


def test_interval_no_wider_than_stock_late():
    stock, floor = WSRBlockCS(), KellyFloorWSR()
    for x in _stream(3, 1000, p=0.25):
        stock.update(x)
        floor.update(x)
    ls, hs = stock.get_bounds()
    lf, hf = floor.get_bounds()
    assert (hf - lf) <= (hs - ls) + 1e-9
