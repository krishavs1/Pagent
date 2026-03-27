"""Tests for Bayesian update math."""

import pytest

from src.scoring.bayesian import BayesianEngine


def test_single_update_half_prior_goes_to_0_9() -> None:
    eng = BayesianEngine()
    posterior = eng.bayes_update(0.5, 0.9, 0.1)
    assert posterior == pytest.approx(0.9, abs=1e-9)


def test_single_update_known_value() -> None:
    eng = BayesianEngine()
    posterior = eng.bayes_update(0.7, 0.95, 0.05)
    assert posterior == pytest.approx(0.97794117647, rel=1e-6)


def test_no_direction_signal_reduces_prior() -> None:
    eng = BayesianEngine()
    # NO-supporting evidence -> lower posterior.
    posterior = eng.bayes_update(0.7, 0.2, 0.8)
    assert posterior < 0.7


def test_neutral_signal_keeps_prior() -> None:
    eng = BayesianEngine()
    posterior = eng.bayes_update(0.37, 0.5, 0.5)
    assert posterior == pytest.approx(0.37, abs=1e-9)


def test_extreme_prior_and_strong_yes_stays_below_one() -> None:
    eng = BayesianEngine()
    posterior = eng.bayes_update(0.01, 0.99, 0.01)
    assert posterior > 0.01
    assert posterior < 1.0


def test_two_confirming_signals_compound() -> None:
    eng = BayesianEngine()
    p1 = eng.bayes_update(0.5, 0.8, 0.2)
    p2 = eng.bayes_update(p1, 0.8, 0.2)
    assert p2 > p1


def test_order_invariance_for_two_independent_signals() -> None:
    eng = BayesianEngine()
    s1 = (0.8, 0.2)
    s2 = (0.7, 0.3)
    a = eng.update_multiple(0.42, [s1, s2])
    b = eng.update_multiple(0.42, [s2, s1])
    assert a == pytest.approx(b, rel=1e-9)


def test_prior_zero_and_one_are_fixed_points() -> None:
    eng = BayesianEngine()
    assert eng.bayes_update(0.0, 0.9, 0.1) == 0.0
    assert eng.bayes_update(1.0, 0.9, 0.1) == 1.0

