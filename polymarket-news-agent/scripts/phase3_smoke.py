"""Phase 3 live smoke runner: RSS/Official -> Aggregator queue.

Usage:
  . .venv/bin/activate
  python scripts/phase3_smoke.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.aggregator import AggregatorConfig, SignalAggregator
from src.ingestion.official import OfficialSource
from src.ingestion.rss import RSSSource
from src.utils.config import load_config
from src.utils.types import SignalTier


def _build_sources() -> list:
    cfg = load_config("config/politics.yaml")
    src_cfg = cfg.get("news_sources", {})
    official_cfg = cfg.get("official_sources", [])

    sources = []

    for item in src_cfg.get("tier_1", []):
        if item.get("kind") == "rss" and item.get("url"):
            sources.append(
                RSSSource(
                    source_name=item["name"],
                    feed_urls=[item["url"]],
                    tier=SignalTier.TIER_1,
                )
            )
    for item in src_cfg.get("tier_2", []):
        if item.get("kind") == "rss" and item.get("url"):
            sources.append(
                RSSSource(
                    source_name=item["name"],
                    feed_urls=[item["url"]],
                    tier=SignalTier.TIER_2,
                )
            )

    for item in official_cfg:
        if item.get("url"):
            sources.append(
                OfficialSource(
                    source_name=item["name"],
                    endpoints=[item["url"]],
                )
            )

    return sources


async def main() -> None:
    sources = _build_sources()
    if not sources:
        raise RuntimeError("No RSS/official sources configured.")

    print(f"Polling {len(sources)} sources once...")
    polled = []
    for source in sources:
        try:
            signals = await source.poll()
            print(f"- {source.source_name}: {len(signals)} signals")
            polled.extend(signals)
        except Exception as exc:  # noqa: BLE001
            print(f"- {source.source_name}: ERROR {exc}")

    aggregator = SignalAggregator([], config=AggregatorConfig(max_queue_size=1000, dedupe_window_seconds=3600))
    await aggregator.put_many(polled)
    total = aggregator._queue.qsize()
    print(f"Deduped queue size: {total}")

    try:
        for i in range(min(10, total)):
            signal = await asyncio.wait_for(aggregator.get(), timeout=2)
            print(
                f"[{i+1}] {signal.timestamp.isoformat()} | {signal.source_name} | "
                f"{signal.tier.value} | {signal.headline[:120]}"
            )
    finally:
        for source in sources:
            close = getattr(source, "close", None)
            if callable(close):
                maybe = close()
                if asyncio.iscoroutine(maybe):
                    await maybe
        print("Stopped aggregator.")


if __name__ == "__main__":
    asyncio.run(main())

