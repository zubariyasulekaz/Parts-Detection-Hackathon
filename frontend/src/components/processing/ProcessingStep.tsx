import { Check } from 'lucide-react'
import type { ProcessingStageStatus } from '@/types/identification'

interface ProcessingStepProps {
  label: string
  status: ProcessingStageStatus
}

export function ProcessingStep({ label, status }: ProcessingStepProps) {
  return (
    <div className="relative flex items-center gap-3 py-1.5">
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
