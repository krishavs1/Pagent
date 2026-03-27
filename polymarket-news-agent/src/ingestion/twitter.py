"""
X (Twitter) ingestion source.

Planned responsibilities:
- Connect to a filtered stream or periodically search recent posts
- Apply lightweight keyword/entity filters at the edge
- Normalize posts into `Signal` objects with appropriate tiering

No API calls are implemented in this scaffold.
"""

from __future__ import annotations

from typing import List, Optional

from src.ingestion.base import NewsSource
from src.utils.types import Signal, SignalTier, SignalType


class TwitterSource(NewsSource):
    """Consumes a filtered X stream and emits normalized `Signal` objects."""

    def __init__(
        self,
        source_name: str,
        tier: SignalTier,
        query: str,
        bearer_token_env: str = "TWITTER_BEARER_TOKEN",
        default_signal_type: SignalType = SignalType.INSIDER_LEAK,
        language: Optional[str] = "en",
    ) -> None:
        super().__init__(source_name=source_name)
        self._tier = tier
        self._query = query
        self._bearer_token_env = bearer_token_env
        self._default_signal_type = default_signal_type
        self._language = language

    async def poll(self) -> List[Signal]:
        """Fetch or stream posts and normalize them into `Signal` objects."""
        raise NotImplementedError("Twitter ingestion not implemented in scaffold.")

