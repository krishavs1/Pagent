"""Tests for signal-to-market matching."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from src.market.indexer import MarketIndexer, MarketIndexerConfig
from src.market.matcher import MarketMatcher, MatcherConfig
from src.utils.types import Signal, SignalTier, SignalType


def _ms(
    *,
    condition_id: str,
    question: str,
    description: str = "",
    entities: list[str] | None = None,
) -> "MarketState":
    from src.utils.types import MarketState

    now = datetime.now(timezone.utc)
    return MarketState(
        condition_id=condition_id,
        question=question,
        description=description,
        tags=[],
        entities=entities or [],
        mid_price=0.5,
        spread=0.02,
        volume_24h=100_000,
        liquidity=10_000,
        best_bid_yes=0.49,
        best_ask_yes=0.51,
        bid_depth_usd=1.0,
        ask_depth_usd=1.0,
        last_updated=now,
    )


def _sig(entities: list[str], headline: str, body: str = "") -> Signal:
    return Signal(
        id="s1",
        source_name="test",
        tier=SignalTier.TIER_2,
        signal_type=SignalType.CREDIBLE_SCOOP,
        headline=headline,
        body=body,
        entities=entities,
        timestamp=datetime.now(timezone.utc),
    )


def test_empty_entities_returns_empty() -> None:
    ix = MarketIndexer(MarketIndexerConfig([], [], 0, 0), "https://gamma-api.polymarket.com")
    ix._by_condition["a"] = _ms(condition_id="a", question="Biden wins", entities=["biden"])
    m = MarketMatcher(ix)
    s = _sig([], "headline")
    assert m.match(s) == []


def test_exact_entity_overlap_ranks_higher() -> None:
    ix = MarketIndexer(MarketIndexerConfig([], [], 0, 0), "https://gamma-api.polymarket.com")
    ix._by_condition["x"] = _ms(
        condition_id="x",
        question="Will Biden announce re-election?",
        description="US presidential politics",
        entities=["biden", "announce"],
    )
    ix._by_condition["y"] = _ms(
        condition_id="y",
        question="Fed cuts rates in 2026?",
        description="Macro",
        entities=["fed", "rates"],
    )
    matcher = MarketMatcher(ix)
    s = _sig(["Biden", "announce"], "Breaking: Biden schedule", "White House")
    out = matcher.match(s)
    assert [m.condition_id for m, _ in out][:1] == ["x"]


def test_partial_match_still_returns_results() -> None:
    ix = MarketIndexer(MarketIndexerConfig([], [], 0, 0), "https://gamma-api.polymarket.com")
    ix._by_condition["p"] = _ms(
        condition_id="p",
        question="Supreme Court to hear major abortion case",
        description="Docket watch",
        entities=["supreme", "court", "abortion"],
    )
    matcher = MarketMatcher(ix, MatcherConfig(min_entity_overlap=1))
    s = _sig(["Supreme Court", "abortion"], "SCOTUS grants cert")
    out = matcher.match(s)
    assert out and out[0][0].condition_id == "p"


def test_no_match_empty_when_no_overlap() -> None:
    ix = MarketIndexer(MarketIndexerConfig([], [], 0, 0), "https://gamma-api.polymarket.com")
    ix._by_condition["a"] = _ms(
        condition_id="a",
        question="2028 Republican presidential nominee?",
        entities=["republican", "nominee"],
    )
    matcher = MarketMatcher(ix, MatcherConfig(min_entity_overlap=2))
    s = _sig(["Supreme Court", "abortion"], "Different story")
    assert matcher.match(s) == []


def test_multiple_matches_ordered_by_score() -> None:
    ix = MarketIndexer(MarketIndexerConfig([], [], 0, 0), "https://gamma-api.polymarket.com")
    ix._by_condition["weak"] = _ms(
        condition_id="weak",
        question="Election polling snapshot",
        entities=["election", "biden"],
    )
    ix._by_condition["strong"] = _ms(
        condition_id="strong",
        question="Biden drops out of 2024 race",
        description="Democratic nominee shifts",
        entities=["biden", "drop", "democratic", "nominee"],
    )
    matcher = MarketMatcher(ix)
    s = _sig(["Biden", "nominee"], "Biden dropout", "Democratic party")
    out = matcher.match(s)
    ids = [m.condition_id for m, _ in out]
    assert "strong" in ids and "weak" in ids
    assert ids[0] == "strong"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_indexer_returns_markets() -> None:
    """Optional: hit Gamma (network). Run with RUN_NETWORK=1 pytest -m integration"""
    if os.getenv("RUN_NETWORK") != "1":
        pytest.skip("set RUN_NETWORK=1 to query Gamma API")
    from src.utils.config import load_config

    cfg = load_config("config/politics.yaml")
    mf = cfg["market_filters"]
    api = cfg.get("api") or {}
    gamma = (api.get("polymarket") or {}).get("gamma_base_url", "https://gamma-api.polymarket.com")
    ix = MarketIndexer(
        MarketIndexerConfig(
            include_tags=list(mf["include_tags"]),
            exclude_tags=list(mf["exclude_tags"]),
            min_volume_24h=float(mf["min_volume_24h"]),
            min_liquidity=float(mf["min_liquidity"]),
        ),
        gamma_base_url=gamma,
    )
    await ix.refresh()
    markets = list(ix.all_markets())
    assert markets
    for m in markets[:5]:
        assert m.condition_id
        assert m.question
        assert 0.0 <= m.mid_price <= 1.0
