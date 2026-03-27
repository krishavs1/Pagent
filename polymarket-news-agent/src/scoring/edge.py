"""Edge computation and decay."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from src.utils.types import EdgeEstimate, MarketState


@dataclass(slots=True)
class EdgeConfig:
    """Configuration for decay and slippage adjustments."""

    half_life_seconds: int = 1800
    decay_floor: float = 0.05


class EdgeCalculator:
    """Computes edge estimates given market state and signals."""

    def __init__(self, config: Optional[EdgeConfig] = None) -> None:
        self._config = config or EdgeConfig()

    @staticmethod
    def calculate_raw_edge(posterior: float, market_mid_price: float) -> float:
        """Signed edge before any frictions/decay."""
        return posterior - market_mid_price

    def apply_decay(self, raw_edge: float, seconds_since_signal: float) -> tuple[float, float]:
        """Apply exponential decay with floor; returns (decayed_edge, decay_factor)."""
        if seconds_since_signal <= 0:
            return raw_edge, 1.0
        half_life = max(1.0, float(self._config.half_life_seconds))
        decay = math.exp(-math.log(2.0) * (seconds_since_signal / half_life))
        decay = max(self._config.decay_floor, min(1.0, decay))
        return raw_edge * decay, decay

    @staticmethod
    def calculate_adjusted_edge(decayed_edge: float, estimated_slippage: float) -> float:
        """
        Apply slippage in the adverse direction.

        Positive edges lose value by slippage; negative edges become more negative.
        """
        if decayed_edge >= 0:
            return decayed_edge - estimated_slippage
        return decayed_edge + estimated_slippage

    def compute(
        self,
        market: MarketState,
        signal_ids: Sequence[str],
        prior: float,
        posterior: float,
        estimated_slippage: float,
        signal_timestamp: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> EdgeEstimate:
        """Return an `EdgeEstimate` encapsulating raw/adjusted edge and metadata."""
        current_time = now or datetime.now(timezone.utc)
        base_ts = signal_timestamp or current_time
        seconds_since = max(0.0, (current_time - base_ts).total_seconds())

        raw = self.calculate_raw_edge(posterior, market.mid_price)
        decayed_edge, decay_factor = self.apply_decay(raw, seconds_since)
        adjusted = self.calculate_adjusted_edge(decayed_edge, estimated_slippage)

        return EdgeEstimate(
            market_id=market.condition_id,
            signal_ids=list(signal_ids),
            prior=prior,
            posterior=posterior,
            raw_edge=raw,
            decay_factor=decay_factor,
            estimated_slippage=estimated_slippage,
            adjusted_edge=adjusted,
            timestamp=current_time,
        )

