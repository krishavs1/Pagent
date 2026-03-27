"""
Order execution wrapper around the Polymarket CLOB client.

Planned responsibilities:
- Initialize and manage the CLOB SDK client session
- Place/cancel orders and query fills
- Translate `TradeDecision` objects into SDK-specific order requests

No SDK calls are implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import TradeDecision


@dataclass(slots=True)
class ExecutionConfig:
    """Configuration for execution behavior and environment."""

    enabled: bool = False
    api_key_env: str = "POLYMARKET_API_KEY"
    secret_env: str = "POLYMARKET_SECRET"


class OrderExecutor:
    """Places orders and updates decisions with fill information."""

    def __init__(self, clob_base_url: str, config: Optional[ExecutionConfig] = None) -> None:
        self._clob_base_url = clob_base_url
        self._config = config or ExecutionConfig()

    async def execute(self, decision: TradeDecision) -> TradeDecision:
        """Execute a trade decision and return an updated decision with fills."""
        raise NotImplementedError("Order execution not implemented in scaffold.")

    async def cancel_all(self, market_id: Optional[str] = None) -> None:
        """Cancel orders globally or for a single market."""
        raise NotImplementedError("Order cancellation not implemented in scaffold.")

