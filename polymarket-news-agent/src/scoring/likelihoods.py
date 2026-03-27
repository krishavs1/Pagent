"""Map classifier output to Bernoulli likelihoods for Bayesian updates."""

from __future__ import annotations

from src.scoring.classifier import ClassificationResult


def likelihoods_from_classification(cr: ClassificationResult) -> tuple[float, float]:
    """Return (P(evidence|YES), P(evidence|NO)) for a binary YES market."""
    conf = max(0.0, min(1.0, cr.confidence))
    d = cr.direction
    if d is None or abs(d) < 1e-9:
        return 0.5, 0.5
    if d > 0:
        ly = 0.5 + 0.5 * conf
        ln = 1.0 - ly
    else:
        ly = 0.5 - 0.5 * conf
        ln = 1.0 - ly
    return ly, ln
