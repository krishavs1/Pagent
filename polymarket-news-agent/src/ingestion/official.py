"""Official government sources ingestion."""

from __future__ import annotations

from typing import List, Optional, Sequence

from src.ingestion.base import NewsSource
from src.ingestion.rss import RSSSource
from src.utils.types import Signal, SignalTier, SignalType


class OfficialSource(NewsSource):
    """Polls official sources and emits normalized `Signal` objects."""

    def __init__(
        self,
        source_name: str,
        tier: SignalTier = SignalTier.TIER_1,
        endpoints: Optional[Sequence[str]] = None,
        congress_api_key_env: str = "CONGRESS_API_KEY",
        default_signal_type: SignalType = SignalType.OFFICIAL_OUTCOME,
    ) -> None:
        super().__init__(source_name=source_name)
        self._tier = tier
        self._endpoints = list(endpoints or [])
        self._congress_api_key_env = congress_api_key_env
        self._default_signal_type = default_signal_type
        self._rss_delegate = RSSSource(
            source_name=source_name,
            feed_urls=[e for e in self._endpoints if e.startswith("http")],
            tier=self._tier,
            default_signal_type=self._default_signal_type,
        )

    async def poll(self) -> List[Signal]:
        """
        Poll official endpoints and normalize updates into `Signal` objects.

        Current implementation supports RSS-style official URLs.
        Congress API endpoints can be added as a dedicated fetch path later.
        """
        return await self._rss_delegate.poll()

