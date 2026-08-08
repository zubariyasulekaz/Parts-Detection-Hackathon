import { CircleCheck, Info, TriangleAlert } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

export type StatusVariant = 'success' | 'warning' | 'info' | 'neutral'

const VARIANT_STYLES: Record<StatusVariant, string> = {
  success: 'shadow-glow-success border-success/30 bg-success-muted text-success-soft',
  warning: 'shadow-glow-warning border-warning/30 bg-warning-muted text-warning-soft',
  info: 'shadow-glow-accent border-accent/30 bg-accent-muted text-accent-soft',
  neutral: 'border-border-strong bg-surface-2 text-muted',
}

const VARIANT_ICONS: Record<StatusVariant, ComponentType<{ className?: string }>> = {
  success: CircleCheck,
  warning: TriangleAlert,
  info: Info,
  neutral: Info,
}

interface StatusBadgeProps {
  variant: StatusVariant
  children: ReactNode
  className?: string
}

/** Icon + label together carry status - never color alone. */
export function StatusBadge({ variant, children, className = '' }: StatusBadgeProps) {
  const Icon = VARIANT_ICONS[variant]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${VARIANT_STYLES[variant]} ${className}`}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {children}
    </span>
  )
}
