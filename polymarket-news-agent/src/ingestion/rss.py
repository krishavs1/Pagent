"""RSS/Atom ingestion source."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional, Sequence

import aiohttp
import feedparser

from src.market.text import tokenize
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
        self._seen_ids: set[str] = set()

    async def _fetch_feed(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch feed text from URL."""
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    @staticmethod
    def _entry_id(entry: Any) -> str:
        """Build deterministic entry identifier for deduplication."""
        base = (
            getattr(entry, "id", None)
            or getattr(entry, "guid", None)
            or getattr(entry, "link", None)
            or getattr(entry, "title", None)
            or repr(entry)
        )
        return hashlib.sha1(str(base).encode("utf-8")).hexdigest()

    @staticmethod
    def _entry_timestamp(entry: Any) -> datetime:
        raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:  # noqa: BLE001
                pass
        return datetime.now(timezone.utc)

    async def poll(self) -> List[Signal]:
        """Fetch and parse new feed entries into `Signal` objects."""
        out: list[Signal] = []
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": self._user_agent} if self._user_agent else None
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for url in self._feed_urls:
                text = await self._fetch_feed(session, url)
                parsed = feedparser.parse(text)
                for entry in parsed.entries:
                    sid = self._entry_id(entry)
                    if sid in self._seen_ids:
                        continue
                    self._seen_ids.add(sid)

                    headline = str(getattr(entry, "title", "")).strip()
                    body = str(getattr(entry, "summary", "")).strip()
                    entities = sorted(tokenize(f"{headline}\n{body}"))[:30]
                    out.append(
                        Signal(
                            id=f"rss:{sid}",
                            source_name=self.source_name,
                            tier=self._tier,
                            signal_type=self._default_signal_type,
                            headline=headline,
                            body=body,
                            entities=entities,
                            timestamp=self._entry_timestamp(entry),
                            url=str(getattr(entry, "link", "")) or None,
                            relevance_score=0.0,
                            direction=None,
                            confidence=0.0,
                        )
                    )
        return out

