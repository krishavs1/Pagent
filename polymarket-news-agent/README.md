# Polymarket Autonomous News Agent

An autonomous pipeline that **ingests real-time news**, **matches** items to Polymarket markets, **scores** predictive edge with Bayesian belief updates and slippage-aware adjustments, and **executes** trades under risk controls (paper mode by default). Built for the Polymarket **Autonomous News-Driven Trading Agent** bounty: it combines diverse feeds, explicit confidence math, orderbook-aware friction, and a reproducible backtest log.

**Official resources**

- Polymarket documentation: [https://docs.polymarket.com/](https://docs.polymarket.com/)
- CLOB client (TypeScript/Python): [https://github.com/Polymarket/clob-client](https://github.com/Polymarket/clob-client)

---

## Contents

- [What this repo delivers](#what-this-repo-delivers)
- [Data inputs and ingestion strategy](#data-inputs-and-ingestion-strategy)
- [Confidence and edge: mathematical framework](#confidence-and-edge-mathematical-framework)
- [Execution, risk, and orderbook analysis](#execution-risk-and-orderbook-analysis)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Configuration](#configuration)
- [Setup](#setup)
- [Running the agent](#running-the-agent)
- [Backtest: simulated run deliverable](#backtest-simulated-run-deliverable)
- [Web dashboard (Next.js)](#web-dashboard-nextjs)
- [Tests](#tests)
- [Limitations and scope](#limitations-and-scope)

---

## What this repo delivers

| Bounty ask | How it is addressed here |
|------------|---------------------------|
| **Monitor real-time news** | RSS (`RSSSource`), curated official feeds (`OfficialSource`), optional X (`XApiSource`), unified `SignalAggregator` with dedupe + bounded queue. |
| **Analyze Polymarket orderbooks** | `OrderbookTracker` (CLOB) for best bid/ask, depth, and ladder-based slippage; backtest uses historical ladders + fees + latency. |
| **Estimate predictive edge** | `SignalClassifier` → Bernoulli likelihoods → `BayesianEngine` posterior → `EdgeCalculator` (decay + slippage). |
| **Execute autonomously** | `TradingStrategy` + `RiskManager` + `OrderExecutor` (paper by default; live guarded). |
| **README: data inputs + math** | This document + `config/politics.yaml` / `config/settings.yaml`. |
| **Simulated run / backtest log** | `python -m backtest.runner` → JSONL with `signal_received`, `edge_calculated`, `trade_executed` / `trade_skipped`, plus summary and equity JSON. |

---

## Data inputs and ingestion strategy

### Design goals

- **Quality**: Prefer established outlets (tier 1–2 RSS), official feeds (tier 1), and high-signal X accounts (tier 3) with keyword filters.
- **Diversity**: Multiple modalities (RSS, official, social) and entity types (see `domain.entity_types` in `config/politics.yaml`).
- **Latency vs cost**: Faster polling for higher tiers; X polling throttled (`poll_seconds`, `max_results_per_account`) with optional cost caps in `config/settings.yaml` (`x_api.daily_budget_usd`).

### Tiered news sources (`config/politics.yaml`)

| Tier | Role | Examples (current config) |
|------|------|---------------------------|
| **1** | Highest trust / lowest latency | NPR Politics, NYT Politics RSS |
| **2** | Strong secondary | Politico, PBS Politics RSS |
| **3** | Fast social / noisy | X API: listed accounts + keywords (`BREAKING`, `JUST IN`, …) |
| **4** | Broad / lower priority | BBC UK Politics RSS |

**Official sources** (separate list): e.g. White House Presidential Actions RSS; Congress.gov-style stub (`bill_updates`) for future expansion.

Each ingested item becomes a normalized `Signal` (headline, body, entities, `SignalTier`, optional `direction`/`confidence` from classification in the live pipeline).

### Signal aggregation (`config/settings.yaml`)

- **Per-tier poll intervals** (`ingestion.poll_interval_seconds`): tier_1 15s … tier_4 120s.
- **Aggregator**: `dedupe_window_seconds`, `max_queue_size` to avoid duplicate bursts and bound memory.

### Market universe (filters)

`market_filters` in `config/politics.yaml` restricts which Gamma markets are indexed:

- `include_tags` / `exclude_tags`
- `question_keywords_allowlist`
- `min_volume_24h`, `min_liquidity`

### `signal_priors` (domain YAML)

Optional per–`SignalType` weights in `config/politics.yaml` (e.g. `OFFICIAL_OUTCOME` vs `PUNDIT_SPECULATION`). They document intent for tuning; the **implemented** belief update uses the Bayesian engine with classifier-derived likelihoods below (wire these priors in code if you want them to affect gating).

---

## Confidence and edge: mathematical framework

### 1. Classification → likelihoods

Live mode uses `SignalClassifier` (Anthropic Claude, with fallback when no key is set). The structured output is a `ClassificationResult`: `signal_type`, `direction` (−1…+1), `confidence` ∈ [0,1], `relevance_score`.

For a binary **YES** market, evidence likelihoods are derived in `likelihoods_from_classification` (`src/scoring/likelihoods.py`):

- Let `conf = clamp(confidence, 0, 1)`.
- If `direction` is neutral → **L_yes = L_no = 0.5** (uninformative).
- If `direction > 0` → **L_yes = 0.5 + 0.5·conf**, **L_no = 1 − L_yes**.
- If `direction < 0` → **L_yes = 0.5 − 0.5·conf**, **L_no = 1 − L_yes**.

This yields a proper pair **(L_yes, L_no)** for Bayes’ rule.

### 2. Bayesian update (per market)

For each market, the engine maintains a prior over **P(YES)**. After each signal:

\[
\text{posterior} = \frac{\text{prior} \cdot L_{\text{yes}}}{\text{prior} \cdot L_{\text{yes}} + (1-\text{prior}) \cdot L_{\text{no}}}
\]

The prior is seeded from the market mid when missing, then updated sequentially as signals arrive.

### 3. Raw edge and time decay

- **Raw edge**: `raw_edge = posterior − mid_price` (belief vs market).
- **Decay** (`EdgeCalculator.apply_decay`): half-life `edge.decay.half_life_seconds`, floor `edge.decay.floor`:

\[
k = e^{-\ln(2)\cdot \Delta t / t_{1/2}},\quad
\text{decay\_factor} = \max(\texttt{decay\_floor},\ \min(1,\ k))
\]

- **Decayed edge**: `decayed_edge = raw_edge * decay_factor` with \(\Delta t\) = time since the signal timestamp.

### 4. Slippage-adjusted edge

Orderbook depth informs executable price. `estimated_slippage` (from `OrderbookTracker` or backtest event) is used:

- If raw edge is **positive**: `adjusted = decayed − slippage` (cost of lifting asks).
- If raw edge is **negative**: `adjusted = decayed + slippage` (friction works against the short-side intuition consistently in the implementation).

Trades require **|adjusted_edge| ≥ `trading.min_adjusted_edge`** (config).

### 5. Position sizing (capped Kelly-style)

- **Kelly strength**: derived from `|posterior − 0.5|`, scaled by `max_kelly_fraction`.
- **Notional** ≈ `bankroll_usd * kelly_fraction`, clamped to `min_order_usd` / `max_order_usd`.

### 6. Strategy side rule (no naked shorts)

- **BUY** when `adjusted_edge > 0` (add to long YES).
- **SELL** when `adjusted_edge < 0` **only** if there is an existing **long** position on that market; size is capped by that position. This avoids opening naked short YES positions in paper/backtest.

### 7. Calibration (`CalibrationTracker`)

Records predicted vs outcomes for offline analysis (Brier score, etc.); extend with your own resolution feed for production calibration.

---

## Execution, risk, and orderbook analysis

### Orderbook

- **Live**: `OrderbookTracker` uses the Polymarket CLOB (`py-clob-client`) to read bids/asks and estimate price impact for a notional.
- **Backtest**: walks historical **bid/ask ladders** in the dataset, applies **taker fee** (`execution.taker_fee_bps`) and **latency** (`latency_bps`) to the fill.

### Execution

- **Default**: **paper** execution — fills are simulated and logged; no live orders.
- **Live**: `OrderExecutor` can be extended; `trading.enabled` and executor config should gate real posting.

### Risk (`RiskManager`)

- Max **total** portfolio exposure, **per-market** cap, **drawdown** guard, optional **correlation cluster** cap (shared entities across markets).
- Approvals treat **BUY** as increasing exposure and **SELL** as reducing exposure for limit checks.

---

## Architecture

```
Ingestion (RSS / Official / X)
        → SignalAggregator (dedupe, queue)
        → MarketIndexer (Gamma) + MarketMatcher (entities)
        → SignalClassifier (LLM)
        → BayesianEngine + EdgeCalculator
        → OrderbookTracker (slippage)
        → TradingStrategy
        → RiskManager
        → OrderExecutor (paper / live)
        → AgentLogger (JSONL)
```

---

## Repository layout

```
polymarket-news-agent/
├── config/
│   ├── settings.yaml      # Global: APIs, trading, edge, risk, ingestion intervals
│   └── politics.yaml      # Domain: sources, tiers, market filters, priors
├── src/
│   ├── main.py            # Async orchestrator
│   ├── ingestion/         # RSS, official, X, aggregator, factory
│   ├── market/            # Indexer, orderbook, matcher
│   ├── scoring/           # Classifier, Bayes, edge, likelihoods, calibration
│   ├── execution/         # Strategy, executor
│   ├── risk/              # Risk manager
│   └── utils/             # types, config loader, logger
├── backtest/
│   ├── runner.py          # Snapshot replay + metrics + MTM equity
│   └── data/              # Event JSON datasets
├── web/                   # Next.js dashboard (v0 UI wired to agent_api)
├── agent_api.py           # FastAPI: backtest JSON + parsed JSONL for the UI
├── scripts/               # Phase smoke tests
├── tests/
├── requirements.txt
└── .env.example
```

---

## Configuration

- **`config/settings.yaml`**: `api.polymarket` (CLOB/Gamma URLs), `trading.*`, `edge.decay`, `risk.*`, `ingestion.poll_interval_seconds`, `x_api` cost caps.
- **`config/politics.yaml`**: `news_sources` by tier, `official_sources`, `market_filters`, optional `signal_priors`, `domain.entity_types`.

Merged at runtime via `load_config()` (domain YAML merged into global).

---

## Setup

```bash
cd polymarket-news-agent
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Environment variables (`.env`)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude classification (optional; fallback when missing) |
| `X_BEARER_TOKEN` | X API v2 ingestion (optional) |
| `POLYMARKET_API_KEY` / `POLYMARKET_SECRET` / `POLYMARKET_PRIVATE_KEY` | CLOB auth for live trading / read-only client as implemented |

---

## Running the agent

### One-shot (process N signals)

```bash
. .venv/bin/activate
python -m src.main --mode once --max-signals 5 --log /tmp/agent_once.jsonl
```

### Continuous loop

```bash
python -m src.main --mode loop --log /tmp/agent_loop.jsonl
```

### Smoke scripts (module checks)

```bash
python scripts/phase2_smoke.py
python scripts/phase3_smoke.py
python scripts/phase4_smoke.py
python scripts/phase2_to_phase4_smoke.py
```

---

## Backtest: simulated run deliverable

Replays a **fixed JSON dataset** through the same scoring + strategy + risk + fill path (no live network for signals).

**Dataset:** `backtest/data/biden_dropout_2024.json`

- **`signals`**: ordered events with `timestamp`, `direction`, `confidence`, `market_ids`, etc.
- **`markets`**: per-market snapshot + optional **`timeline[]`** of `{timestamp, mid_price, orderbook?}` for time-varying mids and books.
- **`execution`**: `taker_fee_bps`, `latency_bps`.
- **`outcomes`**: resolved YES outcomes `{0,1}` for settlement PnL.

**Run:**

```bash
. .venv/bin/activate
python -m backtest.runner
```

**Artifacts**

| File | Content |
|------|---------|
| `backtest/results/<dataset>.jsonl` | Structured log: `signal_received`, `edge_calculated`, `trade_executed` / `trade_skipped`, `backtest_completed` |
| `backtest/results/<dataset>_summary.json` | Settlement PnL, drawdown, fees, MTM metrics |
| `backtest/results/<dataset>_equity_curve.json` | Per-signal MTM equity, cash, position value |

**Optional CLI:**

```bash
python -m backtest.runner --data-dir backtest/data --dataset biden_dropout_2024.json \
  --output-jsonl backtest/results/run.jsonl \
  --output-summary backtest/results/run_summary.json \
  --output-equity backtest/results/run_equity.json
```

**Note:** The sample includes an opener signal (`b0`) so a long can be established before bearish headlines; otherwise the no-naked-short rule would yield zero sells in some purely-negative-edge runs.

---

## Web dashboard (Next.js)

The `web/` app is a **Next.js** front end that reads backtest artifacts and parsed logs from a small **FastAPI** service (`agent_api.py` at the repo root).

### Why two processes?

- **Python** serves JSON from `backtest/results/*` and parses `biden_dropout_2024.jsonl` into dashboard rows (no secrets required for read-only demo).
- **Next.js** (`npm run dev`, default port **3000**) fetches `NEXT_PUBLIC_AGENT_API_URL` (default `http://127.0.0.1:8765`).

### Run locally

**Terminal 1 — API**

```bash
cd polymarket-news-agent
. .venv/bin/activate
pip install -r requirements.txt
uvicorn agent_api:app --reload --port 8765
```

**Terminal 2 — UI**

```bash
cd polymarket-news-agent/web
npm install
cp .env.example .env.local   # optional
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). **Dashboard** and **Backtest** load live data when the API is up; if the API is unreachable, they **fall back to mock data** and show a warning badge.

- **Backtest → Run backtest** calls `POST /api/backtest/run` (runs `python -m backtest.runner` in this repo).
- **Export JSONL** links to `GET /api/backtest/file/jsonl`.

### API endpoints (reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| GET | `/api/dashboard` | KPIs, signal rows, edge sparkline from JSONL + summary |
| GET | `/api/backtest/summary` | Raw `*_summary.json` |
| GET | `/api/backtest/equity` | Raw `*_equity_curve.json` |
| POST | `/api/backtest/run` | Execute backtest runner |
| GET | `/api/backtest/file/jsonl` | Download JSONL log |
| GET | `/api/backtest/replay` | Signals grouped with edges/trades for the UI replay tab |
| GET | `/api/backtest/log_tail?limit=120` | Last N JSONL lines as `{event, text}` summaries |

---

## Tests

```bash
. .venv/bin/activate
pytest -q
```

---

## Limitations and scope

- **Paper execution by default**; live order posting requires explicit enablement and keys.
- **Classifier**: LLM outputs are only as good as prompts and keys; fallback paths are heuristic.
- **Matching**: Entity/token overlap is **heuristic**, not semantic retrieval.
- **Backtest**: Settlement is binary; **MTM** is mark-to-market on timeline mids — not a full margin model.
- **Congress.gov** official source is stub-friendly; wire real API keys for production.

---

## License

Specify a license in your public repository when publishing (e.g. MIT) if you intend open-source reuse.
