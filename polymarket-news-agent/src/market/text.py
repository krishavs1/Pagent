"""Lightweight text helpers for entity-ish tokens (no LLM)."""

from __future__ import annotations

import re
from typing import FrozenSet

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-']{2,}")

_STOP: FrozenSet[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "will",
        "has",
        "are",
        "was",
        "were",
        "been",
        "have",
        "not",
        "but",
        "can",
        "may",
        "any",
        "all",
        "out",
        "its",
        "his",
        "her",
        "they",
        "them",
        "their",
        "than",
        "into",
        "over",
        "such",
        "market",
        "markets",
        "before",
        "after",
        "when",
        "what",
        "which",
        "about",
        "does",
        "did",
        "get",
        "one",
        "two",
        "yes",
        "you",
        "your",
    }
)


def tokenize(text: str) -> set[str]:
    """Lowercase word tokens suitable for overlap scoring."""
    return {m.group(0).lower() for m in _WORD.finditer(text or "")} - _STOP


def extract_entity_tokens(question: str, description: str) -> list[str]:
    """Cheap 'entities': distinct tokens from title + body (sorted for stability)."""
    bag = tokenize(f"{question}\n{description}")
    return sorted(bag)

