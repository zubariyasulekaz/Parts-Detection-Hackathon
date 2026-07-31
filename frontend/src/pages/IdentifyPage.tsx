import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { ScanFrame } from '@/components/common/ScanFrame'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { ProcessingPipeline } from '@/components/processing/ProcessingPipeline'
import { useIdentification } from '@/context/IdentificationContext'
import { PROCESSING_STAGE_DEFINITIONS } from '@/services/identificationService'

export function IdentifyPage() {
  const navigate = useNavigate()
  const { status, pendingFile, uploadedImageUrl, currentStage, error, runIdentification, reset } = useIdentification()
  const hasStarted = useRef(false)

  useEffect(() => {
    if (!pendingFile || hasStarted.current) return
    hasStarted.current = true
    runIdentification()
      .then(() => navigate('/results'))
      .catch(() => {
        /* handled via status === 'error' below */
      })
  }, [pendingFile, runIdentification, navigate])

  function handleRetry() {
    hasStarted.current = false
    runIdentification()
      .then(() => navigate('/results'))
      .catch(() => {
        hasStarted.current = false
      })
  }

  function handleStartOver() {
    reset()
    navigate('/')
  }

  if (!pendingFile) {
    return (
      <PageContainer className="py-20">
        <EmptyState
          title="No image is queued for identification"
          description="Start from the landing page to upload a part photo or try the sample image."
          action={
            <button
              type="button"
              onClick={() => navigate('/')}
              className="mt-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              Go to Upload
            </button>
          }
        />
      </PageContainer>
    )
  }

  const isProcessing = status === 'processing'
  const isDone = status === 'success' || status === 'ambiguous'
  const stageIndex = currentStage ? PROCESSING_STAGE_DEFINITIONS.findIndex((definition) => definition.key === currentStage) : -1
  const activeDefinition = PROCESSING_STAGE_DEFINITIONS[Math.min(stageIndex + 1, PROCESSING_STAGE_DEFINITIONS.length - 1)]
  const progressPercent = isDone ? 100 : Math.round(((stageIndex + 1) / PROCESSING_STAGE_DEFINITIONS.length) * 100)
  const liveLabel = isDone ? 'MATCH LOCKED' : isProcessing ? activeDefinition.activeLabel.toUpperCase() : undefined

  return (
    <div className="relative overflow-hidden">
      <AmbientBackground className="opacity-70" />
      <PageContainer className="relative py-6">
        <div className="mx-auto flex max-w-xl flex-col items-center gap-4">
          <div className="shadow-glow-accent relative h-40 w-40 overflow-hidden rounded-2xl border border-accent/20 bg-surface p-4">
            {uploadedImageUrl && (
              <img src={uploadedImageUrl} alt="Uploaded part" className="h-full w-full object-contain" />
            )}
            <ScanFrame active={isProcessing} label={liveLabel} labelTone={isDone ? 'success' : 'accent'} />
          </div>

          <div className="w-full max-w-55">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
              <div
                className="shadow-glow-accent h-full rounded-full bg-linear-to-r from-accent-hover to-accent transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="mt-1 text-center font-mono text-[11px] text-subtle">{progressPercent}% complete</p>
          </div>

          <div className="text-center">
            <h1 className="text-lg font-bold text-foreground">Analyzing your part</h1>
            <p className="mt-0.5 text-xs text-muted">
              Running the image through PartPilot&apos;s classification and similarity-search pipeline.
            </p>
          </div>

          {status === 'error' ? (
            <>
              <ErrorState message={error ?? 'Identification failed. Please try again.'} onRetry={handleRetry} />
              <button
                type="button"
                onClick={handleStartOver}
                className="text-sm font-medium text-muted underline-offset-4 hover:text-foreground hover:underline"
              >
                Start over with a new image
              </button>
            </>
          ) : (
            <div className="shadow-card animate-fade-in w-full rounded-xl border border-border bg-surface px-5 py-1">
              <ProcessingPipeline currentStage={currentStage} isComplete={status === 'success' || status === 'ambiguous'} />
            </div>
          )}
        </div>
      </PageContainer>
    </div>
  )
}
