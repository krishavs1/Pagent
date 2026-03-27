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
from typing import Any, Optional

import aiohttp

from src.ingestion.base import NewsSource
from src.market.text import tokenize
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
        source_name: str = "political_x",
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

        super().__init__(source_name=source_name)
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
        account_clause = " OR ".join([f"from:{a}" for a in self.accounts]) if self.accounts else ""
        keyword_parts = []
        for kw in self.keywords:
            kw = kw.strip()
            if not kw:
                continue
            if " " in kw:
                keyword_parts.append(f"\"{kw}\"")
            else:
                keyword_parts.append(kw)
        keyword_clause = " OR ".join(keyword_parts)
        if account_clause and keyword_clause:
            return f"({account_clause}) ({keyword_clause}) -is:retweet -is:reply lang:en"
        if account_clause:
            return f"({account_clause}) -is:retweet -is:reply lang:en"
        return f"({keyword_clause}) -is:retweet -is:reply lang:en"

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
        query = self._build_query()
        since_id = max(self._last_seen_ids.values(), default=None)
        payload = await self._search_recent(query=query, since_id=since_id)

        data = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(data, list):
            return []
        if not data:
            return []

        users_by_id: dict[str, dict[str, Any]] = {}
        includes = payload.get("includes", {}) if isinstance(payload, dict) else {}
        users = includes.get("users", []) if isinstance(includes, dict) else []
        if isinstance(users, list):
            for user in users:
                if isinstance(user, dict) and "id" in user:
                    users_by_id[str(user["id"])] = user

        newest_id = max(str(item.get("id", "0")) for item in data if isinstance(item, dict))
        for account in self.accounts:
            self._last_seen_ids[account] = newest_id

        out: list[Signal] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            tid = str(item.get("id", ""))
            text = str(item.get("text", "")).strip()
            if not tid or not text:
                continue
            author_id = str(item.get("author_id", "")) if item.get("author_id") is not None else ""
            username = users_by_id.get(author_id, {}).get("username") if author_id else None
            url = f"https://x.com/{username}/status/{tid}" if username else None
            created_at = str(item.get("created_at", ""))
            ts = datetime.now(timezone.utc)
            if created_at:
                try:
                    ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
                except ValueError:
                    pass
            out.append(
                Signal(
                    id=f"x:{tid}",
                    source_name=self.source_name,
                    tier=SignalTier.TIER_3,
                    signal_type=SignalType.INSIDER_LEAK,
                    headline=text[:140],
                    body=text,
                    entities=sorted(tokenize(text))[:30],
                    timestamp=ts,
                    url=url,
                    relevance_score=0.0,
                    direction=None,
                    confidence=0.0,
                )
            )
        return out

    async def _search_recent(self, query: str, since_id: Optional[str] = None) -> dict:
        """Call GET /2/tweets/search/recent.

        Args:
            query: X API v2 search query string.
            since_id: Only return tweets newer than this ID.

        Returns:
            Raw API response dict.
        """
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(timeout=timeout)
        params: dict[str, str | int] = {
            "query": query,
            "max_results": min(100, max(10, self.max_results * max(1, len(self.accounts)))),
            "tweet.fields": "id,text,author_id,created_at",
            "expansions": "author_id",
            "user.fields": "id,username,name",
        }
        if since_id:
            params["since_id"] = since_id
        async with self._session.get(
            f"{self.BASE_URL}/tweets/search/recent",
            params=params,
            headers=self._get_headers(),
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()

