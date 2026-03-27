"""Sequential Bayesian updating engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence

from src.utils.types import MarketState, Signal


@dataclass(slots=True)
class BayesianConfig:
    """Configuration for priors and evidence mapping."""

    default_prior: float = 0.5
    min_likelihood: float = 1e-6
    max_likelihood: float = 1.0 - 1e-6


class BayesianEngine:
    """Maintains and updates posterior beliefs for markets."""

    def __init__(self, config: Optional[BayesianConfig] = None) -> None:
        self._config = config or BayesianConfig()
        self._posteriors: Dict[str, float] = {}

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _clamp_likelihood(self, value: float) -> float:
        return max(self._config.min_likelihood, min(self._config.max_likelihood, value))

    def bayes_update(self, prior: float, likelihood_yes: float, likelihood_no: float) -> float:
        """Apply one Bayes update and return posterior."""
        prior = self._clamp01(prior)
        if prior in (0.0, 1.0):
            return prior

        ly = self._clamp_likelihood(likelihood_yes)
        ln = self._clamp_likelihood(likelihood_no)

        numerator = prior * ly
        denominator = numerator + (1.0 - prior) * ln
        if denominator <= 0.0:
            return prior
        return self._clamp01(numerator / denominator)

    def update_multiple(self, prior: float, evidence: Sequence[tuple[float, float]]) -> float:
        """Chain multiple Bayes updates in sequence."""
        posterior = self._clamp01(prior)
        for likelihood_yes, likelihood_no in evidence:
            posterior = self.bayes_update(posterior, likelihood_yes, likelihood_no)
        return posterior

    def get_prior(self, market_id: str) -> float:
        """Return the current prior probability for a market."""
        return self._posteriors.get(market_id, self._config.default_prior)

    def set_prior(self, market_id: str, prior: float) -> None:
        """Set or override a prior/posterior anchor for a market."""
        self._posteriors[market_id] = self._clamp01(prior)

    def seed_prior_if_missing(self, market_id: str, mid: float) -> None:
        """Set prior from market-implied probability if no belief stored yet."""
        if market_id not in self._posteriors:
            self.set_prior(market_id, mid)

    def update_from_likelihoods(self, market_id: str, likelihood_yes: float, likelihood_no: float) -> float:
        """Update stored posterior for market from explicit likelihoods."""
        prior = self.get_prior(market_id)
        posterior = self.bayes_update(prior, likelihood_yes, likelihood_no)
        self._posteriors[market_id] = posterior
        return posterior

    def update(self, market: MarketState, signal: Signal, evidence_strength: float) -> float:
        """
        Update posterior belief using a simple evidence strength mapping.

        `evidence_strength` is interpreted in [0, 1]:
        - 0.5 = neutral evidence (no update)
        - >0.5 = YES-supporting evidence
        - <0.5 = NO-supporting evidence
        """
        strength = self._clamp01(evidence_strength)
        likelihood_yes = self._clamp_likelihood(strength)
        likelihood_no = self._clamp_likelihood(1.0 - strength)
        return self.update_from_likelihoods(market.condition_id, likelihood_yes, likelihood_no)

