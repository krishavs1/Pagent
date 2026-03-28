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
import { envVars, resources } from "@/lib/mock-data"
import { ExternalLink, Book, Github, Code, BarChart3, Check, X } from "lucide-react"
import Link from "next/link"

const resourceIcons: Record<string, React.ReactNode> = {
  book: <Book className="h-5 w-5" />,
  github: <Github className="h-5 w-5" />,
  code: <Code className="h-5 w-5" />,
  chart: <BarChart3 className="h-5 w-5" />,
}

export function ReferenceSection() {
  return (
    <section id="reference" className="scroll-mt-24 border-t border-border/50 pt-16">
      <div className="mb-10 border-b border-border/50 pb-6">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Reference</h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Links, environment variables, local setup, and HTTP endpoints for the dashboard API.
        </p>
      </div>

      <div className="mb-12">
        <h3 className="mb-6 text-xl font-semibold">Quick links</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {resources.map((resource) => (
            <Link
              key={resource.label}
              href={resource.url}
              target={resource.url.startsWith("http") ? "_blank" : undefined}
              rel={resource.url.startsWith("http") ? "noopener noreferrer" : undefined}
              className="group"
            >
              <Card className="border-border/50 bg-card/50 transition-colors hover:border-foreground/20 hover:bg-card">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary text-foreground transition-colors group-hover:bg-foreground group-hover:text-background">
                    {resourceIcons[resource.icon]}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{resource.label}</p>
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      <div className="mb-12">
        <h3 className="mb-6 text-xl font-semibold">Environment variables</h3>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/50 hover:bg-transparent">
                    <TableHead className="w-[250px]">Variable</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-[100px] text-center">Required</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {envVars.map((envVar) => (
                    <TableRow key={envVar.key} className="border-border/50">
                      <TableCell className="font-mono text-sm">{envVar.key}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{envVar.description}</TableCell>
                      <TableCell className="text-center">
                        {envVar.required ? (
                          <Check className="mx-auto h-4 w-4 text-positive" />
                        ) : (
                          <X className="mx-auto h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mb-12">
        <h3 className="mb-6 text-xl font-semibold">Quick start (local)</h3>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="space-y-4 p-6">
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Python agent + API</p>
              <div className="space-y-2 rounded-lg bg-secondary/50 p-4">
                <code className="block font-mono text-sm">cd polymarket-news-agent</code>
                <code className="block font-mono text-sm">python -m venv .venv &amp;&amp; source .venv/bin/activate</code>
                <code className="block font-mono text-sm">pip install -r requirements.txt</code>
                <code className="block font-mono text-sm">uvicorn agent_api:app --reload --port 8765</code>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Next.js dashboard</p>
              <div className="space-y-2 rounded-lg bg-secondary/50 p-4">
                <code className="block font-mono text-sm">cd polymarket-news-agent/web</code>
                <code className="block font-mono text-sm">npm install</code>
                <code className="block font-mono text-sm">npm run dev</code>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Optional: copy <code className="rounded bg-secondary px-1 font-mono text-xs">.env.example</code> to{" "}
                <code className="rounded bg-secondary px-1 font-mono text-xs">.env.local</code> and set{" "}
                <code className="rounded bg-secondary px-1 font-mono text-xs">NEXT_PUBLIC_AGENT_API_URL</code> if the
                API is not on port 8765.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div id="api-reference" className="mb-12 scroll-mt-24">
        <h3 className="mb-6 text-xl font-semibold">Dashboard API</h3>
        <p className="mb-4 text-sm text-muted-foreground">
          Served by <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">agent_api.py</code> (FastAPI).
          The live dashboard calls these endpoints; some routes are illustrative until fully wired.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-positive/30 bg-positive/20 text-positive">
                  GET
                </Badge>
                <CardTitle className="font-mono text-sm">/api/dashboard</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Aggregated stats, signals, positions, and sparkline data for the Live Dashboard.
              </p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-positive/30 bg-positive/20 text-positive">
                  GET
                </Badge>
                <CardTitle className="font-mono text-sm">/api/backtest/*</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Summary, equity curve, replay, and log tail for the Backtest page.
              </p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-positive/30 bg-positive/20 text-positive">
                  GET
                </Badge>
                <CardTitle className="font-mono text-sm">/api/signals</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Recent trading signals with confidence and matched markets (when implemented).
              </p>
            </CardContent>
          </Card>
          <Card className="border-border/50 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-positive/30 bg-positive/20 text-positive">
                  GET
                </Badge>
                <CardTitle className="font-mono text-sm">/api/positions</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Open positions and PnL (when implemented).
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}
