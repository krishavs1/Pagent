"""Build `NewsSource` instances from merged YAML config."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from src.ingestion.base import NewsSource
from src.ingestion.official import OfficialSource
from src.ingestion.rss import RSSSource
from src.ingestion.x_api import XApiSource
from src.utils.types import SignalTier, SignalType


_TIER_KEYS = {
    "tier_1": SignalTier.TIER_1,
    "tier_2": SignalTier.TIER_2,
    "tier_3": SignalTier.TIER_3,
    "tier_4": SignalTier.TIER_4,
}


def _skip_url(url: str) -> bool:
    if "example.com" in url:
        return True
    return False


def build_news_sources(cfg: Dict[str, Any]) -> List[NewsSource]:
    """Construct RSS and X sources from `news_sources` + `official_sources`."""
    sources: List[NewsSource] = []
    ns = cfg.get("news_sources") or {}

    for tier_key, tier in _TIER_KEYS.items():
        for item in ns.get(tier_key, []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "unknown"))
            kind = item.get("kind")
            typ = item.get("type")

            if kind == "rss" and item.get("url"):
                url = str(item["url"])
                if _skip_url(url):
                    continue
                sources.append(
                    RSSSource(
                        source_name=name,
                        feed_urls=[url],
                        tier=tier,
                        default_signal_type=SignalType.CREDIBLE_SCOOP,
                    )
                )
                continue

            if typ == "x_api" or kind == "x_api":
                if not os.getenv("X_BEARER_TOKEN"):
                    continue
                accounts = list(item.get("accounts") or [])
                keywords = list(item.get("keywords") or [])
                sources.append(
                    XApiSource(
                        source_name=name,
                        accounts=accounts,
                        keywords=keywords,
                        poll_seconds=int(item.get("poll_seconds", 60)),
                        max_results_per_account=int(item.get("max_results_per_account", 5)),
                    )
                )

    for item in cfg.get("official_sources") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or not str(url).startswith("http"):
            continue
        if _skip_url(str(url)):
            continue
        sources.append(
            OfficialSource(
                source_name=str(item.get("name", "official")),
                tier=SignalTier.TIER_1,
                endpoints=[str(url)],
                default_signal_type=SignalType.OFFICIAL_OUTCOME,
            )
        )

    return sources
