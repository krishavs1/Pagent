"""Risk management module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from src.utils.types import MarketState, PortfolioState, TradeDecision


@dataclass(slots=True)
class RiskConfig:
    """Configuration for risk limits and guards."""

    max_total_exposure_usd: float = 2500.0
    max_position_per_market_usd: float = 400.0
    max_daily_drawdown_usd: float = 300.0
    enable_correlation_checks: bool = True
    max_cluster_exposure_usd: float = 900.0
    min_shared_entities_for_correlation: int = 1


class RiskManager:
    """Evaluates proposed trades against portfolio-level and market-level limits."""

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self._config = config or RiskConfig()
        self._market_entities: Dict[str, Set[str]] = {}

    @staticmethod
    def _position_usd(portfolio: PortfolioState, market_id: str) -> float:
        raw = portfolio.positions.get(market_id, 0.0)
        if isinstance(raw, dict):
            try:
                return abs(float(raw.get("exposure_usd", 0.0)))
            except (TypeError, ValueError):
                return 0.0
        try:
            return abs(float(raw))
        except (TypeError, ValueError):
            return 0.0

    def _cluster_exposure(self, market: MarketState, portfolio: PortfolioState) -> float:
        """Sum exposure on open positions whose stored entities overlap this market."""
        m_entities = {e.lower() for e in market.entities}
        if not m_entities:
            return 0.0
        total = 0.0
        for mid, raw in portfolio.positions.items():
            if mid == market.condition_id:
                continue
            other_ents = self._market_entities.get(mid, set())
            if len(m_entities & other_ents) < self._config.min_shared_entities_for_correlation:
                continue
            if isinstance(raw, dict):
                try:
                    total += abs(float(raw.get("exposure_usd", 0.0)))
                except (TypeError, ValueError):
                    pass
            else:
                try:
                    total += abs(float(raw))
                except (TypeError, ValueError):
                    pass
        return total

    def approve(self, market: MarketState, decision: TradeDecision, portfolio: PortfolioState) -> Tuple[bool, str]:
        """Return (approved, reason)."""
        if portfolio.unrealized_pnl <= -self._config.max_daily_drawdown_usd:
            return False, "drawdown_guard"

        new_exposure = portfolio.total_exposure + decision.size_usd
        if new_exposure > self._config.max_total_exposure_usd + 1e-6:
            return False, "max_total_exposure"

        cur = self._position_usd(portfolio, market.condition_id)
        if cur + decision.size_usd > self._config.max_position_per_market_usd + 1e-6:
            return False, "max_position_per_market"

        if self._config.enable_correlation_checks:
            cluster = self._cluster_exposure(market, portfolio)
            if cluster + decision.size_usd > self._config.max_cluster_exposure_usd + 1e-6:
                return False, "max_cluster_exposure"

        return True, "ok"

    def update_portfolio(self, market: MarketState, decision: TradeDecision, portfolio: PortfolioState) -> PortfolioState:
        """Apply an executed decision; track entities for correlation checks."""
        mid = decision.market_id
        delta = decision.size_usd if decision.side.value == "BUY" else -decision.size_usd
        cur = portfolio.positions.get(mid, 0.0)
        if isinstance(cur, dict):
            cur_float = float(cur.get("exposure_usd", 0.0))
        else:
            cur_float = float(cur)
        new_val = cur_float + delta
        portfolio.positions[mid] = new_val
        self._market_entities[mid] = {e.lower() for e in market.entities}
        portfolio.total_exposure = _sum_abs_positions(portfolio)
        portfolio.trade_history.append(decision)
        return portfolio


def _sum_abs_positions(portfolio: PortfolioState) -> float:
    total = 0.0
    for raw in portfolio.positions.values():
        if isinstance(raw, dict):
            try:
                total += abs(float(raw.get("exposure_usd", 0.0)))
            except (TypeError, ValueError):
                continue
        else:
            try:
                total += abs(float(raw))
            except (TypeError, ValueError):
                continue
    return total
