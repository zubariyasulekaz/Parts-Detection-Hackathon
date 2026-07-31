import type { ComponentType } from 'react'

interface CapabilityBadgeProps {
  icon: ComponentType<{ className?: string }>
  label: string
}

export function CapabilityBadge({ icon: Icon, label }: CapabilityBadgeProps) {
  return (
    <div className="flex items-center gap-2.5 text-sm font-medium text-muted">
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-accent-soft ring-1 ring-accent/25">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      {label}
    </div>
  )
}
