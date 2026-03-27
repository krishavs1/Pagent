"""Phase 2 smoke runner: classifier -> Bayesian -> edge.

This script is intentionally lightweight and safe:
- Uses a mocked classifier payload by default (no API calls)
- Runs one synthetic signal through scoring components
- Prints intermediate outputs for quick sanity checks

Usage:
  . .venv/bin/activate
  python scripts/phase2_smoke.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Ensure `src` imports resolve when script is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scoring.bayesian import BayesianEngine
from src.scoring.classifier import SignalClassifier
from src.scoring.edge import EdgeCalculator
from src.utils.types import MarketState, Signal, SignalTier, SignalType


def build_sample_market() -> MarketState:
    """Create a synthetic market snapshot for smoke testing."""
    return MarketState(
        condition_id="sample-market-1",
        question="Will a cabinet nominee be confirmed this week?",
        description="Synthetic market for Phase 2 smoke testing.",
        tags=["Politics"],
        entities=["cabinet", "nominee", "senate"],
        mid_price=0.62,
        spread=0.02,
        volume_24h=150_000.0,
        liquidity=25_000.0,
        best_bid_yes=0.61,
        best_ask_yes=0.63,
        bid_depth_usd=12_000.0,
        ask_depth_usd=11_000.0,
        last_updated=datetime.now(timezone.utc),
    )


def build_sample_signal() -> Signal:
    """Create a synthetic incoming signal for smoke testing."""
    return Signal(
        id="sample-signal-1",
        source_name="AP Politics",
        tier=SignalTier.TIER_1,
        signal_type=SignalType.CREDIBLE_SCOOP,
        headline="AP: Senate expected to confirm nominee after procedural vote",
        body="Multiple senators indicate final confirmation is likely this week.",
        entities=["senate", "nominee", "confirmation"],
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=20),
        relevance_score=0.8,
        direction=None,
        confidence=0.0,
    )


async def main() -> None:
    """Run a single mocked scoring pass and print outputs."""
    market = build_sample_market()
    signal = build_sample_signal()

    classifier = SignalClassifier()
    bayes = BayesianEngine()
    edge_calc = EdgeCalculator()

    # Keep smoke test deterministic and offline by monkeypatching request method.
    classifier._request_classification = lambda _signal: {  # type: ignore[method-assign]
        "signal_type": "OFFICIAL_OUTCOME",
        "direction": "YES",
        "confidence": 0.86,
        "relevance_score": 0.91,
    }
    classification = await classifier.classify(signal)

    prior = market.mid_price
    evidence_strength = 0.5 + 0.5 * (classification.confidence if classification.direction and classification.direction > 0 else -classification.confidence)
    posterior = bayes.bayes_update(prior=prior, likelihood_yes=evidence_strength, likelihood_no=1.0 - evidence_strength)

    edge = edge_calc.compute(
        market=market,
        signal_ids=[signal.id],
        prior=prior,
        posterior=posterior,
        estimated_slippage=0.01,
        signal_timestamp=signal.timestamp,
        now=datetime.now(timezone.utc),
    )

    print("=== Phase 2 Smoke ===")
    print("classification:", classification)
    print(f"prior={prior:.4f} posterior={posterior:.4f}")
    print(
        "edge:",
        {
            "raw_edge": round(edge.raw_edge, 6),
            "decay_factor": round(edge.decay_factor, 6),
            "adjusted_edge": round(edge.adjusted_edge, 6),
        },
    )


if __name__ == "__main__":
    asyncio.run(main())

