"""
LLM-based signal classification.

Planned responsibilities:
- Use the Anthropic (Claude) API to classify a `Signal` into:
  - refined SignalType (if ingestion default was coarse)
  - direction (expected YES probability move)
  - confidence and relevance
- Provide structured outputs suitable for downstream Bayesian updating

No API calls are implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.types import Signal, SignalType


@dataclass(slots=True)
class ClassificationResult:
    """Structured classification output for a signal."""

    signal_type: SignalType
    direction: Optional[float]
    confidence: float
    relevance_score: float


class SignalClassifier:
    """Classifies signals using an LLM provider (Claude)."""

    def __init__(self, anthropic_api_key_env: str = "ANTHROPIC_API_KEY", model: str = "claude-3-5-sonnet-latest") -> None:
        self._anthropic_api_key_env = anthropic_api_key_env
        self._model = model

    async def classify(self, signal: Signal) -> ClassificationResult:
        """Return a structured classification result for the given signal."""
        raise NotImplementedError("LLM classification not implemented in scaffold.")

