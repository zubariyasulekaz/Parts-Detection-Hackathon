import { TriangleAlert } from 'lucide-react'

interface ConfirmationPanelProps {
  reason?: string
}

export function ConfirmationPanel({ reason }: ConfirmationPanelProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-warning/30 bg-warning-muted/60 px-5 py-4">
      <div className="flex items-center gap-2 text-warning">
        <TriangleAlert className="h-5 w-5" aria-hidden="true" />
        <h2 className="text-sm font-bold">Multiple close matches found</h2>
      </div>
      <p className="text-sm text-foreground/90">
        Please compare the candidates and confirm the correct product before continuing.
      </p>
      {reason && (
        <details className="mt-1 text-xs text-muted">
          <summary className="cursor-pointer font-medium text-muted hover:text-foreground">
            Why confirmation is required
          </summary>
          <p className="mt-1">{reason}</p>
        </details>
      )}
    </div>
  )
}
