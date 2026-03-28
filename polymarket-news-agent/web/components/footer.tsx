import Image from "next/image"

export function Footer() {
  return (
    <footer className="border-t border-border/50 bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center">
            <Image
              src="/logo.png"
              alt="Pagent"
              width={654}
              height={232}
              className="h-8 w-auto object-contain object-left opacity-90 sm:h-9"
            />
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Paper execution by default · Not financial advice
          </p>
          <p className="text-sm text-muted-foreground">
            Built for Penn Blockchain Conference 2026
          </p>
        </div>
      </div>
    </footer>
  )
}
