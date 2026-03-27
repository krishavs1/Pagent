"""
Market indexer.

Planned responsibilities:
- Fetch active Polymarket markets (Gamma / CLOB metadata)
- Extract and normalize entities (people, elections, bills, etc.)
- Build a searchable in-memory index (and optionally persisted snapshots)

No network calls are implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from src.utils.types import MarketState


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
        self._gamma_base_url = gamma_base_url

    async def refresh(self) -> None:
        """Refresh the active market universe and rebuild indexes."""
        raise NotImplementedError("Market indexing not implemented in scaffold.")

    def get_market(self, condition_id: str) -> Optional[MarketState]:
        """Retrieve a `MarketState` snapshot by condition_id."""
        raise NotImplementedError("Index lookup not implemented in scaffold.")

    def search_by_entities(self, entities: Sequence[str], limit: int = 25) -> List[MarketState]:
        """Return candidate markets matching the provided entities."""
        raise NotImplementedError("Entity search not implemented in scaffold.")

    def all_markets(self) -> Iterable[MarketState]:
        """Iterate over all currently indexed markets."""
        raise NotImplementedError("Market iteration not implemented in scaffold.")

