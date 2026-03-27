"""X (Twitter) API v2 adapter using pay-per-use Bearer Token auth.

Polls recent posts from configured political reporter accounts using
the X API v2 /2/tweets/search/recent endpoint. Uses app-only Bearer
Token authentication (read-only public data).

Pricing: $0.005 per post read, $0.01 per user lookup.
Deduplication: X deduplicates within a 24-hour UTC window, so re-reading
the same tweet in a day does not incur additional cost.

Docs: https://docs.x.com/x-api/posts/search/api-reference/get-tweets-search-recent
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from src.ingestion.base import NewsSource
from src.utils.types import Signal, SignalTier, SignalType


class XApiSource(NewsSource):
    """Polls X API v2 for recent posts from political reporters.

    Uses /2/tweets/search/recent with a query built from configured
    accounts and keywords. Bearer Token is loaded from X_BEARER_TOKEN env var.
    """

    BASE_URL = "https://api.x.com/2"

    def __init__(
        self,
        accounts: list[str],
        keywords: list[str],
        poll_seconds: int = 60,
        max_results_per_account: int = 5,
        bearer_token: Optional[str] = None,
    ):
        """Initialize X API source.

        Args:
            accounts: X usernames to monitor (without @).
            keywords: Keywords to filter for (e.g. "BREAKING").
            poll_seconds: Polling interval in seconds.
            max_results_per_account: Max recent tweets to fetch per account per poll.
            bearer_token: X API Bearer Token. Falls back to X_BEARER_TOKEN env var.
        """

        super().__init__(source_name="x_api")
        self.accounts = accounts
        self.keywords = keywords
        self.poll_seconds = poll_seconds
        self.max_results = max_results_per_account
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN")
        self._last_seen_ids: dict[str, str] = {}  # account -> newest tweet ID seen
        self._session: Optional[aiohttp.ClientSession] = None

    def _build_query(self) -> str:
        """Build X API v2 search query string.

        Combines account filters with keyword filters using OR logic.
        Example: (from:jakesherman OR from:AP) (BREAKING OR "JUST IN")
        """
        raise NotImplementedError

    def _get_headers(self) -> dict[str, str]:
        """Return auth headers with Bearer Token."""
        if not self.bearer_token:
            raise ValueError("X_BEARER_TOKEN not set in environment or constructor")
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

    async def poll(self) -> list[Signal]:
        """Fetch recent posts matching query, return new signals since last poll.

        Uses /2/tweets/search/recent with since_id to avoid re-fetching.
        Assigns SignalTier.TIER_3_INSIDER to all results.
        """
        raise NotImplementedError

    async def _search_recent(self, query: str, since_id: Optional[str] = None) -> dict:
        """Call GET /2/tweets/search/recent.

        Args:
            query: X API v2 search query string.
            since_id: Only return tweets newer than this ID.

        Returns:
            Raw API response dict.
        """
        raise NotImplementedError

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()

