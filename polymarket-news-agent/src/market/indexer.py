"""
Market indexer.

Fetches active markets from the Polymarket Gamma API, applies tag/volume/liquidity
filters from config, extracts simple keyword "entities", and keeps an in-memory
index keyed by `condition_id`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urljoin

import aiohttp

from src.market.text import extract_entity_tokens, tokenize
from src.utils.types import MarketState

logger = logging.getLogger(__name__)

# Safety cap: Gamma may return many pages; keep refresh bounded.
_MAX_PAGES_PER_TAG = 50


def _tag_slug(label: str) -> str:
    return label.strip().lower().replace(" ", "-")


def _parse_json_list(raw: Optional[str]) -> list[Any]:
    if not raw:
        return []
    try:
        out = json.loads(raw)
        return out if isinstance(out, list) else []
    except json.JSONDecodeError:
        return []


def _floatish(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _gamma_market_to_state(m: dict[str, Any], now: datetime) -> Optional[MarketState]:
    condition_id = m.get("conditionId") or m.get("condition_id")
    question = (m.get("question") or "").strip()
    if not condition_id or not question:
        return None

    description = (m.get("description") or "").strip()
    outcomes = _parse_json_list(m.get("outcomes"))
    prices = _parse_json_list(m.get("outcomePrices"))
    mid = 0.5
    if prices:
        mid = _floatish(prices[0], 0.5)

    token_ids = _parse_json_list(m.get("clobTokenIds"))
    yes_token_id: Optional[str] = str(token_ids[0]) if token_ids else None

    tags: list[str] = []
    for ev in m.get("events") or []:
        if isinstance(ev, dict):
            cat = ev.get("category")
            if isinstance(cat, str) and cat:
                tags.append(cat)
            slug = ev.get("slug")
            if isinstance(slug, str) and slug:
                tags.append(slug)

    entities = extract_entity_tokens(question, description)

    vol24 = _floatish(m.get("volume24hrClob", m.get("volume24hr")), 0.0)
    liq = _floatish(m.get("liquidityNum", m.get("liquidityClob")), 0.0)

    spread = 0.0
    best_bid = max(0.0, mid - spread / 2)
    best_ask = min(1.0, mid + spread / 2)

    return MarketState(
        condition_id=str(condition_id),
        question=question,
        description=description,
        tags=tags,
        entities=entities,
        mid_price=mid,
        spread=spread,
        volume_24h=vol24,
        liquidity=liq,
        best_bid_yes=best_bid,
        best_ask_yes=best_ask,
        bid_depth_usd=0.0,
        ask_depth_usd=0.0,
        last_updated=now,
        yes_token_id=yes_token_id,
    )


def _market_excludes_tag(m: dict[str, Any], exclude_slugs: set[str]) -> bool:
    blob = json.dumps(m, default=str).lower()
    for ex in exclude_slugs:
        if ex and ex.lower() in blob:
            return True
    return False


@dataclass(slots=True)
class MarketIndexerConfig:
    """Configuration for market indexing and filtering."""

    include_tags: List[str]
    exclude_tags: List[str]
    min_volume_24h: float
    min_liquidity: float


class MarketIndexer:
    """Fetches and indexes active Polymarket markets."""

    def __init__(self, config: MarketIndexerConfig, gamma_base_url: str) -> None:
        self._config = config
        self._gamma_base_url = gamma_base_url.rstrip("/")
        self._by_condition: Dict[str, MarketState] = {}

    async def refresh(self) -> None:
        """Refresh the active market universe and rebuild indexes."""
        include_slugs = [_tag_slug(t) for t in self._config.include_tags if t.strip()]
        exclude_slugs = {_tag_slug(t) for t in self._config.exclude_tags if t.strip()}

        seen: dict[str, dict[str, Any]] = {}
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for slug in include_slugs:
                offset = 0
                limit = 100
                page = 0
                while page < _MAX_PAGES_PER_TAG:
                    url = urljoin(self._gamma_base_url + "/", "markets")
                    params: dict[str, Any] = {
                        "tag_slug": slug,
                        "active": "true",
                        "closed": "false",
                        "limit": limit,
                        "offset": offset,
                    }
                    async with session.get(url, params=params) as resp:
                        resp.raise_for_status()
                        chunk = await resp.json()
                    if not isinstance(chunk, list) or not chunk:
                        break
                    for m in chunk:
                        if not isinstance(m, dict):
                            continue
                        cid = m.get("conditionId") or m.get("condition_id")
                        if cid:
                            seen[str(cid)] = m
                    if len(chunk) < limit:
                        break
                    offset += limit
                    page += 1

        now = datetime.now(timezone.utc)
        self._by_condition.clear()

        for m in seen.values():
            if _market_excludes_tag(m, exclude_slugs):
                continue
            vol = _floatish(m.get("volume24hrClob", m.get("volume24hr")), 0.0)
            liq = _floatish(m.get("liquidityNum", m.get("liquidityClob")), 0.0)
            if vol < self._config.min_volume_24h or liq < self._config.min_liquidity:
                continue
            state = _gamma_market_to_state(m, now)
            if state is not None:
                self._by_condition[state.condition_id] = state

        logger.info("Indexed %d markets after filters", len(self._by_condition))

    def get_market(self, condition_id: str) -> Optional[MarketState]:
        """Retrieve a `MarketState` snapshot by condition_id."""
        return self._by_condition.get(condition_id)

    def search_by_entities(self, entities: Sequence[str], limit: int = 25) -> List[MarketState]:
        """Return candidate markets matching the provided entities (keyword overlap)."""
        if not entities:
            return []
        qset = {e.strip().lower() for e in entities if e.strip()}
        if not qset:
            return []

        scored: list[tuple[MarketState, int]] = []
        for m in self._by_condition.values():
            mset = {t.lower() for t in m.entities} | tokenize(m.question)
            overlap = len(qset & mset)
            if overlap > 0:
                scored.append((m, overlap))

        scored.sort(key=lambda x: (-x[1], x[0].question))
        return [m for m, _ in scored[:limit]]

    def all_markets(self) -> Iterable[MarketState]:
        """Iterate over all currently indexed markets."""
        return self._by_condition.values()


async def _cli_async() -> None:
    from src.utils.config import load_config

    cfg = load_config("config/politics.yaml")
    mf = cfg.get("market_filters") or {}
    api = cfg.get("api") or {}
    gamma = (api.get("polymarket") or {}).get("gamma_base_url", "https://gamma-api.polymarket.com")

    indexer = MarketIndexer(
        MarketIndexerConfig(
            include_tags=list(mf.get("include_tags") or []),
            exclude_tags=list(mf.get("exclude_tags") or []),
            min_volume_24h=float(mf.get("min_volume_24h", 0)),
            min_liquidity=float(mf.get("min_liquidity", 0)),
        ),
        gamma_base_url=gamma,
    )
    await indexer.refresh()
    rows = list(indexer.all_markets())
    print(f"markets={len(rows)}")
    for m in sorted(rows, key=lambda x: -x.volume_24h)[:30]:
        print(f"{m.mid_price:.4f}\t{m.volume_24h:,.0f}\t{m.question[:100]}")


def _cli() -> None:
    asyncio.run(_cli_async())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cli()
