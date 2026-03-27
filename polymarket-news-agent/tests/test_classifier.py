"""Tests for signal classification."""

from datetime import datetime, timezone

import pytest

from src.scoring.classifier import SignalClassifier
from src.utils.types import Signal, SignalTier, SignalType


def _signal() -> Signal:
    return Signal(
        id="s1",
        source_name="AP",
        tier=SignalTier.TIER_1,
        signal_type=SignalType.CREDIBLE_SCOOP,
        headline="AP: Senate confirms nominee",
        body="Details...",
        entities=["senate", "nominee"],
        timestamp=datetime.now(timezone.utc),
    )


def test_parse_response_happy_path() -> None:
    c = SignalClassifier()
    out = c._parse_response(
        {
            "signal_type": "OFFICIAL_OUTCOME",
            "direction": "YES",
            "confidence": 0.85,
            "relevance_score": 0.9,
        }
    )
    assert out.signal_type == SignalType.OFFICIAL_OUTCOME
    assert out.direction == 1.0
    assert out.confidence == pytest.approx(0.85)
    assert out.relevance_score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_classify_uses_retry_and_returns_parsed_result() -> None:
    c = SignalClassifier(max_retries=2)
    calls = {"n": 0}

    def fake_request(signal: Signal):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("transient")
        return {
            "signal_type": "PUNDIT_SPECULATION",
            "direction": "NO",
            "confidence": 0.2,
            "relevance_score": 0.3,
        }

    c._request_classification = fake_request  # type: ignore[method-assign]
    out = await c.classify(_signal())
    assert calls["n"] == 2
    assert out.signal_type == SignalType.PUNDIT_SPECULATION
    assert out.direction == -1.0


@pytest.mark.asyncio
async def test_classify_raises_after_retry_exhaustion() -> None:
    c = SignalClassifier(max_retries=1)

    def always_fail(signal: Signal):  # noqa: ANN001
        raise RuntimeError("nope")

    c._request_classification = always_fail  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="Failed to classify signal"):
        await c.classify(_signal())

