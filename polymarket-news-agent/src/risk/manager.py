"""
Risk management module.

Planned responsibilities:
- Enforce per-market position limits and global exposure caps
- Detect correlated markets (shared entities/tags) and cap cluster exposure
- Enforce drawdown limits and circuit breakers

No risk logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import MarketState, PortfolioState, TradeDecision


@dataclass(slots=True)
class RiskConfig:
    """Configuration for risk limits and guards."""

    max_total_exposure_usd: float = 2500.0
    max_position_per_market_usd: float = 400.0
    max_daily_drawdown_usd: float = 300.0
    enable_correlation_checks: bool = True


class RiskManager:
    """Evaluates proposed trades against portfolio-level and market-level limits."""

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self._config = config or RiskConfig()

    def approve(self, market: MarketState, decision: TradeDecision, portfolio: PortfolioState) -> bool:
        """Return True if the decision is permitted under current risk limits."""
        raise NotImplementedError("Risk checks not implemented in scaffold.")

    def update_portfolio(self, decision: TradeDecision, portfolio: PortfolioState) -> PortfolioState:
        """Apply an executed decision to portfolio state (paper/backtest use)."""
        raise NotImplementedError("Portfolio updates not implemented in scaffold.")

