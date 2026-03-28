"""Tests for RiskManager."""

from __future__ import annotations

from datetime import datetime, timezone

from src.risk.manager import RiskConfig, RiskManager
from src.utils.types import MarketState, OrderSide, PortfolioState, TradeDecision


def _market(mid: str, entities: list[str]) -> MarketState:
    return MarketState(
        condition_id=mid,
        question="q",
        description="d",
        tags=["Politics"],
        entities=entities,
        mid_price=0.5,
        spread=0.02,
        volume_24h=10000,
        liquidity=2000,
        best_bid_yes=0.49,
        best_ask_yes=0.51,
        bid_depth_usd=100,
        ask_depth_usd=100,
        last_updated=datetime.now(timezone.utc),
    )


def _decision(market_id: str, size: float) -> TradeDecision:
    return TradeDecision(
        market_id=market_id,
        edge=0.1,
        side=OrderSide.BUY,
        size_usd=size,
        limit_price=0.5,
        kelly_fraction=0.1,
        reason="test",
        timestamp=datetime.now(timezone.utc),
        executed=False,
    )


def test_approve_ok() -> None:
    r = RiskManager(RiskConfig(max_total_exposure_usd=1000))
    m = _market("a", ["biden"])
    ok, reason = r.approve(m, _decision("a", 100), PortfolioState())
    assert ok and reason == "ok"


def test_drawdown_rejects() -> None:
    r = RiskManager()
    p = PortfolioState(unrealized_pnl=-400.0)
    ok, reason = r.approve(_market("a", []), _decision("a", 10), p)
    assert not ok and reason == "drawdown_guard"


def test_sell_at_total_exposure_cap_reduces_approved() -> None:
    r = RiskManager(RiskConfig(max_total_exposure_usd=1000))
    m = _market("a", ["biden"])
    sell = TradeDecision(
        market_id="a",
        edge=-0.1,
        side=OrderSide.SELL,
        size_usd=1000.0,
        limit_price=0.5,
        kelly_fraction=0.1,
        reason="test",
        timestamp=datetime.now(timezone.utc),
        executed=False,
    )
    p = PortfolioState(positions={"a": 1000.0}, total_exposure=1000.0)
    ok, reason = r.approve(m, sell, p)
    assert ok and reason == "ok"


def test_cluster_cap() -> None:
    r = RiskManager(RiskConfig(max_cluster_exposure_usd=150, enable_correlation_checks=True))
    p = PortfolioState(positions={"m2": 100.0}, total_exposure=100.0)
    r._market_entities["m2"] = {"biden", "senate"}  # noqa: SLF001
    m = _market("m1", ["biden", "house"])
    ok, reason = r.approve(m, _decision("m1", 100), p)
    assert not ok and reason == "max_cluster_exposure"
