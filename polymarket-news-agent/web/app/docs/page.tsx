import Link from "next/link"
import { ArchitectureSection } from "@/components/guide/architecture-section"
import { HowItWorksSection } from "@/components/guide/how-it-works-section"
import { ReferenceSection } from "@/components/guide/reference-section"

const toc = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#architecture", label: "Architecture" },
  { href: "#reference", label: "Reference" },
] as const

export default function GuidePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <header className="mb-12 text-center lg:text-left">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">Docs</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground lg:mx-0">
          How the agent thinks and trades, how the system is wired, and how to run it locally.
        </p>
      </header>

      <nav
        aria-label="On this page"
        className="mb-14 flex flex-wrap justify-center gap-2 border-y border-border/50 py-4 lg:justify-start"
      >
        {toc.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-md border border-border/50 bg-secondary/40 px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:border-foreground/20 hover:text-foreground"
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <HowItWorksSection />
      <ArchitectureSection />
      <ReferenceSection />
    </div>
  )
}
