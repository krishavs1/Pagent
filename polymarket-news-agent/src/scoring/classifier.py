"""LLM-based signal classification."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from anthropic import Anthropic

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

    def __init__(
        self,
        anthropic_api_key_env: str = "ANTHROPIC_API_KEY",
        model: str = "claude-3-5-sonnet-latest",
        timeout_seconds: int = 30,
        max_retries: int = 2,
    ) -> None:
        self._anthropic_api_key_env = anthropic_api_key_env
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    @staticmethod
    def _parse_signal_type(raw: str) -> SignalType:
        return SignalType[raw.strip().upper()]

    @staticmethod
    def _parse_direction(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return max(-1.0, min(1.0, float(raw)))
        token = str(raw).strip().upper()
        if token in {"YES", "UP", "POSITIVE"}:
            return 1.0
        if token in {"NO", "DOWN", "NEGATIVE"}:
            return -1.0
        if token in {"NEUTRAL", "NONE"}:
            return 0.0
        return None

    @staticmethod
    def _clamp01(value: Any, fallback: float = 0.5) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(0.0, min(1.0, v))

    def _build_prompt(self, signal: Signal) -> str:
        """Build a strict JSON classification prompt."""
        return (
            "Classify this political market signal and return strict JSON with keys: "
            "signal_type, direction, confidence, relevance_score.\n\n"
            f"Headline: {signal.headline}\n"
            f"Body: {signal.body}\n"
            f"Source: {signal.source_name}\n"
            "Allowed signal_type values: OFFICIAL_OUTCOME, CREDIBLE_SCOOP, INSIDER_LEAK, "
            "POLL_SHIFT, PUNDIT_SPECULATION.\n"
            "Allowed direction values: YES, NO, NEUTRAL.\n"
        )

    def _parse_response(self, payload: dict[str, Any]) -> ClassificationResult:
        """Parse model response JSON into typed result."""
        return ClassificationResult(
            signal_type=self._parse_signal_type(str(payload["signal_type"])),
            direction=self._parse_direction(payload.get("direction")),
            confidence=self._clamp01(payload.get("confidence"), fallback=0.5),
            relevance_score=self._clamp01(payload.get("relevance_score"), fallback=0.5),
        )

    def _request_classification(self, signal: Signal) -> dict[str, Any]:
        """Request structured classification from Anthropic."""
        api_key = os.getenv(self._anthropic_api_key_env)
        if not api_key:
            raise ValueError(f"{self._anthropic_api_key_env} is not set.")
        client = Anthropic(api_key=api_key, timeout=self._timeout_seconds)
        response = client.messages.create(
            model=self._model,
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": self._build_prompt(signal)}],
        )
        if not response.content:
            raise ValueError("Empty response from Anthropic classifier.")
        text_block = response.content[0].text
        parsed = json.loads(text_block)
        if not isinstance(parsed, dict):
            raise ValueError("Classifier response is not a JSON object.")
        return parsed

    async def classify(self, signal: Signal) -> ClassificationResult:
        """Return a structured classification result for the given signal."""
        last_error: Optional[Exception] = None
        for _ in range(self._max_retries + 1):
            try:
                payload = self._request_classification(signal)
                return self._parse_response(payload)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise RuntimeError("Failed to classify signal after retries.") from last_error

