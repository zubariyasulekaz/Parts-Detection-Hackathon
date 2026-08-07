import type { ComponentType } from 'react'

/**
 * What kind of thing each stage is. Worth carrying as data rather than leaving
 * the cards as undifferentiated boxes: at a glance it separates the three
 * *models* from the plumbing around them, which is the point a judge is
 * actually trying to extract from an architecture diagram.
 */
export type NodeKind = 'Input' | 'Processing' | 'AI Model' | 'Vector Search' | 'Database' | 'Signal' | 'Response'

const KIND_CLASS: Record<NodeKind, string> = {
  'AI Model': 'border-accent/40 bg-accent/12 text-accent-soft',
  'Vector Search': 'border-accent-2/40 bg-accent-2/10 text-accent-2',
  Database: 'border-nebula/40 bg-nebula/10 text-[#b3a1ff]',
  Input: 'border-border-strong bg-surface-2 text-muted',
  Processing: 'border-border-strong bg-surface-2 text-muted',
  Signal: 'border-border-strong bg-surface-2 text-muted',
  Response: 'border-success/35 bg-success/10 text-success-soft',
}

interface ArchitectureNodeProps {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  kind: NodeKind
  emphasis?: boolean
  /** 1-based position in the pipeline. */
  step: number
  /** The scroll pulse has reached this stage. Before that the card sits dormant. */
  active: boolean
  /** Anchor side for the connecting path - mirrors the card's layout side. */
  side: 'left' | 'right'
}

export function ArchitectureNode({
  icon: Icon,
  title,
  description,
  kind,
  emphasis = false,
  step,
  active,
  side,
}: ArchitectureNodeProps) {
  const bevel = side === 'left' ? 'clip-bevel' : 'clip-bevel-mirror'

  // The 1px layer beneath the surface that reads as the border. A gradient
  // rather than a flat colour so the two cut edges catch the light differently
  // from the square ones, which is what sells them as bevels rather than as
  // missing corners.
  const edge = active
    ? emphasis
      ? 'bg-linear-to-br from-accent-2 via-accent/60 to-accent/30'
      : 'bg-linear-to-br from-accent-2/60 via-accent/35 to-border-strong'
    : 'bg-border'

  return (
    // Unclipped positioning context. The anchor dot has to be a sibling of the
    // clipped card, not a child - inside it, clip-path would erase it.
    <div className="relative">
      <span
        aria-hidden="true"
        className={`absolute top-1/2 z-10 hidden h-3 w-3 -translate-y-1/2 rounded-full border-2 transition-all duration-700 lg:block ${
          side === 'left' ? '-right-1.5' : '-left-1.5'
        } ${active ? 'border-accent-2 bg-background shadow-glow-accent scale-125' : 'border-border-strong bg-surface'}`}
      />

      <div
        className={`transition-all duration-700 ease-out ${
          active
            ? // Every reached stage glows, not just the Brains. With only the
              // emphasis cards lit the scroll read as "nothing much happened";
              // the arrival of the pulse should be unmistakable on every card.
              'drop-glow-accent'
            : // Dormant: pushed further back than before so the contrast with a
              // lit card is obvious at a glance, while staying legible enough
              // that the un-scrolled page doesn't look broken.
              'translate-y-2 scale-[0.97] opacity-55'
        }`}
      >
        <div className={`${bevel} p-px ${edge} transition-colors duration-700`}>
          <div
            className={`${bevel} relative p-5 transition-colors duration-700 ${
              active && emphasis
                ? 'bg-linear-to-br from-accent-muted/55 via-surface-2 to-surface'
                : active
                  ? 'bg-linear-to-br from-surface-3 via-surface-2 to-surface'
                  : 'bg-surface'
            }`}
          >
            {/* Lit filament across the top edge - the card's own share of the
                pipeline current, so activation reads as power arriving. */}
            <span
              aria-hidden="true"
              className={`absolute inset-x-0 top-0 h-0.5 bg-linear-to-r from-transparent via-accent-2 to-transparent shadow-[0_0_12px_2px_rgba(45,212,191,0.55)] transition-opacity duration-700 ${
                active ? 'opacity-100' : 'opacity-0'
              }`}
            />

            {/* Oversized step number, set into the surface rather than printed
                on it. Sits on the square corner, never the cut one. */}
            <span
              aria-hidden="true"
              className={`absolute -top-1 font-mono text-4xl font-bold text-foreground/8 select-none ${
                side === 'left' ? 'right-3' : 'left-3'
              }`}
            >
              {String(step).padStart(2, '0')}
            </span>

            {/* The step number sits in the gutter beside the content, on
                whichever side the bevel didn't cut. Only from `lg` up - below
                that every card is full width and the layout doesn't mirror. */}
            <div className={`relative flex gap-4 ${side === 'left' ? '' : 'lg:pl-8'}`}>
              <span
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg transition-all duration-700 ${
                  active && emphasis
                    ? 'shadow-glow-accent bg-linear-to-br from-accent-hover to-accent text-white'
                    : active
                      ? 'edge-3d bg-surface-3 text-accent-soft'
                      : 'bg-surface-2 text-subtle'
                }`}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>

              <div className={`min-w-0 ${side === 'left' ? 'lg:pr-8' : ''}`}>
                <span
                  className={`inline-flex rounded-full border px-2 py-0.5 text-[0.65rem] font-bold tracking-[0.12em] uppercase transition-colors duration-700 ${
                    active ? KIND_CLASS[kind] : 'border-border-strong bg-surface-2 text-subtle'
                  }`}
                >
                  {kind}
                </span>
                <p className="mt-2 text-sm leading-snug font-bold text-foreground">{title}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">{description}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
