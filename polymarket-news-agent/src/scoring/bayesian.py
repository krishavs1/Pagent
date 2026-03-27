"""
Sequential Bayesian updating engine.

Planned responsibilities:
- Maintain per-market priors/posteriors for YES outcome probabilities
- Update beliefs given new evidence from signals/classifications
- Support configurable priors by signal tier/type and evidence strength

No Bayesian math is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from src.utils.types import EdgeEstimate, MarketState, Signal


@dataclass(slots=True)
class BayesianConfig:
    """Configuration for priors and evidence mapping."""

    default_prior: float = 0.5


class BayesianEngine:
    """Maintains and updates posterior beliefs for markets."""

    def __init__(self, config: Optional[BayesianConfig] = None) -> None:
        self._config = config or BayesianConfig()

    def get_prior(self, market_id: str) -> float:
        """Return the current prior probability for a market."""
        raise NotImplementedError("Prior retrieval not implemented in scaffold.")

    def update(self, market: MarketState, signal: Signal, evidence_strength: float) -> float:
        """Update posterior belief for a market and return the new posterior."""
        raise NotImplementedError("Bayesian update not implemented in scaffold.")

