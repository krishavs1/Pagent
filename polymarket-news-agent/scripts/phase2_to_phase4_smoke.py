"""End-to-end smoke: Phase 2 edge output -> Phase 4 execution.

This validates the handoff contract:
EdgeEstimate (scoring) -> TradingStrategy.decide -> OrderExecutor.execute (paper mode).
"""

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


def sample_market_state() -> MarketState:
    return MarketState(
        condition_id="market-phase-link",
        question="Will a nominee be confirmed this month?",
        description="Synthetic market state for handoff validation.",
        tags=["Politics"],
        entities=["nominee", "senate"],
        mid_price=0.60,
        spread=0.02,
        volume_24h=120_000.0,
        liquidity=22_000.0,
        best_bid_yes=0.59,
        best_ask_yes=0.61,
        bid_depth_usd=8_000.0,
        ask_depth_usd=9_500.0,
        last_updated=datetime.now(timezone.utc),
    )


def sample_phase2_edge() -> EdgeEstimate:
    now = datetime.now(timezone.utc)
    return EdgeEstimate(
        market_id="market-phase-link",
        signal_ids=["signal-123"],
        prior=0.60,
        posterior=0.74,
        raw_edge=0.14,
        decay_factor=0.80,
        estimated_slippage=0.01,
        adjusted_edge=0.102,
        timestamp=now,
    )


async def main() -> None:
    market = sample_market_state()
    edge = sample_phase2_edge()
    portfolio = PortfolioState()

    strategy = TradingStrategy(
        StrategyConfig(
            min_adjusted_edge=0.02,
            max_kelly_fraction=0.15,
            min_order_usd=5.0,
            max_order_usd=250.0,
            bankroll_usd=1500.0,
        )
    )
    executor = OrderExecutor(
        "https://clob.polymarket.com",
        ExecutionConfig(enabled=False, paper_mode=True),
    )

    decision = strategy.decide(market, edge, portfolio)
    if decision is None:
        print("No decision generated from edge. Check strategy thresholds/config.")
        return

    executed = await executor.execute(decision)
    print("=== Phase2 -> Phase4 Smoke ===")
    print("edge_adjusted:", edge.adjusted_edge)
    print("decision_side:", decision.side.value)
    print("decision_size_usd:", round(decision.size_usd, 4))
    print("decision_limit:", round(decision.limit_price, 4))
    print("executed:", executed.executed)
    print("fill_price:", executed.fill_price)
    print("fill_size:", executed.fill_size)


if __name__ == "__main__":
    asyncio.run(main())

