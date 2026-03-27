# Polymarket Autonomous News Agent

Autonomous, news-driven trading agent for Polymarket prediction markets.

It ingests real-time news, maps signals to markets, scores edge with Bayesian updates,
applies strategy + risk controls, and executes in paper mode by default.

## Architecture

Pipeline:

1. **Ingestion**
   - `RSSSource`, `OfficialSource`, `XApiSource`
   - `SignalAggregator` handles dedup + async queue
2. **Market**
   - `MarketIndexer` fetches active markets from Gamma
   - `OrderbookTracker` reads CLOB orderbook + slippage estimate
   - `MarketMatcher` ranks market candidates for each signal
3. **Scoring**
   - `SignalClassifier` (Anthropic Claude, fallback if key missing)
   - `BayesianEngine` updates posterior probabilities
   - `EdgeCalculator` computes decayed + slippage-adjusted edge
4. **Execution**
   - `TradingStrategy` gates by edge, sizes via capped Kelly
   - `OrderExecutor` executes in paper mode by default
5. **Risk**
   - `RiskManager` checks total exposure, per-market cap, drawdown, and correlation cluster limits

## Confidence/Edge Math

### Bayesian update

For each matched market:

`posterior = (prior * L_yes) / (prior * L_yes + (1 - prior) * L_no)`

Classifier output (`direction`, `confidence`) is mapped to `(L_yes, L_no)`:
- positive direction -> higher `L_yes`
- negative direction -> higher `L_no`
- neutral -> `(0.5, 0.5)`

### Edge

- Raw edge: `raw_edge = posterior - market_mid_price`
- Time decay:
  - `decay_factor = exp(-ln(2) * t / half_life)`
  - floored by config (`decay.floor`)
- Slippage-adjusted edge:
  - if raw positive: `adjusted = decayed_edge - slippage`
  - if raw negative: `adjusted = decayed_edge + slippage`

### Position sizing

Strategy uses a capped Kelly-style fraction and applies:
- min adjusted edge threshold
- min/max order size clamps
- per-market and portfolio exposure caps

## Setup

```bash
cd polymarket-news-agent
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill keys in `.env` as needed:
- `ANTHROPIC_API_KEY` (optional if using fallback classifier)
- `X_BEARER_TOKEN` (optional, enables X ingestion)
- Polymarket keys only needed for future live execution mode

## Run

### One-shot pipeline run (process a few signals)

```bash
. .venv/bin/activate
python -m src.main --mode once --max-signals 5 --log /tmp/agent_once.jsonl
```

### Continuous loop

```bash
. .venv/bin/activate
python -m src.main --mode loop --log /tmp/agent_loop.jsonl
```

### Phase smokes

```bash
python scripts/phase2_smoke.py
python scripts/phase3_smoke.py
python scripts/phase4_smoke.py
python scripts/phase2_to_phase4_smoke.py
```

## Backtest / Simulated Run Deliverable (Rigorous Mode)

Dataset:
- `backtest/data/biden_dropout_2024.json`

Dataset schema (snapshot replay):
- `signals`: ordered historical signals (timestamp/source/tier/type/direction/confidence)
- `markets`: historical market snapshots (mid, bid/ask, spread, entities)
- `outcomes`: realized YES outcomes for settlement (`0` or `1`)

Run:

```bash
. .venv/bin/activate
python -m backtest.runner
```

Artifacts produced:
- `backtest/results/biden_dropout_2024.jsonl`
- `backtest/results/biden_dropout_2024_summary.json`

Current sample summary:
- total_trades: 9
- buys: 0
- sells: 9
- settled_trades: 9
- win_rate: 0.4444
- total_pnl_usd: 471.67
- max_drawdown_usd: 198.52
- avg_edge_at_entry: -0.3681

## Tests

```bash
. .venv/bin/activate
pytest -q
```

Current status: all implemented tests pass in this repository.

## Notes and Limitations

- Execution is paper-mode by default; live order posting remains intentionally guarded.
- Market matching and source filtering are heuristic and can be further tuned.
- Backtest PnL uses a simplified settlement approximation from notional + fill price.
- For production-grade rigor, include historical orderbook ladders (not only top-of-book snapshots).
