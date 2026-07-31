import { Camera, Cpu, Database, Network, PackageSearch } from 'lucide-react'
import type { ComponentType } from 'react'

interface PipelineStep {
  icon: ComponentType<{ className?: string }>
  label: string
}

const STEPS: PipelineStep[] = [
  { icon: Camera, label: 'Image' },
  { icon: Cpu, label: 'Category Classification' },
  { icon: Network, label: 'Visual Embedding' },
  { icon: Database, label: 'Catalog Match' },
  { icon: PackageSearch, label: 'Product Intelligence' },
]

const STACK_BADGES = ['Fine-tuned Vision Model', 'OpenCLIP', 'FAISS', 'PostgreSQL']

export function PipelineStrip() {
  return (
    <div>
      <p className="mb-7 text-center text-xs font-semibold tracking-[0.2em] text-muted uppercase">How It Works</p>

      <div className="flex items-start gap-1 overflow-x-auto px-1 py-3 sm:justify-center sm:gap-0">
        {STEPS.map((step, index) => (
          <div key={step.label} className="flex items-center">
            <div
              style={{ animationDelay: `${index * 100}ms` }}
              className="animate-pop-in group flex w-24 flex-col items-center gap-3 text-center sm:w-28"
            >
              <div className="shadow-glow-accent flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-linear-to-b from-accent-hover to-accent text-white transition-transform duration-300 group-hover:-translate-y-1 group-hover:scale-110">
                <step.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <span className="text-[11px] leading-tight font-semibold tracking-wide text-muted uppercase transition-colors group-hover:text-foreground">
                {step.label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className="mx-1 h-px w-6 shrink-0 bg-linear-to-r from-accent/60 to-accent/10 sm:w-10"
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </div>

      <div className="mt-9 flex flex-wrap items-center justify-center gap-x-3 gap-y-3 border-t border-border pt-7">
        {STACK_BADGES.map((badge) => (
          <span
            key={badge}
            className="rounded-full border border-border-strong bg-surface-2 px-3.5 py-1.5 text-sm font-semibold text-foreground/90"
          >
            {badge}
          </span>
        ))}
      </div>
    </div>
  )
}
