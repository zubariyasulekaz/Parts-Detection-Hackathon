import { PROCESSING_STAGE_DEFINITIONS } from '@/services/identificationService'
import type { ProcessingStageKey, ProcessingStageStatus } from '@/types/identification'
import { ProcessingStep } from './ProcessingStep'

interface ProcessingPipelineProps {
  /** The most recently completed stage, or null before the first one finishes. */
  currentStage: ProcessingStageKey | null
  isComplete: boolean
}

export function ProcessingPipeline({ currentStage, isComplete }: ProcessingPipelineProps) {
  const lastCompletedIndex = currentStage
    ? PROCESSING_STAGE_DEFINITIONS.findIndex((definition) => definition.key === currentStage)
    : -1

  return (
    <div className="relative" aria-live="polite">
      <div
        aria-hidden="true"
        className="absolute top-3.5 bottom-3.5 left-3.5 w-px bg-linear-to-b from-accent/50 via-border-strong to-border"
      />
      <div className="relative flex flex-col">
        {PROCESSING_STAGE_DEFINITIONS.map((definition, index) => {
          const status: ProcessingStageStatus = isComplete
            ? 'complete'
            : index <= lastCompletedIndex
              ? 'complete'
              : index === lastCompletedIndex + 1
                ? 'active'
                : 'pending'
          const label = status === 'complete' ? definition.completedLabel : definition.activeLabel
          return <ProcessingStep key={definition.key} label={label} status={status} />
        })}
      </div>
    </div>
  )
}
