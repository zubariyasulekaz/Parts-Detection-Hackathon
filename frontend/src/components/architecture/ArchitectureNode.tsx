import type { ComponentType } from 'react'

interface ArchitectureNodeProps {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  emphasis?: boolean
}

export function ArchitectureNode({ icon: Icon, title, description, emphasis = false }: ArchitectureNodeProps) {
  return (
    <div
      className={`flex w-full max-w-lg items-start gap-4 rounded-xl border px-5 py-4 transition-all ${
        emphasis ? 'shadow-glow-accent border-accent/40 bg-accent-muted/20' : 'shadow-card border-border bg-surface'
      }`}
    >
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
          emphasis ? 'bg-linear-to-b from-accent-hover to-accent text-white' : 'bg-surface-2 text-accent-hover'
        }`}
      >
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm font-bold text-foreground">{title}</p>
        <p className="mt-0.5 text-xs text-muted">{description}</p>
      </div>
    </div>
  )
}
