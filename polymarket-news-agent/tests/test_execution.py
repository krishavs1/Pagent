"""Tests for trading strategy and paper executor."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.execution.executor import ExecutionConfig, OrderExecutor
from src.execution.strategy import StrategyConfig, TradingStrategy
from src.utils.types import EdgeEstimate, MarketState, PortfolioState


def _market() -> MarketState:
    return MarketState(
        condition_id="m1",
        question="Will event happen?",
        description="desc",
        tags=["Politics"],
        entities=["event"],
        mid_price=0.55,
        spread=0.02,
        volume_24h=20000,
        liquidity=5000,
        best_bid_yes=0.54,
        best_ask_yes=0.56,
        bid_depth_usd=1200,
        ask_depth_usd=1100,
        last_updated=datetime.now(timezone.utc),
    )


def _edge(adjusted: float, posterior: float = 0.7) -> EdgeEstimate:
    return EdgeEstimate(
        market_id="m1",
        signal_ids=["s1"],
        prior=0.55,
        posterior=posterior,
        raw_edge=posterior - 0.55,
        decay_factor=1.0,
        estimated_slippage=0.01,
        adjusted_edge=adjusted,
        timestamp=datetime.now(timezone.utc),
    )


def test_strategy_returns_none_below_threshold() -> None:
    s = TradingStrategy(StrategyConfig(min_adjusted_edge=0.05))
    d = s.decide(_market(), _edge(0.02), PortfolioState())
    assert d is None


def test_strategy_produces_decision_with_expected_side_and_limits() -> None:
    s = TradingStrategy(
        StrategyConfig(
            min_adjusted_edge=0.01,
            bankroll_usd=1000,
            max_kelly_fraction=0.25,
            min_order_usd=5,
            max_order_usd=250,
        )
    )
    d = s.decide(_market(), _edge(0.10, posterior=0.75), PortfolioState())
    assert d is not None
    assert d.side.value in {"BUY", "SELL"}
    assert 5 <= d.size_usd <= 250
    assert 0.54 <= d.limit_price <= 0.56


def test_strategy_respects_market_position_cap() -> None:
    s = TradingStrategy(StrategyConfig(per_market_position_limit_usd=100))
    p = PortfolioState(positions={"m1": 100.0}, total_exposure=100.0)
    d = s.decide(_market(), _edge(0.20), p)
    assert d is None


@pytest.mark.asyncio
async def test_executor_paper_mode_marks_executed() -> None:
    s = TradingStrategy(StrategyConfig(min_adjusted_edge=0.01))
    decision = s.decide(_market(), _edge(0.12), PortfolioState())
    assert decision is not None
    ex = OrderExecutor("https://clob.polymarket.com", ExecutionConfig(enabled=False, paper_mode=True))
    filled = await ex.execute(decision)
    assert filled.executed is True
    assert filled.fill_price == pytest.approx(decision.limit_price)
    assert filled.fill_size == pytest.approx(decision.size_usd)
