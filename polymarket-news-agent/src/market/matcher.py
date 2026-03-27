"""
Signal-to-market matching.

Ranks indexed markets by token overlap between signal entities/headline/body
and each market's question, description, and extracted entity tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from src.market.indexer import MarketIndexer
from src.market.text import tokenize
from src.utils.types import MarketState, Signal


@dataclass(slots=True)
class MatcherConfig:
    """Configuration for matching thresholds and limits."""

    max_candidates: int = 25
    min_entity_overlap: int = 1
    enable_semantic_fallback: bool = False


class MarketMatcher:
    """Finds candidate markets relevant to a given signal."""

    def __init__(self, indexer: MarketIndexer, config: Optional[MatcherConfig] = None) -> None:
        self._indexer = indexer
        self._config = config or MatcherConfig()

    def match(self, signal: Signal) -> List[Tuple[MarketState, float]]:
        """Return ranked (market, relevance_score) pairs (higher is better)."""
        if not signal.entities:
            return []

        signal_tokens: set[str] = set()
        for ent in signal.entities:
            e = ent.strip()
            if not e:
                continue
            signal_tokens.add(e.lower())
            signal_tokens |= tokenize(e)

        signal_tokens |= tokenize(signal.headline)
        signal_tokens |= tokenize(signal.body)

        if not signal_tokens:
            return []

        scored: list[tuple[MarketState, float]] = []
        for m in self._indexer.all_markets():
            m_tokens: set[str] = set()
            m_tokens |= {t.lower() for t in m.entities}
            m_tokens |= tokenize(m.question)
            m_tokens |= tokenize(m.description)

            overlap = signal_tokens & m_tokens
            if len(overlap) < self._config.min_entity_overlap:
                continue

            union = signal_tokens | m_tokens
            jaccard = len(overlap) / len(union) if union else 0.0
            coverage = len(overlap) / max(1, len(signal_tokens))
            score = 0.6 * jaccard + 0.4 * coverage
            scored.append((m, score))

        scored.sort(key=lambda x: (-x[1], x[0].question))
        return scored[: self._config.max_candidates]
