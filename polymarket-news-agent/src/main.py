"""
Async orchestrator entrypoint.

This module will eventually:
- Load configuration (YAML + environment variables)
- Initialize ingestion sources and the signal aggregator
- Start market indexer/orderbook tracker
- Wire scoring (classifier + Bayesian + edge) to execution and risk gates
- Run an async event loop that processes signals continuously

Only minimal stubs are provided here (no business logic).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from src.execution.executor import OrderExecutor
from src.execution.strategy import TradingStrategy
from src.ingestion.aggregator import SignalAggregator
from src.market.indexer import MarketIndexer
from src.market.matcher import MarketMatcher
from src.market.orderbook import OrderbookTracker
from src.risk.manager import RiskManager
from src.scoring.bayesian import BayesianEngine
from src.scoring.classifier import SignalClassifier
from src.scoring.edge import EdgeCalculator
from src.utils.types import PortfolioState


@dataclass(slots=True)
class AgentComponents:
    """Container for initialized pipeline components (dependency wiring only)."""

    aggregator: SignalAggregator
    market_indexer: MarketIndexer
    orderbook_tracker: OrderbookTracker
    market_matcher: MarketMatcher
    classifier: SignalClassifier
    bayesian: BayesianEngine
    edge: EdgeCalculator
    risk: RiskManager
    strategy: TradingStrategy
    executor: OrderExecutor


class AgentOrchestrator:
    """Coordinates the pipeline modules in an async event loop."""

    def __init__(self, components: AgentComponents, portfolio: Optional[PortfolioState] = None) -> None:
        self._components = components
        self._portfolio = portfolio or PortfolioState()

    async def run_forever(self) -> None:
        """Run the agent event loop until cancelled."""
        raise NotImplementedError("Orchestration loop not implemented in scaffold.")


async def main() -> None:
    """CLI entrypoint for running the agent."""
    raise NotImplementedError("CLI wiring not implemented in scaffold.")


if __name__ == "__main__":
    asyncio.run(main())

