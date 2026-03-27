"""
Async orchestrator: ingestion -> market match -> classify -> Bayes -> edge -> strategy -> risk -> execution.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from src.execution.executor import ExecutionConfig, OrderExecutor
from src.execution.strategy import StrategyConfig, TradingStrategy
from src.ingestion.aggregator import AggregatorConfig, SignalAggregator
from src.ingestion.base import NewsSource
from src.ingestion.factory import build_news_sources
from src.market.indexer import MarketIndexer, MarketIndexerConfig
from src.market.matcher import MatcherConfig, MarketMatcher
from src.market.orderbook import OrderbookConfig, OrderbookTracker
from src.risk.manager import RiskConfig, RiskManager
from src.scoring.bayesian import BayesianEngine
from src.scoring.classifier import ClassificationResult, SignalClassifier
from src.scoring.edge import EdgeCalculator, EdgeConfig
from src.scoring.likelihoods import likelihoods_from_classification
from src.utils.config import load_config
from src.utils.logger import AgentLogger
from src.utils.types import PortfolioState, Signal


@dataclass(slots=True)
class AgentComponents:
    """Container for initialized pipeline components."""

    sources: List[NewsSource]
    aggregator: SignalAggregator
    market_indexer: MarketIndexer
    orderbook_tracker: OrderbookTracker
    market_matcher: MarketMatcher
    classifier: SignalClassifier
    bayesian: BayesianEngine
    edge: EdgeCalculator
    risk: RiskManager
    strategy: TradingStrategy
    executor: OrderExecutor
    logger: AgentLogger


def _cfg_float(cfg: Dict[str, Any], *keys: str, default: float) -> float:
    cur: Any = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    try:
        return float(cur)
    except (TypeError, ValueError):
        return default


def _cfg_int(cfg: Dict[str, Any], *keys: str, default: int) -> int:
    cur: Any = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    try:
        return int(cur)
    except (TypeError, ValueError):
        return default


async def build_components(cfg: Dict[str, Any], log_path: Optional[str]) -> AgentComponents:
    """Wire all modules from merged config."""
    api = cfg.get("api") or {}
    poly = api.get("polymarket") or {}
    anth = api.get("anthropic") or {}
    trading = cfg.get("trading") or {}
    edge_cfg = cfg.get("edge") or {}
    decay = edge_cfg.get("decay") or {}
    _ = edge_cfg.get("slippage") or {}
    risk_cfg = cfg.get("risk") or {}
    corr = risk_cfg.get("correlation") or {}
    mf = cfg.get("market_filters") or {}
    ing = cfg.get("ingestion") or {}

    gamma = str(poly.get("gamma_base_url", "https://gamma-api.polymarket.com"))
    clob = str(poly.get("clob_base_url", "https://clob.polymarket.com"))

    indexer = MarketIndexer(
        MarketIndexerConfig(
            include_tags=list(mf.get("include_tags") or []),
            exclude_tags=list(mf.get("exclude_tags") or []),
            min_volume_24h=float(mf.get("min_volume_24h", 0)),
            min_liquidity=float(mf.get("min_liquidity", 0)),
        ),
        gamma_base_url=gamma,
    )
    await indexer.refresh()

    matcher = MarketMatcher(indexer, MatcherConfig(max_candidates=5, min_entity_overlap=1))
    orderbook = OrderbookTracker(
        clob,
        OrderbookConfig(
            depth_lookahead_levels=_cfg_int(cfg, "edge", "slippage", "depth_lookahead_levels", default=5),
            request_timeout_seconds=_cfg_int(poly, "request_timeout_seconds", default=15),
        ),
    )
    classifier = SignalClassifier(
        model=str(anth.get("model", "claude-3-5-sonnet-latest")),
        timeout_seconds=_cfg_int(anth, "request_timeout_seconds", default=30),
    )
    bayes = BayesianEngine()
    edge = EdgeCalculator(
        EdgeConfig(
            half_life_seconds=_cfg_int(decay, "half_life_seconds", default=1800),
            decay_floor=_cfg_float(decay, "floor", default=0.05),
        )
    )
    strategy = TradingStrategy(
        StrategyConfig(
            min_adjusted_edge=float(trading.get("min_adjusted_edge", 0.02)),
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
    exec_enabled = bool(trading.get("enabled", False))
    executor = OrderExecutor(
        clob,
        ExecutionConfig(
            enabled=exec_enabled,
            paper_mode=not exec_enabled,
        ),
    )
    logger = AgentLogger(name=str(cfg.get("app", {}).get("name", "polymarket-news-agent")), sink_path=log_path)

    sources = build_news_sources(cfg)
    agg_cfg = ing.get("aggregator") or {}
    aggregator = SignalAggregator(
        sources,
        AggregatorConfig(
            max_queue_size=int(agg_cfg.get("max_queue_size", 10_000)),
            dedupe_window_seconds=int(agg_cfg.get("dedupe_window_seconds", 3600)),
        ),
    )

    return AgentComponents(
        sources=sources,
        aggregator=aggregator,
        market_indexer=indexer,
        orderbook_tracker=orderbook,
        market_matcher=matcher,
        classifier=classifier,
        bayesian=bayes,
        edge=edge,
        risk=risk,
        strategy=strategy,
        executor=executor,
        logger=logger,
    )


def trading_placeholder_size() -> float:
    """Notional for slippage probe before strategy size is known."""
    return 50.0


async def _classify_signal(classifier: SignalClassifier, signal: Signal) -> ClassificationResult:
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return await classifier.classify(signal)
        except Exception:
            pass
    return ClassificationResult(
        signal_type=signal.signal_type,
        direction=float(signal.direction) if signal.direction is not None else 0.0,
        confidence=max(signal.confidence, 0.5),
        relevance_score=max(signal.relevance_score, 0.3),
    )


async def process_signal(
    signal: Signal,
    c: AgentComponents,
    portfolio: PortfolioState,
    *,
    max_markets: int = 3,
) -> None:
    """Run scoring + execution for one signal."""
    c.logger.info(
        "signal_received",
        {"signal_id": signal.id, "source": signal.source_name, "headline": signal.headline[:300]},
    )
    matches = c.market_matcher.match(signal)[:max_markets]
    if not matches:
        c.logger.info("trade_skipped", {"reason": "no_market_match", "signal_id": signal.id})
        return

    cr = await _classify_signal(c.classifier, signal)
    c.logger.info(
        "signal_classified",
        {
            "signal_id": signal.id,
            "signal_type": cr.signal_type.value,
            "confidence": cr.confidence,
            "direction": cr.direction,
        },
    )

    ly, ln = likelihoods_from_classification(cr)

    for market, relevance in matches:
        mid = market.condition_id
        c.bayesian.seed_prior_if_missing(mid, market.mid_price)
        prior_before = c.bayesian.get_prior(mid)
        posterior = c.bayesian.update_from_likelihoods(mid, ly, ln)

        mstate = market
        if market.yes_token_id:
            try:
                mstate = await c.orderbook_tracker.update_market_state(market)
            except Exception as exc:  # noqa: BLE001
                c.logger.warning("orderbook_update_failed", {"market_id": mid, "error": str(exc)})

        slip = 0.02
        if market.yes_token_id:
            try:
                slip = await c.orderbook_tracker.estimate_slippage_probability(
                    market.yes_token_id,
                    min(100.0, trading_placeholder_size()),
                )
            except Exception:  # noqa: BLE001
                slip = 0.02

        edge_est = c.edge.compute(
            market=mstate,
            signal_ids=[signal.id],
            prior=prior_before,
            posterior=posterior,
            estimated_slippage=slip,
            signal_timestamp=signal.timestamp,
            now=datetime.now(timezone.utc),
        )
        c.logger.info(
            "edge_calculated",
            {
                "market_id": mid,
                "adjusted_edge": edge_est.adjusted_edge,
                "posterior": posterior,
                "relevance": relevance,
            },
        )

        decision = c.strategy.decide(mstate, edge_est, portfolio)
        if decision is None:
            c.logger.info("trade_skipped", {"reason": "strategy_gate", "market_id": mid})
            continue

        ok, rreason = c.risk.approve(mstate, decision, portfolio)
        if not ok:
            c.logger.info("trade_skipped", {"reason": rreason, "market_id": mid})
            continue

        filled = await c.executor.execute(decision)
        c.risk.update_portfolio(mstate, filled, portfolio)
        paper = getattr(getattr(c.executor, "_config", None), "paper_mode", True)
        c.logger.info(
            "trade_executed",
            {
                "market_id": mid,
                "side": filled.side.value,
                "size_usd": filled.size_usd,
                "executed": filled.executed,
                "paper": paper,
            },
        )


class AgentOrchestrator:
    """Coordinates the pipeline modules in an async event loop."""

    def __init__(self, components: AgentComponents, portfolio: Optional[PortfolioState] = None) -> None:
        self._c = components
        self._portfolio = portfolio or PortfolioState()

    async def run_forever(self) -> None:
        """Run until cancelled; consumes aggregator queue."""
        await self._c.aggregator.start()
        try:
            while True:
                signal = await self._c.aggregator.get()
                await process_signal(signal, self._c, self._portfolio)
        finally:
            await self._c.aggregator.stop()
            self._c.logger.close()

    async def run_once(self, max_signals: int = 5) -> None:
        """Poll all sources once and process up to `max_signals` items."""
        count = 0
        for source in self._c.sources:
            try:
                batch = await source.poll()
            except Exception as exc:  # noqa: BLE001
                self._c.logger.warning("source_poll_failed", {"source": source.source_name, "error": str(exc)})
                continue
            for sig in batch:
                await process_signal(sig, self._c, self._portfolio)
                count += 1
                if count >= max_signals:
                    return
        self._c.logger.info("run_once_complete", {"processed": count})


async def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Polymarket news-driven agent")
    parser.add_argument("--config", default="config/politics.yaml", help="Domain YAML")
    parser.add_argument("--settings", default="config/settings.yaml", help="Global settings YAML")
    parser.add_argument("--log", default=None, help="Optional JSONL log file path")
    parser.add_argument("--mode", choices=("loop", "once"), default="once", help="once=poll sources once; loop=aggregator")
    parser.add_argument("--max-signals", type=int, default=5, help="Max signals to process in `once` mode")
    args = parser.parse_args()

    cfg = load_config(args.config, settings_path=args.settings)
    components = await build_components(cfg, args.log)

    if args.mode == "loop" and not components.sources:
        print("No ingestion sources configured. Add RSS URLs or set X_BEARER_TOKEN for X API.")
        return

    orch = AgentOrchestrator(components)
    if args.mode == "once":
        await orch.run_once(max_signals=args.max_signals)
        components.logger.close()
        return

    try:
        await orch.run_forever()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
