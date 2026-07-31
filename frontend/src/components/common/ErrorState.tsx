import { TriangleAlert } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorState({ title = 'Something went wrong', message, onRetry, retryLabel = 'Try again' }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="shadow-card flex flex-col items-center gap-3 rounded-xl border border-danger/30 bg-danger-muted/40 px-8 py-16 text-center"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-muted text-danger">
        <TriangleAlert className="h-6 w-6" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      <p className="max-w-sm text-sm text-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="shadow-glow-accent mt-2 rounded-lg bg-linear-to-b from-accent-hover to-accent px-4 py-2 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
        >
          {retryLabel}
        </button>
      )}
    </div>
  )
}
