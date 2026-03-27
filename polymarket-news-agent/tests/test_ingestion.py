"""Tests for Phase 3 ingestion components."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.ingestion.aggregator import AggregatorConfig, SignalAggregator
from src.ingestion.base import NewsSource
from src.ingestion.rss import RSSSource
from src.ingestion.x_api import XApiSource
from src.utils.types import Signal, SignalTier, SignalType


class _DummySource(NewsSource):
    def __init__(self, batches: list[list[Signal]]) -> None:
        super().__init__("dummy")
        self._batches = batches
        self._i = 0

    async def poll(self) -> list[Signal]:
        if self._i >= len(self._batches):
            return []
        out = self._batches[self._i]
        self._i += 1
        return out


def _signal(id_: str, headline: str, url: str | None = None) -> Signal:
    return Signal(
        id=id_,
        source_name="test",
        tier=SignalTier.TIER_2,
        signal_type=SignalType.CREDIBLE_SCOOP,
        headline=headline,
        body=headline,
        entities=[],
        timestamp=datetime.now(timezone.utc),
        url=url,
    )


@pytest.mark.asyncio
async def test_aggregator_dedupes_similar_headlines() -> None:
    s1 = _signal("a", "Breaking: Senate confirms nominee")
    s2 = _signal("b", "Breaking Senate confirms nominee")  # near-duplicate
    agg = SignalAggregator([], AggregatorConfig(max_queue_size=10, dedupe_window_seconds=3600))
    await agg.put_many([s1, s2])
    first = await agg.get()
    assert first.id == "a"
    assert agg._queue.empty()  # second item deduped


def test_x_api_build_query() -> None:
    src = XApiSource(accounts=["jakesherman", "AP"], keywords=["BREAKING", "JUST IN"])
    q = src._build_query()
    assert "from:jakesherman" in q
    assert "from:AP" in q
    assert "BREAKING" in q
    assert "\"JUST IN\"" in q


@pytest.mark.asyncio
async def test_rss_poll_dedupes_on_second_poll() -> None:
    rss_text = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <title>Test</title>
        <item>
          <guid>1</guid>
          <title>AP: test headline</title>
          <description>body text</description>
          <link>https://example.com/1</link>
          <pubDate>Fri, 27 Mar 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    source = RSSSource(
        source_name="rss-test",
        feed_urls=["https://example.com/feed.xml"],
        tier=SignalTier.TIER_2,
    )

    async def _fake_fetch(session, url):  # noqa: ANN001
        return rss_text

    source._fetch_feed = _fake_fetch  # type: ignore[method-assign]

    first = await source.poll()
    second = await source.poll()
    assert len(first) == 1
    assert first[0].headline == "AP: test headline"
    assert len(second) == 0
