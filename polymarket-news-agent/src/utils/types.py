"""
Shared type definitions for the polymarket news-driven trading agent.

This module is the single source of truth for data models exchanged between:
- Ingestion (news -> normalized signals)
- Market (signals -> candidate markets and orderbook state)
- Scoring (signals/markets -> posterior beliefs and edge estimates)
- Execution (edge -> trade decisions and orders)
- Risk (portfolio state -> constraints and guards)

Unlike the rest of the scaffold, this file is fully implemented so other modules
can import stable types while remaining logic-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class SignalTier(str, Enum):
    """Source quality tier used for priors, throttling, and risk weighting."""

    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class SignalType(str, Enum):
    """Categorization of signal provenance/strength for scoring and priors."""

    OFFICIAL_OUTCOME = "OFFICIAL_OUTCOME"
    CREDIBLE_SCOOP = "CREDIBLE_SCOOP"
    INSIDER_LEAK = "INSIDER_LEAK"
    POLL_SHIFT = "POLL_SHIFT"
    PUNDIT_SPECULATION = "PUNDIT_SPECULATION"


class OrderSide(str, Enum):
    """Trade direction relative to the market's YES token."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Signal:
    """
    Normalized representation of a news event.

    Notes:
    - `entities` is a lightweight list of extracted entity strings (e.g., candidates,
      bills, agencies). Downstream modules may enrich with structured metadata.
    - `direction` is an optional signed value indicating expected movement for a
      matched market (convention: -1.0..+1.0), if known.
    """

    id: str
    source_name: str
    tier: SignalTier
    signal_type: SignalType
    headline: str
    body: str
    entities: List[str]
    timestamp: datetime
    url: Optional[str] = None
    relevance_score: float = 0.0
    direction: Optional[float] = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class MarketState:
    """
    Snapshot of a Polymarket market's relevant tradable state.

    This is intended to be populated by the Market module and consumed by Scoring,
    Execution, and Risk.
    """

    condition_id: str
    question: str
    description: str
    tags: List[str]
    entities: List[str]
    mid_price: float
    spread: float
    volume_24h: float
    liquidity: float
    best_bid_yes: float
    best_ask_yes: float
    bid_depth_usd: float
    ask_depth_usd: float
    last_updated: datetime
    yes_token_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class EdgeEstimate:
    """
    Output of scoring: belief update + edge after decay/slippage adjustments.

    - `prior`/`posterior` are probabilities for the market's YES outcome (0..1).
    - `raw_edge` is typically posterior - mid_price (before frictions).
    """

    market_id: str
    signal_ids: List[str]
    prior: float
    posterior: float
    raw_edge: float
    decay_factor: float
    estimated_slippage: float
    adjusted_edge: float
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class TradeDecision:
    """
    Execution intent produced by strategy and optionally populated with fills.

    - `executed` indicates whether an order was actually sent/filled in the chosen
      environment (paper/backtest/live).
    """

    market_id: str
    edge: float
    side: OrderSide
    size_usd: float
    limit_price: float
    kelly_fraction: float
    reason: str
    timestamp: datetime
    executed: bool = False
    fill_price: Optional[float] = None
    fill_size: Optional[float] = None


@dataclass(slots=True)
class PortfolioState:
    """
    Minimal portfolio view for risk checks and backtest replay.

    `positions` is a free-form mapping keyed by market_id. The value can be a
    float (net exposure) or a richer structure in future iterations.
    """

    positions: Dict[str, Any] = field(default_factory=dict)
    total_exposure: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trade_history: List[TradeDecision] = field(default_factory=list)


JsonDict = Dict[str, Any]
StrSeq = Sequence[str]

__all__ = [
    "EdgeEstimate",
    "JsonDict",
    "MarketState",
    "OrderSide",
    "PortfolioState",
    "Signal",
    "SignalTier",
    "SignalType",
    "StrSeq",
    "TradeDecision",
]
