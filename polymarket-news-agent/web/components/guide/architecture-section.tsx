import { Card, CardContent } from "@/components/ui/card"
import { architectureNodes } from "@/lib/mock-data"
import {
  ArrowRight,
  Rss,
  Layers,
  Search,
  MessageSquare,
  Calculator,
  TrendingUp,
  BookOpen,
  Sliders,
  Shield,
  Play,
  FileText,
} from "lucide-react"

const nodeIcons: Record<string, React.ReactNode> = {
  ingestion: <Rss className="h-5 w-5" />,
  aggregator: <Layers className="h-5 w-5" />,
  indexer: <Search className="h-5 w-5" />,
  classifier: <MessageSquare className="h-5 w-5" />,
  bayesian: <Calculator className="h-5 w-5" />,
  edge: <TrendingUp className="h-5 w-5" />,
  orderbook: <BookOpen className="h-5 w-5" />,
  strategy: <Sliders className="h-5 w-5" />,
  risk: <Shield className="h-5 w-5" />,
  executor: <Play className="h-5 w-5" />,
  logger: <FileText className="h-5 w-5" />,
}

export function ArchitectureSection() {
  return (
    <section id="architecture" className="scroll-mt-24 border-t border-border/50 pt-16">
      <div className="mb-10 border-b border-border/50 pb-6">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Architecture</h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          End-to-end pipeline from news ingestion to trade execution.
        </p>
      </div>

      <div className="relative">
        <div className="hidden lg:block">
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-center gap-2">
              <ArchNode node={architectureNodes[0]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[1]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[2]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[3]} />
            </div>

            <div className="flex justify-end pr-24">
              <div className="relative flex h-8 w-px items-center justify-center bg-border">
                <div className="absolute translate-y-4">
                  <ArrowRight className="h-4 w-4 rotate-90 text-muted-foreground" />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-2">
              <ArchNode node={architectureNodes[4]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[5]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[6]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[7]} />
            </div>

            <div className="flex justify-end pr-24">
              <div className="relative flex h-8 w-px items-center justify-center bg-border">
                <div className="absolute translate-y-4">
                  <ArrowRight className="h-4 w-4 rotate-90 text-muted-foreground" />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-2">
              <ArchNode node={architectureNodes[8]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[9]} />
              <FlowArrow />
              <ArchNode node={architectureNodes[10]} />
            </div>
          </div>
        </div>

        <div className="lg:hidden">
          <div className="flex flex-col items-center gap-2">
            {architectureNodes.map((node, index) => (
              <div key={node.id} className="flex flex-col items-center">
                <ArchNode node={node} />
                {index < architectureNodes.length - 1 && (
                  <div className="relative flex h-6 w-px items-center justify-center bg-border">
                    <ArrowRight className="absolute h-4 w-4 translate-y-3 rotate-90 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-16 border-t border-border/50 pt-8">
        <h3 className="mb-6 text-center text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Component details
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {architectureNodes.map((node) => (
            <Card key={node.id} className="border-border/50 bg-card/50">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-secondary">
                    {nodeIcons[node.id]}
                  </div>
                  <div>
                    <h4 className="font-medium">{node.label}</h4>
                    <p className="mt-1 text-sm text-muted-foreground">{node.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function ArchNode({ node }: { node: { id: string; label: string; description: string } }) {
  return (
    <div className="flex w-36 flex-col items-center rounded-lg border border-border/50 bg-card/50 p-4 backdrop-blur-sm">
      <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-secondary">
        {nodeIcons[node.id]}
      </div>
      <span className="text-center text-sm font-medium">{node.label}</span>
    </div>
  )
}

function FlowArrow() {
  return (
    <div className="flex h-px w-8 items-center justify-center bg-border">
      <ArrowRight className="h-4 w-4 text-muted-foreground" />
    </div>
  )
}
