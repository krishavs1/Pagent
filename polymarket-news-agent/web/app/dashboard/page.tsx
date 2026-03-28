"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  signals as mockSignals,
  dashboardStats as mockStats,
  pipelineStatus as mockPipeline,
  positions as mockPositions,
} from "@/lib/mock-data"
import { AGENT_API_BASE, fetchDashboard, type DashboardPayload } from "@/lib/agent-api"
import { cn } from "@/lib/utils"
import { Check, Circle, Loader2, Wallet, TrendingUp, BarChart3, DollarSign } from "lucide-react"
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis } from "recharts"

const fallbackSpark = [
  { x: 0, y: 5 },
  { x: 1, y: 8 },
  { x: 2, y: 12 },
  { x: 3, y: 9 },
  { x: 4, y: 11 },
  { x: 5, y: 15 },
  { x: 6, y: 12 },
]

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch(() =>
        setError(
          `Cannot reach ${AGENT_API_BASE}. From the polymarket-news-agent folder run: uvicorn agent_api:app --reload --port 8765`,
        ),
      )
  }, [])

  const stats = data?.stats ?? mockStats
  const signals = data?.signals?.length ? data.signals : mockSignals
  const pipelineStatus = data?.pipelineStatus ?? mockPipeline
  const positions = data?.positions?.length ? data.positions : mockPositions
  const edgeSparkline = data?.edgeSparkline?.length ? data.edgeSparkline : fallbackSpark

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Live Dashboard
          </h1>
          <p className="mt-1 text-muted-foreground">
            Real-time trading signals and portfolio status
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {error && (
            <div className="max-w-xl rounded-md border border-amber-500/50 bg-amber-500/5 px-3 py-2 text-left text-sm text-amber-700 dark:text-amber-500">
              <p className="font-medium">Agent API unavailable — showing mock data.</p>
              <p className="mt-1 break-words font-mono text-xs leading-relaxed opacity-90">{error}</p>
            </div>
          )}
          {data && (
            <Badge variant="outline" className="border-positive/50 text-positive">
              Agent API
            </Badge>
          )}
          <Badge variant="outline" className="w-fit gap-2 border-positive/50 text-positive">
            <span className="h-2 w-2 rounded-full bg-positive animate-pulse" />
            Paper Trading
          </Badge>
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          icon={<Wallet className="h-4 w-4" />}
          label="Bankroll"
          value={`$${stats.bankroll.toLocaleString()}`}
        />
        <KPICard
          icon={<BarChart3 className="h-4 w-4" />}
          label="Total Exposure"
          value={`$${stats.totalExposure.toLocaleString()}`}
          sublabel={
            stats.bankroll > 0
              ? `${((stats.totalExposure / stats.bankroll) * 100).toFixed(1)}% of bankroll`
              : undefined
          }
        />
        <KPICard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Open Positions"
          value={stats.openPositions.toString()}
        />
        <KPICard
          icon={<DollarSign className="h-4 w-4" />}
          label="Unrealized PnL"
          value={`${stats.unrealizedPnl >= 0 ? "+" : ""}$${stats.unrealizedPnl.toFixed(2)}`}
          valueClassName={stats.unrealizedPnl >= 0 ? "text-positive" : "text-negative"}
        />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-3">
        <Card className="border-border/50 bg-card/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Pipeline Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {pipelineStatus.map((step, index) => (
                <div key={step.step} className="flex items-center gap-2">
                  <PipelineStatusIndicator status={step.status} />
                  <span
                    className={cn(
                      "text-sm",
                      step.status === "pending" && "text-muted-foreground"
                    )}
                  >
                    {step.step}
                  </span>
                  {index < pipelineStatus.length - 1 && (
                    <span className="mx-1 text-muted-foreground">→</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Edge (recent)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-16">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={edgeSparkline}>
                  <defs>
                    <linearGradient id="edgeFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.65 0.2 250)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="oklch(0.65 0.2 250)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="x" hide />
                  <YAxis hide />
                  <Area
                    type="monotone"
                    dataKey="y"
                    stroke="oklch(0.65 0.2 250)"
                    strokeWidth={2}
                    fill="url(#edgeFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Avg edge: {(stats.avgEdge * 100).toFixed(1)}% (abs)
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="mb-8 border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Recent Signals</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="w-[140px]">Time</TableHead>
                  <TableHead className="w-[60px]">Tier</TableHead>
                  <TableHead>Headline</TableHead>
                  <TableHead className="hidden lg:table-cell">Market</TableHead>
                  <TableHead className="w-[80px] text-right">Prior</TableHead>
                  <TableHead className="w-[80px] text-right">Post</TableHead>
                  <TableHead className="w-[80px] text-right">Edge</TableHead>
                  <TableHead className="w-[80px] text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((signal, index) => (
                  <TableRow key={`${signal.id}-${index}`} className="border-border/50">
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {"time" in signal && signal.time.includes(" ")
                        ? signal.time.split(" ")[1]
                        : String(signal.time).slice(11, 19) || signal.time}
                    </TableCell>
                    <TableCell>
                      <TierBadge tier={signal.sourceTier} />
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm">
                      {signal.headline}
                    </TableCell>
                    <TableCell className="hidden max-w-[150px] truncate text-sm text-muted-foreground lg:table-cell">
                      {signal.matchedMarket}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {(signal.prior * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {(signal.posterior * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono text-sm",
                        signal.adjustedEdge > 0
                          ? "text-positive"
                          : signal.adjustedEdge < 0
                            ? "text-negative"
                            : ""
                      )}
                    >
                      {signal.adjustedEdge > 0 ? "+" : ""}
                      {(signal.adjustedEdge * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell className="text-right">
                      <ActionBadge action={signal.action} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Open Positions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead>Market</TableHead>
                  <TableHead className="w-[80px]">Side</TableHead>
                  <TableHead className="w-[80px] text-right">Shares</TableHead>
                  <TableHead className="w-[80px] text-right">Avg</TableHead>
                  <TableHead className="w-[80px] text-right">Current</TableHead>
                  <TableHead className="w-[100px] text-right">PnL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      No open positions (paper / backtest replay)
                    </TableCell>
                  </TableRow>
                ) : (
                  positions.map((position) => (
                    <TableRow key={position.id} className="border-border/50">
                      <TableCell className="max-w-[250px] truncate text-sm">
                        {position.market}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            position.side === "YES"
                              ? "border-positive/50 text-positive"
                              : "border-negative/50 text-negative"
                          )}
                        >
                          {position.side}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {position.shares}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        ${position.avgPrice.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        ${position.currentPrice.toFixed(2)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-mono text-sm",
                          position.pnl >= 0 ? "text-positive" : "text-negative"
                        )}
                      >
                        {position.pnl >= 0 ? "+" : ""}${position.pnl.toFixed(2)}
                        <span className="ml-1 text-xs text-muted-foreground">
                          ({position.pnlPercent.toFixed(1)}%)
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function KPICard({
  icon,
  label,
  value,
  sublabel,
  valueClassName,
}: {
  icon: React.ReactNode
  label: string
  value: string
  sublabel?: string
  valueClassName?: string
}) {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-sm">{label}</span>
        </div>
        <p className={cn("mt-2 text-2xl font-semibold", valueClassName)}>{value}</p>
        {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
      </CardContent>
    </Card>
  )
}

function PipelineStatusIndicator({ status }: { status: "complete" | "running" | "pending" }) {
  if (status === "complete") {
    return (
      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-positive/20">
        <Check className="h-3 w-3 text-positive" />
      </div>
    )
  }
  if (status === "running") {
    return (
      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-chart-3/20">
        <Loader2 className="h-3 w-3 animate-spin text-chart-3" />
      </div>
    )
  }
  return (
    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-secondary">
      <Circle className="h-3 w-3 text-muted-foreground" />
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    T1: "bg-positive/20 text-positive border-positive/30",
    T2: "bg-chart-4/20 text-chart-4 border-chart-4/30",
    T3: "bg-muted text-muted-foreground border-border",
    T4: "bg-secondary text-secondary-foreground border-border",
  }
  return (
    <Badge variant="outline" className={cn("text-xs", colors[tier] ?? colors.T3)}>
      {tier}
    </Badge>
  )
}

function ActionBadge({ action }: { action: "BUY" | "HOLD" | "SKIP" | "SELL" }) {
  const styles = {
    BUY: "bg-positive/20 text-positive border-positive/30",
    SELL: "bg-negative/20 text-negative border-negative/30",
    HOLD: "bg-chart-4/20 text-chart-4 border-chart-4/30",
    SKIP: "bg-muted text-muted-foreground border-border",
  }
  return (
    <Badge variant="outline" className={cn("text-xs", styles[action])}>
      {action}
    </Badge>
  )
}
