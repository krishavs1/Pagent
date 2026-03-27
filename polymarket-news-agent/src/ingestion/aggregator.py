"""Signal aggregation and deduplication."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Iterable, Optional, Sequence

from src.ingestion.base import NewsSource
from src.market.text import tokenize
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
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False
        self._seen: dict[str, float] = {}

    @staticmethod
    def _signal_key(signal: Signal) -> str:
        if signal.url:
            return f"url:{signal.url}"
        bag = " ".join(sorted(tokenize(signal.headline)))
        if not bag:
            bag = signal.headline.strip().lower()
        digest = hashlib.sha1(bag.encode("utf-8")).hexdigest()
        return f"headline:{digest}"

    def _is_duplicate(self, signal: Signal, now_ts: float) -> bool:
        key = self._signal_key(signal)
        old = self._seen.get(key)
        if old is not None and (now_ts - old) <= self._config.dedupe_window_seconds:
            return True
        self._seen[key] = now_ts
        # opportunistic cleanup
        cutoff = now_ts - self._config.dedupe_window_seconds
        if len(self._seen) > 5000:
            self._seen = {k: ts for k, ts in self._seen.items() if ts >= cutoff}
        return False

    async def _poll_loop(self, source: NewsSource) -> None:
        interval = int(getattr(source, "poll_seconds", 60))
        interval = max(5, interval)
        while self._running:
            try:
                signals = await source.poll()
                await self.put_many(signals)
            except Exception:  # noqa: BLE001
                # Continue polling even if one cycle fails.
                pass
            await asyncio.sleep(interval)

    async def start(self) -> None:
        """Start polling sources and enqueue deduplicated signals."""
        if self._running:
            return
        self._running = True
        self._tasks = [asyncio.create_task(self._poll_loop(source)) for source in self._sources]

    async def stop(self) -> None:
        """Stop polling and drain/close resources."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        for source in self._sources:
            close = getattr(source, "close", None)
            if close is not None and callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result

    async def put_many(self, signals: Iterable[Signal]) -> None:
        """Enqueue a batch of signals (dedupe should occur here eventually)."""
        now_ts = datetime.now(timezone.utc).timestamp()
        for signal in signals:
            if self._is_duplicate(signal, now_ts):
                continue
            await self._queue.put(signal)

    async def get(self) -> Signal:
        """Get the next available signal from the unified queue."""
        return await self._queue.get()

    async def stream(self) -> AsyncIterator[Signal]:
        """Async iterator over signals as they arrive."""
        while True:
            yield await self.get()

