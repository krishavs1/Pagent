"""
Trading strategy logic.

Planned responsibilities:
- Gate on minimum adjusted edge and liquidity constraints
- Use Kelly criterion (or capped Kelly) to size position changes
- Choose order types (limit/market) and limit price buffers

No strategy logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import EdgeEstimate, MarketState, PortfolioState, TradeDecision


@dataclass(slots=True)
class StrategyConfig:
    """Configuration parameters for strategy decisions."""

    min_adjusted_edge: float = 0.02
    max_kelly_fraction: float = 0.10
    min_order_usd: float = 5.0
    max_order_usd: float = 250.0


class TradingStrategy:
    """Converts an `EdgeEstimate` into a `TradeDecision` (sizing and gating)."""

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        self._config = config or StrategyConfig()

    def decide(self, market: MarketState, edge: EdgeEstimate, portfolio: PortfolioState) -> Optional[TradeDecision]:
        """Return a trade decision, or None if no trade should be placed."""
        raise NotImplementedError("Strategy decisions not implemented in scaffold.")

