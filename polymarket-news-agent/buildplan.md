Polymarket News Agent — Build Plan
Ordered by dependency. Each step has what to build, how to test it, and what "done" looks like.

Phase 0: Project Setup
0.1 — Scaffold the repo

 Verify every file exists and imports resolve
Test: python -c "from src.utils.types import Signal, MarketState, EdgeEstimate, TradeDecision" runs without error
Test: find . -name "*.py" | head -30 shows all expected files

0.2 — Install dependencies + env

 pip install -r requirements.txt
 Copy .env.example to .env, fill in keys:

POLYMARKET_PRIVATE_KEY — export from reveal.magic.link/polymarket or MetaMask
ANTHROPIC_API_KEY — from console.anthropic.com
CONGRESS_API_KEY — free at api.data.gov/signup
TWITTER_BEARER_TOKEN — optional, skip for now


 Add .env to .gitignore
Test: python -c "from dotenv import load_dotenv; load_dotenv(); import os; assert os.getenv('ANTHROPIC_API_KEY')" passes

0.3 — Config loading

 Write a src/utils/config.py that loads settings.yaml + a domain yaml, merges them into a typed config object (dataclass or dict)
 Support CLI override: --config config/politics.yaml
Test: Unit test that loads both yamls and asserts expected values exist (thresholds, source lists, signal priors)
Test: python -c "from src.utils.config import load_config; c = load_config('config/politics.yaml'); assert c['trading']['min_edge_threshold'] == 0.05"


