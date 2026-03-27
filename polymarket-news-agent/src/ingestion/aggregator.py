"""
Signal aggregation and deduplication.

Planned responsibilities:
- Merge signals from many `NewsSource` instances
- Deduplicate within a configurable time window
- Maintain a unified async queue for downstream processing
- Optionally enrich signals with lightweight metadata (e.g., normalized entities)

This scaffold provides only interfaces and placeholders.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Iterable, List, Optional, Sequence

from src.ingestion.base import NewsSource
from src.utils.types import Signal


@dataclass(slots=True)
class AggregatorConfig:
    """Configuration values for the signal aggregator."""

    max_queue_size: int = 10_000
    dedupe_window_seconds: int = 3600


class SignalAggregator:
    """Consumes multiple sources and emits a unified stream of deduplicated signals."""

    def __init__(self, sources: Sequence[NewsSource], config: Optional[AggregatorConfig] = None) -> None:
        self._sources = list(sources)
        self._config = config or AggregatorConfig()
        self._queue: asyncio.Queue[Signal] = asyncio.Queue(maxsize=self._config.max_queue_size)

    async def start(self) -> None:
        """Start polling sources and enqueue deduplicated signals."""
        raise NotImplementedError("Aggregator loop not implemented in scaffold.")

    async def stop(self) -> None:
        """Stop polling and drain/close resources."""
        raise NotImplementedError("Aggregator shutdown not implemented in scaffold.")

    async def put_many(self, signals: Iterable[Signal]) -> None:
        """Enqueue a batch of signals (dedupe should occur here eventually)."""
        raise NotImplementedError("Batch enqueue not implemented in scaffold.")

    async def get(self) -> Signal:
        """Get the next available signal from the unified queue."""
        raise NotImplementedError("Queue consumption not implemented in scaffold.")

    async def stream(self) -> AsyncIterator[Signal]:
        """Async iterator over signals as they arrive."""
        raise NotImplementedError("Async streaming not implemented in scaffold.")

