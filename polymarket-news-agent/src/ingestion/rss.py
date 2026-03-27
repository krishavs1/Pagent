"""
RSS/Atom ingestion source.

Planned responsibilities:
- Poll one or more RSS/Atom feeds on an interval
- Parse entries and normalize to `Signal`
- Track seen entry IDs and timestamps to avoid duplicates

No network calls or parsing logic is implemented in this scaffold.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from src.ingestion.base import NewsSource
from src.utils.types import Signal, SignalTier, SignalType


class RSSSource(NewsSource):
    """Polls RSS/Atom feeds and emits normalized `Signal` objects."""

    def __init__(
        self,
        source_name: str,
        feed_urls: Sequence[str],
        tier: SignalTier,
        default_signal_type: SignalType = SignalType.CREDIBLE_SCOOP,
        user_agent: Optional[str] = None,
    ) -> None:
        super().__init__(source_name=source_name)
        self._feed_urls = list(feed_urls)
        self._tier = tier
        self._default_signal_type = default_signal_type
        self._user_agent = user_agent

    async def poll(self) -> List[Signal]:
        """Fetch and parse new feed entries into `Signal` objects."""
        raise NotImplementedError("RSS polling not implemented in scaffold.")

