import { Check } from 'lucide-react'
import type { ProcessingStageStatus } from '@/types/identification'

interface ProcessingStepProps {
  label: string
  status: ProcessingStageStatus
}

/**
 * Depth carries the progress state, not just colour: the running stage stands
 * off the page, finished ones sit flat on it, and not-yet-reached ones fall
 * behind it. Requires the `transform-3d` column in `ProcessingPipeline` - on
 * its own this Z offset would collapse to nothing.
 */
const DEPTH_BY_STATUS: Record<ProcessingStageStatus, string> = {
  active: 'translate-z-10 scale-[1.03]',
  complete: 'translate-z-0',
  pending: '-translate-z-8 opacity-70',
}

export function ProcessingStep({ label, status }: ProcessingStepProps) {
  return (
    <div
      className={`relative flex origin-left transform-3d items-center gap-3 py-1.5 transition-all duration-500 ease-out ${DEPTH_BY_STATUS[status]}`}
    >
      <span
        className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
          status === 'complete'
            ? 'shadow-glow-success bg-linear-to-b from-success-soft to-success text-white'
            : status === 'active'
              ? 'shadow-glow-accent animate-glow-pulse bg-linear-to-b from-accent-hover to-accent text-white'
              : 'border-2 border-border-strong bg-surface text-subtle'
        }`}
        aria-hidden="true"
      >
        {status === 'complete' && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
        {status === 'active' && <span className="h-2 w-2 rounded-full bg-white" />}
      </span>
      <span
        className={
          status === 'pending'
            ? 'text-xs text-subtle'
            : status === 'active'
              ? 'text-xs font-semibold text-foreground'
              : 'text-xs text-muted'
        }
      >
        {label}
      </span>
    </div>
  )
}
