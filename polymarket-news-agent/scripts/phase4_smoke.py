"""Phase 4 smoke runner: strategy decision + paper execution."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution.executor import ExecutionConfig, OrderExecutor
from src.execution.strategy import StrategyConfig, TradingStrategy
from src.utils.types import EdgeEstimate, MarketState, PortfolioState


def sample_market() -> MarketState:
    return MarketState(
        condition_id="m1",
        question="Will nominee be confirmed?",
        description="sample",
        tags=["Politics"],
        entities=["nominee", "senate"],
        mid_price=0.58,
        spread=0.02,
        volume_24h=40000,
        liquidity=9000,
        best_bid_yes=0.57,
        best_ask_yes=0.59,
        bid_depth_usd=2000,
        ask_depth_usd=2200,
        last_updated=datetime.now(timezone.utc),
    )


def sample_edge() -> EdgeEstimate:
    now = datetime.now(timezone.utc)
    return EdgeEstimate(
        market_id="m1",
        signal_ids=["s1"],
        prior=0.58,
        posterior=0.71,
        raw_edge=0.13,
        decay_factor=0.9,
        estimated_slippage=0.01,
        adjusted_edge=0.107,
        timestamp=now,
    )


async def main() -> None:
    strategy = TradingStrategy(StrategyConfig(min_adjusted_edge=0.01, bankroll_usd=1500))
    executor = OrderExecutor(
        "https://clob.polymarket.com",
        ExecutionConfig(enabled=False, paper_mode=True),
    )
    decision = strategy.decide(sample_market(), sample_edge(), PortfolioState())
    if decision is None:
        print("No trade decision generated.")
        return
    print("decision:", decision)
    filled = await executor.execute(decision)
    print("executed:", filled)


if __name__ == "__main__":
    asyncio.run(main())

