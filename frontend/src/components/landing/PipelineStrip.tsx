import { ArrowRight, Camera, Cpu, Database, Network, PackageSearch } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Tilt3D } from '@/components/common/Tilt3D'
import type { ComponentType } from 'react'

interface PipelineStep {
  icon: ComponentType<{ className?: string }>
  label: string
  detail: string
}

const STEPS: PipelineStep[] = [
  { icon: Camera, label: 'Your Photo', detail: 'Background removed' },
  { icon: Cpu, label: 'Fine-tuned DINOv2', detail: 'Trained on this catalog' },
  { icon: Network, label: 'Visual Fingerprint', detail: '768 numbers, whitened' },
  { icon: Database, label: 'Catalog Match', detail: '13,701 photos searched' },
  { icon: PackageSearch, label: 'Ranked Shortlist', detail: 'Five, with confidence' },
]

export function PipelineStrip() {
  return (
    <div>
      <div className="mb-10 text-center">
        <p className="heading-eyebrow justify-center text-xs font-bold tracking-[0.2em] text-accent-soft uppercase">
          How It Works
        </p>
        <h2 className="mt-3 text-2xl font-bold text-foreground sm:text-3xl">
          One photo. <span className="text-gradient-accent">A ranked shortlist.</span>
        </h2>
      </div>

      <div className="flex items-stretch gap-2 overflow-x-auto px-1 py-3 sm:justify-center">
        {STEPS.map((step, index) => (
          <div key={step.label} className="flex items-center">
            {/* The entry animation stays on this wrapper rather than moving
                onto the tile. `animate-pop-in` uses fill-mode `both`, so its
                final `transform` keeps winning the cascade after the animation
                ends - on the tilting element that would pin it flat forever.
                Animating the scene and tilting the surface keeps the two
                transforms on separate elements, where they can't collide. */}
            <div style={{ animationDelay: `${index * 100}ms` }} className="animate-pop-in h-full">
              <Tilt3D
                near
                glare
                sceneClassName="h-full w-36 shrink-0 sm:w-40"
                className="group shadow-depth flex h-full flex-col items-center gap-2.5 rounded-xl border border-border-strong bg-surface px-3 py-5 text-center hover:border-accent/40 hover:shadow-depth-lift"
              >
                <span className="absolute top-2.5 right-3 font-mono text-xs font-semibold text-subtle">
                  0{index + 1}
                </span>
                {/* No `overflow-hidden` on this tile, so the surface keeps
                    `preserve-3d` and the icon can genuinely stand off the
                    card face instead of only scaling up. */}
                <div className="shadow-glow-accent flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-linear-to-br from-accent to-[#1fa2a2] text-white transition-all duration-300 group-hover:scale-110 group-hover:translate-z-8">
                  <step.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <span className="text-sm leading-tight font-semibold text-foreground">{step.label}</span>
                <span className="text-xs leading-tight text-muted">{step.detail}</span>
              </Tilt3D>
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

      {/* Hand-off, not a dead end. This strip is the teaser; /architecture is
          the same pipeline in full, and it already lists every model and
          datastore with descriptions - so the "Powered by" badge row that used
          to sit here was the same stack said twice, worse. Linking on turns the
          duplication into a funnel. */}
      <div className="mt-10 flex flex-col items-center gap-4 border-t border-border pt-8">
        <p className="max-w-md text-center text-sm text-muted">
          A model trained on this catalog, an index of every product photograph in it, and the
          product database sit behind these five steps.
        </p>
        <Link
          to="/architecture"
          className="group inline-flex items-center gap-2 rounded-lg border border-border-strong bg-surface-2 px-5 py-2.5 text-sm font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-soft"
        >
          See the full architecture
          <ArrowRight
            className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </Link>
      </div>
    </div>
  )
}
