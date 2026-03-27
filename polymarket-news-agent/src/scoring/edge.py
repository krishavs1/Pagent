"""
Edge computation and decay.

Planned responsibilities:
- Compute raw edge from posterior belief vs market mid-price
- Apply time decay to stale signals (exponential decay)
- Subtract estimated slippage and fees to compute adjusted edge

No computation logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from src.utils.types import EdgeEstimate, MarketState, Signal


@dataclass(slots=True)
class EdgeConfig:
    """Configuration for decay and slippage adjustments."""

    half_life_seconds: int = 1800
    decay_floor: float = 0.05


class EdgeCalculator:
    """Computes edge estimates given market state and signals."""

    def __init__(self, config: Optional[EdgeConfig] = None) -> None:
        self._config = config or EdgeConfig()

    def compute(
        self,
        market: MarketState,
        signal_ids: Sequence[str],
        prior: float,
        posterior: float,
        estimated_slippage: float,
        now: Optional[datetime] = None,
    ) -> EdgeEstimate:
        """Return an `EdgeEstimate` encapsulating raw/adjusted edge and metadata."""
        raise NotImplementedError("Edge computation not implemented in scaffold.")

