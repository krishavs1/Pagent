"""
Ingestion base abstractions.

Defines the `NewsSource` interface that all ingestion sources must implement.
Sources should be responsible for:
- Polling or streaming data from a specific upstream
- Converting raw items into normalized `Signal` objects
- Avoiding heavy scoring/market logic (that belongs downstream)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.utils.types import Signal


class NewsSource(ABC):
    """Abstract base class for a signal-producing news source."""

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abstractmethod
    async def poll(self) -> List[Signal]:
        """
        Poll the upstream source and return newly discovered signals.

        Implementations should be idempotent and avoid emitting duplicates when
        possible; final deduplication is handled by the aggregator.
        """

        raise NotImplementedError

