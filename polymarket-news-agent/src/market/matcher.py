"""
Signal-to-market matching.

Planned responsibilities:
- Given a `Signal`, find relevant markets using:
  - Entity overlap (fast)
  - Keyword heuristics (fallback)
  - Optional semantic matching (embedding/LLM-assisted) for ambiguous cases
- Produce a ranked list of candidate markets for scoring

No matching logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from src.market.indexer import MarketIndexer
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

    def match(self, signal: Signal) -> List[MarketState]:
        """Return a ranked list of candidate markets for a signal."""
        raise NotImplementedError("Market matching not implemented in scaffold.")

