"""
Orderbook tracking and slippage estimation.

Uses `py_clob_client` in L0 mode (host only) for public `get_order_book` calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from py_clob_client.clob_types import OrderBookSummary, OrderSummary
from py_clob_client.client import ClobClient

from src.utils.types import MarketState


@dataclass(slots=True)
class OrderbookConfig:
    """Configuration for orderbook tracking and sampling."""

    depth_lookahead_levels: int = 5
    request_timeout_seconds: int = 15


def _best_bid_ask(book: OrderBookSummary) -> tuple[float, float]:
    bids = [float(x.price) for x in (book.bids or []) if x.price is not None]
    asks = [float(x.price) for x in (book.asks or []) if x.price is not None]
    best_bid = max(bids) if bids else 0.0
    best_ask = min(asks) if asks else 1.0
    return best_bid, best_ask


def _depth_usd(levels: list[OrderSummary], *, descending: bool, max_levels: int) -> float:
    if not levels:
        return 0.0
    priced = [x for x in levels if x.price is not None and x.size is not None]
    key = lambda x: float(x.price)
    priced.sort(key=key, reverse=descending)
    total = 0.0
    for lvl in priced[:max_levels]:
        p = float(lvl.price)
        s = float(lvl.size)
        total += p * s
    return total


def _mid_spread(book: OrderBookSummary) -> tuple[float, float]:
    bb, ba = _best_bid_ask(book)
    if ba <= bb:
        return (bb + ba) / 2 if bb or ba else 0.5, max(ba - bb, 0.0)
    mid = (bb + ba) / 2.0
    spread = ba - bb
    return mid, spread


def slippage_buy_yes_probability(
    book: OrderBookSummary,
    mid: float,
    notional_usd: float,
) -> float:
    """
    Price impact (probability points) for buying YES with a USDC notional, walking the ask side.

    Returns abs(vwap - mid) clamped to [0, 1]. For ``notional_usd <= 0`` returns 0.
    """
    if notional_usd <= 0:
        return 0.0
    asks = [x for x in (book.asks or []) if x.price is not None and x.size is not None]
    if not asks:
        return 0.0
    levels = sorted(asks, key=lambda x: float(x.price))
    remaining = notional_usd
    cost = 0.0
    shares = 0.0
    for lvl in levels:
        p = float(lvl.price)
        sz = float(lvl.size)
        if p <= 0:
            continue
        level_notional = p * sz
        if level_notional <= remaining + 1e-12:
            cost += level_notional
            shares += sz
            remaining -= level_notional
        else:
            take = remaining / p
            cost += remaining
            shares += take
            remaining = 0.0
            break
    if shares <= 0 or cost <= 0:
        return 0.0
    vwap = cost / shares
    return max(0.0, min(1.0, abs(vwap - mid)))


class OrderbookTracker:
    """Maintains orderbook-derived fields within `MarketState` snapshots."""

    def __init__(self, clob_base_url: str, config: Optional[OrderbookConfig] = None) -> None:
        host = clob_base_url.rstrip("/")
        self._client = ClobClient(host=host)
        self._config = config or OrderbookConfig()

    async def update_market_state(self, market: MarketState) -> MarketState:
        """Return a new `MarketState` snapshot with refreshed orderbook fields."""
        if not market.yes_token_id:
            return market
        book = await asyncio.to_thread(self._client.get_order_book, market.yes_token_id)
        mid, spread = _mid_spread(book)
        bb, ba = _best_bid_ask(book)
        bid_depth = _depth_usd(
            list(book.bids or []),
            descending=True,
            max_levels=self._config.depth_lookahead_levels,
        )
        ask_depth = _depth_usd(
            list(book.asks or []),
            descending=False,
            max_levels=self._config.depth_lookahead_levels,
        )
        now = datetime.now(timezone.utc)
        return replace(
            market,
            mid_price=mid,
            spread=spread,
            best_bid_yes=bb,
            best_ask_yes=ba,
            bid_depth_usd=bid_depth,
            ask_depth_usd=ask_depth,
            last_updated=now,
        )

    async def estimate_slippage_probability(self, token_id: str, notional_usd: float) -> float:
        """
        Estimate price impact (0..1 probability points) for a hypothetical YES buy.
        """
        if notional_usd <= 0:
            return 0.0
        book = await asyncio.to_thread(self._client.get_order_book, token_id)
        mid, _ = _mid_spread(book)
        return slippage_buy_yes_probability(book, mid, notional_usd)

    async def estimate_slippage_usd(self, market_id: str, notional_usd: float) -> float:
        """Deprecated alias: ``market_id`` must be a YES ``token_id`` for now."""
        return await self.estimate_slippage_probability(market_id, notional_usd)
