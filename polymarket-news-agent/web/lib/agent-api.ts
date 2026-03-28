/** Backend for the Python agent (FastAPI). See `agent_api.py` and README. */

export const AGENT_API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://127.0.0.1:8765")
    : process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://127.0.0.1:8765"

export type DashboardSignal = {
  id: string
  time: string
  sourceTier: string
  source: string
  headline: string
  matchedMarket: string
  marketId?: string
  prior: number
  posterior: number
  adjustedEdge: number
  action: "BUY" | "SELL" | "SKIP" | "HOLD"
  confidence: number
}

export type DashboardPayload = {
  stats: {
    bankroll: number
    totalExposure: number
    openPositions: number
    unrealizedPnl: number
    realizedPnl: number
    winRate: number
    totalTrades: number
    avgEdge: number
  }
  signals: DashboardSignal[]
  positions: Array<{
    id: string
    market: string
    side: string
    shares: number
    avgPrice: number
    currentPrice: number
    pnl: number
    pnlPercent: number
  }>
  pipelineStatus: Array<{ step: string; status: "complete" | "running" | "pending"; lastRun: string }>
  edgeSparkline: Array<{ x: number; y: number }>
}

export async function fetchDashboard(): Promise<DashboardPayload> {
  const r = await fetch(`${AGENT_API_BASE}/api/dashboard`, { cache: "no-store" })
  if (!r.ok) throw new Error(`dashboard ${r.status}`)
  return r.json()
}

export type BacktestSummary = Record<string, number | string | boolean | null>

export async function fetchBacktestSummary(): Promise<BacktestSummary> {
  const r = await fetch(`${AGENT_API_BASE}/api/backtest/summary`, { cache: "no-store" })
  if (!r.ok) throw new Error(`summary ${r.status}`)
  return r.json()
}

export type EquityPayload = {
  dataset: string
  bankroll_start_usd: number
  points: Array<{
    timestamp: string
    unix_ts: number
    signal_id: string
    equity_usd: number
    cash_usd: number
    position_value_usd: number
    unrealized_mtm_usd: number
    shares_yes: Record<string, number>
  }>
  metrics: Record<string, number>
}

export async function fetchBacktestEquity(): Promise<EquityPayload> {
  const r = await fetch(`${AGENT_API_BASE}/api/backtest/equity`, { cache: "no-store" })
  if (!r.ok) throw new Error(`equity ${r.status}`)
  return r.json()
}

export async function runBacktest(): Promise<{ ok: boolean; message?: string }> {
  const r = await fetch(`${AGENT_API_BASE}/api/backtest/run`, { method: "POST" })
  if (!r.ok) {
    const t = await r.text()
    throw new Error(t || `run ${r.status}`)
  }
  return r.json()
}

export function jsonlDownloadUrl(): string {
  return `${AGENT_API_BASE}/api/backtest/file/jsonl`
}

export type ReplayEdge = {
  marketId: string
  posterior: number
  adjustedEdge: number
}

export type ReplayTrade = {
  marketId: string
  side: string
  sizeUsd: number
  feeUsd: number
  slippageBps: number
}

export type ReplaySkip = {
  marketId: string
  reason: string
}

export type ReplaySignal = {
  signalId: string
  headline: string
  source: string
  timestamp: string
  edges: ReplayEdge[]
  trades: ReplayTrade[]
  skipped: ReplaySkip[]
}

export type ReplayPayload = {
  dataset: string
  signals: ReplaySignal[]
}

export async function fetchBacktestReplay(): Promise<ReplayPayload> {
  const r = await fetch(`${AGENT_API_BASE}/api/backtest/replay`, { cache: "no-store" })
  if (!r.ok) throw new Error(`replay ${r.status}`)
  return r.json()
}

export type LogTailPayload = {
  lines: Array<{ event: string; text: string }>
}

export async function fetchBacktestLogTail(limit = 120): Promise<LogTailPayload> {
  const r = await fetch(`${AGENT_API_BASE}/api/backtest/log_tail?limit=${limit}`, {
    cache: "no-store",
  })
  if (!r.ok) throw new Error(`log_tail ${r.status}`)
  return r.json()
}