Phase 1: Market Module (no external news needed, test against live Polymarket)
1.1 — MarketIndexer: fetch active markets

 Use Polymarket Gamma API (https://gamma-api.polymarket.com/markets) to fetch active markets
 Filter by tags (politics, us-politics, elections, etc.) and minimum liquidity/volume from config
 Extract entities from each market's question/description using simple keyword extraction (no LLM needed here)
 Store as list of MarketState objects with an in-memory searchable index
 Add a refresh() method that re-fetches periodically
Test: Run indexer, print count of active political markets. Should be >0.
Test: python -m src.market.indexer prints a table of market questions, mid-prices, and volumes
Test: Assert every returned MarketState has non-null condition_id, question, mid_price

1.2 — OrderbookTracker: get orderbook snapshots

 For a given token_id, call client.get_order_book() via py-clob-client
 Compute mid-price, spread, best bid/ask, and depth at N levels
 Implement estimate_slippage(size_usd) — walk the book to estimate fill price for a given order size
 Note: read-only operations do NOT require API key, just the public CLOB endpoint
Test: Pick a known active political market token_id, fetch orderbook, print spread and depth
Test: estimate_slippage(10) returns a float between 0 and 1 (representing price impact in probability terms)
Test: estimate_slippage(0) returns 0
Test: Slippage increases monotonically with size (test with 10, 100, 500)

1.3 — MarketMatcher: map entities to markets

 Given a list of entity strings (e.g. ["Biden", "Democratic nominee"]), find matching MarketState objects from the index
 Use fuzzy string matching (simple: keyword overlap; better: TF-IDF or embedding similarity)
 Return ranked list of (MarketState, relevance_score) tuples
 Start simple with keyword overlap, upgrade later if needed
Test: Manually create a Signal with entities=["Biden", "nominee"]. Matcher should return Biden-related markets with high relevance.
Test: Signal with entities=["Supreme Court", "abortion"] should NOT match presidential election markets (or match with low score)
Test: Empty entities list returns empty matches
Test: Write 5+ test cases in tests/test_matcher.py covering exact match, partial match, no match, multiple matches


Phase 2: Scoring Module (core math, can test with synthetic data)
2.1 — BayesianEngine: sequential probability updates

 Implement update(prior, likelihood_yes, likelihood_no) -> posterior using Bayes' rule:

  posterior = (prior * L_yes) / (prior * L_yes + (1 - prior) * L_no)

 Implement update_multiple(prior, signals) -> posterior that chains updates sequentially
 Handle edge cases: prior = 0 or 1, likelihood = 0, numerical stability
 Support both YES-direction and NO-direction signals (flip likelihoods for NO)
Test (tests/test_bayesian.py):

Single update: prior=0.5, L_yes=0.9, L_no=0.1 -> posterior should be 0.9
Single update: prior=0.7, L_yes=0.95, L_no=0.05 -> posterior ~0.978
NO-direction: prior=0.7, signal supports NO -> posterior < 0.7
Neutral signal: L_yes=0.5, L_no=0.5 -> posterior == prior (no information)
Extreme prior: prior=0.01, strong YES signal -> posterior jumps but stays < 1.0
Two independent confirming signals compound: posterior after 2 > posterior after 1
Order invariance: update(update(p, s1), s2) == update(update(p, s2), s1)
prior=0.0 stays 0.0 (can't update away from certainty)
prior=1.0 stays 1.0



2.2 — EdgeCalculator: raw edge + decay + slippage

 calculate_raw_edge(posterior, market_mid_price) -> float (just subtraction, but signed for direction)
 apply_decay(raw_edge, seconds_since_signal, tier) -> float using exponential decay:

  decay_factor = exp(-0.693 * t / half_life)  # 0.693 = ln(2)
Half-lives from config per tier.

 calculate_adjusted_edge(raw_edge, decay_factor, slippage) -> float
 Return full EdgeEstimate dataclass
Test (tests/test_edge.py):

Raw edge: posterior=0.8, mid=0.6 -> edge=0.2
Raw edge: posterior=0.3, mid=0.6 -> edge=-0.3 (NO direction)
Decay at t=0: factor=1.0 (no decay)
Decay at t=half_life: factor~=0.5
Decay at t=2*half_life: factor~=0.25
Tier 1 decays faster than Tier 4 (shorter half-life)
Adjusted edge = raw * decay - slippage
Adjusted edge can go negative (signal too stale to trade)



2.3 — SignalClassifier: LLM-based classification

 Takes a Signal (headline + body) and list of active MarketStates
 Calls Claude API with a structured prompt that returns JSON:

json  {
    "signal_type": "credible_scoop",
    "direction": "YES",
    "confidence": 0.85,
    "relevant_markets": ["condition_id_1"],
    "reasoning": "AP confirms Senate vote passed..."
  }

 Map signal_type to tier reliability priors from config
 Set the Signal's classified fields (signal_type, direction, confidence)
 Add retry logic and timeout handling for API calls
 Use a system prompt that defines the signal taxonomy and gives examples
Test (tests/test_classifier.py):

Mock the Claude API response, verify parsing works
Test with a real API call (integration test, mark as slow):

Headline: "AP: Senate confirms John Smith as Secretary of Defense" -> should classify as credible_scoop, direction=YES
Headline: "Pundit on Fox News predicts Biden will run again" -> should classify as pundit_speculation
Headline: "Congress.gov: H.R. 1234 signed into law" -> should classify as official_outcome


Test malformed API response handling (retry or graceful fallback)
Test that classifier returns valid SignalType enum values



2.4 — CalibrationTracker: log predictions vs outcomes

 Simple append-only log: (market_id, predicted_prob, actual_outcome, timestamp)
 Method to compute calibration metrics: Brier score, calibration curve bins
 Not critical for hackathon but impressive if included in README
Test: Add 10 synthetic predictions, compute Brier score, verify it's between 0 and 1
Test: Perfect predictions (all 1.0 for YES outcomes) give Brier score of 0.0


Phase 3: Ingestion Module (news sources)
3.1 — Base NewsSource + RSS adapter

 Abstract base: async poll() -> list[Signal]
 RSS adapter using feedparser + aiohttp:

Tracks last_seen_id or published_date to avoid re-emitting old entries
Converts feed entries to Signal objects
Assigns tier based on source config


 Configure AP, Reuters, White House RSS feeds from politics.yaml
Test: Point at a real RSS feed (e.g. AP politics), call poll(), verify it returns Signal objects with non-empty headlines
Test: Call poll() twice rapidly, second call should return 0 new signals (dedup by ID)
Test: Verify tier assignment matches config

3.2 — Official government source adapter

 Congress.gov API adapter: poll for recent bill actions, votes, nominations
 Convert to Signal objects with tier=TIER_1_OFFICIAL
 Extract entities from bill titles and sponsor names
Test: Fetch recent bill actions, verify at least some come back
Test: Verify entities extracted contain recognizable names/bill numbers
Test: Rate limiting works (don't exceed 5000/hr)

3.3 — Twitter/X adapter (optional, low priority)

 If you have a Bearer token ($200/mo Basic tier): filtered stream or search recent
 If not: stub it out, use for backtest only with hardcoded fixtures
 Filter by account list and keyword list from config
 Assign tier=TIER_3_INSIDER
Test: If live: search for "BREAKING" from political accounts, verify results
Test: If stubbed: load from fixture JSON, verify Signal objects parse correctly

3.4 — SignalAggregator: dedup + unified queue

 Maintains an async queue that all sources push into
 Deduplication by content similarity (not just ID — same story from AP and Reuters should merge)

Simple approach: hash of normalized headline keywords
Better: TF-IDF cosine similarity with threshold


 When duplicate detected, upgrade tier to highest (AP + Reuters both report = higher confidence)
 Emit deduplicated signals to the scoring pipeline
Test: Push two signals with same headline from different sources, only one comes out
Test: Push two signals about same event with different wording, should still dedup (if using similarity)
Test: Merged signal gets upgraded tier
Test: Unrelated signals both pass through


Phase 4: Execution Module
4.1 — TradingStrategy: Kelly sizing + trade decisions

 evaluate(edge: EdgeEstimate, market: MarketState, portfolio: PortfolioState) -> TradeDecision | None
 Check edge > min_edge_threshold from config
 Kelly criterion position sizing:

  kelly_size = (edge * bankroll) / odds
  actual_size = kelly_size * kelly_fraction  # fractional Kelly from config

 Clamp to per-market max and portfolio max from config
 Determine side: if posterior > prior, BUY YES; if posterior < prior, BUY NO
 Set limit price slightly inside the spread for better fills
 Return None if edge too small, position limit hit, or risk check fails
Test:

Edge=0.10, bankroll=1000, kelly_fraction=0.25 -> size should be reasonable (not 0, not > max)
Edge=0.02 with threshold=0.05 -> returns None (below threshold)
Existing position at max -> returns None
Portfolio at max exposure -> returns None
Verify side is BUY for positive edge, SELL for negative edge
Verify limit_price is between best_bid and best_ask



4.2 — OrderExecutor: place orders via CLOB SDK

 Wraps py-clob-client to place limit orders
 Paper trading mode: logs the order without submitting (default for hackathon)
 Live mode: actually calls create_and_post_order
 Handle order responses: fills, partial fills, rejections
 Cancel stale orders after configurable timeout
Test (paper mode):

Create a TradeDecision, pass to executor in paper mode, verify log output
Verify no actual API call is made in paper mode


Test (live mode, optional, use tiny size):

Place a $0.01 limit order far from mid on a liquid market
Verify order appears in client.get_orders()
Cancel it immediately
Verify it's gone from open orders




Phase 5: Risk Module
5.1 — RiskManager: position + portfolio limits

 check_trade(decision: TradeDecision, portfolio: PortfolioState) -> (bool, str)

Returns (approved, reason)


 Per-market position limit (config: max_position_usd)
 Total portfolio exposure limit (config: max_total_exposure_usd)
 Correlated market detection: if two markets share entities (e.g. "nominee" and "confirmed"), reduce combined position limit
 Max drawdown guard: if unrealized PnL drops below threshold, pause trading
Test:

Empty portfolio, reasonable trade -> approved
Portfolio at 90% of max, trade that would exceed -> rejected with reason
Two correlated markets, second trade reduced or rejected
Portfolio in drawdown -> all trades rejected until recovery




Phase 6: Orchestrator (wire it all together)
6.1 — Main event loop

 Async loop in src/main.py:

Initialize all modules with config
Start market indexer refresh loop (background task)
Start all news source polling loops (background tasks)
Main loop: pull signals from aggregator queue

Classify signal (LLM)
Match to markets
For each matched market:

Get orderbook snapshot
Run Bayesian update (prior = market mid-price)
Calculate edge with decay
Generate trade decision
Risk check
Execute (paper or live)


Log everything


Graceful shutdown on SIGINT


Test: Run with --mode paper, feed a single hardcoded signal through, verify full pipeline log output
Test: Verify each log event type appears: signal_received, signal_classified, edge_calculated, trade_decision (or trade_skipped)
Test: Ctrl+C cleanly shuts down all background tasks


Phase 7: Backtest
7.1 — Historical data collection

 Biden dropout (July 21, 2024):

Collect timeline of tweets/news from public sources (news archives, Twitter threads)
Record Polymarket price snapshots if available (or approximate from public charts)
Format as JSON: [{"timestamp": "...", "source": "...", "tier": 3, "headline": "...", "body": "..."}, ...]


 Optionally: one more event (SCOTUS ruling or cabinet confirmation)
Test: JSON loads without error, all required fields present, timestamps are chronologically ordered

7.2 — BacktestRunner

 Replays historical signals through the full pipeline with simulated clock
 Uses recorded market prices instead of live orderbook
 Outputs structured JSON log identical to live agent format
 Computes summary metrics:

Total trades, win rate, total PnL
Average edge at entry, average time to fill
Max drawdown


Test: Run Biden dropout backtest end-to-end
Test: Agent should:

Detect Tier 3 rumors and open a small position
Detect Tier 1 official announcement and increase position aggressively
Total edge captured should be positive
All trades should respect risk limits



7.3 — Backtest visualization

 Plot edge decay over time for each signal
 Plot market price vs agent's posterior probability
 Plot cumulative PnL
 Save as PNG or HTML in backtest/results/
Test: Plots render without error and show meaningful curves (not flat lines)


Phase 8: Documentation + Polish
8.1 — README

 Architecture diagram (ASCII or mermaid)
 Signal taxonomy table with reliability priors
 Bayesian math walkthrough with a concrete numerical example
 Edge decay formula + plot
 Kelly sizing explanation
 Setup instructions
 Backtest results summary with key plots
 Limitations and future work

8.2 — Code quality

 Type hints on all public methods
 Docstrings on all classes and non-trivial methods
 Remove dead code and TODOs
 Run ruff or flake8 and fix lint errors
 Verify pytest passes all tests
Test: ruff check . returns 0 errors
Test: pytest -v all green

8.3 — Demo log

 Include a complete backtest log in backtest/results/biden_dropout_2024.jsonl
 Include summary output showing trades, PnL, edge metrics
 This is a judging deliverable — make it look good