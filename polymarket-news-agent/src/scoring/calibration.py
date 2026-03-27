"""Calibration tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from src.utils.types import EdgeEstimate, MarketState, Signal


@dataclass(slots=True)
class CalibrationRecord:
    """Single record linking a prediction to eventual outcome."""

    market_id: str
    predicted_prob: float
    actual_outcome: Optional[float]
    timestamp: float


class CalibrationTracker:
    """Tracks model calibration by logging predicted vs realized outcomes."""

    def __init__(self, sink_path: Optional[str] = None) -> None:
        self._sink_path = sink_path
        self._records: List[CalibrationRecord] = []

    def record(self, market: MarketState, signal: Signal, edge: EdgeEstimate) -> None:
        """Record a calibration datapoint."""
        record = CalibrationRecord(
            market_id=market.condition_id,
            predicted_prob=max(0.0, min(1.0, edge.posterior)),
            actual_outcome=None,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
        self._records.append(record)

    def resolve(self, market_id: str, actual_outcome: float) -> None:
        """Attach realized outcome (0/1) to unresolved records for a market."""
        outcome = max(0.0, min(1.0, actual_outcome))
        for rec in self._records:
            if rec.market_id == market_id and rec.actual_outcome is None:
                rec.actual_outcome = outcome

    def brier_score(self) -> Optional[float]:
        """Compute Brier score over resolved records; lower is better."""
        resolved = [r for r in self._records if r.actual_outcome is not None]
        if not resolved:
            return None
        return sum((r.predicted_prob - float(r.actual_outcome)) ** 2 for r in resolved) / len(resolved)

    def records(self) -> List[CalibrationRecord]:
        """Return an immutable-style copy of calibration records."""
        return list(self._records)

