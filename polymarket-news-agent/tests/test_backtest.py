"""Tests for backtest timeline resolution and MTM cash/share accounting."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backtest.runner import BacktestConfig, BacktestRunner
from src.utils.types import OrderSide, TradeDecision


def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_resolve_timeline_nearest_prior() -> None:
    runner = BacktestRunner(BacktestConfig(data_dir=Path(".")))
    raw: dict = {
        "mid_price": 0.5,
        "orderbook": {"bids": [], "asks": []},
        "timeline": [
            {"timestamp": "2024-01-01T10:00:00Z", "mid_price": 0.40},
            {"timestamp": "2024-01-01T12:00:00Z", "mid_price": 0.60},
        ],
    }
    out = runner._resolve_market_snapshot_at(raw, _utc("2024-01-01T11:00:00Z"))
    assert abs(float(out["mid_price"]) - 0.40) < 1e-9


def test_resolve_timeline_uses_latest_before_or_equal() -> None:
    runner = BacktestRunner(BacktestConfig(data_dir=Path(".")))
    raw: dict = {
        "mid_price": 0.5,
        "timeline": [
            {"timestamp": "2024-01-01T10:00:00Z", "mid_price": 0.40},
            {"timestamp": "2024-01-01T12:00:00Z", "mid_price": 0.60},
        ],
    }
    out = runner._resolve_market_snapshot_at(raw, _utc("2024-01-01T13:00:00Z"))
    assert abs(float(out["mid_price"]) - 0.60) < 1e-9


def test_resolve_before_first_timeline_row_uses_earliest() -> None:
    runner = BacktestRunner(BacktestConfig(data_dir=Path(".")))
    raw: dict = {
        "mid_price": 0.99,
        "timeline": [
            {"timestamp": "2024-01-01T10:00:00Z", "mid_price": 0.40},
            {"timestamp": "2024-01-01T12:00:00Z", "mid_price": 0.60},
        ],
    }
    out = runner._resolve_market_snapshot_at(raw, _utc("2024-01-01T09:00:00Z"))
    assert abs(float(out["mid_price"]) - 0.40) < 1e-9


def test_apply_fill_buy_updates_cash_and_shares() -> None:
    t = TradeDecision(
        market_id="m1",
        edge=0.1,
        side=OrderSide.BUY,
        size_usd=10.0,
        limit_price=0.5,
        kelly_fraction=0.05,
        reason="test",
        timestamp=_utc("2024-01-01T12:00:00Z"),
        executed=True,
        fill_price=0.5,
        fill_size=10.0,
    )
    cash, shares = BacktestRunner._apply_fill_to_cash_shares(1000.0, {}, t)
    assert abs(cash - 990.0) < 1e-9
    assert abs(shares["m1"] - 20.0) < 1e-9


def test_equity_mtm_matches_cash_plus_shares_times_mid() -> None:
    runner = BacktestRunner(BacktestConfig(data_dir=Path(".")))
    snaps = {
        "m1": {"mid_price": 0.25, "timeline": []},
    }
    eq, pos = runner._equity_mtm(100.0, {"m1": 400.0}, _utc("2024-01-01T12:00:00Z"), snaps)
    assert abs(pos - 100.0) < 1e-9
    assert abs(eq - 200.0) < 1e-9


def test_time_under_water_counts_post_peak_dips() -> None:
    s = [1000.0, 1010.0, 1005.0, 1020.0]
    assert BacktestRunner._time_under_water_events(s) == 1
