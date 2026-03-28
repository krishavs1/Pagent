"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  backtestMetrics as mockMetrics,
  equityCurve as mockEquity,
  eventTimeline as mockTimeline,
} from "@/lib/mock-data"
import {
  fetchBacktestEquity,
  fetchBacktestLogTail,
  fetchBacktestReplay,
  fetchBacktestSummary,
  jsonlDownloadUrl,
  runBacktest,
  type EquityPayload,
  type ReplaySignal,
} from "@/lib/agent-api"
import { cn } from "@/lib/utils"
import {
  Download,
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Clock,
  BarChart3,
  Loader2,
  Play,
  Pause,
  Activity,
  Cpu,
  Radio,
  Terminal,
  Zap,
} from "lucide-react"
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts"

const PIPELINE_STEPS = [
  { id: "load", label: "Load dataset", icon: Cpu },
  { id: "signals", label: "Replay signals", icon: Radio },
  { id: "bayes", label: "Bayesian + edge", icon: Activity },
  { id: "book", label: "Orderbook fill", icon: Zap },
  { id: "risk", label: "Risk + sizing", icon: Target },
  { id: "settle", label: "Settlement + MTM", icon: DollarSign },
  { id: "write", label: "Write artifacts", icon: Terminal },
]

type Metrics = {
  settlementPnl: number
  maxDrawdown: number
  winRate: number
  totalFees: number
  mtmEquity: number
  totalTrades: number
  avgSlippageBps: number
  maxDrawdownMtm: number
  executionAttempts?: number
  fillRate?: number
}

function summaryToMetrics(s: Record<string, unknown>): Metrics {
  const g = (k: string, d = 0) => {
    const v = s[k]
    return typeof v === "number" ? v : d
  }
  return {
    settlementPnl: g("total_pnl_usd"),
    maxDrawdown: -Math.abs(g("max_drawdown_usd")),
    winRate: g("win_rate"),
    totalFees: g("fees_paid_usd"),
    mtmEquity: g("terminal_equity_mtm_usd"),
    totalTrades: g("settled_trades", g("total_trades")),
    avgSlippageBps: g("avg_slippage_bps"),
    maxDrawdownMtm: g("max_drawdown_mtm_usd"),
    executionAttempts: g("execution_attempts"),
    fillRate: g("fill_rate"),
  }
}

