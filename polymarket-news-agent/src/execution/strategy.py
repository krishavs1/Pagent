"""Trading strategy logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.utils.types import EdgeEstimate, MarketState, OrderSide, PortfolioState, TradeDecision


@dataclass(slots=True)
class StrategyConfig:
    """Configuration parameters for strategy decisions."""

    min_adjusted_edge: float = 0.02
    max_kelly_fraction: float = 0.10
    min_order_usd: float = 5.0
    max_order_usd: float = 250.0
    max_portfolio_exposure_usd: float = 2500.0
    per_market_position_limit_usd: float = 400.0
    limit_price_buffer_bps: float = 15.0
    bankroll_usd: float = 1000.0


class TradingStrategy:
    """Converts an `EdgeEstimate` into a `TradeDecision` (sizing and gating)."""

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        self._config = config or StrategyConfig()

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _current_position_usd(self, market_id: str, portfolio: PortfolioState) -> float:
        raw = portfolio.positions.get(market_id, 0.0)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _compute_kelly_fraction(self, posterior: float) -> float:
        """
        Binary Kelly approximation vs fair-coin baseline.

        For this scaffold, use:
          edge = |posterior - 0.5| * 2
          kelly = edge * max_kelly_fraction
        """
        edge_strength = abs(posterior - 0.5) * 2.0
        return self._clamp(edge_strength * self._config.max_kelly_fraction, 0.0, self._config.max_kelly_fraction)

    def decide(self, market: MarketState, edge: EdgeEstimate, portfolio: PortfolioState) -> Optional[TradeDecision]:
        """Return a trade decision, or None if no trade should be placed."""
        if abs(edge.adjusted_edge) < self._config.min_adjusted_edge:
            return None

        side = OrderSide.BUY if edge.adjusted_edge > 0 else OrderSide.SELL
        signed_pos = self._current_position_usd(market.condition_id, portfolio)

        # Do not open or add to a short YES: SELL only trims an existing long.
        if side == OrderSide.SELL and signed_pos <= 0:
            return None

        kelly_fraction = self._compute_kelly_fraction(edge.posterior)
        if kelly_fraction <= 0:
            return None

        target_size = self._config.bankroll_usd * kelly_fraction
        size_usd = self._clamp(target_size, self._config.min_order_usd, self._config.max_order_usd)

        if side == OrderSide.SELL:
            size_usd = min(size_usd, signed_pos)
            if size_usd < self._config.min_order_usd:
                return None

        if side == OrderSide.BUY and signed_pos >= self._config.per_market_position_limit_usd:
            return None

        if side == OrderSide.BUY:
            remaining_market = self._config.per_market_position_limit_usd - max(0.0, signed_pos)
            size_usd = min(size_usd, max(0.0, remaining_market))
            remaining_portfolio = self._config.max_portfolio_exposure_usd - max(0.0, portfolio.total_exposure)
            size_usd = min(size_usd, max(0.0, remaining_portfolio))

        if size_usd < self._config.min_order_usd:
            return None

        buffer = self._config.limit_price_buffer_bps / 10_000.0
        if side == OrderSide.BUY:
            limit_price = self._clamp(market.best_ask_yes * (1.0 + buffer), market.best_bid_yes, market.best_ask_yes)
        else:
            limit_price = self._clamp(market.best_bid_yes * (1.0 - buffer), market.best_bid_yes, market.best_ask_yes)

        return TradeDecision(
            market_id=market.condition_id,
            edge=edge.adjusted_edge,
            side=side,
            size_usd=size_usd,
            limit_price=limit_price,
            kelly_fraction=kelly_fraction,
            reason="edge_gated_kelly",
            timestamp=datetime.now(timezone.utc),
            executed=False,
        )

