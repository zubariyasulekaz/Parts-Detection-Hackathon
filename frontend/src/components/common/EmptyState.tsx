import type { ComponentType, ReactNode } from 'react'

interface EmptyStateProps {
  icon?: ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="shadow-card flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-surface px-8 py-16 text-center">
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-muted">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
      )}
      <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      {description && <p className="max-w-sm text-sm text-muted">{description}</p>}
      {action}
    </div>
  )
}
