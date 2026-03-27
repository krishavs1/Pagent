"""
Calibration tracking.

Planned responsibilities:
- Record predicted probabilities/edges alongside realized outcomes
- Compute calibration curves and Brier scores over time
- Export datasets for offline analysis

No persistence or analytics logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import EdgeEstimate, MarketState, Signal


@dataclass(slots=True)
class CalibrationRecord:
    """Single record linking a prediction to eventual outcome (placeholder)."""

    market_id: str
    timestamp: float


class CalibrationTracker:
    """Tracks model calibration by logging predicted vs realized outcomes."""

    def __init__(self, sink_path: Optional[str] = None) -> None:
        self._sink_path = sink_path

    def record(self, market: MarketState, signal: Signal, edge: EdgeEstimate) -> None:
        """Record a calibration datapoint."""
        raise NotImplementedError("Calibration tracking not implemented in scaffold.")

