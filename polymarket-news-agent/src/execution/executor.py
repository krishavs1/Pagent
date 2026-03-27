"""Order execution wrapper around the Polymarket CLOB client."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from py_clob_client.client import ClobClient

from src.utils.types import TradeDecision


@dataclass(slots=True)
class ExecutionConfig:
    """Configuration for execution behavior and environment."""

    enabled: bool = False
    paper_mode: bool = True
    chain_id: int = 137
    signature_type: int = 0
    funder_env: str = "POLYMARKET_FUNDER"
    private_key_env: str = "POLYMARKET_PRIVATE_KEY"
    api_key_env: str = "POLYMARKET_API_KEY"
    secret_env: str = "POLYMARKET_SECRET"
    passphrase_env: str = "POLYMARKET_PASSPHRASE"


class OrderExecutor:
    """Places orders and updates decisions with fill information."""

    def __init__(self, clob_base_url: str, config: Optional[ExecutionConfig] = None) -> None:
        self._clob_base_url = clob_base_url
        self._config = config or ExecutionConfig()
        self._client: Optional[ClobClient] = None

    def _ensure_live_client(self) -> ClobClient:
        """Initialize live CLOB client from env for non-paper execution."""
        if self._client is not None:
            return self._client
        pk = os.getenv(self._config.private_key_env)
        if not pk:
            raise ValueError(f"Missing env var: {self._config.private_key_env}")
        funder = os.getenv(self._config.funder_env) or None
        self._client = ClobClient(
            host=self._clob_base_url,
            chain_id=self._config.chain_id,
            key=pk,
            signature_type=self._config.signature_type,
            funder=funder,
        )
        return self._client

    async def execute(self, decision: TradeDecision) -> TradeDecision:
        """Execute a trade decision and return an updated decision with fills."""
        if self._config.paper_mode or not self._config.enabled:
            return TradeDecision(
                market_id=decision.market_id,
                edge=decision.edge,
                side=decision.side,
                size_usd=decision.size_usd,
                limit_price=decision.limit_price,
                kelly_fraction=decision.kelly_fraction,
                reason=f"{decision.reason}|paper_mode",
                timestamp=decision.timestamp,
                executed=True,
                fill_price=decision.limit_price,
                fill_size=decision.size_usd,
            )

        # Live mode intentionally remains minimal until token_id mapping/order args are wired.
        self._ensure_live_client()
        raise NotImplementedError("Live order placement wiring pending token_id/order conversion.")

    async def cancel_all(self, market_id: Optional[str] = None) -> None:
        """Cancel orders globally or for a single market."""
        if self._config.paper_mode or not self._config.enabled:
            return
        _ = market_id
        raise NotImplementedError("Live cancellation wiring pending API creds + order ids.")

