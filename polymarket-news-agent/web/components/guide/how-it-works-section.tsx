import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Rss,
  Star,
  MessageSquare,
  Calculator,
  TrendingUp,
  AlertTriangle,
  Gauge,
  Shield,
} from "lucide-react"

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="scroll-mt-24">
      <div className="mb-10 border-b border-border/50 pb-6">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">How it works</h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          From raw news to executed trades, every step is explainable and auditable.
        </p>
      </div>

      <div className="mb-16">
        <h3 className="mb-6 text-xl font-semibold">Data inputs</h3>
        <p className="mb-6 text-muted-foreground">
          Information quality matters. We tier sources by reliability and weight their impact accordingly.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SourceCard
            tier="T1"
            icon={<Rss className="h-5 w-5" />}
            title="Official Sources"
            sources={["Reuters", "AP News", "Bloomberg", "Government feeds"]}
            weight="100%"
          />
          <SourceCard
            tier="T2"
            icon={<Star className="h-5 w-5" />}
            title="High-Trust X Accounts"
            sources={["Verified journalists", "Domain experts", "Official accounts"]}
            weight="70%"
          />
          <SourceCard
            tier="T3"
            icon={<MessageSquare className="h-5 w-5" />}
            title="General Social"
            sources={["Trending topics", "Community sentiment", "Rumor tracking"]}
            weight="30%"
          />
        </div>
      </div>

      <div className="mb-16">
        <h3 className="mb-6 text-xl font-semibold">Belief updates</h3>
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Bayesian posterior
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="overflow-x-auto rounded-lg bg-secondary/50 p-6">
              <code className="font-mono text-sm sm:text-base">P(H|E) = P(E|H) × P(H) / P(E)</code>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-border/50 p-4">
                <p className="mb-1 text-sm font-medium text-muted-foreground">Prior P(H)</p>
                <p>Current market price, representing crowd belief</p>
              </div>
              <div className="rounded-lg border border-border/50 p-4">
                <p className="mb-1 text-sm font-medium text-muted-foreground">Likelihood P(E|H)</p>
                <p>LLM-estimated probability news appears given outcome</p>
              </div>
              <div className="rounded-lg border border-border/50 p-4">
                <p className="mb-1 text-sm font-medium text-muted-foreground">Evidence P(E)</p>
                <p>Base rate of similar news events occurring</p>
              </div>
              <div className="rounded-lg border border-border/50 p-4">
                <p className="mb-1 text-sm font-medium text-muted-foreground">Posterior P(H|E)</p>
                <p>Updated belief after incorporating new evidence</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mb-16">
        <h3 className="mb-6 text-xl font-semibold">Edge calculation</h3>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Raw edge
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 rounded-lg bg-secondary/50 p-4">
                <code className="font-mono text-sm">edge = posterior - market_price</code>
              </div>
              <p className="text-sm text-muted-foreground">
                The difference between our belief and the market consensus. Positive edge = underpriced,
                negative = overpriced.
              </p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Adjusted edge
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 rounded-lg bg-secondary/50 p-4">
                <code className="font-mono text-sm">adj_edge = edge - decay - slippage</code>
              </div>
              <p className="text-sm text-muted-foreground">
                Decay accounts for stale signals. Slippage estimates execution costs from orderbook depth.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="mb-16">
        <h3 className="mb-6 text-xl font-semibold">Position sizing</h3>
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5" />
              Kelly criterion
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="overflow-x-auto rounded-lg bg-secondary/50 p-6">
              <code className="font-mono text-sm sm:text-base">f* = (p × b - q) / b</code>
            </div>
            <p className="text-muted-foreground">
              Where <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-sm">p</code> is win
              probability, <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-sm">q = 1-p</code>,
              and <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-sm">b</code> is the odds. We
              apply fractional Kelly (typically 25–50%) to reduce variance.
            </p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h3 className="mb-6 text-xl font-semibold">Risk controls</h3>
        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Configurable limits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="position">
                <AccordionTrigger>Position limits</AccordionTrigger>
                <AccordionContent>
                  <p className="text-muted-foreground">
                    Maximum single-market exposure capped at 10% of bankroll by default. Prevents concentration
                    risk in any single prediction.
                  </p>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="exposure">
                <AccordionTrigger>Total exposure</AccordionTrigger>
                <AccordionContent>
                  <p className="text-muted-foreground">
                    Aggregate open positions limited to 50% of bankroll. Maintains dry powder for new
                    opportunities.
                  </p>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="drawdown">
                <AccordionTrigger>Drawdown circuit breaker</AccordionTrigger>
                <AccordionContent>
                  <p className="text-muted-foreground">
                    Trading pauses if drawdown exceeds 15% in a 24-hour period. Requires manual review before
                    resuming.
                  </p>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="edge">
                <AccordionTrigger>Minimum edge threshold</AccordionTrigger>
                <AccordionContent>
                  <p className="text-muted-foreground">
                    Only execute trades with adjusted edge above 5%. Filters marginal opportunities that may not
                    cover transaction costs.
                  </p>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}

function SourceCard({
  tier,
  icon,
  title,
  sources,
  weight,
}: {
  tier: string
  icon: React.ReactNode
  title: string
  sources: string[]
  weight: string
}) {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-secondary text-xs font-semibold">
              {tier}
            </span>
            {icon}
          </div>
          <span className="text-sm font-medium text-positive">{weight}</span>
        </div>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1 text-sm text-muted-foreground">
          {sources.map((source) => (
            <li key={source}>• {source}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
