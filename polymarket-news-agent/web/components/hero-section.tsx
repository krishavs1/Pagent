"use client"

import Link from "next/link"
import { ArrowRight, Zap, Brain, Target } from "lucide-react"
import { Button } from "@/components/ui/button"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 grid-pattern opacity-50" />
      
      <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8 lg:py-40">
        <div className="flex flex-col items-center text-center">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border/50 bg-secondary/50 px-4 py-1.5 text-sm">
            <span className="h-2 w-2 rounded-full bg-positive animate-pulse" />
            <span className="text-muted-foreground">Paper trading on Polymarket</span>
          </div>

          {/* Headline */}
          <h1 className="max-w-4xl text-balance text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            Autonomous News-Trading Agent for{" "}
            <span className="text-positive">Prediction Markets</span>
          </h1>

          {/* Subheadline */}
          <p className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground sm:text-xl">
            Ingest real-time news feeds. Run Bayesian belief updates. Execute with
            risk-controlled precision. All on autopilot.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col gap-4 sm:flex-row">
            <Button asChild size="lg" className="gap-2">
              <Link href="/dashboard">
                View Live Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/docs">Docs</Link>
            </Button>
          </div>
        </div>

        {/* Pipeline Diagram */}
        <div className="mt-20 lg:mt-28">
          <div className="mb-8 text-center">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              The Pipeline
            </h2>
          </div>
          <div className="flex flex-col items-center justify-center gap-4 md:flex-row md:gap-0">
            <PipelineStep
              icon={<Zap className="h-6 w-6" />}
              title="Ingest"
              description="RSS, official feeds, X posts"
            />
            <PipelineArrow />
            <PipelineStep
              icon={<Brain className="h-6 w-6" />}
              title="Score"
              description="Bayesian belief updates"
            />
            <PipelineArrow />
            <PipelineStep
              icon={<Target className="h-6 w-6" />}
              title="Execute"
              description="Risk-controlled orders"
            />
          </div>
        </div>

        {/* Trust Row */}
        <div className="mt-20 border-t border-border/50 pt-12">
          <p className="mb-8 text-center text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Built on
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16">
            <TrustBadge label="Polymarket" sublabel="CLOB API" />
            <TrustBadge label="Claude" sublabel="Signal classifier" />
            <TrustBadge label="Python" sublabel="Agent runtime" />
            <TrustBadge label="Next.js" sublabel="Dashboard" />
          </div>
        </div>
      </div>
    </section>
  )
}

function PipelineStep({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-border/50 bg-card/50 p-6 backdrop-blur-sm md:w-56">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-md bg-secondary text-foreground">
        {icon}
      </div>
      <h3 className="mb-1 font-semibold">{title}</h3>
      <p className="text-center text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

function PipelineArrow() {
  return (
    <div className="hidden h-px w-12 bg-border md:block" />
  )
}

function TrustBadge({ label, sublabel }: { label: string; sublabel: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="font-semibold">{label}</span>
      <span className="text-sm text-muted-foreground">{sublabel}</span>
    </div>
  )
}
