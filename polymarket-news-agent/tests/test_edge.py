"""Tests for edge calculation and decay."""

from datetime import datetime, timedelta, timezone

import pytest

from src.scoring.edge import EdgeCalculator, EdgeConfig
from src.utils.types import MarketState


def _market(mid_price: float = 0.6) -> MarketState:
    return MarketState(
        condition_id="m1",
        question="Will X happen?",
        description="desc",
        tags=["Politics"],
        entities=["x"],
        mid_price=mid_price,
        spread=0.02,
        volume_24h=10000,
        liquidity=2000,
        best_bid_yes=mid_price - 0.01,
        best_ask_yes=mid_price + 0.01,
        bid_depth_usd=1000,
        ask_depth_usd=1000,
        last_updated=datetime.now(timezone.utc),
    )


def test_raw_edge_sign() -> None:
    calc = EdgeCalculator()
    assert calc.calculate_raw_edge(0.8, 0.6) == pytest.approx(0.2)
    assert calc.calculate_raw_edge(0.3, 0.6) == pytest.approx(-0.3)


def test_decay_expected_points() -> None:
    calc = EdgeCalculator(EdgeConfig(half_life_seconds=100, decay_floor=0.01))
    raw = 0.2
    e0, f0 = calc.apply_decay(raw, 0)
    e1, f1 = calc.apply_decay(raw, 100)
    e2, f2 = calc.apply_decay(raw, 200)
    assert f0 == pytest.approx(1.0)
    assert f1 == pytest.approx(0.5, rel=1e-3)
    assert f2 == pytest.approx(0.25, rel=1e-3)
    assert e0 == pytest.approx(raw)


def test_adjusted_edge_applies_slippage() -> None:
    calc = EdgeCalculator()
    assert calc.calculate_adjusted_edge(0.2, 0.03) == pytest.approx(0.17)
    assert calc.calculate_adjusted_edge(-0.2, 0.03) == pytest.approx(-0.17)


def test_compute_full_estimate() -> None:
    calc = EdgeCalculator(EdgeConfig(half_life_seconds=60, decay_floor=0.05))
    now = datetime.now(timezone.utc)
    signal_ts = now - timedelta(seconds=60)
    edge = calc.compute(
        market=_market(0.6),
        signal_ids=["s1"],
        prior=0.55,
        posterior=0.8,
        estimated_slippage=0.01,
        signal_timestamp=signal_ts,
        now=now,
    )
    assert edge.market_id == "m1"
    assert edge.raw_edge == pytest.approx(0.2, rel=1e-3)
    assert edge.decay_factor == pytest.approx(0.5, rel=1e-2)
    assert edge.adjusted_edge == pytest.approx(0.09, rel=1e-2)

