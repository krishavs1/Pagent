"""
Orderbook tracking and slippage estimation.

Planned responsibilities:
- Fetch orderbook snapshots for tracked markets (or subscribe via websockets)
- Maintain best bid/ask and depth metrics
- Estimate slippage for a target notional size

No API calls are implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import MarketState


@dataclass(slots=True)
class OrderbookConfig:
    """Configuration for orderbook tracking and sampling."""

    depth_lookahead_levels: int = 5
    request_timeout_seconds: int = 15


class OrderbookTracker:
    """Maintains orderbook-derived fields within `MarketState` snapshots."""

    def __init__(self, clob_base_url: str, config: Optional[OrderbookConfig] = None) -> None:
        self._clob_base_url = clob_base_url
        self._config = config or OrderbookConfig()

    async def update_market_state(self, market: MarketState) -> MarketState:
        """Return a new `MarketState` snapshot with refreshed orderbook fields."""
        raise NotImplementedError("Orderbook updates not implemented in scaffold.")

    async def estimate_slippage_usd(self, market_id: str, notional_usd: float) -> float:
        """Estimate slippage in USD for a hypothetical order."""
        raise NotImplementedError("Slippage estimation not implemented in scaffold.")