export default function BacktestPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [equity, setEquity] = useState<Array<{ date: string; equity: number }>>([])
  const [equityLines, setEquityLines] = useState<
    Array<{ label: string; equity: number; cash: number; position: number }>
  >([])
  const [timeline, setTimeline] = useState(mockTimeline)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const [simStep, setSimStep] = useState(0)
  const [replay, setReplay] = useState<ReplaySignal[]>([])
  const [logLines, setLogLines] = useState<Array<{ event: string; text: string }>>([])
  const [replayPlaying, setReplayPlaying] = useState(false)
  const [replayIdx, setReplayIdx] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sum, eq, rp, logs] = await Promise.all([
        fetchBacktestSummary(),
        fetchBacktestEquity(),
        fetchBacktestReplay().catch(() => ({ signals: [] as ReplaySignal[] })),
        fetchBacktestLogTail(150).catch(() => ({ lines: [] })),
      ])
      setMetrics(summaryToMetrics(sum))
      setReplay(rp.signals ?? [])
      setLogLines(logs.lines ?? [])

      const pts = (eq as EquityPayload).points ?? []
      if (pts.length) {
        setEquity(
          pts.map((p) => ({
            date: p.timestamp.slice(5, 16).replace("T", " "),
            equity: p.equity_usd,
          }))
        )
        setEquityLines(
          pts.map((p) => ({
            label: p.timestamp.slice(11, 19) + " · " + p.signal_id,
            equity: p.equity_usd,
            cash: p.cash_usd,
            position: p.position_value_usd,
          }))
        )
        setTimeline(
          pts.map((p, i) => ({
            id: `pt-${i}`,
            date: p.timestamp.slice(0, 10),
            event: `${p.signal_id}: MTM equity $${p.equity_usd.toFixed(2)}`,
            type: "signal" as const,
            posterior: 0,
          }))
        )
      } else {
        setEquity(mockEquity)
        setEquityLines([])
        setTimeline(mockTimeline)
      }
      setLive(true)
    } catch {
      setMetrics({
        settlementPnl: mockMetrics.settlementPnl,
        maxDrawdown: mockMetrics.maxDrawdown,
        winRate: mockMetrics.winRate,
        totalFees: mockMetrics.totalFees,
        mtmEquity: mockMetrics.mtmEquity,
        totalTrades: mockMetrics.totalTrades,
        avgSlippageBps: 0,
        maxDrawdownMtm: 0,
      })
      setEquity(mockEquity)
      setEquityLines([])
      setTimeline(mockTimeline)
      setReplay([])
      setLogLines([])
      setError("Agent API unavailable — mock metrics only.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!running) {
      setSimStep(0)
      return
    }
    const id = window.setInterval(() => {
      setSimStep((s) => (s + 1) % PIPELINE_STEPS.length)
    }, 420)
    return () => clearInterval(id)
  }, [running])

  useEffect(() => {
    if (!replayPlaying || replay.length === 0) return
    const id = window.setInterval(() => {
      setReplayIdx((i) => (i + 1) % replay.length)
    }, 2200)
    return () => clearInterval(id)
  }, [replayPlaying, replay.length])

  const onRun = async () => {
    setRunning(true)
    setError(null)
    try {
      await runBacktest()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest failed")
    } finally {
      setRunning(false)
    }
  }

  const m = metrics ?? {
    settlementPnl: mockMetrics.settlementPnl,
    maxDrawdown: mockMetrics.maxDrawdown,
    winRate: mockMetrics.winRate,
    totalFees: mockMetrics.totalFees,
    mtmEquity: mockMetrics.mtmEquity,
    totalTrades: mockMetrics.totalTrades,
    avgSlippageBps: 0,
    maxDrawdownMtm: 0,
  }

  const eqMin = equity.length ? Math.min(...equity.map((e) => e.equity)) * 0.98 : 0
  const eqMax = equity.length ? Math.max(...equity.map((e) => e.equity)) * 1.02 : 1

  const winLoss = useMemo(() => {
    const total = Math.max(1, Math.round(m.totalTrades))
    const wins = Math.round(m.winRate * total)
    const losses = Math.max(0, total - wins)
    return [
      { name: "Wins", value: wins, fill: "oklch(0.65 0.2 145)" },
      { name: "Losses", value: losses, fill: "oklch(0.55 0.2 25)" },
    ]
  }, [m.totalTrades, m.winRate])

  const simProgress = running ? ((simStep + 1) / PIPELINE_STEPS.length) * 100 : 0

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Backtest lab
            </h1>
            <Badge variant="outline" className="gap-1 border-chart-3/50 font-mono text-xs text-chart-3">
              <Activity className="h-3 w-3" />
              snapshot replay
            </Badge>
          </div>
          <p className="mt-1 text-muted-foreground">
            Python runner · historical JSON · ladder fills · MTM equity
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {live && (
            <Badge variant="outline" className="border-positive/50 text-positive">
              Agent API
            </Badge>
          )}
          {error && (
            <Badge variant="outline" className="max-w-[280px] border-amber-500/50 text-amber-600">
              {error}
            </Badge>
          )}
          <Button variant="outline" className="gap-2" asChild>
            <a href={jsonlDownloadUrl()} download target="_blank" rel="noreferrer">
              <Download className="h-4 w-4" />
              JSONL
            </a>
          </Button>
          <Button className="gap-2" disabled={running || loading} onClick={onRun}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            Run backtest
          </Button>
        </div>
      </div>

      {/* Live simulation strip */}
      <Card
        className={cn(
          "mb-8 overflow-hidden border-border/60 bg-gradient-to-br from-card/80 to-card/40",
          running && "ring-2 ring-chart-3/40"
        )}
      >
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Radio className={cn("h-5 w-5", running && "animate-pulse text-chart-3")} />
                {running ? "Running backtest…" : "Simulation engine idle"}
              </CardTitle>
              <CardDescription>
                While Python runs, this panel cycles through pipeline stages (visual only). When
                finished, metrics and charts refresh from disk.
              </CardDescription>
            </div>
            {running && (
              <Badge className="bg-chart-3/20 text-chart-3">
                subprocess · backtest.runner
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={simProgress} className="h-2" />
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {PIPELINE_STEPS.map((step, i) => {
              const Icon = step.icon
              const active = running && i === simStep
              const done = running && i < simStep
              return (
                <div
                  key={step.id}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-all",
                    active && "border-chart-3 bg-chart-3/10 shadow-md",
                    done && !active && "border-positive/30 bg-positive/5",
                    !running && "opacity-70"
                  )}
                >
                  <Icon className={cn("h-4 w-4 shrink-0", active && "text-chart-3")} />
                  <span className="font-medium leading-tight">{step.label}</span>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading results…
        </div>
      ) : (
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full max-w-lg grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="replay">Signal replay</TabsTrigger>
            <TabsTrigger value="console">Console log</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-8">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                icon={<DollarSign className="h-4 w-4" />}
                label="Settlement PnL"
                value={`${m.settlementPnl >= 0 ? "+" : ""}$${m.settlementPnl.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                valueClassName={m.settlementPnl >= 0 ? "text-positive" : "text-negative"}
              />
              <MetricCard
                icon={<TrendingDown className="h-4 w-4" />}
                label="Max DD (settlement)"
                value={`$${m.maxDrawdown.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                valueClassName="text-negative"
              />
              <MetricCard
                icon={<Target className="h-4 w-4" />}
                label="Win rate"
                value={`${(m.winRate * 100).toFixed(0)}%`}
              />
              <MetricCard
                icon={<BarChart3 className="h-4 w-4" />}
                label="Avg slippage (bps)"
                value={m.avgSlippageBps > 0 ? m.avgSlippageBps.toFixed(0) : "—"}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
                <MetricCard
                  icon={<DollarSign className="h-4 w-4" />}
                  label="Fees paid"
                  value={`$${m.totalFees.toFixed(2)}`}
                  small
                />
                <MetricCard
                  icon={<TrendingUp className="h-4 w-4" />}
                  label="Terminal MTM equity"
                  value={`$${m.mtmEquity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                  small
                />
                <MetricCard
                  icon={<BarChart3 className="h-4 w-4" />}
                  label="Settled trades"
                  value={String(m.totalTrades)}
                  small
                />
                <MetricCard
                  icon={<Clock className="h-4 w-4" />}
                  label="Max MTM drawdown"
                  value={m.maxDrawdownMtm > 0 ? `$${m.maxDrawdownMtm.toFixed(2)}` : "—"}
                  small
                />
                {m.executionAttempts != null && m.executionAttempts > 0 && (
                  <>
                    <MetricCard
                      icon={<Activity className="h-4 w-4" />}
                      label="Execution attempts"
                      value={String(Math.round(m.executionAttempts))}
                      small
                    />
                    <MetricCard
                      icon={<Target className="h-4 w-4" />}
                      label="Fill rate"
                      value={m.fillRate != null ? `${(m.fillRate * 100).toFixed(0)}%` : "—"}
                      small
                    />
                  </>
                )}
              </div>

              <Card className="border-border/50 bg-card/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Outcome mix</CardTitle>
                  <CardDescription className="text-xs">Settled trades (approx)</CardDescription>
                </CardHeader>
                <CardContent className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={winLoss}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={48}
                        outerRadius={72}
                        paddingAngle={2}
                      >
                        {winLoss.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "oklch(0.16 0.005 260)",
                          border: "1px solid oklch(0.28 0.005 260)",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {equityLines.length > 0 ? (
              <Card className="border-border/50 bg-card/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Equity, cash & position (MTM)</CardTitle>
                  <CardDescription>
                    After each signal: total equity vs cash vs mark-to-market position value
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={equityLines} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.005 260)" />
                      <XAxis dataKey="label" tick={{ fontSize: 9 }} hide />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: number) =>
                          Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`
                        }
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "oklch(0.16 0.005 260)",
                          border: "1px solid oklch(0.28 0.005 260)",
                          borderRadius: "8px",
                          maxWidth: 360,
                        }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="equity" stroke="oklch(0.65 0.2 250)" dot={false} strokeWidth={2} name="Equity" />
                      <Line type="monotone" dataKey="cash" stroke="oklch(0.65 0.2 145)" dot={false} strokeWidth={1.5} name="Cash" />
                      <Line type="monotone" dataKey="position" stroke="oklch(0.7 0.15 55)" dot={false} strokeWidth={1.5} name="Position MTM" />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            ) : null}

            <Card className="border-border/50 bg-card/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Cumulative MTM equity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 sm:h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equity} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="equityFill2" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="oklch(0.65 0.2 250)" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="oklch(0.65 0.2 250)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.005 260)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis domain={[eqMin, eqMax]} tick={{ fontSize: 11 }} tickFormatter={(v: number) =>
                        `$${v >= 1000 ? (v / 1000).toFixed(1) + "k" : v.toFixed(0)}`
                      } />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "oklch(0.16 0.005 260)",
                          border: "1px solid oklch(0.28 0.005 260)",
                          borderRadius: "8px",
                        }}
                        formatter={(value: number) => [`$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`, "Equity"]}
                      />
                      <Area type="monotone" dataKey="equity" stroke="oklch(0.65 0.2 250)" strokeWidth={2} fill="url(#equityFill2)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/50 bg-card/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Signal checkpoints</CardTitle>
                <CardDescription>One row per post-signal MTM snapshot</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <div className="absolute left-[7px] top-3 h-[calc(100%-24px)] w-px bg-border" />
                  <div className="space-y-5">
                    {timeline.map((event) => (
                      <div key={event.id} className="relative flex gap-4">
                        <div
                          className={cn(
                            "relative z-10 mt-1.5 h-3.5 w-3.5 rounded-full border-2",
                            event.type === "signal" && "border-chart-3 bg-chart-3/20",
                            event.type === "trade" && "border-chart-4 bg-chart-4/20",
                            event.type === "resolution" && "border-positive bg-positive/20"
                          )}
                        />
                        <div className="flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs text-muted-foreground">{event.date}</span>
                            <Badge variant="outline" className="text-[10px] capitalize">
                              {event.type}
                            </Badge>
                          </div>
                          <p className="mt-1 text-sm">{event.event}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="replay" className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                Each card is one ingested signal: Bayesian edges per market, then simulated fills.
              </p>
              <div className="flex gap-2">
                <Button
                  variant={replayPlaying ? "secondary" : "outline"}
                  size="sm"
                  className="gap-1"
                  onClick={() => setReplayPlaying(!replayPlaying)}
                  disabled={replay.length === 0}
                >
                  {replayPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {replayPlaying ? "Pause" : "Play"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setReplayIdx(0)}>
                  Reset
                </Button>
              </div>
            </div>
            {replay.length === 0 ? (
              <p className="text-sm text-muted-foreground">No replay data — run the API with a generated JSONL.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {replay.map((sig, idx) => (
                  <Card
                    key={`${sig.signalId}-${idx}-${sig.timestamp}`}
                    className={cn(
                      "border-border/50 transition-all",
                      replayPlaying && replayIdx === idx && "ring-2 ring-chart-3/60"
                    )}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {sig.signalId}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">{sig.timestamp.slice(11, 19)}</span>
                      </div>
                      <CardTitle className="text-base leading-snug">{sig.headline}</CardTitle>
                      <CardDescription className="text-xs">{sig.source}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      <div>
                        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Edge / posterior
                        </p>
                        <ul className="space-y-1 font-mono text-xs">
                          {sig.edges.map((e, j) => (
                            <li key={j} className="flex justify-between gap-2 border-b border-border/40 py-1">
                              <span className="truncate text-muted-foreground">{e.marketId.slice(-12)}</span>
                              <span>
                                p={e.posterior.toFixed(3)} · Δ={e.adjustedEdge >= 0 ? "+" : ""}
                                {e.adjustedEdge.toFixed(3)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      {(sig.trades.length > 0 || sig.skipped.length > 0) && (
                        <div>
                          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Execution
                          </p>
                          {sig.trades.map((t, j) => (
                            <div
                              key={j}
                              className="mb-1 flex flex-wrap items-center justify-between gap-1 rounded-md bg-positive/10 px-2 py-1 font-mono text-xs text-positive"
                            >
                              <span>{t.side}</span>
                              <span className="truncate">{t.marketId.slice(-14)}</span>
                              <span>${t.sizeUsd.toFixed(2)}</span>
                            </div>
                          ))}
                          {sig.skipped.map((s, j) => (
                            <div
                              key={j}
                              className="mb-1 rounded-md bg-muted/50 px-2 py-1 font-mono text-[11px] text-muted-foreground"
                            >
                              skip {s.reason}
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="console">
            <Card className="border-border/50 bg-[oklch(0.12_0.01_260)] font-mono text-xs">
              <CardHeader className="flex flex-row items-center justify-between py-3">
                <CardTitle className="flex items-center gap-2 text-sm text-chart-3">
                  <Terminal className="h-4 w-4" />
                  JSONL tail (structured)
                </CardTitle>
                <Badge variant="outline" className="text-[10px] text-muted-foreground">
                  {logLines.length} lines
                </Badge>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[min(420px,50vh)] rounded-md border border-border/50">
                  <div className="space-y-0.5 p-4 leading-relaxed">
                    {logLines.length === 0 ? (
                      <p className="text-muted-foreground">No log — start the API and run a backtest.</p>
                    ) : (
                      logLines.map((line, i) => (
                        <div
                          key={i}
                          className={cn(
                            "break-all border-l-2 border-transparent pl-2",
                            line.event === "trade_executed" && "border-positive/50 text-positive",
                            line.event === "edge_calculated" && "border-chart-3/50 text-chart-3",
                            line.event === "signal_received" && "border-chart-4/50 text-foreground"
                          )}
                        >
                          <span className="mr-2 opacity-50">{line.event}</span>
                          {line.text}
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  valueClassName,
  small,
}: {
  icon: React.ReactNode
  label: string
  value: string
  valueClassName?: string
  small?: boolean
}) {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className={cn("p-4", small && "py-3")}>
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className={cn("text-sm", small && "text-xs")}>{label}</span>
        </div>
        <p className={cn("mt-2 font-semibold", small ? "text-lg" : "text-2xl", valueClassName)}>
          {value}
        </p>
      </CardContent>
    </Card>
  )
}
