import { Camera, Cpu, Database, Network, PackageSearch } from 'lucide-react'
import type { ComponentType } from 'react'

interface PipelineStep {
  icon: ComponentType<{ className?: string }>
  label: string
  detail: string
}

const STEPS: PipelineStep[] = [
  { icon: Camera, label: 'Image', detail: 'Background removed' },
  { icon: Cpu, label: 'Classification', detail: 'EfficientNet category' },
  { icon: Network, label: 'Visual Embedding', detail: 'DINOv2 / OpenCLIP' },
  { icon: Database, label: 'Catalog Match', detail: 'FAISS similarity' },
  { icon: PackageSearch, label: 'Product Intelligence', detail: 'Fitment + alternatives' },
]

const STACK_BADGES = ['EfficientNet', 'DINOv2', 'OpenCLIP', 'FAISS', 'PostgreSQL']

export function PipelineStrip() {
  return (
    <div>
      <div className="mb-10 text-center">
        <p className="heading-eyebrow justify-center text-xs font-bold tracking-[0.2em] text-accent-soft uppercase">
          How It Works
        </p>
        <h2 className="mt-3 text-2xl font-bold text-foreground sm:text-3xl">
          Four models. <span className="text-gradient-accent">One answer.</span>
        </h2>
      </div>

      <div className="flex items-stretch gap-2 overflow-x-auto px-1 py-3 sm:justify-center">
        {STEPS.map((step, index) => (
          <div key={step.label} className="flex items-center">
            <div
              style={{ animationDelay: `${index * 100}ms` }}
              className="animate-pop-in group shadow-card relative flex h-full w-36 shrink-0 flex-col items-center gap-2.5 rounded-xl border border-border-strong bg-surface px-3 py-5 text-center transition-all hover:-translate-y-1 hover:border-accent/40 sm:w-40"
            >
              <span className="absolute top-2.5 right-3 font-mono text-xs font-semibold text-subtle">
                0{index + 1}
              </span>
              <div className="shadow-glow-accent flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-linear-to-br from-accent to-[#1fa2a2] text-white transition-transform duration-300 group-hover:scale-110">
                <step.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <span className="text-sm leading-tight font-semibold text-foreground">{step.label}</span>
              <span className="text-xs leading-tight text-muted">{step.detail}</span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className="h-0.5 w-4 shrink-0 rounded-full bg-linear-to-r from-accent/70 to-accent-2/40 sm:w-7"
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </div>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-x-2.5 gap-y-3 border-t border-border pt-7">
        <span className="mr-2 text-xs font-bold tracking-[0.2em] text-subtle uppercase">Powered by</span>
        {STACK_BADGES.map((badge) => (
          <span
            key={badge}
            className="inline-flex items-center gap-2 rounded-full border border-border-strong bg-surface-2 px-3.5 py-1.5 font-mono text-xs font-semibold text-foreground/90"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-linear-to-r from-accent to-accent-2" aria-hidden="true" />
            {badge}
          </span>
        ))}
      </div>
    </div>
  )
}
