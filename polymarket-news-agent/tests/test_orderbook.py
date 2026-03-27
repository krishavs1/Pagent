"""Tests for orderbook-derived slippage (probability impact)."""

from __future__ import annotations

from py_clob_client.clob_types import OrderBookSummary, OrderSummary

from src.market.orderbook import _mid_spread, slippage_buy_yes_probability


def _book() -> OrderBookSummary:
    asks = [
        OrderSummary(price="0.50", size="100"),
        OrderSummary(price="0.52", size="100"),
        OrderSummary(price="0.55", size="100"),
    ]
    bids = [
        OrderSummary(price="0.48", size="100"),
        OrderSummary(price="0.46", size="100"),
    ]
    return OrderBookSummary(bids=bids, asks=asks)


def test_slippage_zero_for_zero_notional() -> None:
    book = _book()
    assert slippage_buy_yes_probability(book, mid=0.51, notional_usd=0.0) == 0.0


def test_slippage_nonnegative_and_bounded() -> None:
    book = _book()
    mid, _ = _mid_spread(book)
    s = slippage_buy_yes_probability(book, mid=mid, notional_usd=10.0)
    assert 0.0 <= s <= 1.0


def test_slippage_monotonic_in_notional() -> None:
    book = _book()
    mid, _ = _mid_spread(book)
    s10 = slippage_buy_yes_probability(book, mid, 10.0)
    s100 = slippage_buy_yes_probability(book, mid, 100.0)
    s500 = slippage_buy_yes_probability(book, mid, 500.0)
    assert s10 <= s100 <= s500
