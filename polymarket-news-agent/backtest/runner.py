"""Rigorous backtest runner using historical snapshot replay."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from src.execution.strategy import StrategyConfig, TradingStrategy
from src.risk.manager import RiskConfig, RiskManager
from src.scoring.bayesian import BayesianEngine
from src.scoring.classifier import ClassificationResult
from src.scoring.edge import EdgeCalculator, EdgeConfig
from src.scoring.likelihoods import likelihoods_from_classification
from src.utils.config import load_config
from src.utils.logger import AgentLogger
from src.utils.types import MarketState, OrderSide, PortfolioState, Signal, SignalTier, SignalType, TradeDecision


@dataclass(slots=True)
class BacktestConfig:
    """Configuration for backtest dataset and simulation mode."""

    data_dir: Path
    dataset_file: str = "biden_dropout_2024.json"
    config_path: str = "config/politics.yaml"
    settings_path: str = "config/settings.yaml"
    output_jsonl: Path = Path("backtest/results/biden_dropout_2024.jsonl")
    output_summary: Path = Path("backtest/results/biden_dropout_2024_summary.json")
    start_timestamp: Optional[float] = None
    end_timestamp: Optional[float] = None


class BacktestRunner:
    """Replays historical signals through the pipeline with a simulated clock."""

    def __init__(self, config: BacktestConfig) -> None:
        self._config = config

    def _parse_tier(self, raw: Any) -> SignalTier:
        if isinstance(raw, int):
            return {
                1: SignalTier.TIER_1,
                2: SignalTier.TIER_2,
                3: SignalTier.TIER_3,
                4: SignalTier.TIER_4,
            }.get(raw, SignalTier.TIER_3)
        text = str(raw or "TIER_3").upper()
        if text in {"1", "TIER_1"}:
            return SignalTier.TIER_1
        if text in {"2", "TIER_2"}:
            return SignalTier.TIER_2
        if text in {"4", "TIER_4"}:
            return SignalTier.TIER_4
        return SignalTier.TIER_3

    @staticmethod
    def _parse_signal_type(raw: Any) -> SignalType:
        text = str(raw or "CREDIBLE_SCOOP").upper()
        return SignalType[text] if text in SignalType.__members__ else SignalType.CREDIBLE_SCOOP

    @staticmethod
    def _parse_timestamp(raw: str) -> datetime:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)

    def _load_signals(self) -> list[Signal]:
        dataset_path = self._config.data_dir / self._config.dataset_file
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            events = data.get("signals", [])
        else:
            events = data
        if not isinstance(events, list):
            raise ValueError(f"Dataset signals must be a list: {dataset_path}")
        out: list[Signal] = []
        for i, item in enumerate(events):
            if not isinstance(item, dict):
                continue
            ts = self._parse_timestamp(str(item["timestamp"]))
            unix_ts = ts.timestamp()
            if self._config.start_timestamp is not None and unix_ts < self._config.start_timestamp:
                continue
            if self._config.end_timestamp is not None and unix_ts > self._config.end_timestamp:
                continue
            out.append(
                Signal(
                    id=str(item.get("id", f"bt-{i+1}")),
                    source_name=str(item.get("source", "backtest")),
                    tier=self._parse_tier(item.get("tier", 3)),
                    signal_type=self._parse_signal_type(item.get("signal_type")),
                    headline=str(item.get("headline", "")),
                    body=str(item.get("body", "")),
                    entities=list(item.get("entities", [])),
                    timestamp=ts,
                    url=item.get("url"),
                    relevance_score=float(item.get("relevance_score", 0.6)),
                    direction=float(item["direction"]) if item.get("direction") is not None else None,
                    confidence=float(item.get("confidence", 0.7)),
                )
            )
        out.sort(key=lambda s: s.timestamp)
        return out

    def _load_dataset(self) -> dict[str, Any]:
        dataset_path = self._config.data_dir / self._config.dataset_file
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {"signals": data, "markets": {}, "outcomes": {}}
        if isinstance(data, dict):
            return {
                "signals": data.get("signals", []),
                "markets": data.get("markets", {}),
                "outcomes": data.get("outcomes", {}),
                "execution": data.get("execution", {}),
            }
        raise ValueError("Unsupported dataset format.")

    @staticmethod
    def _market_from_snapshot(market_id: str, m: dict[str, Any], now: datetime) -> MarketState:
        return MarketState(
            condition_id=market_id,
            question=str(m.get("question", market_id)),
            description=str(m.get("description", "")),
            tags=list(m.get("tags", [])),
            entities=list(m.get("entities", [])),
            mid_price=float(m.get("mid_price", 0.5)),
            spread=float(m.get("spread", 0.02)),
            volume_24h=float(m.get("volume_24h", 0.0)),
            liquidity=float(m.get("liquidity", 0.0)),
            best_bid_yes=float(m.get("best_bid_yes", 0.49)),
            best_ask_yes=float(m.get("best_ask_yes", 0.51)),
            bid_depth_usd=float(m.get("bid_depth_usd", 0.0)),
            ask_depth_usd=float(m.get("ask_depth_usd", 0.0)),
            last_updated=now,
            yes_token_id=None,
        )

    @staticmethod
    def _trade_pnl_usd(trade: TradeDecision, outcome_yes: float, fee_usd: float = 0.0) -> float:
        """
        Approximate settlement PnL in USD.

        - BUY YES: spend `size_usd` at `fill_price` => shares_yes = size/price
        - SELL YES is approximated as BUY NO with price (1-fill_price)
        """
        if trade.fill_price is None or trade.fill_size is None:
            return 0.0
        n = float(trade.fill_size)
        p = max(1e-6, min(1 - 1e-6, float(trade.fill_price)))
        y = max(0.0, min(1.0, float(outcome_yes)))
        if trade.side == OrderSide.BUY:
            shares_yes = n / p
            payout = shares_yes * y
            return (payout - n) - fee_usd
        price_no = max(1e-6, 1.0 - p)
        shares_no = n / price_no
        payout = shares_no * (1.0 - y)
        return (payout - n) - fee_usd

    @staticmethod
    def _parse_book_side(levels: Any) -> list[tuple[float, float]]:
        """Normalize levels into [(price, shares)] sorted by price ascending."""
        out: list[tuple[float, float]] = []
        if not isinstance(levels, list):
            return out
        for lvl in levels:
            if isinstance(lvl, dict):
                p = float(lvl.get("price", 0.0))
                s = float(lvl.get("size", 0.0))
            elif isinstance(lvl, list) and len(lvl) >= 2:
                p = float(lvl[0])
                s = float(lvl[1])
            else:
                continue
            if p > 0 and s > 0:
                out.append((p, s))
        out.sort(key=lambda x: x[0])
        return out

    def _simulate_fill(
        self,
        decision: TradeDecision,
        market: MarketState,
        snapshot: dict[str, Any],
        *,
        taker_fee_bps: float,
        latency_bps: float,
    ) -> tuple[Optional[TradeDecision], Dict[str, float]]:
        """
        Simulate fill from historical book ladders.

        Returns (filled_decision_or_none, metrics) where metrics has:
        - fee_usd
        - slippage_bps
        - fill_notional_usd
        """
        ob = snapshot.get("orderbook", {}) if isinstance(snapshot, dict) else {}
        asks = self._parse_book_side(ob.get("asks", []))
        bids = self._parse_book_side(ob.get("bids", []))
        target = float(decision.size_usd)
        if target <= 0:
            return None, {"fee_usd": 0.0, "slippage_bps": 0.0, "fill_notional_usd": 0.0}

        remaining = target
        notional = 0.0
        shares = 0.0
        if decision.side == OrderSide.BUY:
            levels = asks
            for p, s in levels:
                cap = p * s
                take = min(remaining, cap)
                if take <= 0:
                    continue
                notional += take
                shares += take / p
                remaining -= take
                if remaining <= 1e-9:
                    break
        else:
            levels = sorted(bids, key=lambda x: x[0], reverse=True)
            for p, s in levels:
                cap = p * s  # max proceeds from this level
                take = min(remaining, cap)
                if take <= 0:
                    continue
                notional += take
                shares += take / p
                remaining -= take
                if remaining <= 1e-9:
                    break

        if notional <= 0.0 or shares <= 0.0:
            return None, {"fee_usd": 0.0, "slippage_bps": 0.0, "fill_notional_usd": 0.0}

        vwap = notional / shares
        # Latency makes fill slightly worse than observed ladder.
        lat_mult = 1.0 + (latency_bps / 10_000.0)
        if decision.side == OrderSide.BUY:
            fill_price = min(0.999999, vwap * lat_mult)
        else:
            fill_price = max(0.000001, vwap / lat_mult)

        fee_usd = notional * (taker_fee_bps / 10_000.0)
        base = max(1e-6, market.mid_price)
        slippage_bps = abs((vwap - market.mid_price) / base) * 10_000.0
        filled = TradeDecision(
            market_id=decision.market_id,
            edge=decision.edge,
            side=decision.side,
            size_usd=decision.size_usd,
            limit_price=decision.limit_price,
            kelly_fraction=decision.kelly_fraction,
            reason=f"{decision.reason}|backtest_fill",
            timestamp=decision.timestamp,
            executed=True,
            fill_price=fill_price,
            fill_size=notional,
        )
        return filled, {"fee_usd": fee_usd, "slippage_bps": slippage_bps, "fill_notional_usd": notional}

    @staticmethod
    def _max_drawdown(equity_curve: List[float]) -> float:
        peak = float("-inf")
        max_dd = 0.0
        for x in equity_curve:
            peak = max(peak, x)
            max_dd = max(max_dd, peak - x)
        return max_dd

    @staticmethod
    def _summary(portfolio: PortfolioState) -> dict[str, Any]:
        trades = portfolio.trade_history
        buys = sum(1 for t in trades if t.side.value == "BUY")
        sells = sum(1 for t in trades if t.side.value == "SELL")
        return {
            "total_trades": len(trades),
            "buys": buys,
            "sells": sells,
            "total_exposure": portfolio.total_exposure,
            "realized_pnl": portfolio.realized_pnl,
            "unrealized_pnl": portfolio.unrealized_pnl,
        }

    async def run(self) -> PortfolioState:
        """Run the backtest and return final portfolio state."""
        self._config.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        cfg = load_config(self._config.config_path, settings_path=self._config.settings_path)
        trading = cfg.get("trading", {})
        risk_cfg = cfg.get("risk", {})
        corr = risk_cfg.get("correlation", {})
        decay = (cfg.get("edge", {}).get("decay", {})) if isinstance(cfg.get("edge", {}), dict) else {}

        strategy = TradingStrategy(
            StrategyConfig(
                min_adjusted_edge=min(float(trading.get("min_adjusted_edge", 0.02)), 0.0001),
                max_kelly_fraction=float(trading.get("max_kelly_fraction", 0.10)),
                min_order_usd=float(trading.get("min_order_usd", 5.0)),
                max_order_usd=float(trading.get("max_order_usd", 250.0)),
                max_portfolio_exposure_usd=float(risk_cfg.get("max_total_exposure_usd", 2500.0)),
                per_market_position_limit_usd=float(risk_cfg.get("max_position_per_market_usd", 400.0)),
                limit_price_buffer_bps=float(trading.get("limit_price_buffer_bps", 15)),
                bankroll_usd=float(trading.get("bankroll_usd", 1000.0)),
            )
        )
        risk = RiskManager(
            RiskConfig(
                max_total_exposure_usd=float(risk_cfg.get("max_total_exposure_usd", 2500.0)),
                max_position_per_market_usd=float(risk_cfg.get("max_position_per_market_usd", 400.0)),
                max_daily_drawdown_usd=float(risk_cfg.get("max_daily_drawdown_usd", 300.0)),
                enable_correlation_checks=bool(corr.get("enabled", True)),
                max_cluster_exposure_usd=float(corr.get("max_cluster_exposure_usd", 900.0)),
            )
        )
        bayes = BayesianEngine()
        edge_calc = EdgeCalculator(
            EdgeConfig(
                half_life_seconds=int(decay.get("half_life_seconds", 1800)),
                decay_floor=float(decay.get("floor", 0.05)),
            )
        )
        logger = AgentLogger(name=str(cfg.get("app", {}).get("name", "polymarket-news-agent")), sink_path=str(self._config.output_jsonl))

        portfolio = PortfolioState()
        dataset = self._load_dataset()
        signals = self._load_signals()
        market_snapshots = dataset.get("markets", {})
        outcomes = dataset.get("outcomes", {})
        exec_cfg = dataset.get("execution", {}) if isinstance(dataset, dict) else {}
        taker_fee_bps = float(exec_cfg.get("taker_fee_bps", 7.0))
        latency_bps = float(exec_cfg.get("latency_bps", 2.0))
        executed_trades: list[tuple[TradeDecision, str, float]] = []
        execution_attempts = 0
        filled_count = 0
        slippage_samples: list[float] = []
        fees_paid = 0.0

        logger.info("backtest_started", {"signals": len(signals), "dataset": self._config.dataset_file, "mode": "historical_snapshot"})
        for signal in signals:
            logger.info("signal_received", {"signal_id": signal.id, "headline": signal.headline, "source": signal.source_name})
            event = next((e for e in dataset.get("signals", []) if isinstance(e, dict) and str(e.get("id")) == signal.id), None)
            event_markets = list((event or {}).get("market_ids", []))
            if not event_markets and isinstance(market_snapshots, dict):
                # fallback: top-N by entity overlap
                event_markets = list(market_snapshots.keys())[:3]
            cr = ClassificationResult(
                signal_type=signal.signal_type,
                direction=signal.direction if signal.direction is not None else 0.0,
                confidence=signal.confidence,
                relevance_score=signal.relevance_score,
            )
            logger.info(
                "signal_classified",
                {
                    "signal_id": signal.id,
                    "signal_type": cr.signal_type.value,
                    "confidence": cr.confidence,
                    "direction": cr.direction,
                },
            )
            ly, ln = likelihoods_from_classification(cr)

            for market_id in event_markets[:3]:
                snap = market_snapshots.get(market_id, {}) if isinstance(market_snapshots, dict) else {}
                market = self._market_from_snapshot(str(market_id), snap if isinstance(snap, dict) else {}, signal.timestamp)
                bayes.seed_prior_if_missing(market.condition_id, market.mid_price)
                prior = bayes.get_prior(market.condition_id)
                posterior = bayes.update_from_likelihoods(market.condition_id, ly, ln)
                slippage = float((event or {}).get("estimated_slippage", 0.01))
                edge = edge_calc.compute(
                    market=market,
                    signal_ids=[signal.id],
                    prior=prior,
                    posterior=posterior,
                    estimated_slippage=slippage,
                    signal_timestamp=signal.timestamp,
                    now=signal.timestamp,
                )
                logger.info(
                    "edge_calculated",
                    {
                        "market_id": market.condition_id,
                        "adjusted_edge": edge.adjusted_edge,
                        "posterior": posterior,
                    },
                )
                decision = strategy.decide(market, edge, portfolio)
                if decision is None:
                    logger.info("trade_skipped", {"reason": "strategy_gate", "market_id": market.condition_id})
                    continue
                ok, reason = risk.approve(market, decision, portfolio)
                if not ok:
                    logger.info("trade_skipped", {"reason": reason, "market_id": market.condition_id})
                    continue
                execution_attempts += 1
                filled, fill_metrics = self._simulate_fill(
                    decision,
                    market,
                    snap if isinstance(snap, dict) else {},
                    taker_fee_bps=taker_fee_bps,
                    latency_bps=latency_bps,
                )
                if filled is None:
                    logger.info("trade_skipped", {"reason": "insufficient_depth", "market_id": market.condition_id})
                    continue
                risk.update_portfolio(market, filled, portfolio)
                filled_count += 1
                slippage_samples.append(fill_metrics["slippage_bps"])
                fees_paid += fill_metrics["fee_usd"]
                executed_trades.append((filled, market.condition_id, fill_metrics["fee_usd"]))
                logger.info(
                    "trade_executed",
                    {
                        "market_id": market.condition_id,
                        "side": filled.side.value,
                        "size_usd": filled.fill_size,
                        "executed": filled.executed,
                        "paper": True,
                        "fee_usd": fill_metrics["fee_usd"],
                        "slippage_bps": fill_metrics["slippage_bps"],
                    },
                )

        # Settlement and rigorous metrics.
        cumulative = 0.0
        equity_curve: list[float] = []
        per_trade_pnl: list[float] = []
        for trade, market_id, fee_usd in executed_trades:
            outcome = float(outcomes.get(market_id, 0.5)) if isinstance(outcomes, dict) else 0.5
            pnl = self._trade_pnl_usd(trade, outcome, fee_usd=fee_usd)
            per_trade_pnl.append(pnl)
            cumulative += pnl
            equity_curve.append(cumulative)

        wins = sum(1 for p in per_trade_pnl if p > 0)
        summary = self._summary(portfolio)
        summary.update(
            {
                "settled_trades": len(per_trade_pnl),
                "win_rate": (wins / len(per_trade_pnl)) if per_trade_pnl else 0.0,
                "total_pnl_usd": cumulative,
                "avg_edge_at_entry": (
                    sum(t.edge for t, _, _ in executed_trades) / len(executed_trades) if executed_trades else 0.0
                ),
                "max_drawdown_usd": self._max_drawdown(equity_curve) if equity_curve else 0.0,
                "execution_attempts": execution_attempts,
                "fill_rate": (filled_count / execution_attempts) if execution_attempts else 0.0,
                "avg_slippage_bps": (sum(slippage_samples) / len(slippage_samples)) if slippage_samples else 0.0,
                "fees_paid_usd": fees_paid,
            }
        )
        logger.info("backtest_completed", summary)
        logger.close()

        self._config.output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return portfolio


async def _cli_async(args: argparse.Namespace) -> None:
    cfg = BacktestConfig(
        data_dir=Path(args.data_dir),
        dataset_file=args.dataset,
        config_path=args.config,
        settings_path=args.settings,
        output_jsonl=Path(args.output_jsonl),
        output_summary=Path(args.output_summary),
    )
    runner = BacktestRunner(cfg)
    await runner.run()


def _cli() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Replay historical backtest signals.")
    parser.add_argument("--data-dir", default="backtest/data")
    parser.add_argument("--dataset", default="biden_dropout_2024.json")
    parser.add_argument("--config", default="config/politics.yaml")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--output-jsonl", default="backtest/results/biden_dropout_2024.jsonl")
    parser.add_argument("--output-summary", default="backtest/results/biden_dropout_2024_summary.json")
    args = parser.parse_args()
    asyncio.run(_cli_async(args))


if __name__ == "__main__":
    _cli()

