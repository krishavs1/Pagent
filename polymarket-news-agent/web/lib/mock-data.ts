// Mock data for the trading agent dashboard

export const signals = [
  {
    id: "h0",
    time: "2024-07-20 22:30:00",
    sourceTier: "T2",
    source: "CNN (reporting)",
    headline: "Biden meets campaign advisors July 20 as path to nomination questioned",
    matchedMarket: "Biden wins 2024 Dem nomination?",
    marketId: "biden_dnom_2024",
    prior: 0.265,
    posterior: 0.104,
    adjustedEdge: -0.161,
    action: "SKIP" as const,
    confidence: 0.55,
  },
  {
    id: "h1",
    time: "2024-07-21 13:00:00",
    sourceTier: "T2",
    source: "Press reports",
    headline: "Major outlets report Democratic leaders preparing for possible nominee change",
    matchedMarket: "Biden wins 2024 Dem nomination?",
    marketId: "biden_dnom_2024",
    prior: 0.285,
    posterior: 0.03,
    adjustedEdge: -0.255,
    action: "SKIP" as const,
    confidence: 0.58,
  },
  {
    id: "h2",
    time: "2024-07-21 17:50:00",
    sourceTier: "T1",
    source: "White House / public letter",
    headline: "Biden releases letter withdrawing from 2024 presidential candidacy",
    matchedMarket: "Biden wins 2024 Dem nomination?",
    marketId: "biden_dnom_2024",
    prior: 0.275,
    posterior: 0.001,
    adjustedEdge: -0.274,
    action: "SKIP" as const,
    confidence: 0.96,
  },
  {
    id: "h3",
    time: "2024-07-21 18:45:00",
    sourceTier: "T1",
    source: "AP / wires",
    headline: "Wire services confirm Biden ends bid; focus shifts to successor",
    matchedMarket: "Biden wins 2024 Dem nomination?",
    marketId: "biden_dnom_2024",
    prior: 0.017,
    posterior: 0.0,
    adjustedEdge: 0.017,
    action: "BUY" as const,
    confidence: 0.9,
  },
]

export const positions = [
  {
    id: "pos_001",
    market: "Biden wins 2024 Dem nomination?",
    side: "YES",
    shares: 5882,
    avgPrice: 0.017,
    currentPrice: 0.0015,
    pnl: -90.12,
    pnlPercent: -91.2,
  },
]

export const dashboardStats = {
  bankroll: 1000,
  totalExposure: 100,
  openPositions: 1,
  unrealizedPnl: -90.12,
  realizedPnl: 0.0,
  winRate: 0.0,
  totalTrades: 1,
  avgEdge: 0.017,
}

export const pipelineStatus = [
  { step: "Ingestion", status: "complete" as const, lastRun: "from replay" },
  { step: "Aggregation", status: "complete" as const, lastRun: "from replay" },
  { step: "Market Matching", status: "complete" as const, lastRun: "from replay" },
  { step: "Bayesian Update", status: "complete" as const, lastRun: "from replay" },
  { step: "Edge Calculation", status: "complete" as const, lastRun: "from replay" },
  { step: "Risk Check", status: "complete" as const, lastRun: "from replay" },
  { step: "Execution", status: "complete" as const, lastRun: "from replay" },
]

export const edgeHistory = [
  { time: "22:30", edge: 16.1 },
  { time: "13:00", edge: 25.5 },
  { time: "17:50", edge: 27.4 },
  { time: "18:45", edge: 1.7 },
]

export const backtestMetrics = {
  settlementPnl: -100.06,
  maxDrawdown: 0,
  winRate: 0.0,
  totalFees: 0.07,
  mtmEquity: 901.26,
  sharpeRatio: 0,
  totalTrades: 1,
  avgHoldTime: "instant",
}

export const equityCurve = [
  { date: "Jul 20 22:30", equity: 1000 },
  { date: "Jul 21 13:00", equity: 1000 },
  { date: "Jul 21 17:50", equity: 1000 },
  { date: "Jul 21 18:45", equity: 901.26 },
]

export const eventTimeline = [
  {
    id: "evt_h0",
    date: "2024-07-20",
    event: "Signal: Biden meets advisors as nomination questioned — edge -16.1%, SKIP",
    type: "signal" as const,
    posterior: 0.104,
  },
  {
    id: "evt_h1",
    date: "2024-07-21",
    event: "Signal: Democratic leaders preparing for possible nominee change — edge -25.5%, SKIP",
    type: "signal" as const,
    posterior: 0.03,
  },
  {
    id: "evt_h2",
    date: "2024-07-21",
    event: "Signal: Biden releases withdrawal letter — edge -27.4%, SKIP",
    type: "signal" as const,
    posterior: 0.001,
  },
  {
    id: "evt_h3",
    date: "2024-07-21",
    event: "Signal: Wire services confirm; BUY YES $100 @ 0.017 — resolved NO → loss",
    type: "trade" as const,
    posterior: 0.0,
  },
  {
    id: "evt_res",
    date: "2024-07-21",
    event: "Market resolved: NO — Biden did not win 2024 Democratic nomination",
    type: "resolution" as const,
    posterior: 0.0,
  },
]

// Architecture data
export const architectureNodes = [
  { id: "ingestion", label: "Ingestion", description: "RSS, official feeds, X API polling" },
  { id: "aggregator", label: "Aggregator", description: "Dedup, normalize, timestamp align" },
  { id: "indexer", label: "Indexer/Matcher", description: "Map news to Polymarket contracts" },
  { id: "classifier", label: "Classifier", description: "LLM-based relevance & sentiment" },
  { id: "bayesian", label: "Bayesian Engine", description: "Prior → posterior belief updates" },
  { id: "edge", label: "Edge Calculator", description: "Edge vs orderbook, decay, slippage" },
  { id: "orderbook", label: "Orderbook Client", description: "CLOB depth, liquidity analysis" },
  { id: "strategy", label: "Strategy", description: "Kelly sizing, portfolio allocation" },
  { id: "risk", label: "Risk Manager", description: "Position limits, exposure caps" },
  { id: "executor", label: "Executor", description: "Order placement (paper by default)" },
  { id: "logger", label: "Logger", description: "Audit trail, metrics, JSONL export" },
]

// Docs data
export const envVars = [
  { key: "ANTHROPIC_API_KEY", description: "Claude API for classification", required: true },
  { key: "X_BEARER_TOKEN", description: "Twitter/X API access", required: true },
  { key: "POLYMARKET_API_KEY", description: "Polymarket CLOB access", required: true },
  { key: "POLYMARKET_SECRET", description: "Signing key for orders", required: true },
  { key: "PAPER_MODE", description: "Enable paper trading (default: true)", required: false },
]

export const resources = [
  { label: "Polymarket Docs", url: "https://docs.polymarket.com", icon: "book" },
  { label: "CLOB Client GitHub", url: "https://github.com/polymarket/clob-client", icon: "github" },
  { label: "API Reference", url: "#api-reference", icon: "code" },
  { label: "Bayesian Methodology", url: "#methodology", icon: "chart" },
]
